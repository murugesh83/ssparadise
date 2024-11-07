from flask import render_template, request, jsonify, flash, redirect, url_for
from app import app, db
from models import Room, Booking, Contact
from datetime import datetime

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rooms')
def rooms():
    rooms = Room.query.all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/room/<int:room_id>')
def room_detail(room_id):
    room = Room.query.get_or_404(room_id)
    return render_template('room_detail.html', room=room)

@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
def booking(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        try:
            booking = Booking(
                room_id=room_id,
                guest_name=request.form['name'],
                guest_email=request.form['email'],
                check_in=datetime.strptime(request.form['check_in'], '%Y-%m-%d'),
                check_out=datetime.strptime(request.form['check_out'], '%Y-%m-%d'),
                guests=int(request.form['guests'])
            )
            db.session.add(booking)
            db.session.commit()
            flash('Booking request submitted successfully!', 'success')
            return redirect(url_for('rooms'))
        except Exception as e:
            flash('Error processing booking. Please try again.', 'error')
    return render_template('booking.html', room=room)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            contact = Contact(
                name=request.form['name'],
                email=request.form['email'],
                message=request.form['message']
            )
            db.session.add(contact)
            db.session.commit()
            flash('Message sent successfully!', 'success')
            return redirect(url_for('contact'))
        except Exception as e:
            flash('Error sending message. Please try again.', 'error')
    return render_template('contact.html')

@app.route('/api/check-availability', methods=['POST'])
def check_availability():
    data = request.json
    existing_bookings = Booking.query.filter(
        Booking.room_id == data['room_id'],
        Booking.check_out >= data['check_in'],
        Booking.check_in <= data['check_out']
    ).count()
    return jsonify({'available': existing_bookings == 0})
