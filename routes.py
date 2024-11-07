from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import Room, Booking, Contact, User, Review
from datetime import datetime
from email_validator import validate_email, EmailNotValidError
from payment import create_payment_intent, confirm_payment
import stripe

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        
        try:
            # Validate email
            valid = validate_email(email)
            email = valid.email
            
            # Check if user already exists
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
        # Check if user has a completed booking for this room
        completed_booking = Booking.query.filter_by(
            user_id=current_user.id,
            room_id=room_id,
            status='confirmed'
        ).first()
        if completed_booking:
            # Check if user hasn't already reviewed
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
    
    # Check if user has a confirmed booking
    booking = Booking.query.filter_by(
        user_id=current_user.id,
        room_id=room_id,
        status='confirmed'
    ).first()
    
    if not booking:
        flash('You can only review rooms you have stayed in.', 'error')
        return redirect(url_for('room_detail', room_id=room_id))
    
    # Check if user has already reviewed
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

            # Create payment intent
            payment_intent = create_payment_intent(booking.id)
            
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
        confirm_payment(payment_intent.id)

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

@app.route('/api/check-availability', methods=['POST'])
def check_availability():
    data = request.json
    existing_bookings = Booking.query.filter(
        Booking.room_id == data['room_id'],
        Booking.check_out >= data['check_in'],
        Booking.check_in <= data['check_out']
    ).count()
    return jsonify({'available': existing_bookings == 0})
