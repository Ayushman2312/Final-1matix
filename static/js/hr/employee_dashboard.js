// employee_dashboard.js
// This file provides additional functionality for the employee dashboard

// Helper function to get CSRF token
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

// Initialize event listeners when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard functionality
    initDashboard();
});

function initDashboard() {
    // Set up event listeners for attendance features
    setupAttendanceListeners();
    
    // Initialize any charts or visualizations
    initDashboardCharts();
}

function setupAttendanceListeners() {
    // Quick Attendance Button
    const quickAttendanceBtn = document.getElementById('quickAttendanceBtn');
    if (quickAttendanceBtn) {
        quickAttendanceBtn.addEventListener('click', function() {
            if (this.hasAttribute('disabled') || this.classList.contains('cursor-not-allowed')) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Account Pending Approval',
                    text: 'You need to wait for your account to be approved before using this feature.',
                    confirmButtonColor: '#6366F1'
                });
                return;
            }
            
            handleAttendanceAction(this);
        });
    }
    
    // QR Scanner Modal
    const markAttendanceBtn = document.getElementById('markAttendanceBtn');
    const qrScannerModal = document.getElementById('qrScannerModal');
    const closeQrScannerBtn = document.getElementById('closeQrScannerBtn');
    
    if (markAttendanceBtn && qrScannerModal) {
        markAttendanceBtn.addEventListener('click', function(e) {
            // If link is disabled, show warning instead of following the link
            if (this.hasAttribute('disabled') || this.classList.contains('cursor-not-allowed')) {
                e.preventDefault();
                Swal.fire({
                    icon: 'warning',
                    title: 'Account Pending Approval',
                    text: 'You need to wait for your account to be approved before using this feature.',
                    confirmButtonColor: '#6366F1'
                });
                return;
            }
            
            // Show info about location requirement
            Swal.fire({
                icon: 'info',
                title: 'Location Requirement',
                html: 'For attendance marking, please note:<br><br>' +
                      '• You must be within <b>20 meters</b> of the attendance location<br>' +
                      '• Your device location services must be enabled<br>' +
                      '• The QR code must be scanned at the actual attendance location',
                confirmButtonColor: '#6366F1',
                confirmButtonText: 'Proceed to Attendance'
            }).then((result) => {
                if (result.isConfirmed) {
                    // Continue with the normal link behavior
                    window.location.href = markAttendanceBtn.getAttribute('href');
                }
            });
            
            // Prevent the default link behavior
            e.preventDefault();
        });
    }
}

function handleAttendanceAction(button) {
    // Show loading state
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin mr-1.5 text-[10px]"></i>Processing...';
    button.disabled = true;
    
    // Get action type from button
    const action = button.dataset.action || 'check_in';
    
    // Send attendance request
    fetch('/hr/api/mark-attendance/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            action: action,
            method: 'button'
        })
    })
    .then(response => response.json())
    .then(data => {
        button.disabled = false;
        
        if(data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Success!',
                text: data.message || 'Attendance marked successfully',
                showConfirmButton: false,
                timer: 2000
            }).then(() => {
                window.location.reload();
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.message || 'Failed to mark attendance',
                confirmButtonColor: '#6366F1'
            });
            button.innerHTML = originalText;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'An unexpected error occurred. Please try again.',
            confirmButtonColor: '#6366F1'
        });
        button.disabled = false;
        button.innerHTML = originalText;
    });
}

// Initialize dashboard charts if they exist
function initDashboardCharts() {
    // Attendance Chart
    const attendanceChartEl = document.getElementById('attendanceChart');
    if (attendanceChartEl) {
        try {
            const ctx = attendanceChartEl.getContext('2d');
            const presentDays = parseInt(attendanceChartEl.getAttribute('data-present') || 0);
            const totalDays = parseInt(attendanceChartEl.getAttribute('data-total') || 30);
            const absentDays = totalDays - presentDays;
            
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Present', 'Absent'],
                    datasets: [{
                        data: [presentDays, absentDays],
                        backgroundColor: [
                            'rgba(16, 185, 129, 0.8)',  // Green for present
                            'rgba(229, 231, 235, 0.8)'  // Gray for absent
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    cutout: '75%',
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.formattedValue || '';
                                    return `${label}: ${value} days`;
                                }
                            }
                        }
                    },
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        } catch (error) {
            console.error('Error initializing attendance chart:', error);
        }
    }
} 