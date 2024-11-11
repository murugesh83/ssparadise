document.addEventListener('DOMContentLoaded', function() {
    // Get form elements with improved error handling
    const bookingForm = document.getElementById('bookingForm');
    const checkInInput = document.getElementById('check_in');
    const checkOutInput = document.getElementById('check_out');
    const guestsInput = document.getElementById('guests');
    const numRoomsInput = document.getElementById('num_rooms');
    const roomIdInput = document.getElementById('room_id');
    const roomPriceInput = document.getElementById('room_price');
    const submitButton = bookingForm?.querySelector('button[type="submit"]');
    
    // Get summary elements
    const stayDurationEl = document.getElementById('stayDuration');
    const roomConfigEl = document.getElementById('roomConfig');
    const numberOfNightsEl = document.getElementById('numberOfNights');
    const numberOfRoomsEl = document.getElementById('numberOfRooms');
    const totalAmountEl = document.getElementById('totalAmount');
    
    // Enhanced availability checking
    let availabilityCheckTimeout;
    const AVAILABILITY_CHECK_DELAY = 500; // ms

    // Initialize tooltips with error handling
    try {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        if (tooltipTriggerList.length > 0 && typeof bootstrap !== 'undefined') {
            tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));
        }
    } catch (e) {
        console.warn('Bootstrap tooltips initialization failed:', e);
    }
    
    if (bookingForm && checkInInput && checkOutInput) {
        // Enhanced date initialization with validation
        initializeDates();
        
        // Add real-time availability check for all room selection changes
        checkInInput.addEventListener('change', handleDateChange);
        checkOutInput.addEventListener('change', handleDateChange);
        numRoomsInput?.addEventListener('change', handleRoomCountChange);
        guestsInput?.addEventListener('change', handleGuestCountChange);

        // Enhanced form submission with real-time validation
        bookingForm.addEventListener('submit', handleFormSubmit);
    }

    // Initialize dates with improved validation
    function initializeDates() {
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        checkInInput.min = today.toISOString().split('T')[0];
        checkInInput.value = today.toISOString().split('T')[0];
        checkOutInput.min = tomorrow.toISOString().split('T')[0];
        checkOutInput.value = tomorrow.toISOString().split('T')[0];
        
        updateBookingSummary();
        checkRoomAvailability();
    }

    // Enhanced date change handler with debouncing
    function handleDateChange(event) {
        if (event.target.id === 'check_in') {
            const selectedDate = new Date(event.target.value);
            const nextDay = new Date(selectedDate);
            nextDay.setDate(nextDay.getDate() + 1);
            
            checkOutInput.min = nextDay.toISOString().split('T')[0];
            
            if (checkOutInput.value && new Date(checkOutInput.value) <= selectedDate) {
                checkOutInput.value = nextDay.toISOString().split('T')[0];
                showFeedback('Check-out date automatically adjusted', 'info');
            }
        }
        
        updateBookingSummary();
        
        // Debounce availability check
        clearTimeout(availabilityCheckTimeout);
        availabilityCheckTimeout = setTimeout(() => {
            checkRoomAvailability();
        }, AVAILABILITY_CHECK_DELAY);
    }

    // Enhanced room count change handler
    function handleRoomCountChange() {
        const maxRooms = parseInt(numRoomsInput.getAttribute('max') || 6);
        const selectedRooms = parseInt(numRoomsInput.value);
        
        if (selectedRooms > maxRooms) {
            showFeedback(`Maximum ${maxRooms} rooms allowed per booking`, 'warning');
            numRoomsInput.value = maxRooms;
        }
        
        updateBookingSummary();
        updateMaxGuests();
        checkRoomAvailability();
    }

    // Enhanced guest count handler
    function handleGuestCountChange() {
        const maxGuests = parseInt(guestsInput.getAttribute('max'));
        const selectedGuests = parseInt(guestsInput.value);
        
        if (selectedGuests > maxGuests) {
            showFeedback(`Maximum ${maxGuests} guests allowed`, 'warning');
            guestsInput.value = maxGuests;
        }
        
        updateBookingSummary();
    }

    // Enhanced form submission handler with availability check
    async function handleFormSubmit(e) {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }
        
        if (submitButton) {
            const originalButtonText = submitButton.innerHTML;
            submitButton.disabled = true;
            submitButton.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2"></span>
                Processing your booking...
            `;
            
            try {
                const response = await fetch('/api/check-room-availability', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        room_id: roomIdInput.value,
                        check_in: checkInInput.value,
                        check_out: checkOutInput.value
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to check availability');
                }

                const data = await response.json();
                
                if (!data.success || !data.available_rooms.includes(parseInt(roomIdInput.value))) {
                    throw new Error('Sorry, this room is no longer available for the selected dates.');
                }
                
                this.submit();
            } catch (error) {
                console.error('Error:', error);
                showFeedback(error.message || 'An error occurred. Please try again.', 'danger');
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            }
        }
    }

    // Enhanced validation with improved feedback
    function validateForm() {
        const checkIn = new Date(checkInInput.value);
        const checkOut = new Date(checkOutInput.value);
        
        if (checkOut <= checkIn) {
            showFeedback('Check-out date must be after check-in date', 'warning');
            return false;
        }
        
        if (checkIn < new Date().setHours(0,0,0,0)) {
            showFeedback('Check-in date cannot be in the past', 'warning');
            return false;
        }
        
        return true;
    }

    // Enhanced room availability check with improved error handling
    async function checkRoomAvailability() {
        if (!roomIdInput?.value || !checkInInput?.value || !checkOutInput?.value) return;
        
        try {
            const response = await fetch('/api/check-room-availability', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    room_id: roomIdInput.value,
                    check_in: checkInInput.value,
                    check_out: checkOutInput.value
                })
            });

            if (!response.ok) {
                throw new Error('Failed to check availability');
            }

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Error checking availability');
            }

            updateAvailabilityUI(data);
        } catch (error) {
            console.error('Error:', error);
            showFeedback(error.message || 'Error checking room availability', 'danger');
            if (submitButton) {
                submitButton.disabled = true;
            }
        }
    }

    // Enhanced UI update function with animation
    function updateAvailabilityUI(data) {
        const roomData = data.rooms_count[roomIdInput.value];
        if (!roomData) return;

        // Update room selection with improved feedback
        if (numRoomsInput) {
            const currentRooms = parseInt(numRoomsInput.value);
            numRoomsInput.innerHTML = '';
            
            for (let i = 1; i <= roomData.available; i++) {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = `${i} room${i !== 1 ? 's' : ''}`;
                numRoomsInput.appendChild(option);
            }
            
            if (currentRooms <= roomData.available) {
                numRoomsInput.value = currentRooms;
            } else {
                numRoomsInput.value = roomData.available;
                showFeedback(`Number of rooms adjusted to available capacity`, 'info');
            }
            
            updateMaxGuests();
        }

        // Update booking button state
        if (submitButton) {
            if (!data.available_rooms.includes(parseInt(roomIdInput.value))) {
                submitButton.disabled = true;
                showFeedback(`Sorry, no rooms are available for these dates.`, 'warning');
            } else {
                submitButton.disabled = false;
                document.querySelectorAll('.alert-warning').forEach(alert => alert.remove());
            }
        }

        // Update availability display
        const availabilityDisplay = document.querySelector('.room-availability');
        if (availabilityDisplay) {
            availabilityDisplay.innerHTML = `
                <div class="alert ${roomData.available > 2 ? 'alert-success' : roomData.available > 0 ? 'alert-warning' : 'alert-danger'}">
                    <i class="bi ${roomData.available > 2 ? 'bi-check-circle' : 'bi-exclamation-triangle'}"></i>
                    ${roomData.available} out of ${roomData.total} rooms available
                    ${roomData.available <= 2 && roomData.available > 0 ? '<br><small class="text-muted">Book soon, rooms are filling up!</small>' : ''}
                </div>
            `;
        }
    }
    
    // Enhanced booking summary update function
    function updateBookingSummary() {
        if (!checkInInput?.value || !checkOutInput?.value) return;
        
        const checkIn = new Date(checkInInput.value);
        const checkOut = new Date(checkOutInput.value);
        const nights = Math.ceil((checkOut - checkIn) / (1000 * 60 * 60 * 24));
        const rooms = parseInt(numRoomsInput?.value || 1);
        const guests = parseInt(guestsInput?.value || 1);
        const roomPrice = parseFloat(roomPriceInput?.value || 0);
        
        // Update stay duration with improved formatting
        if (stayDurationEl) {
            stayDurationEl.innerHTML = `
                <i class="bi bi-calendar-check me-2"></i>
                ${checkIn.toLocaleDateString('en-US', { 
                    weekday: 'short', 
                    month: 'short', 
                    day: 'numeric' 
                })} - ${checkOut.toLocaleDateString('en-US', { 
                    weekday: 'short', 
                    month: 'short', 
                    day: 'numeric' 
                })}
                <br>
                <small class="text-muted">${nights} night${nights !== 1 ? 's' : ''}</small>
            `;
        }
        
        // Update room configuration with enhanced display
        if (roomConfigEl) {
            roomConfigEl.innerHTML = `
                <i class="bi bi-people me-2"></i>
                ${rooms} room${rooms !== 1 ? 's' : ''}, ${guests} guest${guests !== 1 ? 's' : ''}
                <br>
                <small class="text-muted">Max ${guestsInput?.getAttribute('max')} guests per room</small>
            `;
        }
        
        // Update price breakdown with animations
        if (numberOfNightsEl) {
            numberOfNightsEl.innerHTML = `
                <span>Number of nights</span>
                <span class="badge bg-secondary">${nights}</span>
            `;
        }
        
        if (numberOfRoomsEl) {
            numberOfRoomsEl.innerHTML = `
                <span>Number of rooms</span>
                <span class="badge bg-secondary">${rooms}</span>
            `;
        }
        
        // Calculate and update total amount with animation
        if (totalAmountEl) {
            const oldTotal = parseFloat(totalAmountEl.getAttribute('data-total') || '0');
            const newTotal = roomPrice * nights * rooms;
            
            totalAmountEl.setAttribute('data-total', newTotal);
            animateNumber(oldTotal, newTotal, value => {
                totalAmountEl.textContent = `₹${value.toFixed(2)}`;
            });
        }
    }
    
    // Enhanced max guests update function
    function updateMaxGuests() {
        if (!guestsInput || !numRoomsInput) return;
        
        const maxGuestsPerRoom = parseInt(guestsInput.getAttribute('data-max-per-room') || 2);
        const rooms = parseInt(numRoomsInput.value);
        const totalMaxGuests = maxGuestsPerRoom * rooms;
        
        // Update guests dropdown with improved UX
        const currentGuests = parseInt(guestsInput.value);
        guestsInput.innerHTML = '';
        
        for (let i = 1; i <= totalMaxGuests; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = `${i} guest${i !== 1 ? 's' : ''}`;
            guestsInput.appendChild(option);
        }
        
        // Try to keep current selection if possible
        if (currentGuests <= totalMaxGuests) {
            guestsInput.value = currentGuests;
        } else {
            guestsInput.value = totalMaxGuests;
            showFeedback(`Number of guests adjusted to maximum capacity`, 'info');
        }
    }
});

// Enhanced feedback display function
function showFeedback(message, type = 'warning') {
    // Remove any existing alerts
    document.querySelectorAll('.booking-feedback').forEach(alert => alert.remove());

    const form = document.getElementById('bookingForm');
    if (!form) return;

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show booking-feedback`;
    alertDiv.innerHTML = `
        <i class="bi ${type === 'success' ? 'bi-check-circle' : 
                      type === 'warning' ? 'bi-exclamation-triangle' : 
                      type === 'info' ? 'bi-info-circle' : 
                      'bi-x-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    form.insertAdjacentElement('beforebegin', alertDiv);
    
    // Auto dismiss after 5 seconds for non-error messages
    if (type !== 'danger') {
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
}

// Utility function to animate number changes
function animateNumber(start, end, callback) {
    const duration = 500;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const value = start + (end - start) * progress;
        callback(value);
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}