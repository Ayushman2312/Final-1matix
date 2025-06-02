// Add getCookie function to handle CSRF token
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

// Attendance flow management
const attendanceFlow = {
    scanning: false,
    scanInterval: 100,
    lastResult: null,
    lastResultTime: 0,
    
    async init() {
        // Check for existing device ID
        const deviceId = localStorage.getItem('attendance_device_id');
        if (deviceId) {
            this.showStep('qr-scanner');
            this.initQRScanner();
        } else {
            this.showStep('email-verification');
        }
    },

    showStep(stepId) {
        document.querySelectorAll('.step').forEach(step => step.classList.add('hidden'));
        document.getElementById(stepId).classList.remove('hidden');
    },

    async sendOTP() {
        const email = document.getElementById('email-input').value;
        if (!email || !email.includes('@')) {
            alert('Please enter a valid email address');
            return;
        }
        
        try {
            const response = await fetch('/hr_management/mark-attendance/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    action: 'send_otp',
                    email: email
                })
            });
            const data = await response.json();
            if (data.success) {
                localStorage.setItem('attendance_email', email);
                this.showStep('otp-verification');
            } else {
                alert(data.error || 'Error sending OTP');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error sending OTP');
        }
    },

    async verifyOTP() {
        const otp = document.getElementById('otp-input').value;
        if (!otp) {
            alert('Please enter the OTP');
            return;
        }
        
        const email = localStorage.getItem('attendance_email');
        try {
            const response = await fetch('/hr_management/mark-attendance/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    action: 'verify_otp',
                    otp: otp,
                    email: email
                })
            });
            const data = await response.json();
            if (data.success) {
                localStorage.setItem('attendance_device_id', data.device_id);
                this.showStep('qr-scanner');
                this.initQRScanner();
            } else {
                alert(data.error || 'Invalid OTP');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error verifying OTP');
        }
    },

    // QR scanner implementation using jsQR
    async initQRScanner() {
        const video = document.getElementById('qr-video');
        const canvas = document.getElementById('qr-canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        const statusElement = document.getElementById('scan-status');
        const videoContainer = document.getElementById('video-container');
        
        statusElement.textContent = 'Requesting camera access...';
        
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            const constraints = {
                video: {
                    facingMode: "environment",
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };
            
            try {
                const stream = await navigator.mediaDevices.getUserMedia(constraints);
                video.srcObject = stream;
                video.setAttribute('playsinline', true);
                
                video.onloadedmetadata = () => {
                    video.play();
                    this.scanning = true;
                    this.scanQRCode();
                    statusElement.textContent = 'Scanner active - point camera at a QR code';
                };
            } catch (error) {
                console.error('Error accessing camera:', error);
                statusElement.textContent = 'Error accessing camera: ' + error.message;
                document.getElementById('error-details').innerText = 'Error accessing camera: ' + error.message;
                this.showStep('error-message');
            }
        } else {
            statusElement.textContent = 'Sorry, your browser does not support accessing the camera';
            document.getElementById('error-details').innerText = 'Your browser does not support camera access';
            this.showStep('error-message');
        }
    },
    
    scanQRCode() {
        if (!this.scanning) return;
        
        const video = document.getElementById('qr-video');
        const canvas = document.getElementById('qr-canvas');
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        const statusElement = document.getElementById('scan-status');
        const videoContainer = document.getElementById('video-container');
        
        if (video.readyState === video.HAVE_ENOUGH_DATA) {
            // Set canvas size to match video dimensions
            canvas.height = video.videoHeight;
            canvas.width = video.videoWidth;
            
            // Draw current video frame to canvas
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            try {
                // Get image data from canvas
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                
                // Attempt to detect QR code
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "dontInvert",
                });
                
                if (code) {
                    // Only update if it's a new result or more than 2 seconds has passed
                    const now = new Date().getTime();
                    if (this.lastResult !== code.data || now - this.lastResultTime > 2000) {
                        this.lastResult = code.data;
                        this.lastResultTime = now;
                        
                        document.getElementById('result-content').innerText = "Processing attendance...";
                        document.getElementById('scan-result').classList.remove('hidden');
                        statusElement.textContent = 'QR code detected!';
                        
                        // Add strong vibration for feedback (works on mobile devices)
                        if (navigator.vibrate) {
                            navigator.vibrate([200, 100, 200]); // Vibrate, pause, vibrate pattern
                        }
                        
                        // Visual feedback
                        videoContainer.classList.add('detected');
                        
                        // Highlight the QR code location
                        ctx.beginPath();
                        ctx.lineWidth = 4;
                        ctx.strokeStyle = "#FF3B58";
                        ctx.moveTo(code.location.topLeftCorner.x, code.location.topLeftCorner.y);
                        ctx.lineTo(code.location.topRightCorner.x, code.location.topRightCorner.y);
                        ctx.lineTo(code.location.bottomRightCorner.x, code.location.bottomRightCorner.y);
                        ctx.lineTo(code.location.bottomLeftCorner.x, code.location.bottomLeftCorner.y);
                        ctx.lineTo(code.location.topLeftCorner.x, code.location.topLeftCorner.y);
                        ctx.stroke();
                        
                        // Stop scanning and process the QR code
                        this.scanning = false;
                        try {
                            const qrData = JSON.parse(code.data);
                            this.markAttendance(qrData);
                        } catch (error) {
                            console.error("QR Parse Error:", error);
                            document.getElementById('error-details').innerText = 'Invalid QR Code format';
                            this.showStep('error-message');
                        }
                    }
                } else {
                    statusElement.textContent = 'Scanning... (No QR code detected)';
                }
            } catch (error) {
                console.error('Error processing frame:', error);
                statusElement.textContent = 'Error processing frame: ' + error.message;
            }
        } else {
            statusElement.textContent = 'Waiting for camera stream...';
        }
        
        // Continue scanning after a short delay if still in scanning mode
        if (this.scanning) {
            setTimeout(() => this.scanQRCode(), this.scanInterval);
        }
    },
    
    stopQrScanner() {
        this.scanning = false;
        const video = document.getElementById('qr-video');
        
        // Stop the camera stream if it exists
        if (video.srcObject) {
            const tracks = video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            video.srcObject = null;
        }
    },
    
    async markAttendance(qrData) {
        try {
            // Get current location
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject);
            });

            const email = localStorage.getItem('attendance_email');
            const device_id = localStorage.getItem('attendance_device_id');

            const currentLocation = {
                name: qrData.location_data.name,
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            };

            const response = await fetch('/hr_management/mark-attendance/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    action: 'mark_attendance',
                    qr_data: qrData,
                    location: currentLocation,
                    email: email,
                    device_id: device_id
                })
            });
            
            const data = await response.json();
            if (data.success) {
                document.getElementById('success-details').innerText = data.message;
                // Add status-specific styling
                const successMessage = document.getElementById('success-message');
                if (data.status === 'completed') {
                    successMessage.classList.add('bg-yellow-100');
                }
                this.showStep('success-message');
            } else {
                document.getElementById('error-details').innerText = data.error || 'Failed to mark attendance';
                this.showStep('error-message');
            }
        } catch (error) {
            console.error('Error marking attendance:', error);
            document.getElementById('error-details').innerText = 
                error.message === 'User denied Geolocation' 
                    ? 'Please enable location access to mark attendance' 
                    : 'Error connecting to server';
            this.showStep('error-message');
        } finally {
            this.stopQrScanner();
        }
    }
};

// Initialize the attendance flow
document.addEventListener('DOMContentLoaded', () => attendanceFlow.init());