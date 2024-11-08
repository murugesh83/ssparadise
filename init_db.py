from app import app, db
from models import User, Room, Booking, Review, Contact

def init_database():
    with app.app_context():
        # Drop and recreate all tables in correct order
        db.drop_all()
        
        # Create tables in order of dependencies
        # Create User table first
        db.Table('user', 
                db.MetaData(),
                db.Column('id', db.Integer, primary_key=True),
                db.Column('email', db.String(120), unique=True, nullable=False),
                db.Column('password_hash', db.String(256), nullable=False),
                db.Column('name', db.String(100), nullable=False),
                db.Column('is_admin', db.Boolean, default=False),
                db.Column('created_at', db.DateTime, default=db.func.now())
        ).create(db.engine)
        
        # Then create Room table
        db.Table('room',
                db.MetaData(),
                db.Column('id', db.Integer, primary_key=True),
                db.Column('name', db.String(100), nullable=False),
                db.Column('description', db.Text, nullable=False),
                db.Column('price', db.Float, nullable=False),
                db.Column('capacity', db.Integer, nullable=False),
                db.Column('room_type', db.String(50), nullable=False),
                db.Column('amenities', db.JSON),
                db.Column('image_url', db.String(200)),
                db.Column('available', db.Boolean, default=True)
        ).create(db.engine)
        
        # Then create all remaining tables
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
