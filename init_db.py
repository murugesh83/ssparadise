from app import app, db
from models import User, Room, Booking, Review, Contact

def init_database():
    with app.app_context():
        try:
            # Ensure clean state
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
            
            # Add and commit in a transaction
            db.session.begin()
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

if __name__ == "__main__":
    init_database()
