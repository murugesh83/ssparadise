from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import Room, Booking, Contact, User, Review
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
from payment import create_payment_intent, confirm_payment
from utils import admin_required
from email_utils import send_booking_confirmation, send_booking_status_update
import stripe

@app.route('/')
def index():
    # Fetch featured rooms
    featured_rooms = Room.query.filter_by(available=True).order_by(Room.id).limit(4).all()
    return render_template('index.html', featured_rooms=featured_rooms, current_year=datetime.now().year)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        
        try:
            valid = validate_email(email)
            email = valid.email
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered. Please login.', 'error')
                return redirect(url_for('login'))
            
            user = User(email=email, name=name)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
            
        except EmailNotValidError:
            flash('Invalid email address.', 'error')
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember = 'remember' in request.form
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/rooms')
def rooms():
    rooms = Room.query.all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/room/<int:room_id>')
def room_detail(room_id):
    room = Room.query.get_or_404(room_id)
    reviews = Review.query.filter_by(room_id=room_id).order_by(Review.created_at.desc()).all()
    can_review = False
    if current_user.is_authenticated:
        completed_booking = Booking.query.filter_by(
            user_id=current_user.id,
            room_id=room_id,
            status='confirmed'
        ).first()
        if completed_booking:
            existing_review = Review.query.filter_by(
                user_id=current_user.id,
                room_id=room_id
            ).first()
            can_review = not existing_review
    
    return render_template('room_detail.html', room=room, reviews=reviews, can_review=can_review)

@app.route('/room/<int:room_id>/review', methods=['POST'])
@login_required
def submit_review(room_id):
    room = Room.query.get_or_404(room_id)
    
    booking = Booking.query.filter_by(
        user_id=current_user.id,
        room_id=room_id,
        status='confirmed'
    ).first()
    
    if not booking:
        flash('You can only review rooms you have stayed in.', 'error')
        return redirect(url_for('room_detail', room_id=room_id))
    
    existing_review = Review.query.filter_by(
        user_id=current_user.id,
        room_id=room_id
    ).first()
    
    if existing_review:
        flash('You have already reviewed this room.', 'error')
        return redirect(url_for('room_detail', room_id=room_id))
    
    rating = int(request.form.get('rating', 0))
    comment = request.form.get('comment', '').strip()
    
    if not (1 <= rating <= 5):
        flash('Please provide a rating between 1 and 5.', 'error')
        return redirect(url_for('room_detail', room_id=room_id))
    
    if not comment:
        flash('Please provide a review comment.', 'error')
        return redirect(url_for('room_detail', room_id=room_id))
    
    review = Review(
        room_id=room_id,
        user_id=current_user.id,
        rating=rating,
        comment=comment
    )
    
    db.session.add(review)
    db.session.commit()
    
    flash('Thank you for your review!', 'success')
    return redirect(url_for('room_detail', room_id=room_id))

@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
@login_required
def booking(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        try:
            booking = Booking(
                room_id=room_id,
                user_id=current_user.id,
                guest_name=request.form['name'],
                guest_email=request.form['email'],
                check_in=datetime.strptime(request.form['check_in'], '%Y-%m-%d'),
                check_out=datetime.strptime(request.form['check_out'], '%Y-%m-%d'),
                guests=int(request.form['guests'])
            )
            db.session.add(booking)
            db.session.commit()

            payment_intent = create_payment_intent(booking.id)
            
            # Send booking confirmation email
            if send_booking_confirmation(booking):
                flash('Booking confirmation email sent.', 'success')
            else:
                flash('Could not send confirmation email, but your booking is confirmed.', 'warning')
            
            return render_template('payment.html', 
                                 booking=booking,
                                 client_secret=payment_intent.client_secret,
                                 publishable_key=app.config['STRIPE_PUBLISHABLE_KEY'])
        except Exception as e:
            flash('Error processing booking. Please try again.', 'error')
            app.logger.error(f"Booking error: {str(e)}")
    return render_template('booking.html', room=room)

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, app.config['STRIPE_WEBHOOK_SECRET']
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        booking = Booking.query.filter_by(payment_intent_id=payment_intent.id).first()
        if booking and confirm_payment(payment_intent.id):
            # Send status update email
            if send_booking_status_update(booking):
                app.logger.info(f"Payment confirmation email sent for booking {booking.id}")
            else:
                app.logger.warning(f"Could not send payment confirmation email for booking {booking.id}")

    return jsonify({'status': 'success'})

@app.route('/my-bookings')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)

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

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    stats = {
        'total_rooms': Room.query.count(),
        'active_bookings': Booking.query.filter_by(status='confirmed').count(),
        'daily_revenue': db.session.query(db.func.sum(Room.price)).join(Booking).filter(
            Booking.status == 'confirmed',
            Booking.check_in <= datetime.now(),
            Booking.check_out >= datetime.now()
        ).scalar() or 0,
        'occupancy_rate': calculate_occupancy_rate()
    }
    
    recent_activity = get_recent_activity()
    
    return render_template('admin/dashboard.html', stats=stats, recent_activity=recent_activity)

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
        room = Room(
            name=request.form['name'],
            description=request.form['description'],
            price=float(request.form['price']),
            capacity=int(request.form['capacity']),
            room_type=request.form['room_type'],
            image_url=request.form['image_url'],
            available='available' in request.form,
            amenities=[]
        )
        db.session.add(room)
        db.session.commit()
        flash('Room added successfully!', 'success')
    except Exception as e:
        flash('Error adding room.', 'error')
        app.logger.error(f"Error adding room: {str(e)}")
    return redirect(url_for('admin_rooms'))

@app.route('/admin/rooms/<int:room_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        try:
            room.name = request.form['name']
            room.description = request.form['description']
            room.price = float(request.form['price'])
            room.capacity = int(request.form['capacity'])
            room.room_type = request.form['room_type']
            room.image_url = request.form['image_url']
            room.available = 'available' in request.form
            db.session.commit()
            flash('Room updated successfully!', 'success')
            return redirect(url_for('admin_rooms'))
        except Exception as e:
            flash('Error updating room.', 'error')
            app.logger.error(f"Error updating room: {str(e)}")
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
        app.logger.error(f"Error deleting room: {str(e)}")
        return jsonify({'success': False})

@app.route('/admin/bookings')
@login_required
@admin_required
def admin_bookings():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin/bookings/<int:booking_id>/update', methods=['POST'])
@login_required
@admin_required
def admin_update_booking(booking_id):
    try:
        booking = Booking.query.get_or_404(booking_id)
        data = request.get_json()
        booking.status = data.get('status')
        db.session.commit()
        
        # Send status update email
        if send_booking_status_update(booking):
            app.logger.info(f"Status update email sent for booking {booking.id}")
        else:
            app.logger.warning(f"Could not send status update email for booking {booking.id}")
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error updating booking: {str(e)}")
        return jsonify({'success': False})

@app.route('/api/check-availability', methods=['POST'])
def check_availability():
    data = request.json
    try:
        check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
        check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
        
        # Check for existing bookings in the date range
        existing_bookings = Booking.query.filter(
            Booking.room_id == data['room_id'],
            Booking.status != 'cancelled',  # Exclude cancelled bookings
            db.or_(
                db.and_(
                    Booking.check_in <= check_out,
                    Booking.check_out >= check_in
                )
            )
        ).count()
        
        return jsonify({'available': existing_bookings == 0})
    except Exception as e:
        app.logger.error(f"Availability check error: {str(e)}")
        return jsonify({'available': False, 'error': 'Invalid dates'})

def calculate_occupancy_rate():
    total_rooms = Room.query.count()
    if total_rooms == 0:
        return 0
    
    occupied_rooms = Booking.query.filter(
        Booking.status == 'confirmed',
        Booking.check_in <= datetime.now(),
        Booking.check_out >= datetime.now()
    ).count()
    
    return (occupied_rooms / total_rooms) * 100

def get_recent_activity():
    activities = []
    
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    for booking in recent_bookings:
        activities.append({
            'timestamp': booking.created_at,
            'event_type': 'New Booking',
            'details': f'Room: {booking.room.name}, Guest: {booking.guest_name}',
            'status': booking.status,
            'status_color': 'success' if booking.status == 'confirmed' else 'warning'
        })
    
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    return activities[:5]
