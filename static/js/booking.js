document.addEventListener('DOMContentLoaded', function() {
    const bookingForm = document.querySelector('#bookingForm');
    const checkInInput = document.querySelector('#check_in');
    const checkOutInput = document.querySelector('#check_out');
    
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
            
            const submitButton = this.querySelector('button[type="submit"]');
            if (!submitButton) return;
            
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
            
            try {
                const formData = new FormData(this);
                const response = await fetch(this.action, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('Failed to submit booking');
                }
                
                const result = await response.json();
                if (result.success) {
                    window.location.href = result.redirect_url;
                } else {
                    showAlert(result.error || 'Error processing booking', 'danger');
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert('An error occurred. Please try again.', 'danger');
            } finally {
                submitButton.disabled = false;
                submitButton.innerHTML = 'Confirm Booking';
            }
        });
    }
});

// Helper function to show alerts
function showAlert(message, type = 'warning') {
    const container = document.querySelector('.container') || document.body;
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}