document.addEventListener('DOMContentLoaded', function() {
    // Get form elements
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
    
    if (bookingForm && checkInInput && checkOutInput) {
        // Set minimum dates
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        checkInInput.min = today.toISOString().split('T')[0];
        checkInInput.value = today.toISOString().split('T')[0];
        checkOutInput.min = tomorrow.toISOString().split('T')[0];
        checkOutInput.value = tomorrow.toISOString().split('T')[0];
        
        // Update checkout min date when checkin changes
        checkInInput.addEventListener('change', function() {
            const selectedDate = new Date(this.value);
            const nextDay = new Date(selectedDate);
            nextDay.setDate(nextDay.getDate() + 1);
            checkOutInput.min = nextDay.toISOString().split('T')[0];
            
            if (checkOutInput.value && new Date(checkOutInput.value) <= selectedDate) {
                checkOutInput.value = nextDay.toISOString().split('T')[0];
            }
            
            updateBookingSummary();
            checkRoomAvailability();
        });
        
        // Update summary when checkout date changes
        checkOutInput.addEventListener('change', function() {
            updateBookingSummary();
            checkRoomAvailability();
        });
        
        // Update summary when number of rooms changes
        numRoomsInput?.addEventListener('change', function() {
            updateBookingSummary();
            updateMaxGuests();
        });
        
        // Update summary when number of guests changes
        guestsInput?.addEventListener('change', updateBookingSummary);
        
        // Form submission handler with validation
        bookingForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!validateForm()) {
                return;
            }
            
            // Show loading state
            if (submitButton) {
                const originalButtonText = submitButton.innerHTML;
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

                try {
                    // Check final room availability before submitting
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
                    
                    // If available, submit the form
                    bookingForm.submit();
                } catch (error) {
                    console.error('Error:', error);
                    showAlert(error.message || 'An error occurred. Please try again.', 'danger');
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalButtonText;
                }
            }
        });

        // Initialize booking summary
        updateBookingSummary();
        checkRoomAvailability();
    }
    
    // Function to update booking summary
    function updateBookingSummary() {
        if (!checkInInput?.value || !checkOutInput?.value) return;
        
        const checkIn = new Date(checkInInput.value);
        const checkOut = new Date(checkOutInput.value);
        const nights = Math.ceil((checkOut - checkIn) / (1000 * 60 * 60 * 24));
        const rooms = parseInt(numRoomsInput?.value || 1);
        const guests = parseInt(guestsInput?.value || 1);
        const roomPrice = parseFloat(roomPriceInput?.value || 0);
        
        // Update stay duration
        if (stayDurationEl) {
            stayDurationEl.textContent = `${checkIn.toLocaleDateString()} - ${checkOut.toLocaleDateString()} (${nights} night${nights !== 1 ? 's' : ''})`;
        }
        
        // Update room configuration
        if (roomConfigEl) {
            roomConfigEl.textContent = `${rooms} room${rooms !== 1 ? 's' : ''}, ${guests} guest${guests !== 1 ? 's' : ''}`;
        }
        
        // Update number of nights
        if (numberOfNightsEl) {
            numberOfNightsEl.innerHTML = `
                <span>Number of nights</span>
                <span>${nights}</span>
            `;
        }
        
        // Update number of rooms
        if (numberOfRoomsEl) {
            numberOfRoomsEl.innerHTML = `
                <span>Number of rooms</span>
                <span>${rooms}</span>
            `;
        }
        
        // Calculate and update total amount
        if (totalAmountEl) {
            const total = roomPrice * nights * rooms;
            totalAmountEl.textContent = `₹${total.toFixed(2)}`;
        }
    }
    
    // Function to update max guests based on number of rooms
    function updateMaxGuests() {
        if (!guestsInput || !numRoomsInput) return;
        
        const maxGuestsPerRoom = parseInt(guestsInput.getAttribute('max') || guestsInput.options.length);
        const rooms = parseInt(numRoomsInput.value);
        const totalMaxGuests = maxGuestsPerRoom * rooms;
        
        // Update guests dropdown options
        const currentGuests = parseInt(guestsInput.value);
        guestsInput.innerHTML = '';
        
        for (let i = 1; i <= totalMaxGuests; i++) {
            const option = document.createElement('option');
            option.value = i;
            option.textContent = i;
            guestsInput.appendChild(option);
        }
        
        // Try to keep current selection if possible
        if (currentGuests <= totalMaxGuests) {
            guestsInput.value = currentGuests;
        }
    }
    
    // Function to validate form
    function validateForm() {
        const checkIn = new Date(checkInInput.value);
        const checkOut = new Date(checkOutInput.value);
        
        if (checkOut <= checkIn) {
            showAlert('Check-out date must be after check-in date', 'warning');
            return false;
        }
        
        if (checkIn < new Date().setHours(0,0,0,0)) {
            showAlert('Check-in date cannot be in the past', 'warning');
            return false;
        }
        
        return true;
    }
    
    // Function to check room availability
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

            const roomData = data.rooms_count[roomIdInput.value] || { available: 0, total: 0 };
            
            // Update number of rooms dropdown
            if (numRoomsInput) {
                const currentRooms = parseInt(numRoomsInput.value);
                numRoomsInput.innerHTML = '';
                
                for (let i = 1; i <= roomData.available; i++) {
                    const option = document.createElement('option');
                    option.value = i;
                    option.textContent = i;
                    numRoomsInput.appendChild(option);
                }
                
                // Try to keep current selection if possible
                if (currentRooms <= roomData.available) {
                    numRoomsInput.value = currentRooms;
                }
                
                // Update max guests after updating rooms
                updateMaxGuests();
            }
            
            if (submitButton) {
                if (!data.available_rooms.includes(parseInt(roomIdInput.value))) {
                    showAlert(`Sorry, no rooms are available for these dates.`, 'warning');
                    submitButton.disabled = true;
                } else {
                    submitButton.disabled = false;
                    // Remove any existing warning alerts
                    document.querySelectorAll('.alert-warning').forEach(alert => alert.remove());
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showAlert(error.message || 'Error checking room availability', 'danger');
            if (submitButton) {
                submitButton.disabled = true;
            }
        }
    }
});

// Helper function to show alerts
function showAlert(message, type = 'warning') {
    // Remove any existing alerts
    document.querySelectorAll('.alert').forEach(alert => alert.remove());

    const form = document.getElementById('bookingForm');
    if (!form) return;

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    form.insertAdjacentElement('beforebegin', alertDiv);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}
