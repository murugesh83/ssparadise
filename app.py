import os
from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from email_utils import init_mail_app
from datetime import datetime

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

app = Flask(__name__)

# Configuration settings
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "ss_paradise_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["DEBUG"] = True

# Stripe Configuration
app.config["STRIPE_PUBLISHABLE_KEY"] = os.environ.get("STRIPE_PUBLISHABLE_KEY")
app.config["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY")
app.config["STRIPE_WEBHOOK_SECRET"] = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_test")

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Initialize email
init_mail_app(app)

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Basic routes
@app.route('/')
def index():
    from models import Room
    featured_rooms = Room.query.filter_by(available=True).limit(4).all()
    return render_template('index.html', featured_rooms=featured_rooms)

@app.route('/rooms')
def rooms():
    from models import Room
    rooms = Room.query.filter_by(available=True).all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

# Make current year available to all templates
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# Import routes after app initialization to avoid circular imports
from routes import *
from oauth_routes import *
from auth_routes import *

# Create database tables
with app.app_context():
    db.create_all()
