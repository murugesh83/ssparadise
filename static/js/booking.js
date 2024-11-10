document.addEventListener('DOMContentLoaded', function() {
    // Get form elements with null checks
    const bookingForm = document.getElementById('bookingForm');
    const checkInInput = document.getElementById('check_in');
    const checkOutInput = document.getElementById('check_out');
    const guestsInput = document.getElementById('guests');
    const roomIdInput = document.getElementById('room_id');
    const submitButton = bookingForm?.querySelector('button[type="submit"]');
    
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
            
            // Check availability when dates change
            checkRoomAvailability();
        });
        
        checkOutInput.addEventListener('change', checkRoomAvailability);
        
        // Form submission handler
        bookingForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Get form values with null checks
            const roomId = roomIdInput?.value;
            const checkIn = checkInInput?.value;
            const checkOut = checkOutInput?.value;
            const guestName = document.getElementById('name')?.value;
            const guestEmail = document.getElementById('email')?.value;
            const guests = guestsInput?.value;
            const paymentOption = document.querySelector('input[name="payment_option"]:checked')?.value;

            // Validate form fields
            if (!roomId || !checkIn || !checkOut || !guestName || !guestEmail || !guests || !paymentOption) {
                showAlert('Please fill in all required fields', 'warning');
                return;
            }

            // Show loading state
            if (submitButton) {
                const originalButtonText = submitButton.innerHTML;
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

                try {
                    // Check room availability before submitting
                    const response = await fetch('/api/check-room-availability', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            room_id: roomId,
                            check_in: checkIn,
                            check_out: checkOut
                        })
                    });

                    if (!response.ok) {
                        throw new Error('Failed to check availability');
                    }

                    const data = await response.json();
                    
                    if (!data.success || !data.available_rooms.includes(parseInt(roomId))) {
                        const roomData = data.rooms_count[roomId] || { available: 0, total: 0 };
                        throw new Error(`Sorry, only ${roomData.available} out of ${roomData.total} rooms are available for the selected dates.`);
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

        // Initial availability check
        checkRoomAvailability();
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

            if (submitButton) {
                if (!data.available_rooms.includes(parseInt(roomIdInput.value))) {
                    const roomData = data.rooms_count[roomIdInput.value] || { available: 0, total: 0 };
                    showAlert(`Sorry, only ${roomData.available} out of ${roomData.total} rooms are available for these dates.`, 'warning');
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
