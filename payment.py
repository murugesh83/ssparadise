import os
import stripe
from datetime import datetime
from app import app, db
from models import Booking

stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def calculate_booking_amount(check_in, check_out, room_price):
    """Calculate the total amount for the booking."""
    days = (check_out - check_in).days
    return days * room_price

def create_payment_intent(booking_id):
    """Create a Stripe PaymentIntent for a booking."""
    booking = Booking.query.get(booking_id)
    if not booking:
        raise ValueError("Booking not found")
    
    amount = calculate_booking_amount(booking.check_in, booking.check_out, booking.room.price)
    amount_cents = int(amount * 100)  # Convert to cents for Stripe
    
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='inr',
            metadata={
                'booking_id': booking_id,
                'guest_email': booking.guest_email
            }
        )
        
        # Update booking with payment intent ID
        booking.payment_intent_id = intent.id
        booking.amount_paid = amount
        db.session.commit()
        
        return intent
        
    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe error: {str(e)}")
        raise

def confirm_payment(payment_intent_id):
    """Confirm a successful payment and update booking status."""
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        booking = Booking.query.filter_by(payment_intent_id=payment_intent_id).first()
        
        if not booking:
            raise ValueError("Booking not found")
            
        if payment_intent.status == 'succeeded':
            booking.payment_status = 'completed'
            booking.status = 'confirmed'
            booking.payment_date = datetime.utcnow()
            db.session.commit()
            return True
            
        return False
        
    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe error: {str(e)}")
        raise

def process_refund(booking_id):
    """Process refund for a cancelled booking."""
    booking = Booking.query.get(booking_id)
    if not booking or not booking.payment_intent_id:
        raise ValueError("Invalid booking or no payment found")
    
    if booking.payment_status != 'completed':
        raise ValueError("Cannot refund an incomplete payment")
    
    refund_amount = booking.refund_amount_available
    if refund_amount <= 0:
        booking.refund_status = 'no_refund'
        db.session.commit()
        return None
    
    try:
        refund_amount_cents = int(refund_amount * 100)
        refund = stripe.Refund.create(
            payment_intent=booking.payment_intent_id,
            amount=refund_amount_cents,
            metadata={
                'booking_id': booking_id,
                'refund_reason': booking.cancellation_reason
            }
        )
        
        booking.refund_status = 'completed'
        booking.refund_amount = refund_amount
        db.session.commit()
        
        return refund
        
    except stripe.error.StripeError as e:
        app.logger.error(f"Stripe refund error: {str(e)}")
        booking.refund_status = 'failed'
        db.session.commit()
        raise
