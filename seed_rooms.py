from app import app, db
from models import Room

def seed_rooms():
    # Clear existing rooms
    with app.app_context():
        Room.query.delete()
        
        # Add single cot room
        single_room = Room(
            name="Deluxe Single Room",
            description="Comfortable single occupancy room with modern amenities including air conditioning, high-speed WiFi, LED TV, and an attached bathroom with hot water. Perfect for solo travelers seeking comfort and convenience.",
            price=1500,
            capacity=1,
            room_type="Single",
            image_url="https://images.unsplash.com/photo-1631049307264-da0ec9d70304?auto=format&fit=crop&w=800",
            amenities=["Air Conditioning", "Free Wi-Fi", "LED TV", "Attached Bathroom", "Hot Water", "Room Service"]
        )
        
        # Add double cot room
        double_room = Room(
            name="Premium Double Room",
            description="Spacious room with two comfortable beds and modern amenities including air conditioning, high-speed WiFi, LED TV, and an attached bathroom with hot water. Ideal for couples or friends traveling together.",
            price=2500,
            capacity=2,
            room_type="Double",
            image_url="https://images.unsplash.com/photo-1595576508898-0ad5c879a061?auto=format&fit=crop&w=800",
            amenities=["Air Conditioning", "Free Wi-Fi", "LED TV", "Attached Bathroom", "Hot Water", "Room Service", "Mini Fridge"]
        )
        
        db.session.add(single_room)
        db.session.add(double_room)
        db.session.commit()
        print("Sample rooms have been added successfully!")

if __name__ == "__main__":
    seed_rooms()
