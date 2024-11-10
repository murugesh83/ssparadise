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
        
        if booking.status == 'cancelled':
            flash('Booking is already cancelled', 'warning')
            return redirect(url_for('my_bookings'))
        
        # Update booking status
        booking.status = 'cancelled'
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = request.form.get('cancellation_reason')
        
        # Handle refund if payment was made
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
        
        # Send cancellation email
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
