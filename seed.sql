DELETE FROM room;

INSERT INTO room (name, description, price, capacity, room_type, total_rooms, image_url, amenities, available) VALUES 
('Deluxe Single Room', 'Comfortable single occupancy room with modern amenities including air conditioning, high-speed WiFi, LED TV, and an attached bathroom with hot water. Perfect for solo travelers seeking comfort and convenience.', 1500, 1, 'Single', 6, 'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?auto=format&fit=crop&w=800', '["Air Conditioning", "Free Wi-Fi", "LED TV", "Attached Bathroom", "Hot Water", "Room Service"]', 1);

INSERT INTO room (name, description, price, capacity, room_type, total_rooms, image_url, amenities, available) VALUES 
('Premium Double Room', 'Spacious room with two comfortable beds and modern amenities including air conditioning, high-speed WiFi, LED TV, and an attached bathroom with hot water. Ideal for couples or friends traveling together.', 2500, 2, 'Double', 6, 'https://images.unsplash.com/photo-1595576508898-0ad5c879a061?auto=format&fit=crop&w=800', '["Air Conditioning", "Free Wi-Fi", "LED TV", "Attached Bathroom", "Hot Water", "Room Service", "Mini Fridge"]', 1);
