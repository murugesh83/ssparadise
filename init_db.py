from app import app, db
from models import User, Room, Booking, Review, Contact
import logging
from sqlalchemy import text
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    with app.app_context():
        try:
            # Clean up any existing sessions and connections
            db.session.remove()
            db.engine.dispose()
            
            # Wait for database to be ready
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # Check if database is accessible
                    with db.engine.connect() as conn:
                        conn.execute(text('SELECT 1'))
                        logger.info("Database connection successful")
                        break
                except Exception as e:
                    retry_count += 1
                    if retry_count == max_retries:
                        raise e
                    logger.warning(f"Database not ready, retrying... ({retry_count}/{max_retries})")
                    time.sleep(2)
            
            # Drop all existing tables
            logger.info("Dropping all tables...")
            db.drop_all()
            logger.info("All tables dropped successfully")
            
            # Create all tables
            logger.info("Creating new tables...")
            db.create_all()
            logger.info("All tables created successfully")
            
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
            logger.info("Admin user created successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during database initialization: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return False
        finally:
            try:
                db.session.remove()
                db.engine.dispose()
            except:
                pass

if __name__ == "__main__":
    try:
        success = init_database()
        if not success:
            logger.error("Database initialization failed")
            exit(1)
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {str(e)}")
        exit(1)
