document.addEventListener('DOMContentLoaded', function() {
    // Safely initialize tooltips
    try {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        if (tooltipTriggerList.length > 0 && typeof bootstrap !== 'undefined') {
            tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));
        }
    } catch (e) {
        console.warn('Bootstrap tooltips initialization failed:', e);
    }

    // Room filtering and availability checking
    const roomFilterForm = document.getElementById('roomFilterForm');
    const roomFilter = document.getElementById('roomFilter');
    const checkIn = document.getElementById('checkIn');
    const checkOut = document.getElementById('checkOut');
    const availabilityCounter = document.getElementById('availabilityCounter');
    
    // Initialize date pickers if they exist
    if (checkIn && checkOut) {
        initializeDatePickers(checkIn, checkOut);
    }
    
    // Initialize room filtering if form exists
    if (roomFilterForm && checkIn && checkOut) {
        initializeRoomFiltering(roomFilterForm, roomFilter, checkIn, checkOut, availabilityCounter);
    }

    // Add real-time availability check for all room selection changes
    const roomCountSelects = document.querySelectorAll('.room-count');
    roomCountSelects.forEach(select => {
        select.addEventListener('change', function() {
            const roomId = this.closest('.room-item').dataset.roomId;
            checkRoomAvailabilityForRoom(roomId);
        });
    });

    // Enhance navbar transparency on scroll
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('navbar-scrolled');
            } else {
                navbar.classList.remove('navbar-scrolled');
            }
        });
    }
});

// Initialize date pickers with validation and real-time updates
function initializeDatePickers(checkIn, checkOut) {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    checkIn.min = today.toISOString().split('T')[0];
    checkIn.value = today.toISOString().split('T')[0];
    checkOut.min = tomorrow.toISOString().split('T')[0];
    checkOut.value = tomorrow.toISOString().split('T')[0];
    
    checkIn.addEventListener('change', function() {
        const selectedDate = new Date(this.value);
        const nextDay = new Date(selectedDate);
        nextDay.setDate(nextDay.getDate() + 1);
        checkOut.min = nextDay.toISOString().split('T')[0];
        
        if (checkOut.value && new Date(checkOut.value) <= selectedDate) {
            checkOut.value = nextDay.toISOString().split('T')[0];
        }
        
        // Update availability for all visible rooms
        updateAllRoomsAvailability();
    });
    
    checkOut.addEventListener('change', function() {
        updateAllRoomsAvailability();
    });
}

// Update availability for all visible rooms
function updateAllRoomsAvailability() {
    const visibleRooms = document.querySelectorAll('.room-item:not([style*="display: none"])');
    visibleRooms.forEach(room => {
        const roomId = room.dataset.roomId;
        if (roomId) {
            checkRoomAvailabilityForRoom(roomId);
        }
    });
}

// Check availability for a specific room
async function checkRoomAvailabilityForRoom(roomId) {
    const checkIn = document.getElementById('checkIn');
    const checkOut = document.getElementById('checkOut');
    
    if (!checkIn || !checkOut || !checkIn.value || !checkOut.value) return;
    
    try {
        const response = await fetch('/api/check-room-availability', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                room_id: roomId,
                check_in: checkIn.value,
                check_out: checkOut.value
            })
        });

        if (!response.ok) {
            throw new Error('Failed to check availability');
        }

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Error checking availability');
        }

        updateRoomAvailabilityUI(roomId, data);
        
    } catch (error) {
        console.error('Error:', error);
        showAvailabilityError(roomId, error.message);
    }
}

// Update room availability UI elements
function updateRoomAvailabilityUI(roomId, data) {
    const roomItem = document.querySelector(`.room-item[data-room-id="${roomId}"]`);
    if (!roomItem) return;

    const availabilityIndicator = roomItem.querySelector('.rooms-left');
    const roomCountSelect = roomItem.querySelector('.room-count');
    const bookButton = roomItem.querySelector('.btn-primary');
    
    const roomData = data.rooms_count[roomId];
    if (!roomData) return;

    const available = Math.min(roomData.available, 6);
    const total = Math.min(roomData.total, 6);

    // Update availability indicator
    if (availabilityIndicator) {
        availabilityIndicator.innerHTML = `
            <i class="bi bi-exclamation-circle"></i>
            ${available} out of ${total} rooms available
            <br>
            <small class="text-muted">Maximum ${total} rooms per booking</small>`;
        
        // Add visual feedback based on availability
        availabilityIndicator.className = 'rooms-left ' + 
            (available === 0 ? 'text-danger' : 
             available <= 2 ? 'text-warning' : 'text-success');
    }

    // Update room selection dropdown
    if (roomCountSelect) {
        const currentValue = parseInt(roomCountSelect.value) || 0;
        roomCountSelect.innerHTML = '';
        
        for (let i = 0; i <= available; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = i;
            roomCountSelect.appendChild(option);
        }

        // Try to maintain previous selection if possible
        if (currentValue <= available) {
            roomCountSelect.value = currentValue;
        }
    }

    // Update booking button state
    if (bookButton) {
        bookButton.disabled = available === 0;
        bookButton.title = available === 0 ? 'No rooms available for selected dates' : '';
    }
}

// Show availability error message
function showAvailabilityError(roomId, message) {
    const roomItem = document.querySelector(`.room-item[data-room-id="${roomId}"]`);
    if (!roomItem) return;

    const availabilityIndicator = roomItem.querySelector('.rooms-left');
    if (availabilityIndicator) {
        availabilityIndicator.innerHTML = `
            <i class="bi bi-exclamation-triangle text-danger"></i>
            ${message}`;
        availabilityIndicator.className = 'rooms-left text-danger';
    }
}

// Filter rooms by search term with improved feedback
function filterRoomsBySearchTerm(searchTerm, counter) {
    const visibleRooms = document.querySelectorAll('.room-item:not([style*="display: none"])');
    let visibleCount = 0;

    visibleRooms.forEach(room => {
        const roomName = room.querySelector('h5')?.textContent.toLowerCase() || '';
        const roomType = room.querySelector('.room-type')?.textContent.toLowerCase() || '';
        const description = room.querySelector('small')?.textContent.toLowerCase() || '';
        
        if (roomName.includes(searchTerm) || 
            roomType.includes(searchTerm) || 
            description.includes(searchTerm)) {
            room.style.display = '';
            visibleCount++;
        } else {
            room.style.display = 'none';
        }
    });

    if (counter) {
        counter.innerHTML = `<div class="alert ${visibleCount > 0 ? 'alert-info' : 'alert-warning'}">
            <i class="bi ${visibleCount > 0 ? 'bi-search' : 'bi-exclamation-triangle'} me-2"></i>
            ${visibleCount > 0 ? 
                `${visibleCount} room${visibleCount !== 1 ? 's' : ''} match your search` : 
                'No rooms match your search criteria'}
        </div>`;
    }

    // Update availability for visible rooms
    if (visibleCount > 0) {
        updateAllRoomsAvailability();
    }
}
