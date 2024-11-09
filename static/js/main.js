document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Room filtering and availability checking
    const roomFilterForm = document.getElementById('roomFilterForm');
    const roomFilter = document.getElementById('roomFilter');
    const checkIn = document.getElementById('checkIn');
    const checkOut = document.getElementById('checkOut');
    const availabilityCounter = document.getElementById('availabilityCounter');
    
    if (roomFilterForm && checkIn && checkOut) {
        // Set minimum dates for check-in and check-out
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        checkIn.min = today.toISOString().split('T')[0];
        checkIn.value = today.toISOString().split('T')[0];
        checkOut.min = tomorrow.toISOString().split('T')[0];
        checkOut.value = tomorrow.toISOString().split('T')[0];
        
        // Update checkout min date when checkin changes
        checkIn.addEventListener('change', function() {
            const selectedDate = new Date(this.value);
            const nextDay = new Date(selectedDate);
            nextDay.setDate(nextDay.getDate() + 1);
            checkOut.min = nextDay.toISOString().split('T')[0];
            
            if (checkOut.value && new Date(checkOut.value) <= selectedDate) {
                checkOut.value = nextDay.toISOString().split('T')[0];
            }
            
            // Trigger availability check when dates change
            roomFilterForm.dispatchEvent(new Event('submit'));
        });

        checkOut.addEventListener('change', function() {
            // Trigger availability check when dates change
            roomFilterForm.dispatchEvent(new Event('submit'));
        });

        // Handle room filter form submission
        roomFilterForm.addEventListener('submit', async function(e) {
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

                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Error checking availability');
                }

                const roomRows = document.querySelectorAll('.room-item');
                let totalRooms = 0;

                roomRows.forEach(row => {
                    const roomId = parseInt(row.getAttribute('data-room-id'));
                    const availabilityIndicator = row.querySelector('.rooms-left');
                    const roomCountSelect = row.querySelector('.room-count');
                    
                    if (data.available_rooms.includes(roomId)) {
                        row.style.display = 'table-row';
                        const roomsLeft = data.rooms_count[roomId];
                        totalRooms += roomsLeft;
                        
                        // Update rooms left count
                        if (availabilityIndicator) {
                            availabilityIndicator.textContent = 
                                `Only ${roomsLeft} room${roomsLeft !== 1 ? 's' : ''} of this type left`;
                        }
                        
                        // Update room count select options
                        if (roomCountSelect) {
                            roomCountSelect.innerHTML = '';
                            for (let i = 0; i <= roomsLeft; i++) {
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

                // Update availability counter with date range and total rooms
                const checkInDate = new Date(checkIn.value).toLocaleDateString();
                const checkOutDate = new Date(checkOut.value).toLocaleDateString();
                availabilityCounter.innerHTML = 
                    `<i class="bi bi-calendar-check me-2"></i>` +
                    `${totalRooms} room${totalRooms !== 1 ? 's' : ''} available between ` +
                    `<strong>${checkInDate}</strong> and <strong>${checkOutDate}</strong>`;
                
            } catch (error) {
                console.error('Error:', error);
                availabilityCounter.innerHTML = 
                    `<i class="bi bi-exclamation-triangle me-2"></i>${error.message || 'Error checking room availability'}`;
            }
        });

        // Text-based filtering
        if (roomFilter) {
            roomFilter.addEventListener('input', function() {
                const searchTerm = this.value.toLowerCase();
                const visibleRows = document.querySelectorAll('.room-item[style="display: table-row"]');
                let visibleCount = 0;

                visibleRows.forEach(row => {
                    const roomName = row.querySelector('h5').textContent.toLowerCase();
                    const roomType = row.querySelector('.room-type').textContent.toLowerCase();
                    
                    if (roomName.includes(searchTerm) || roomType.includes(searchTerm)) {
                        row.style.display = 'table-row';
                        visibleCount++;
                    } else {
                        row.style.display = 'none';
                    }
                });

                // Update counter for text search
                if (this.value) {
                    availabilityCounter.innerHTML = 
                        `<i class="bi bi-search me-2"></i>` +
                        `${visibleCount} room${visibleCount !== 1 ? 's' : ''} match your search`;
                } else {
                    // Trigger availability check to restore original counter
                    roomFilterForm.dispatchEvent(new Event('submit'));
                }
            });
        }

        // Trigger initial availability check
        roomFilterForm.dispatchEvent(new Event('submit'));
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
