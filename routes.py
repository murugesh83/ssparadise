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

@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
@login_required
def booking(room_id):
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
                payment_option=payment_option
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
            flash('Error processing booking. Please try again.', 'error')
            app.logger.error(f"Booking error: {str(e)}")
    return render_template('booking.html', room=room)

@app.route('/complete-payment/<int:booking_id>')
@login_required
def complete_payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('my_bookings'))
    
    if booking.payment_status != 'pending':
        flash('Payment already completed or not required.', 'warning')
        return redirect(url_for('my_bookings'))
    
    try:
        payment_intent = create_payment_intent(booking.id)
        return render_template('payment.html',
                            booking=booking,
                            client_secret=payment_intent.client_secret,
                            publishable_key=app.config['STRIPE_PUBLISHABLE_KEY'])
    except Exception as e:
        flash('Error processing payment. Please try again.', 'error')
        app.logger.error(f"Payment error: {str(e)}")
        return redirect(url_for('my_bookings'))

@app.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        flash('Unauthorized action.', 'error')
        return redirect(url_for('my_bookings'))
    
    if not booking.can_cancel:
        flash('This booking cannot be cancelled.', 'error')
        return redirect(url_for('my_bookings'))
    
    cancellation_reason = request.form.get('cancellation_reason')
    if not cancellation_reason:
        flash('Please provide a reason for cancellation.', 'error')
        return redirect(url_for('my_bookings'))
    
    try:
        booking.status = 'cancelled'
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = cancellation_reason
        
        if booking.payment_status == 'completed':
            refund = process_refund(booking.id)
            if refund:
                flash(f'Booking cancelled. Refund of ₹{booking.refund_amount:.2f} will be processed.', 'success')
            else:
                flash('Booking cancelled. No refund is available based on cancellation policy.', 'warning')
        else:
            flash('Booking cancelled.', 'success')
        
        db.session.commit()
        
        if send_booking_status_update(booking):
            app.logger.info(f"Cancellation email sent for booking {booking.id}")
        else:
            app.logger.warning(f"Could not send cancellation email for booking {booking.id}")
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error cancelling booking: {str(e)}")
        flash('An error occurred while cancelling the booking. Please try again.', 'error')
    
    return redirect(url_for('my_bookings'))
