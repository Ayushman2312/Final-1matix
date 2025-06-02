function openPopup() {
    document.getElementById('employeePopup').classList.remove('hidden');
}

function closePopup() {
    document.getElementById('employeePopup').classList.add('hidden');
}

async function sendOtp() {
    const email = document.getElementById('employeeEmail').value;
    const departmentId = document.getElementById('departmentSelect').value;
    
    if (!email || !departmentId) {
        Swal.fire({
            icon: 'error',
            title: 'Error!',
            text: 'Please fill in all required fields'
        });
        return;
    }

    try {
        const response = await fetch('/masteradmin/create_employee/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                email: email,
                department: departmentId
            })
        });

        let data;
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            data = { message: await response.text() };
        }

        if (response.ok) {
            Swal.fire({
                icon: 'success',
                title: 'Success!',
                text: data.message || 'OTP sent successfully!'
            });
            // Clear form fields after successful submission
            document.getElementById('employeeEmail').value = '';
            document.getElementById('departmentSelect').value = '';
        } else {
            throw new Error(data.message || 'Failed to send OTP');
        }
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error!',
            text: error.message || 'An error occurred'
        });
        console.error('Error:', error);
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
function toggleAddEmployee() {
    const content = document.getElementById('addEmployeeContent');
    const arrow = document.getElementById('toggleArrow');
    
    if (content.classList.contains('hidden')) {
        content.classList.remove('hidden');
        setTimeout(() => {
            content.classList.remove('opacity-0', '-translate-y-4');
            arrow.classList.add('rotate-180');
        }, 10);
    } else {
        content.classList.add('opacity-0', '-translate-y-4');
        arrow.classList.remove('rotate-180');
        setTimeout(() => {
            content.classList.add('hidden');
        }, 300);
    }
}