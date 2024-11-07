from app import app, db
from models import User

with app.app_context():
    # Create tables
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
    
    print("Admin user created successfully!")
