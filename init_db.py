from app import app, db
from models import User, Room, Booking, Review, Contact
from datetime import datetime

def init_database():
    with app.app_context():
        # Drop all tables using SQLAlchemy
        db.drop_all()
        db.create_all()
        
        # Create admin user
        admin = User(
            email='admin@ssparadise.com',
            name='Admin',
            is_admin=True
        )
        admin.set_password('admin123')
        
        try:
            # Add admin user
            db.session.add(admin)
            db.session.commit()
            print("Database initialized and admin user created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {str(e)}")
            raise

if __name__ == "__main__":
    init_database()