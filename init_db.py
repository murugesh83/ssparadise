from app import app, db
from models import User, Room, Booking, Review, Contact
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with proper transaction handling"""
    with app.app_context():
        try:
            # Clean up any existing sessions
            db.session.remove()
            
            # Drop all tables if they exist
            logger.info("Dropping existing tables...")
            db.drop_all()
            db.session.commit()
            
            # Create all tables
            logger.info("Creating new tables...")
            db.create_all()
            db.session.commit()
            
            # Create admin user
            logger.info("Creating admin user...")
            admin = User(
                email='admin@ssparadise.com',
                name='Admin',
                is_admin=True
            )
            admin.set_password('admin123')
            
            # Add admin user
            db.session.add(admin)
            db.session.commit()
            
            logger.info("Database initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            if db.session.is_active:
                db.session.rollback()
            return False
        finally:
            db.session.remove()

if __name__ == "__main__":
    try:
        # Initialize database
        success = init_database()
        if not success:
            logger.error("Database initialization failed")
            exit(1)
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        exit(1)
