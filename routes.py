from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import Room, Booking, Contact, User, Review
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
from payment import create_payment_intent, confirm_payment, process_refund
from utils import admin_required
from email_utils import send_booking_confirmation, send_booking_status_update
import stripe
from sqlalchemy import func, and_, not_

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Get statistics
    stats = {
        'total_rooms': Room.query.count(),
        'active_bookings': Booking.query.filter_by(status='confirmed').count(),
        'daily_revenue': db.session.query(func.sum(Room.price)).join(Booking).filter(
            Booking.status == 'confirmed',
            Booking.check_in <= datetime.now().date(),
            Booking.check_out > datetime.now().date()
        ).scalar() or 0,
        'occupancy_rate': (Booking.query.filter_by(status='confirmed')
                          .filter(Booking.check_in <= datetime.now().date())
                          .filter(Booking.check_out > datetime.now().date())
                          .count() / max(Room.query.count(), 1)) * 100
    }
    
    # Get recent activity
    recent_activity = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_activity=recent_activity)

@app.route('/admin/rooms')
@login_required
@admin_required
def admin_rooms():
    rooms = Room.query.all()
    return render_template('admin/rooms.html', rooms=rooms)

@app.route('/admin/rooms/add', methods=['POST'])
@login_required
@admin_required
def admin_add_room():
    try:
        room = Room()
        room.name = request.form.get('name')
        room.description = request.form.get('description')
        room.price = float(request.form.get('price', 0))
        room.capacity = int(request.form.get('capacity', 1))
        room.room_type = request.form.get('room_type')
        room.total_rooms = int(request.form.get('total_rooms', 1))
        room.image_url = request.form.get('image_url')
        room.available = bool(request.form.get('available'))
        room.amenities = ['Air Conditioning', 'Free Wi-Fi', 'LED TV', 'Attached Bathroom']
        
        db.session.add(room)
        db.session.commit()
        flash('Room added successfully', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding room: {str(e)}")
        flash('Error adding room', 'error')
    return redirect(url_for('admin_rooms'))

@app.route('/admin/rooms/<int:room_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        try:
            room.name = request.form.get('name')
            room.description = request.form.get('description')
            room.price = float(request.form.get('price', 0))
            room.capacity = int(request.form.get('capacity', 1))
            room.room_type = request.form.get('room_type')
            room.total_rooms = int(request.form.get('total_rooms', 1))
            room.image_url = request.form.get('image_url')
            room.available = bool(request.form.get('available'))
            db.session.commit()
            flash('Room updated successfully', 'success')
            return redirect(url_for('admin_rooms'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating room: {str(e)}")
            flash('Error updating room', 'error')
    return render_template('admin/edit_room.html', room=room)

@app.route('/admin/rooms/<int:room_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_room(room_id):
    try:
        room = Room.query.get_or_404(room_id)
        db.session.delete(room)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting room: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/bookings')
@login_required
@admin_required
def admin_bookings():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin/bookings/<int:booking_id>/update', methods=['POST'])
@login_required
@admin_required
def admin_update_booking(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['confirmed', 'cancelled']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
            
        booking.status = new_status
        if new_status == 'cancelled':
            booking.cancelled_at = datetime.utcnow()
            
        db.session.commit()
        
        # Send email notification
        if send_booking_status_update(booking):
            return jsonify({'success': True})
        else:
            return jsonify({'success': True, 'warning': 'Email notification failed'})
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating booking: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
@login_required
def booking(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        # Handle booking submission
        return redirect(url_for('my_bookings'))
    return render_template('booking.html', room=room)

@app.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Verify booking belongs to user
        if booking.user_id != current_user.id:
            flash('Unauthorized access', 'error')
            return redirect(url_for('my_bookings'))
        
        # Check if booking can be cancelled
        if not booking.can_cancel:
            flash('This booking cannot be cancelled', 'error')
            return redirect(url_for('my_bookings'))
        
        booking.status = 'cancelled'
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = request.form.get('cancellation_reason')
        
        # Process refund if payment was made
        if booking.payment_status == 'completed':
            try:
                refund = process_refund(booking.payment_intent_id)
                if refund:
                    booking.refund_status = 'completed'
                    booking.refund_amount = booking.refund_amount_available
            except Exception as e:
                app.logger.error(f"Refund processing error: {str(e)}")
                booking.refund_status = 'failed'
        
        db.session.commit()
        
        # Send cancellation notification
        if send_booking_status_update(booking):
            flash('Booking cancelled successfully. Check your email for details.', 'success')
        else:
            flash('Booking cancelled but email notification failed.', 'warning')
            
        return redirect(url_for('my_bookings'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error cancelling booking: {str(e)}")
        flash('Error cancelling booking. Please try again.', 'error')
        return redirect(url_for('my_bookings'))

@app.route('/rooms')
def rooms():
    """Display all available rooms with filtering capability"""
    rooms = Room.query.filter_by(available=True).all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/room/<int:room_id>')
def room_detail(room_id):
    room = Room.query.get_or_404(room_id)
    reviews = Review.query.filter_by(room_id=room_id).order_by(Review.created_at.desc()).all()
    can_review = False
    if current_user.is_authenticated:
        completed_bookings = Booking.query.filter_by(
            user_id=current_user.id,
            room_id=room_id,
            status='confirmed'
        ).filter(Booking.check_out < datetime.now().date()).all()
        can_review = len(completed_bookings) > 0
    return render_template('room_detail.html', room=room, reviews=reviews, can_review=can_review)

@app.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)
