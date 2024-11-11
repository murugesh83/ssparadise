import os
from app import db
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'user'  # Updated to match database
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Room(db.Model):
    __tablename__ = 'room'  # Updated to match database
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(50), nullable=False)
    amenities = db.Column(db.JSON)
    image_url = db.Column(db.String(200))
    available = db.Column(db.Boolean, default=True)
    total_rooms = db.Column(db.Integer, default=1)
    bookings = db.relationship('Booking', backref='room', lazy=True)
    reviews = db.relationship('Review', backref='room', lazy=True)

    @property
    def average_rating(self):
        if not self.reviews:
            return 0
        return sum(review.rating for review in self.reviews) / len(self.reviews)

class Booking(db.Model):
    __tablename__ = 'booking'  # Updated to match database
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    guest_name = db.Column(db.String(100), nullable=False)
    guest_email = db.Column(db.String(120), nullable=False)
    check_in = db.Column(db.Date, nullable=False)
    check_out = db.Column(db.Date, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    payment_status = db.Column(db.String(20), default='pending')
    payment_option = db.Column(db.String(20), default='now')
    payment_intent_id = db.Column(db.String(100))
    amount_paid = db.Column(db.Float)
    payment_date = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    cancellation_reason = db.Column(db.Text)
    refund_status = db.Column(db.String(20))
    refund_amount = db.Column(db.Float)

    @property
    def can_cancel(self):
        if self.status == 'cancelled':
            return False
        if self.check_in <= datetime.now().date():
            return False
        hours_until_checkin = (self.check_in - datetime.now().date()).days * 24
        return hours_until_checkin >= 48

    @property
    def cancellation_fee(self):
        if not self.amount_paid:
            return 0
        hours_until_checkin = (self.check_in - datetime.now().date()).days * 24
        if hours_until_checkin >= 168:  # More than 7 days
            return self.amount_paid * 0.1
        elif hours_until_checkin >= 72:  # 3-7 days
            return self.amount_paid * 0.3
        elif hours_until_checkin >= 48:  # 48-72 hours
            return self.amount_paid * 0.5
        else:  # Less than 48 hours
            return self.amount_paid

    @property
    def refund_amount_available(self):
        if not self.amount_paid:
            return 0
        return self.amount_paid - self.cancellation_fee

class Contact(db.Model):
    __tablename__ = 'contact'  # Updated to match database
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    __tablename__ = 'review'  # Updated to match database
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
