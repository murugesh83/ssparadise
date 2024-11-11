from app import app, db
from models import User, Room, Booking, Review, Contact

def init_database():
    with app.app_context():
        try:
            # Clean up any existing sessions and connections
            db.session.remove()
            db.engine.dispose()
            
            # Drop all existing tables
            db.drop_all()
            db.session.commit()
            
            # Create all tables
            db.create_all()
            db.session.commit()
            
            # Create admin user
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
            print(f"Error: {str(e)}")
            db.session.rollback()
            return False
        finally:
            db.session.remove()
            db.engine.dispose()

if __name__ == "__main__":
    try:
        success = init_database()
        if not success:
            print("Database initialization failed")
            exit(1)
        print("Database initialization completed successfully")
    except Exception as e:
        print(f"Unexpected error during database initialization: {str(e)}")
        exit(1)