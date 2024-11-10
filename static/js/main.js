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
    const roomFilterForm = document.querySelector('#roomFilterForm');
    const roomFilter = document.querySelector('#roomFilter');
    const checkIn = document.querySelector('#checkIn');
    const checkOut = document.querySelector('#checkOut');
    const availabilityCounter = document.querySelector('#availabilityCounter');
    
    // Initialize date pickers if they exist
    if (checkIn && checkOut) {
        initializeDatePickers(checkIn, checkOut);
    }
    
    // Initialize room filtering if form exists
    if (roomFilterForm && checkIn && checkOut) {
        initializeRoomFiltering(roomFilterForm, roomFilter, checkIn, checkOut, availabilityCounter);
    }

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

// Initialize date pickers with validation
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
        
        // Trigger availability check when dates change
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
    // Handle room filter form submission
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
            if (counter) {
                counter.innerHTML = 
                    `<i class="bi bi-exclamation-triangle me-2"></i>${error.message || 'Error checking room availability'}`;
            }
        }
    });

    // Text-based filtering if filter input exists
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
    const roomRows = document.querySelectorAll('.room-item');
    let totalAvailable = 0;
    let totalCapacity = 0;

    if (!roomRows.length) return;

    roomRows.forEach(row => {
        const roomId = parseInt(row.getAttribute('data-room-id'));
        const availabilityIndicator = row.querySelector('.rooms-left');
        const roomCountSelect = row.querySelector('.room-count');
        
        if (data.available_rooms.includes(roomId)) {
            row.style.display = 'table-row';
            const roomData = data.rooms_count[roomId];
            const available = roomData.available;
            const total = roomData.total;
            
            totalAvailable += available;
            totalCapacity += total;
            
            if (availabilityIndicator) {
                availabilityIndicator.innerHTML = 
                    `<i class="bi bi-exclamation-circle"></i> ` +
                    `Only ${available} out of ${total} room${total !== 1 ? 's' : ''} available`;
            }
            
            if (roomCountSelect) {
                roomCountSelect.innerHTML = '';
                for (let i = 0; i <= available; i++) {
                    const option = document.createElement('option');
                    option.value = i;
                    option.textContent = i;
                    roomCountSelect.appendChild(option);
                }
            }
        } else {
            row.style.display = 'none';
        }
    });

    if (counter) {
        const checkInDate = new Date(document.querySelector('#checkIn').value).toLocaleDateString();
        const checkOutDate = new Date(document.querySelector('#checkOut').value).toLocaleDateString();
        counter.innerHTML = 
            `<i class="bi bi-calendar-check me-2"></i>` +
            `${totalAvailable} out of ${totalCapacity} rooms available between ` +
            `<strong>${checkInDate}</strong> and <strong>${checkOutDate}</strong>`;
    }
}

// Filter rooms by search term
function filterRoomsBySearchTerm(searchTerm, counter) {
    const visibleRows = document.querySelectorAll('.room-item[style="display: table-row"]');
    let totalAvailable = 0;
    let totalCapacity = 0;

    if (!visibleRows.length) return;

    visibleRows.forEach(row => {
        const roomName = row.querySelector('h5');
        const roomType = row.querySelector('.room-type');
        const availabilityText = row.querySelector('.rooms-left').textContent;
        const [available, total] = availabilityText.match(/(\d+)/g).map(Number);
        
        if (roomName && roomType) {
            const name = roomName.textContent.toLowerCase();
            const type = roomType.textContent.toLowerCase();
            
            if (name.includes(searchTerm) || type.includes(searchTerm)) {
                row.style.display = 'table-row';
                totalAvailable += available;
                totalCapacity += total;
            } else {
                row.style.display = 'none';
            }
        }
    });

    if (counter) {
        if (searchTerm) {
            counter.innerHTML = 
                `<i class="bi bi-search me-2"></i>` +
                `${totalAvailable} out of ${totalCapacity} rooms match your search`;
        } else {
            // Trigger availability check to restore original counter
            document.querySelector('#roomFilterForm')?.dispatchEvent(new Event('submit'));
        }
    }
}
