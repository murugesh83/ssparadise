from app import app, db
from models import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    with app.app_context():
        try:
            # Clean up existing sessions
            db.session.remove()
            db.engine.dispose()
            
            # Drop all tables
            db.drop_all()
            db.session.commit()
            
            # Create all tables
            db.create_all()
            db.session.commit()
            
            # Create admin user with correct credentials
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
            db.engine.dispose()

if __name__ == "__main__":
    init_database()
