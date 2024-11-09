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

def calculate_occupancy_rate():
    total_rooms = Room.query.count()
    if total_rooms == 0:
        return 0
    occupied_rooms = Booking.query.filter(
        Booking.status == 'confirmed',
        Booking.check_in <= datetime.now().date(),
        Booking.check_out > datetime.now().date()
    ).count()
    return (occupied_rooms / total_rooms) * 100

@app.route('/api/check-room-availability', methods=['POST'])
def check_room_availability():
    try:
        data = request.json
        if not data or 'check_in' not in data or 'check_out' not in data:
            return jsonify({'error': 'Missing required data'}), 400

        check_in = datetime.strptime(data.get('check_in'), '%Y-%m-%d').date()
        check_out = datetime.strptime(data.get('check_out'), '%Y-%m-%d').date()
        room_id = data.get('room_id')
        
        # Validate dates
        if check_in >= check_out:
            return jsonify({'error': 'Check-out date must be after check-in date'}), 400
            
        if check_in < datetime.now().date():
            return jsonify({'error': 'Check-in date cannot be in the past'}), 400
        
        # Get all rooms that are available
        all_rooms = Room.query.filter_by(available=True).all()
        
        # Count booked rooms for each room type during the date range
        booked_rooms_count = db.session.query(
            Booking.room_id,
            func.count(Booking.id).label('booking_count')
        ).filter(
            Booking.status.in_(['confirmed', 'pending']),
            Booking.check_in < check_out,
            Booking.check_out > check_in
        ).group_by(Booking.room_id).all()
        
        # Create a dictionary of booked room counts
        booked_counts = {room_id: count for room_id, count in booked_rooms_count}
        
        if room_id:
            # Single room availability check
            room = Room.query.get(room_id)
            if not room or not room.available:
                return jsonify({'available': False, 'error': 'Room not available'})
            
            booked_count = booked_counts.get(room.id, 0)
            available_rooms_count = max(0, room.total_rooms - booked_count)
            
            if available_rooms_count <= 0:
                return jsonify({'available': False, 'error': 'No rooms available for selected dates'})
            
            return jsonify({
                'available': True,
                'rooms_left': available_rooms_count
            })
        else:
            # Multiple rooms availability check
            available_rooms = []
            for room in all_rooms:
                booked_count = booked_counts.get(room.id, 0)
                available_rooms_count = max(0, room.total_rooms - booked_count)
                
                if available_rooms_count > 0:
                    available_rooms.append({
                        'id': room.id,
                        'rooms_left': available_rooms_count
                    })
            
            return jsonify({
                'available_rooms': [room['id'] for room in available_rooms],
                'rooms_count': {str(room['id']): room['rooms_left'] for room in available_rooms},
                'total_rooms': len(all_rooms),
                'available_count': len(available_rooms)
            })
        
    except ValueError as e:
        app.logger.error(f"Date parsing error: {str(e)}")
        return jsonify({'error': 'Invalid date format'}), 400
    except Exception as e:
        app.logger.error(f"Room availability check error: {str(e)}")
        return jsonify({'error': 'Error checking room availability'}), 500

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

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Get statistics for dashboard
    stats = {
        'total_rooms': Room.query.count(),
        'active_bookings': Booking.query.filter_by(status='confirmed').count(),
        'daily_revenue': db.session.query(func.sum(Booking.amount_paid))
            .filter(Booking.payment_status == 'completed')
            .filter(func.date(Booking.created_at) == datetime.now().date()).scalar() or 0,
        'occupancy_rate': calculate_occupancy_rate()
    }
    
    # Get recent activity
    recent_activity = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                         stats=stats,
                         recent_activity=recent_activity)

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin/rooms')
@admin_required
def admin_rooms():
    rooms = Room.query.all()
    return render_template('admin/rooms.html', rooms=rooms)

@app.route('/admin/rooms/add', methods=['POST'])
@admin_required
def admin_add_room():
    try:
        room = Room()
        room.name = request.form['name']
        room.room_type = request.form['room_type']
        room.price = float(request.form['price'])
        room.capacity = int(request.form['capacity'])
        room.total_rooms = int(request.form.get('total_rooms', 1))
        room.image_url = request.form['image_url']
        room.description = request.form['description']
        room.available = bool(request.form.get('available', True))
        
        db.session.add(room)
        db.session.commit()
        flash('Room added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error adding room. Please try again.', 'error')
    return redirect(url_for('admin_rooms'))

@app.route('/admin/rooms/<int:room_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        try:
            room.name = request.form['name']
            room.room_type = request.form['room_type']
            room.price = float(request.form['price'])
            room.capacity = int(request.form['capacity'])
            room.total_rooms = int(request.form.get('total_rooms', 1))
            room.image_url = request.form['image_url']
            room.description = request.form['description']
            room.available = bool(request.form.get('available'))
            db.session.commit()
            flash('Room updated successfully!', 'success')
            return redirect(url_for('admin_rooms'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating room. Please try again.', 'error')
    return render_template('admin/edit_room.html', room=room)

@app.route('/admin/rooms/<int:room_id>/delete', methods=['POST'])
@admin_required
def admin_delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    try:
        db.session.delete(room)
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e))

@app.route('/admin/bookings/<int:booking_id>/update', methods=['POST'])
@admin_required
def admin_update_booking(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        data = request.get_json()
        new_status = data.get('status')
        if new_status:
            booking.status = new_status
            db.session.commit()
            
            if send_booking_status_update(booking):
                return jsonify({'success': True, 'message': 'Booking updated and notification sent'})
            else:
                return jsonify({'success': True, 'message': 'Booking updated but notification failed'})
        
        return jsonify({'success': False, 'error': 'No status provided'})
    except Exception as e:
        app.logger.error(f"Error updating booking: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/bookings/<int:booking_id>/cancel', methods=['POST'])
@admin_required
def admin_cancel_booking(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        if booking.status == 'cancelled':
            return jsonify({'success': False, 'error': 'Booking is already cancelled'})
            
        booking.status = 'cancelled'
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = request.form.get('reason', 'Cancelled by admin')
        
        if booking.payment_status == 'completed':
            try:
                refund = process_refund(booking.id)
                if refund:
                    booking.refund_status = 'completed'
            except Exception as e:
                app.logger.error(f"Refund processing error: {str(e)}")
                booking.refund_status = 'failed'
        
        db.session.commit()
        
        if send_booking_status_update(booking):
            return jsonify({'success': True, 'message': 'Booking cancelled and notification sent'})
        else:
            return jsonify({'success': True, 'message': 'Booking cancelled but notification failed'})
            
    except Exception as e:
        app.logger.error(f"Error cancelling booking: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
