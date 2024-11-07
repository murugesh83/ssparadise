document.addEventListener('DOMContentLoaded', function() {
    const bookingForm = document.getElementById('bookingForm');
    
    if (bookingForm) {
        bookingForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const checkIn = document.getElementById('check_in').value;
            const checkOut = document.getElementById('check_out').value;
            const roomId = document.getElementById('room_id').value;

            try {
                const response = await fetch('/api/check-availability', {
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
                
                if (!data.available) {
                    const message = data.error || 'Sorry, this room is not available for the selected dates.';
                    alert(message);
                    return;
                }
                
                bookingForm.submit();
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
            }
        });

        // Date input validation
        const checkInInput = document.getElementById('check_in');
        const checkOutInput = document.getElementById('check_out');

        checkInInput.min = new Date().toISOString().split('T')[0];
        
        checkInInput.addEventListener('change', function() {
            checkOutInput.min = this.value;
        });
    }
});
