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
    'pool_size': 10,
    'max_overflow': 5,
    'connect_args': {
        'connect_timeout': 10,
        'application_name': 'SSParadise-Flask'
    }
}

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
    try:
        return User.query.get(int(user_id))
    except Exception as e:
        logger.error(f"Error loading user: {str(e)}")
        return None

# Add event listeners for database connection handling
@event.listens_for(Engine, "connect")
def connect(dbapi_connection, connection_record):
    try:
        # Clean up any pending transactions
        dbapi_connection.rollback()
        # Set session parameters
        cursor = dbapi_connection.cursor()
        cursor.execute("""
            SET SESSION idle_in_transaction_session_timeout = '60s';
            SET SESSION lock_timeout = '30s';
        """)
        cursor.close()
    except Exception as e:
        logger.error(f"Error in connect listener: {str(e)}")

@event.listens_for(Engine, "engine_connect")
def ping_connection(connection, branch):
    if branch:
        return
    
    try:
        connection.scalar(text("SELECT 1"))
    except Exception as e:
        logger.warning(f"Database connection check failed: {str(e)}")
        connection.invalidate()
        raise

# Updated before_request handler for transaction management
@app.before_request
def before_request():
    try:
        if db.session.is_active:
            db.session.rollback()
    except Exception as e:
        logger.error(f"Error in before_request: {str(e)}")
    finally:
        db.session.remove()

@app.teardown_request
def teardown_request(exception=None):
    if exception:
        try:
            db.session.rollback()
        except Exception as e:
            logger.error(f"Error in teardown_request rollback: {str(e)}")
    try:
        db.session.remove()
    except Exception as e:
        logger.error(f"Error in teardown_request remove: {str(e)}")

@app.teardown_appcontext
def shutdown_session(exception=None):
    if exception:
        logger.error(f"Error in app context teardown: {str(exception)}")
    try:
        db.session.remove()
    except Exception as e:
        logger.error(f"Error removing session in teardown: {str(e)}")

# Basic routes
@app.route('/')
def index():
    from models import Room
    try:
        featured_rooms = Room.query.filter_by(available=True).limit(4).all()
        return render_template('index.html', featured_rooms=featured_rooms)
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('index.html', featured_rooms=[])

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
    """Initialize database tables with proper transaction management"""
    from models import User, Room, Booking, Review, Contact
    
    with app.app_context():
        try:
            # Clean up any existing sessions
            db.session.remove()
            
            # Drop all tables
            db.drop_all()
            
            # Create all tables
            db.create_all()
            
            # Create admin user
            admin = User(
                email='admin@ssparadise.com',
                name='Admin',
                is_admin=True
            )
            admin.set_password('admin123')
            
            # Add admin user in a clean transaction
            db.session.add(admin)
            db.session.commit()
            
            logger.info("Database initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            db.session.rollback()
            return False
        finally:
            db.session.remove()

# Initialize database and import routes
with app.app_context():
    # Import routes after app initialization to avoid circular imports
    from routes import *
    from oauth_routes import *
    from auth_routes import *
    
    try:
        logger.info("App initialization complete")
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)