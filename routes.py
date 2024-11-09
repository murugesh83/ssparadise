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
        if not data or 'room_id' not in data or 'check_in' not in data or 'check_out' not in data:
            return jsonify({'available': False, 'error': 'Missing required data'}), 400

        room_id = data.get('room_id')
        check_in = datetime.strptime(data.get('check_in'), '%Y-%m-%d').date()
        check_out = datetime.strptime(data.get('check_out'), '%Y-%m-%d').date()
        
        app.logger.info(f"Checking availability for room {room_id} between {check_in} and {check_out}")
        
        # Validate dates
        if check_in >= check_out:
            return jsonify({'available': False, 'error': 'Check-out date must be after check-in date'})
        
        # Check if room exists and is available
        room = Room.query.get(room_id)
        if not room or not room.available:
            return jsonify({'available': False, 'error': 'Room not available'})
            
        # Check for conflicting bookings
        conflicting_booking = Booking.query.filter(
            Booking.room_id == room_id,
            Booking.status.in_(['confirmed', 'pending']),
            Booking.check_in < check_out,
            Booking.check_out > check_in
        ).first()
        
        if conflicting_booking:
            app.logger.info(f"Found conflicting booking: {conflicting_booking.id}")
        
        return jsonify({'available': not bool(conflicting_booking)})
        
    except ValueError as e:
        app.logger.error(f"Date parsing error: {str(e)}")
        return jsonify({'available': False, 'error': 'Invalid date format'}), 400
    except Exception as e:
        app.logger.error(f"Room availability check error: {str(e)}")
        return jsonify({'available': False, 'error': 'Error checking availability'}), 500

@app.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)

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

@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
@login_required
def booking(room_id):
    """Handle room booking"""
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        try:
            payment_option = request.form.get('payment_option', 'now')
            booking = Booking(
                room_id=room_id,
                user_id=current_user.id,
                guest_name=request.form['name'],
                guest_email=request.form['email'],
                check_in=datetime.strptime(request.form['check_in'], '%Y-%m-%d'),
                check_out=datetime.strptime(request.form['check_out'], '%Y-%m-%d'),
                guests=int(request.form['guests']),
                payment_option=payment_option,
                status='pending'
            )
            db.session.add(booking)
            db.session.commit()

            if payment_option == 'now':
                payment_intent = create_payment_intent(booking.id)
                if send_booking_confirmation(booking):
                    flash('Booking confirmation email sent.', 'success')
                else:
                    flash('Could not send confirmation email, but your booking is confirmed.', 'warning')
                
                return render_template('payment.html', 
                                    booking=booking,
                                    client_secret=payment_intent.client_secret,
                                    publishable_key=app.config['STRIPE_PUBLISHABLE_KEY'])
            else:
                booking.status = 'pending_payment'
                db.session.commit()
                
                if send_booking_confirmation(booking):
                    flash('Booking confirmation email sent.', 'success')
                else:
                    flash('Could not send confirmation email, but your booking is confirmed.', 'warning')
                
                flash('Booking confirmed! Please complete your payment before check-in.', 'success')
                return redirect(url_for('my_bookings'))

        except Exception as e:
            db.session.rollback()
            flash('Error processing booking. Please try again.', 'error')
            app.logger.error(f"Booking error: {str(e)}")
    return render_template('booking.html', room=room)

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