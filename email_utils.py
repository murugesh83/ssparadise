import os
from flask_mail import Mail, Message
from flask import render_template_string, current_app
from functools import wraps
import time
from datetime import datetime

mail = Mail()

def retry_on_failure(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    current_app.logger.error(f"Email sending attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        current_app.logger.error(f"All attempts failed for sending email: {str(e)}")
                        return False
                    time.sleep(delay)
            return False
        return wrapper
    return decorator

# Email templates with enhanced information
BOOKING_CONFIRMATION_TEMPLATE = '''
Dear {{ booking.guest_name }},

Thank you for choosing SS Paradise Residency! Your booking has been confirmed.

Booking Details:
- Booking ID: {{ booking.id }}
- Room: {{ booking.room.name }} ({{ booking.room.room_type }})
- Check-in: {{ booking.check_in.strftime('%Y-%m-%d') }}
- Check-out: {{ booking.check_out.strftime('%Y-%m-%d') }}
- Number of Guests: {{ booking.guests }}
- Total Amount: ₹{{ "%.2f"|format(booking.amount_paid if booking.amount_paid else (booking.room.price * (booking.check_out - booking.check_in).days)) }}
- Payment Status: {{ booking.payment_status.title() }}
- Payment Option: {{ "Pay Now" if booking.payment_option == 'now' else "Pay Later" }}

{% if booking.payment_option == 'later' %}
Important: Payment must be completed before check-in.
You can complete your payment through our website at any time.
{% endif %}

Cancellation Policy:
- More than 7 days before check-in: 10% cancellation fee
- 3-7 days before check-in: 30% cancellation fee
- 48-72 hours before check-in: 50% cancellation fee
- Less than 48 hours before check-in: No refund available

Hotel Information:
SS Paradise Residency
Address: Near Arunachaleswarar Temple, Tiruvannamalai
Email: ssparadisehotels@gmail.com
Phone: +91 1234567890
Website: https://ssparadise.com

Need assistance? Contact our 24/7 support desk.

Best regards,
SS Paradise Residency Team
'''

BOOKING_STATUS_UPDATE_TEMPLATE = '''
Dear {{ booking.guest_name }},

Your booking status has been updated.

Booking Details:
- Booking ID: {{ booking.id }}
- Room: {{ booking.room.name }} ({{ booking.room.room_type }})
- Check-in: {{ booking.check_in.strftime('%Y-%m-%d') }}
- Check-out: {{ booking.check_out.strftime('%Y-%m-%d') }}
- Number of Guests: {{ booking.guests }}
- Current Status: {{ booking.status.title() }}
- Payment Status: {{ booking.payment_status.title() }}

{% if booking.status == 'cancelled' %}
Cancellation Details:
- Cancellation Date: {{ booking.cancelled_at.strftime('%Y-%m-%d %H:%M') }}
- Cancellation Fee: ₹{{ "%.2f"|format(booking.cancellation_fee) }}
- Refund Amount: ₹{{ "%.2f"|format(booking.refund_amount_available) }}
- Refund Status: {{ booking.refund_status.title() if booking.refund_status else 'Pending' }}
{% endif %}

Hotel Information:
SS Paradise Residency
Address: Near Arunachaleswarar Temple, Tiruvannamalai
Email: ssparadisehotels@gmail.com
Phone: +91 1234567890

If you have any questions, please don't hesitate to contact us.

Best regards,
SS Paradise Residency Team
'''

def init_mail_app(app):
    """Initialize mail settings for the Flask app"""
    try:
        app.config['MAIL_SERVER'] = 'smtp.gmail.com'
        app.config['MAIL_PORT'] = 587
        app.config['MAIL_USE_TLS'] = True
        app.config['MAIL_USERNAME'] = os.environ.get('SMTP_USERNAME', 'ssparadisehotels@gmail.com')
        app.config['MAIL_PASSWORD'] = os.environ.get('SMTP_PASSWORD')
        app.config['MAIL_DEFAULT_SENDER'] = ('SS Paradise Residency', 'ssparadisehotels@gmail.com')
        
        if not app.config['MAIL_PASSWORD']:
            app.logger.error("SMTP_PASSWORD environment variable is not set")
            return False
            
        mail.init_app(app)
        return True
    except Exception as e:
        app.logger.error(f"Error initializing mail app: {str(e)}")
        return False

@retry_on_failure(max_retries=3, delay=1)
def send_booking_confirmation(booking):
    """Send booking confirmation email with retry mechanism"""
    try:
        msg = Message(
            'Booking Confirmation - SS Paradise Residency',
            recipients=[booking.guest_email],
            cc=['ssparadisehotels@gmail.com']
        )
        msg.body = render_template_string(BOOKING_CONFIRMATION_TEMPLATE, booking=booking)
        mail.send(msg)
        current_app.logger.info(f"Booking confirmation email sent successfully to {booking.guest_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending confirmation email: {str(e)}")
        raise

@retry_on_failure(max_retries=3, delay=1)
def send_booking_status_update(booking):
    """Send booking status update email with retry mechanism"""
    try:
        msg = Message(
            'Booking Status Update - SS Paradise Residency',
            recipients=[booking.guest_email],
            cc=['ssparadisehotels@gmail.com']
        )
        msg.body = render_template_string(BOOKING_STATUS_UPDATE_TEMPLATE, booking=booking)
        mail.send(msg)
        current_app.logger.info(f"Booking status update email sent successfully to {booking.guest_email}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending status update email: {str(e)}")
        raise
