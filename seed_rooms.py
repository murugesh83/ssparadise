from app import app, db
from models import Room
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_rooms():
    with app.app_context():
        try:
            # Clean up any existing sessions
            db.session.remove()
            
            # Create rooms
            single_room = Room()
            single_room.name = "Deluxe Single Room"
            single_room.description = "Comfortable single occupancy room with modern amenities including air conditioning, high-speed WiFi, LED TV, and an attached bathroom with hot water. Perfect for solo travelers seeking comfort and convenience."
            single_room.price = 1500
            single_room.capacity = 1
            single_room.room_type = "Single"
            single_room.total_rooms = 6
            single_room.image_url = "https://images.unsplash.com/photo-1631049307264-da0ec9d70304"
            single_room.amenities = ["Air Conditioning", "Free Wi-Fi", "LED TV", "Attached Bathroom"]
            single_room.available = True
            
            double_room = Room()
            double_room.name = "Premium Double Room"
            double_room.description = "Spacious room with two comfortable beds and modern amenities including air conditioning, high-speed WiFi, LED TV, and an attached bathroom with hot water. Ideal for couples or friends traveling together."
            double_room.price = 2500
            double_room.capacity = 2
            double_room.room_type = "Double"
            double_room.total_rooms = 6
            double_room.image_url = "https://images.unsplash.com/photo-1595576508898-0ad5c879a061"
            double_room.amenities = ["Air Conditioning", "Free Wi-Fi", "LED TV", "Attached Bathroom"]
            double_room.available = True
            
            # Add rooms in a single transaction
            db.session.add(single_room)
            db.session.add(double_room)
            db.session.commit()
            
            logger.info("Sample rooms have been added successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error seeding rooms: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            return False
        finally:
            db.session.remove()
            db.engine.dispose()

if __name__ == "__main__":
    seed_rooms()
