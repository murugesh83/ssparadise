from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db, get_db
from models import Room, Booking, Contact, User, Review
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
from payment import create_payment_intent, confirm_payment, process_refund
from utils import admin_required
from email_utils import send_booking_confirmation, send_booking_status_update
import stripe
from sqlalchemy import func, and_, not_
from sqlalchemy.exc import OperationalError

@app.route('/api/check-room-availability', methods=['POST'])
def check_room_availability():
    try:
        data = request.get_json()
        if not data or 'check_in' not in data or 'check_out' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required date parameters'
            }), 400

        try:
            check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
            check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Please use YYYY-MM-DD format.'
            }), 400

        session = get_db()
        query = Room.query.filter_by(available=True)
        
        if 'room_id' in data:
            query = query.filter(Room.id == data['room_id'])

        rooms = query.all()
        available_rooms = []
        rooms_count = {}

        for room in rooms:
            booked_rooms = session.query(func.sum(Booking.room_quantity)).filter(
                Booking.room_id == room.id,
                Booking.status == 'confirmed',
                Booking.check_in < check_out,
                Booking.check_out > check_in
            ).scalar() or 0

            available = room.total_rooms - booked_rooms
            if available > 0:
                available_rooms.append(room.id)
                rooms_count[room.id] = available

        return jsonify({
            'success': True,
            'available_rooms': available_rooms,
            'rooms_count': rooms_count
        })

    except OperationalError:
        return jsonify({
            'success': False,
            'error': 'Database connection error. Please try again.'
        }), 503
    except Exception as e:
        app.logger.error(f"Error checking room availability: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error checking room availability'
        }), 500

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
    room = Room.query.get_or_404(room_id)
    
    if request.method == 'POST':
        try:
            # Get and validate form data
            check_in = datetime.strptime(request.form['check_in'], '%Y-%m-%d').date()
            check_out = datetime.strptime(request.form['check_out'], '%Y-%m-%d').date()
            guests = int(request.form['guests'])
            room_quantity = int(request.form['room_quantity'])
            guest_name = request.form['name'].strip()
            guest_email = request.form['email'].strip()
            payment_option = request.form['payment_option']

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
            
            # Verify room availability for the requested quantity
            existing_bookings = Booking.query.filter(
                Booking.room_id == room_id,
                Booking.status == 'confirmed',
                Booking.check_in < check_out,
                Booking.check_out > check_in
            ).with_entities(func.sum(Booking.room_quantity)).scalar() or 0
            
            if existing_bookings + room_quantity > room.total_rooms:
                flash('Not enough rooms available for the selected dates.', 'error')
                return redirect(url_for('booking', room_id=room_id))
            
            # Calculate total amount based on room quantity
            days = (check_out - check_in).days
            amount = room.price * days * room_quantity
            
            # Create booking
            booking = Booking()
            booking.room_id = room_id
            booking.user_id = current_user.id
            booking.guest_name = guest_name
            booking.guest_email = guest_email
            booking.check_in = check_in
            booking.check_out = check_out
            booking.guests = guests
            booking.room_quantity = room_quantity
            booking.payment_option = payment_option
            booking.status = 'pending'
            booking.payment_status = 'pending'
            
            db.session.add(booking)
            db.session.commit()
            
            # Handle payment based on option
            if payment_option == 'now':
                try:
                    # Create payment intent with updated amount
                    intent = create_payment_intent(amount)
                    booking.payment_intent_id = intent.id
                    db.session.commit()
                    
                    # Redirect to payment page
                    return redirect(url_for('payment', booking_id=booking.id))
                except Exception as e:
                    app.logger.error(f"Payment error: {str(e)}")
                    db.session.delete(booking)
                    db.session.commit()
                    flash('Error processing payment. Please try again.', 'error')
                    return redirect(url_for('booking', room_id=room_id))
            else:
                # For pay later option
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
        
        if booking.payment_status == 'completed':
            try:
                refund = process_refund(booking.payment_intent_id, booking.refund_amount_available)
                if refund:
                    booking.refund_status = 'completed'
                    booking.refund_amount = booking.refund_amount_available
            except Exception as e:
                app.logger.error(f"Refund processing error: {str(e)}")
                booking.refund_status = 'failed'
        
        db.session.commit()
        
        try:
            if send_booking_status_update(booking):
                flash('Booking cancelled successfully. Check your email for details.', 'success')
            else:
                flash('Booking cancelled but email notification failed.', 'warning')
        except Exception as e:
            app.logger.error(f"Error sending cancellation email: {str(e)}")
            flash('Booking cancelled but email notification failed.', 'warning')
            
        return redirect(url_for('my_bookings'))
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error cancelling booking: {str(e)}")
        flash('Error cancelling booking. Please try again.', 'error')
        return redirect(url_for('my_bookings'))

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    try:
        # Calculate statistics
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
        
        # Get recent activity (last 10 bookings)
        recent_activity = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
        
        return render_template('admin/dashboard.html',
                            stats=stats,
                            recent_activity=recent_activity)
    except Exception as e:
        app.logger.error(f"Error in admin dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('index'))

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
        room.price = float(request.form.get('price'))
        room.capacity = int(request.form.get('capacity'))
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
            room.price = float(request.form.get('price'))
            room.capacity = int(request.form.get('capacity'))
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
    # Get all bookings ordered by creation date
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