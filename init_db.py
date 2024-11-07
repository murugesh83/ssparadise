from app import app, db
from models import User, Room

def init_database():
    with app.app_context():
        # Drop and recreate all tables
        db.drop_all()
        db.create_all()
        
        # Create admin user
        admin = User(
            email='admin@ssparadise.com',
            name='Admin',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        
        print("Database initialized and admin user created successfully!")

if __name__ == "__main__":
    init_database()
