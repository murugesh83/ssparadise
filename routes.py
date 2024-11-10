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

@app.route('/api/check-room-availability', methods=['POST'])
def check_room_availability():
    """API endpoint to check room availability for given dates"""
    try:
        data = request.get_json()
        if not data or 'check_in' not in data or 'check_out' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required date parameters'
            }), 400

        check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
        check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
        room_id = data.get('room_id')  # Optional, if checking specific room

        if check_in >= check_out:
            return jsonify({
                'success': False,
                'error': 'Check-in date must be before check-out date'
            }), 400

        if check_in < datetime.now().date():
            return jsonify({
                'success': False,
                'error': 'Check-in date cannot be in the past'
            }), 400

        # Base query for available rooms
        query = Room.query.filter_by(available=True)
        
        # If room_id is provided, check only that room
        if room_id:
            query = query.filter(Room.id == room_id)

        # Get all rooms that match the criteria
        rooms = query.all()
        available_rooms = []
        rooms_count = {}

        for room in rooms:
            # Count existing bookings for these dates
            existing_bookings = Booking.query.filter(
                Booking.room_id == room.id,
                Booking.status == 'confirmed',
                Booking.check_in < check_out,
                Booking.check_out > check_in
            ).count()

            # Calculate available rooms, capped at 6
            total_rooms = min(room.total_rooms, 6)  # Ensure total rooms never exceeds 6
            available = min(total_rooms - existing_bookings, 6)  # Cap available rooms at 6
            
            if available > 0:
                available_rooms.append(room.id)
                rooms_count[room.id] = {
                    'available': available,
                    'total': total_rooms,
                    'room_type': room.room_type,
                    'capacity': room.capacity
                }

        return jsonify({
            'success': True,
            'available_rooms': available_rooms,
            'rooms_count': rooms_count
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid date format'
        }), 400
    except Exception as e:
        app.logger.error(f"Error checking room availability: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error checking room availability'
        }), 500

@app.route('/room/<int:room_id>')
def room_detail(room_id):
    """Display detailed information about a specific room"""
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

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    try:
        # Calculate dashboard statistics
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
    except Exception as e:
        app.logger.error(f"Error in admin dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('index'))

@app.route('/rooms')
def rooms():
    """Display all available rooms with filtering capability"""
    rooms = Room.query.filter_by(available=True).all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
@login_required
def booking(room_id):
    room = Room.query.get_or_404(room_id)
    
    if request.method == 'POST':
        try:
            # Create booking
            booking = Booking(
                room_id=room_id,
                user_id=current_user.id,
                guest_name=request.form['name'].strip(),
                guest_email=request.form['email'].strip(),
                check_in=datetime.strptime(request.form['check_in'], '%Y-%m-%d').date(),
                check_out=datetime.strptime(request.form['check_out'], '%Y-%m-%d').date(),
                guests=int(request.form['guests']),
                payment_option=request.form['payment_option'],
                status='pending'
            )
            
            db.session.add(booking)
            
            # Handle payment
            if booking.payment_option == 'now':
                days = (booking.check_out - booking.check_in).days
                amount = room.price * days * int(request.form['num_rooms'])
                
                try:
                    intent = create_payment_intent(amount)
                    booking.payment_intent_id = intent.id
                    db.session.commit()
                    return redirect(url_for('payment', booking_id=booking.id))
                except Exception as e:
                    db.session.rollback()
                    raise e
            else:
                booking.status = 'confirmed'
                db.session.commit()
                
                try:
                    send_booking_confirmation(booking)
                except Exception as e:
                    app.logger.error(f"Error sending confirmation email: {str(e)}")
                
                flash('Booking confirmed! Please complete payment before check-in.', 'success')
                return redirect(url_for('my_bookings'))
                
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Booking error: {str(e)}")
            flash('An error occurred while processing your booking. Please try again.', 'error')
            return redirect(url_for('booking', room_id=room_id))
            
    return render_template('booking.html', room=room)

@app.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)

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
        try:
            send_booking_status_update(booking)
            flash('Booking cancelled successfully. Check your email for details.', 'success')
        except Exception as e:
            app.logger.error(f"Error sending cancellation email: {str(e)}")
            flash('Booking cancelled but email notification failed.', 'warning')
            
        return redirect(url_for('my_bookings'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error cancelling booking: {str(e)}")
        flash('Error cancelling booking. Please try again.', 'error')
        return redirect(url_for('my_bookings'))
