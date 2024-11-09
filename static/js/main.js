document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Room filtering
    const roomFilter = document.getElementById('roomFilter');
    const roomFilterForm = document.getElementById('roomFilterForm');
    const checkIn = document.getElementById('checkIn');
    const checkOut = document.getElementById('checkOut');
    const availabilityCounter = document.getElementById('availabilityCounter');
    
    if (roomFilter && roomFilterForm) {
        // Set minimum dates for check-in and check-out
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        if (checkIn) {
            checkIn.min = today.toISOString().split('T')[0];
            checkIn.value = today.toISOString().split('T')[0];
        }
        
        if (checkOut) {
            checkOut.min = tomorrow.toISOString().split('T')[0];
            checkOut.value = tomorrow.toISOString().split('T')[0];
        }
        
        // Update checkout min date when checkin changes
        checkIn.addEventListener('change', function() {
            const selectedDate = new Date(this.value);
            const nextDay = new Date(selectedDate);
            nextDay.setDate(nextDay.getDate() + 1);
            checkOut.min = nextDay.toISOString().split('T')[0];
            
            if (checkOut.value && new Date(checkOut.value) <= selectedDate) {
                checkOut.value = nextDay.toISOString().split('T')[0];
            }
        });

        // Handle form submission for availability check
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

                const roomCards = document.querySelectorAll('.room-item');
                let visibleCount = 0;

                roomCards.forEach(card => {
                    const roomId = parseInt(card.getAttribute('data-room-id'));
                    if (data.available_rooms.includes(roomId)) {
                        card.style.display = 'block';
                        visibleCount++;
                    } else {
                        card.style.display = 'none';
                    }
                });

                // Update availability counter with date range
                const checkInDate = new Date(checkIn.value).toLocaleDateString();
                const checkOutDate = new Date(checkOut.value).toLocaleDateString();
                availabilityCounter.textContent = 
                    `${visibleCount} room${visibleCount !== 1 ? 's' : ''} available between ${checkInDate} and ${checkOutDate}`;
                
            } catch (error) {
                console.error('Error:', error);
                availabilityCounter.textContent = error.message || 'Error checking room availability';
            }
        });

        // Text-based filtering
        roomFilter.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const roomCards = document.querySelectorAll('.room-item[style="display: block"]');
            let visibleCount = 0;

            roomCards.forEach(card => {
                const roomName = card.querySelector('.card-title').textContent.toLowerCase();
                const roomType = card.querySelector('.room-type').textContent.toLowerCase();
                
                if (roomName.includes(searchTerm) || roomType.includes(searchTerm)) {
                    card.style.display = 'block';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            // Update counter for text search
            if (this.value) {
                availabilityCounter.textContent = `${visibleCount} room${visibleCount !== 1 ? 's' : ''} match your search`;
            } else {
                // Trigger availability check to restore original counter
                roomFilterForm.dispatchEvent(new Event('submit'));
            }
        });
    }

    // Smooth scroll for navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href && href !== '#' && href.length > 1) {
                const targetElement = document.querySelector(href);
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
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
