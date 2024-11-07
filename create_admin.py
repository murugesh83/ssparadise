from app import app, db
from models import User

def create_admin_user():
    with app.app_context():
        # Add is_admin column if it doesn't exist
        admin_user = User.query.filter_by(email='admin@ssparadise.com').first()
        if not admin_user:
            admin = User(
                email='admin@ssparadise.com',
                name='Admin',
                is_admin=True
            )
            admin.set_password('admin123')  # Set a secure password in production
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")
        else:
            print("Admin user already exists!")

if __name__ == "__main__":
    create_admin_user()
