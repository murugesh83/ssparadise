from app import app, db
from models import User, Room, Booking, Review, Contact

def init_database():
    with app.app_context():
        try:
            # Ensure all existing transactions are cleaned up
            db.session.close()
            db.session.remove()
            
            # Drop all tables
            db.drop_all()
            
            # Create tables
            db.create_all()
            
            # Create admin user if not exists
            admin = User(
                email='admin@ssparadise.com',
                name='Admin',
                is_admin=True
            )
            admin.set_password('admin123')
            
            # Add admin user in a new transaction
            db.session.add(admin)
            db.session.commit()
            
            print("Database initialized successfully!")
            return True
            
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return False
            
        finally:
            db.session.remove()

if __name__ == "__main__":
    init_database()
