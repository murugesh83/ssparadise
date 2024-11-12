from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import Room, Booking, Contact, User, Review
from datetime import datetime, timedelta
from email_validator import validate_email, EmailNotValidError
from payment import create_payment_intent, confirm_payment, process_refund
from utils import admin_required
from email_utils import send_booking_confirmation, send_booking_status_update
import stripe
from sqlalchemy import func, and_, not_, or_
import json

@app.route('/rooms/<int:room_id>')
def room_detail(room_id):
    """Display detailed information about a specific room"""
    room = Room.query.get_or_404(room_id)
    return render_template('room_detail.html', room=room)

@app.route('/api/check-room-availability', methods=['POST'])
def check_room_availability():
    """API endpoint to check room availability for given dates"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        # Validate required fields
        check_in_str = data.get('check_in')
        check_out_str = data.get('check_out')
        if not check_in_str or not check_out_str:
            return jsonify({'success': False, 'error': 'Missing required date parameters'}), 400

        # Parse and validate dates
        try:
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Validate date logic
        today = datetime.now().date()
        if check_in < today:
            return jsonify({'success': False, 'error': 'Check-in date cannot be in the past'}), 400

        if check_in >= check_out:
            return jsonify({'success': False, 'error': 'Check-in date must be before check-out date'}), 400

        if (check_out - check_in).days > 30:
            return jsonify({'success': False, 'error': 'Maximum booking duration is 30 days'}), 400

        # Get specific room if requested
        room_id = data.get('room_id')
        
        # Query available rooms
        query = Room.query.filter_by(available=True)
        if room_id:
            query = query.filter(Room.id == room_id)

        rooms = query.all()
        available_rooms = []
        rooms_count = {}

        for room in rooms:
            # Count existing bookings for these dates
            booked_count = db.session.query(func.coalesce(func.sum(Booking.room_quantity), 0)).filter(
                Booking.room_id == room.id,
                Booking.status == 'confirmed',
                not_(or_(
                    Booking.check_out <= check_in,
                    Booking.check_in >= check_out
                ))
            ).scalar()

            # Calculate available rooms
            available = room.total_rooms - int(booked_count or 0)
            if available > 0:
                available_rooms.append(room.id)
                rooms_count[str(room.id)] = available

        return jsonify({
            'success': True,
            'available_rooms': available_rooms,
            'rooms_count': rooms_count
        })

    except Exception as e:
        app.logger.error(f"Error checking room availability: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while checking availability'
        }), 500

@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
@login_required
def booking(room_id):
    """Handle room booking process"""
    room = Room.query.get_or_404(room_id)
    
    if request.method == 'POST':
        try:
            # Get and validate form data
            check_in = datetime.strptime(request.form['check_in'], '%Y-%m-%d').date()
            check_out = datetime.strptime(request.form['check_out'], '%Y-%m-%d').date()
            guests = int(request.form['guests'])
            room_quantity = int(request.form.get('room_quantity', 1))
            guest_name = request.form['name'].strip()
            guest_email = request.form['email'].strip()
            payment_option = request.form.get('payment_option', 'now')

            # Validate dates
            if check_in >= check_out:
                flash('Check-in date must be before check-out date', 'error')
                return redirect(url_for('booking', room_id=room_id))

            if check_in < datetime.now().date():
                flash('Check-in date cannot be in the past', 'error')
                return redirect(url_for('booking', room_id=room_id))

            # Validate guest count
            if guests < 1 or guests > room.capacity:
                flash(f'Number of guests must be between 1 and {room.capacity}', 'error')
                return redirect(url_for('booking', room_id=room_id))

            # Validate email
            try:
                validate_email(guest_email)
            except EmailNotValidError:
                flash('Please enter a valid email address', 'error')
                return redirect(url_for('booking', room_id=room_id))
            
            # Check room availability
            booked_rooms = db.session.query(
                func.coalesce(func.sum(Booking.room_quantity), 0)
            ).filter(
                Booking.room_id == room_id,
                Booking.status == 'confirmed',
                not_(or_(
                    Booking.check_out <= check_in,
                    Booking.check_in >= check_out
                ))
            ).scalar()
            
            available_rooms = room.total_rooms - int(booked_rooms or 0)
            if room_quantity > available_rooms:
                flash(f'Only {available_rooms} room(s) available for the selected dates.', 'error')
                return redirect(url_for('booking', room_id=room_id))
            
            # Calculate total amount
            days = (check_out - check_in).days
            amount = room.price * days * room_quantity
            
            # Create booking
            booking = Booking(
                room_id=room_id,
                user_id=current_user.id,
                guest_name=guest_name,
                guest_email=guest_email,
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                room_quantity=room_quantity,
                payment_option=payment_option,
                status='pending',
                payment_status='pending',
                created_at=datetime.utcnow()
            )
            
            db.session.add(booking)
            db.session.commit()
            
            # Handle payment
            if payment_option == 'now':
                try:
                    intent = create_payment_intent(amount)
                    booking.payment_intent_id = intent.id
                    db.session.commit()
                    return redirect(url_for('payment', booking_id=booking.id))
                except Exception as e:
                    app.logger.error(f"Payment error: {str(e)}")
                    db.session.delete(booking)
                    db.session.commit()
                    flash('Error processing payment. Please try again.', 'error')
                    return redirect(url_for('booking', room_id=room_id))
            else:
                # Pay later option
                booking.status = 'confirmed'
                db.session.commit()
                
                # Send confirmation email
                try:
                    send_booking_confirmation(booking)
                except Exception as e:
                    app.logger.error(f"Error sending confirmation email: {str(e)}")
                
                flash('Booking confirmed! Please complete the payment before check-in.', 'success')
                return redirect(url_for('my_bookings'))
                
        except ValueError as e:
            flash('Please enter valid dates', 'error')
            return redirect(url_for('booking', room_id=room_id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Booking error: {str(e)}")
            flash('An error occurred while processing your booking. Please try again.', 'error')
            return redirect(url_for('booking', room_id=room_id))
            
    return render_template('booking.html', room=room)

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    try:
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
        recent_activity = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
        return render_template('admin/dashboard.html', stats=stats, recent_activity=recent_activity)
    except Exception as e:
        app.logger.error(f"Error in admin dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('index'))

@app.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        if booking.user_id != current_user.id:
            flash('Unauthorized access', 'error')
            return redirect(url_for('my_bookings'))
        
        if booking.status == 'cancelled':
            flash('Booking is already cancelled', 'warning')
            return redirect(url_for('my_bookings'))
            
        if not booking.can_cancel:
            flash('Cancellation period has expired', 'error')
            return redirect(url_for('my_bookings'))
        
        booking.status = 'cancelled'
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = request.form.get('cancellation_reason')
        
        db.session.commit()
        
        try:
            send_booking_status_update(booking)
            flash('Booking cancelled successfully', 'success')
        except Exception as e:
            app.logger.error(f"Error sending cancellation email: {str(e)}")
            flash('Booking cancelled but email notification failed', 'warning')
            
        return redirect(url_for('my_bookings'))
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error cancelling booking: {str(e)}")
        flash('Error cancelling booking', 'error')
        return redirect(url_for('my_bookings'))

@app.route('/rooms')
def rooms():
    """Display all available rooms with filtering capability"""
    rooms = Room.query.filter_by(available=True).all()
    return render_template('rooms.html', rooms=rooms)
