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
            db.session.remove()
            db.drop_all()
            db.create_all()
            
            # Create admin user
            admin = User(
                email='admin@ssparadise.com',
                name='Admin',
                is_admin=True
            )
            admin.set_password('admin123')
            
            db.session.begin()
            db.session.add(admin)
            db.session.commit()
            
            logger.info("Database initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            db.session.rollback()
            raise e
        finally:
            db.session.remove()

if __name__ == "__main__":
    try:
        db.session.remove()  # Clean up any existing sessions before starting
        success = init_database()
        if not success:
            logger.error("Database initialization failed")
            exit(1)
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        exit(1)
