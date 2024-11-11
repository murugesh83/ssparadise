from app import app, db
from models import User
import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    with app.app_context():
        try:
            # Clean up existing sessions and connections
            db.session.remove()
            db.engine.dispose()
            
            # Drop and recreate tables
            db.drop_all()
            db.create_all()
            
            # Create admin user with proper transaction handling
            admin = User(
                email='admin@ssparadise.com',
                name='Admin',
                is_admin=True
            )
            admin.set_password('admin123')
            
            db.session.add(admin)
            db.session.commit()
            
            print("Database initialized successfully!")
            return True
            
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            db.session.rollback()
            return False
        finally:
            db.session.remove()
            db.engine.dispose()

if __name__ == "__main__":
    init_database()
