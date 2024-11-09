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
    """Check room availability for given dates"""
    try:
        data = request.json
        if not data or 'check_in' not in data or 'check_out' not in data:
            return jsonify({'error': 'Missing required data'}), 400

        check_in = datetime.strptime(data.get('check_in'), '%Y-%m-%d').date()
        check_out = datetime.strptime(data.get('check_out'), '%Y-%m-%d').date()
        
        # Validate dates
        if check_in >= check_out:
            return jsonify({'error': 'Check-out date must be after check-in date'}), 400
        
        # Get all rooms
        all_rooms = Room.query.filter_by(available=True).all()
        
        # Find rooms with conflicting bookings
        booked_room_ids = db.session.query(Booking.room_id).filter(
            Booking.status != 'cancelled',
            Booking.check_in < check_out,
            Booking.check_out > check_in
        ).distinct().all()
        
        booked_room_ids = [room_id for (room_id,) in booked_room_ids]
        available_room_ids = [room.id for room in all_rooms if room.id not in booked_room_ids]
        
        return jsonify({
            'available_rooms': available_room_ids,
            'total_rooms': len(all_rooms),
            'available_count': len(available_room_ids)
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

# Placeholder for other routes that would be in the original file