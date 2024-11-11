document.addEventListener('DOMContentLoaded', function() {
    const bookingForm = document.querySelector('#bookingForm');
    const checkInInput = document.querySelector('#check_in');
    const checkOutInput = document.querySelector('#check_out');
    const payNowOption = document.querySelector('#pay_now');
    const payLaterOption = document.querySelector('#pay_later');
    
    if (bookingForm && checkInInput && checkOutInput) {
        // Set minimum dates
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        checkInInput.min = today.toISOString().split('T')[0];
        checkOutInput.min = tomorrow.toISOString().split('T')[0];
        
        // Update checkout min date when checkin changes
        checkInInput.addEventListener('change', function() {
            const selectedDate = new Date(this.value);
            const nextDay = new Date(selectedDate);
            nextDay.setDate(nextDay.getDate() + 1);
            checkOutInput.min = nextDay.toISOString().split('T')[0];
            
            if (checkOutInput.value && new Date(checkOutInput.value) <= selectedDate) {
                checkOutInput.value = nextDay.toISOString().split('T')[0];
            }
        });
        
        // Form submission handler
        bookingForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const roomId = document.querySelector('#room_id')?.value;
            const checkIn = checkInInput.value;
            const checkOut = checkOutInput.value;
            const guestName = document.querySelector('#name')?.value;
            const guestEmail = document.querySelector('#email')?.value;
            const guests = document.querySelector('#guests')?.value;
            const paymentOption = document.querySelector('input[name="payment_option"]:checked')?.value;

            // Validate form fields
            if (!roomId || !checkIn || !checkOut || !guestName || !guestEmail || !guests || !paymentOption) {
                showAlert('Please fill in all required fields', 'warning');
                return;
            }

            // Show loading state
            const submitButton = bookingForm.querySelector('button[type="submit"]');
            if (!submitButton) return;

            const originalButtonText = submitButton.innerHTML;
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

            try {
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

                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || 'Error checking availability');
                }
                
                if (!data.success || !data.available_rooms.includes(parseInt(roomId))) {
                    const errorMessage = data.error || 'Sorry, this room is not available for the selected dates.';
                    showAlert(errorMessage, 'warning');
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalButtonText;
                    return;
                }
                
                // If available, submit the form
                bookingForm.submit();
            } catch (error) {
                console.error('Error:', error);
                showAlert(error.message || 'An error occurred. Please try again.', 'danger');
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            }
        });

        // Payment option selection handler
        const paymentOptions = document.querySelectorAll('input[name="payment_option"]');
        if (paymentOptions.length > 0) {
            paymentOptions.forEach(option => {
                option.addEventListener('change', function() {
                    const submitButton = bookingForm.querySelector('button[type="submit"]');
                    if (submitButton) {
                        if (this.value === 'now') {
                            submitButton.innerHTML = '<i class="bi bi-credit-card me-2"></i>Proceed to Payment';
                        } else {
                            submitButton.innerHTML = '<i class="bi bi-calendar-check me-2"></i>Confirm Booking';
                        }
                    }
                });
            });
        }
    }
});

// Helper function to show alerts
function showAlert(message, type = 'warning') {
    const form = document.querySelector('#bookingForm');
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
