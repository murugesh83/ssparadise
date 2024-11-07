import os
from flask_mail import Mail, Message
from flask import render_template_string

mail = Mail()

# Email templates
BOOKING_CONFIRMATION_TEMPLATE = '''
Dear {{ booking.guest_name }},

Thank you for booking with SS Paradise Residency!

Booking Details:
- Room: {{ booking.room.name }}
- Check-in: {{ booking.check_in.strftime('%Y-%m-%d') }}
- Check-out: {{ booking.check_out.strftime('%Y-%m-%d') }}
- Number of Guests: {{ booking.guests }}
- Total Amount: ₹{{ "%.2f"|format(booking.amount_paid) }}

Your booking status is: {{ booking.status }}

If you have any questions, please don't hesitate to contact us.

Best regards,
SS Paradise Residency Team
'''

BOOKING_STATUS_UPDATE_TEMPLATE = '''
Dear {{ booking.guest_name }},

Your booking status has been updated.

Booking Details:
- Room: {{ booking.room.name }}
- Check-in: {{ booking.check_in.strftime('%Y-%m-%d') }}
- Check-out: {{ booking.check_out.strftime('%Y-%m-%d') }}
- New Status: {{ booking.status }}

If you have any questions, please don't hesitate to contact us.

Best regards,
SS Paradise Residency Team
'''

def init_mail_app(app):
    """Initialize mail settings for the Flask app"""
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('SMTP_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('SMTP_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('SMTP_USERNAME')
    mail.init_app(app)

def send_booking_confirmation(booking):
    """Send booking confirmation email"""
    try:
        msg = Message(
            'Booking Confirmation - SS Paradise Residency',
            recipients=[booking.guest_email]
        )
        msg.body = render_template_string(BOOKING_CONFIRMATION_TEMPLATE, booking=booking)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending confirmation email: {str(e)}")
        return False

def send_booking_status_update(booking):
    """Send booking status update email"""
    try:
        msg = Message(
            'Booking Status Update - SS Paradise Residency',
            recipients=[booking.guest_email]
        )
        msg.body = render_template_string(BOOKING_STATUS_UPDATE_TEMPLATE, booking=booking)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending status update email: {str(e)}")
        return False
