import os
from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from email_utils import init_mail_app
from datetime import datetime
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError, DatabaseError
from sqlalchemy.engine import Engine
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Enhanced SQLAlchemy configuration for better connection handling
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
    'pool_timeout': 20,
    'pool_size': 30,
    'max_overflow': 10,
    'connect_args': {
        'sslmode': 'require',
        'connect_timeout': 10
    }
}

# Stripe Configuration
app.config["STRIPE_PUBLISHABLE_KEY"] = os.environ.get("STRIPE_PUBLISHABLE_KEY")
app.config["STRIPE_SECRET_KEY"] = os.environ.get("STRIPE_SECRET_KEY")
app.config["STRIPE_WEBHOOK_SECRET"] = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_test")

# Database connection retry decorator
def retry_on_db_error(max_retries=3, delay=1):
    def decorator(f):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return f(*args, **kwargs)
                except (OperationalError, DatabaseError) as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    logger.warning(f"Database error, retrying ({retries}/{max_retries}): {str(e)}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

# Add event listeners for database connection handling
@event.listens_for(Engine, "connect")
def connect(dbapi_connection, connection_record):
    logger.info("New database connection established")
    
@event.listens_for(Engine, "engine_connect")
def ping_connection(connection, branch):
    if branch:
        return

    try:
        connection.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning(f"Database connection check failed: {str(e)}")
        raise

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
@retry_on_db_error()
def index():
    from models import Room
    featured_rooms = Room.query.filter_by(available=True).limit(4).all()
    return render_template('index.html', featured_rooms=featured_rooms)

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

def init_database():
    """Initialize database tables with proper session management"""
    from models import User, Room, Booking, Review, Contact
    
    try:
        # Create tables in the application context
        with app.app_context():
            # Ensure any existing transactions are cleaned up
            db.session.remove()
            
            # Drop and recreate tables
            db.drop_all()
            db.create_all()
            
            # Commit changes and log success
            db.session.commit()
            logger.info("Database initialized successfully")
            return True
            
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        # Ensure we rollback any failed transaction
        try:
            db.session.rollback()
        except:
            pass
        return False
    finally:
        # Always make sure to clean up the session
        db.session.remove()

# Initialize database and import routes
with app.app_context():
    # Import routes after app initialization to avoid circular imports
    from routes import *
    from oauth_routes import *
    from auth_routes import *
    
    try:
        # Initialize database
        db.session.remove()  # Clean up any existing sessions
        success = init_database()
        if not success:
            logger.error("Failed to initialize database")
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
