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

# ... [rest of the file remains unchanged]
