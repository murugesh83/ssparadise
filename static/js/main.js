document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if bootstrap is available
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (tooltipTriggerList.length > 0 && typeof bootstrap !== 'undefined') {
        const tooltipList = [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
    }

    // Get form elements with proper null checks
    const roomFilterForm = document.querySelector('#roomFilterForm');
    const roomFilter = document.querySelector('#roomFilter');
    const checkIn = document.querySelector('#checkIn');
    const checkOut = document.querySelector('#checkOut');
    const availabilityCounter = document.querySelector('#availabilityCounter');

    // Initialize date pickers if they exist
    if (checkIn && checkOut) {
        initializeDatePickers(checkIn, checkOut);
    }
    
    // Initialize room filtering if all required elements exist
    if (roomFilterForm && checkIn && checkOut && availabilityCounter) {
        initializeRoomFiltering(roomFilterForm, roomFilter, checkIn, checkOut, availabilityCounter);
    }

    // Handle room quantity selection
    const roomQuantitySelects = document.querySelectorAll('select.room-count');
    if (roomQuantitySelects.length > 0) {
        roomQuantitySelects.forEach(select => {
            select.addEventListener('change', function() {
                const roomItem = this.closest('.room-item');
                if (roomItem) {
                    const roomId = roomItem.getAttribute('data-room-id');
                    if (roomId) {
                        updateAvailabilityDisplay(roomId, parseInt(this.value));
                    }
                }
            });
        });
    }
});

// Initialize date pickers with validation
function initializeDatePickers(checkIn, checkOut) {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    checkIn.min = today.toISOString().split('T')[0];
    checkIn.value = checkIn.value || today.toISOString().split('T')[0];
    checkOut.min = tomorrow.toISOString().split('T')[0];
    checkOut.value = checkOut.value || tomorrow.toISOString().split('T')[0];
    
    checkIn.addEventListener('change', function() {
        const selectedDate = new Date(this.value);
        const nextDay = new Date(selectedDate);
        nextDay.setDate(nextDay.getDate() + 1);
        checkOut.min = nextDay.toISOString().split('T')[0];
        
        if (checkOut.value && new Date(checkOut.value) <= selectedDate) {
            checkOut.value = nextDay.toISOString().split('T')[0];
        }
        
        const form = this.closest('form');
        if (form) {
            form.dispatchEvent(new Event('submit'));
        }
    });
    
    checkOut.addEventListener('change', function() {
        const form = this.closest('form');
        if (form) {
            form.dispatchEvent(new Event('submit'));
        }
    });
}

// Initialize room filtering functionality
function initializeRoomFiltering(form, filter, checkIn, checkOut, counter) {
    if (!form || !checkIn || !checkOut || !counter) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        try {
            const response = await fetch('/api/check-room-availability', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    check_in: checkIn.value,
                    check_out: checkOut.value
                })
            });

            if (!response.ok) {
                throw new Error('Failed to check room availability');
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Error checking availability');
            }

            updateRoomAvailability(data, counter);
            
        } catch (error) {
            console.error('Error:', error);
            showAlert(error.message || 'Error checking room availability', 'danger');
        }
    });

    if (filter) {
        filter.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            filterRoomsBySearchTerm(searchTerm, counter);
        });
    }

    // Trigger initial availability check
    form.dispatchEvent(new Event('submit'));
}

// Update room availability display
function updateRoomAvailability(data, counter) {
    const roomItems = document.querySelectorAll('.room-item');
    let visibleRooms = 0;

    roomItems.forEach(item => {
        if (!item) return;
        
        const roomId = item.getAttribute('data-room-id');
        if (!roomId) return;

        const roomQuantitySelect = item.querySelector('select.room-count');
        const roomsLeft = item.querySelector('.rooms-left');
        
        if (data.available_rooms.includes(parseInt(roomId))) {
            const availableCount = data.rooms_count[roomId] || 0;
            item.style.display = 'table-row';
            visibleRooms++;

            if (roomQuantitySelect) {
                roomQuantitySelect.innerHTML = '';
                for (let i = 0; i <= availableCount; i++) {
                    const option = document.createElement('option');
                    option.value = i;
                    option.textContent = i;
                    roomQuantitySelect.appendChild(option);
                }
            }

            if (roomsLeft) {
                roomsLeft.innerHTML = `
                    <i class="bi bi-exclamation-circle"></i>
                    Only ${availableCount} room${availableCount !== 1 ? 's' : ''} of this type left
                `;
            }
        } else {
            item.style.display = 'none';
        }
    });

    updateAvailabilityCounter(counter, visibleRooms);
}

// Update availability counter display
function updateAvailabilityCounter(counter, visibleRooms) {
    if (!counter) return;
    
    counter.innerHTML = `
        <div class="alert alert-info">
            <i class="bi bi-calendar-check me-2"></i>
            ${visibleRooms} room${visibleRooms !== 1 ? 's' : ''} available
        </div>`;
}

// Filter rooms by search term
function filterRoomsBySearchTerm(searchTerm, counter) {
    const roomItems = document.querySelectorAll('.room-item');
    let visibleCount = 0;

    roomItems.forEach(item => {
        if (!item || item.style.display === 'none') return;
        
        const roomName = item.querySelector('h5')?.textContent.toLowerCase() || '';
        const roomType = item.querySelector('.room-type')?.textContent.toLowerCase() || '';
        
        if (roomName.includes(searchTerm) || roomType.includes(searchTerm)) {
            item.style.display = 'table-row';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });

    updateAvailabilityCounter(counter, visibleCount);
}

// Show alert messages
function showAlert(message, type = 'warning') {
    const container = document.querySelector('.container');
    if (!container) return;  // Exit if no container found
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        if (alertDiv && alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Update availability display for room quantity changes
function updateAvailabilityDisplay(roomId, quantity) {
    if (!roomId) return;
    
    const roomItem = document.querySelector(`.room-item[data-room-id="${roomId}"]`);
    if (!roomItem) return;

    const bookButton = roomItem.querySelector('.btn-primary');
    if (bookButton) {
        bookButton.disabled = quantity === 0;
    }
}
