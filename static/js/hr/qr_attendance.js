// QR Code Attendance System
// Features:
// - First-time scan requires email/OTP verification
// - Subsequent scans work directly with trusted device/browser
// - Device trust stored in localStorage

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

// Helper function to get URL parameters
function getUrlParams() {
    const params = {};
    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);
    
    for (const [key, value] of urlParams.entries()) {
        params[key] = value;
    }
    
    return params;
}

// Main attendance system controller
const attendanceSystem = {
    html5QrCode: null,
    isScanning: false,
    urlParams: null,

    // Initialize the attendance system
    init() {
        // Get URL parameters
        this.urlParams = getUrlParams();
        
        // Check if device is already trusted
        const trustToken = this.getTrustToken();

        // Auto-mark attendance if device is trusted and URL has QR parameters
        if (trustToken && this.urlParams.auto_mark === 'true' && this.urlParams.qr_code_id && this.urlParams.secret_key) {
            // Device is trusted and we have QR parameters - auto mark attendance
            this.showSection('scanner-section');
            
            // Display a message that we're processing the attendance
            const scanStatus = document.getElementById('scan-status');
            if (scanStatus) {
                scanStatus.innerHTML = '<span class="status-dot bg-blue-500 animate-pulse"></span> Processing attendance automatically...';
            }
            
            // Process the QR attendance automatically
            this.processUrlQrAttendance();
        } else if (trustToken) {
            // Device is trusted, go directly to QR scanner
            this.showSection('scanner-section');
            this.initQrScanner();
        } else {
            // Device not trusted, show email verification
            this.showSection('email-section');
        }

        // Set up event listeners
        this.setupEventListeners();
        
        // Set up debug mode keyboard shortcut
        this.setupDebugMode();
    },

    // Process QR attendance from URL parameters
    async processUrlQrAttendance() {
        try {
            // Create QR data from URL parameters
            const qrData = {
                qr_code_id: this.urlParams.qr_code_id,
                secret_key: this.urlParams.secret_key,
                company_id: this.urlParams.company_id,
                company_name: this.urlParams.company_name,
                location_data: {
                    name: this.urlParams.location_name || 'Unknown',
                    coordinates: {}
                }
            };
            
            // Add coordinates if available
            if (this.urlParams.latitude && this.urlParams.longitude) {
                qrData.location_data.coordinates = {
                    latitude: parseFloat(this.urlParams.latitude),
                    longitude: parseFloat(this.urlParams.longitude)
                };
            }
            
            // Wait for location before marking attendance
            await this.requestLocationPermission();
            
            // Mark attendance with the QR data
            this.markAttendance(qrData);
        } catch (error) {
            console.error('Error processing attendance from URL:', error);
            this.showAlert('Error processing attendance. Please try again.', 'error');
        }
    },

    // Show the specified section and hide others
    showSection(sectionId) {
        document.querySelectorAll('.attendance-section').forEach(section => {
            section.classList.add('hidden');
        });
        document.getElementById(sectionId).classList.remove('hidden');
    },

    // Set up event listeners for buttons
    setupEventListeners() {
        // Email verification button
        const sendOtpBtn = document.getElementById('send-otp-btn');
        if (sendOtpBtn) {
            sendOtpBtn.addEventListener('click', () => this.sendOtp());
        }

        // OTP verification button
        const verifyOtpBtn = document.getElementById('verify-otp-btn');
        if (verifyOtpBtn) {
            verifyOtpBtn.addEventListener('click', () => this.verifyOtp());
        }

        // Cancel scan button
        const cancelScanBtn = document.getElementById('cancel-scan-btn');
        if (cancelScanBtn) {
            cancelScanBtn.addEventListener('click', () => {
                this.stopScanner();
                window.location.reload();
            });
        }
        
        // Test QR code generation button (for demonstration purposes)
        const generateTestQRBtn = document.getElementById('generate-test-qr');
        if (generateTestQRBtn) {
            generateTestQRBtn.addEventListener('click', () => this.generateTestQR());
        }

        // Try again buttons
        document.querySelectorAll('.try-again-btn').forEach(btn => {
            btn.addEventListener('click', () => window.location.reload());
        });

        // Add listeners for Enter key
        const emailInput = document.getElementById('email-input');
        if (emailInput) {
            emailInput.addEventListener('keyup', (e) => {
                if (e.key === 'Enter') sendOtpBtn.click();
            });
        }

        const otpInput = document.getElementById('otp-input');
        if (otpInput) {
            otpInput.addEventListener('keyup', (e) => {
                if (e.key === 'Enter') verifyOtpBtn.click();
            });
        }
    },

    // Send OTP to the provided email
    async sendOtp() {
        const emailInput = document.getElementById('email-input');
        const email = emailInput.value.trim();
        
        if (!email || !email.includes('@')) {
            this.showAlert('Please enter a valid email address', 'error');
            return;
        }

        // Show loading state
        const sendOtpBtn = document.getElementById('send-otp-btn');
        const originalBtnText = sendOtpBtn.innerHTML;
        sendOtpBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
        sendOtpBtn.disabled = true;
        
        try {
            const response = await fetch('/hr/mark-attendance/', {
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
                // Store email for later
                localStorage.setItem('attendance_email', email);
                
                // Show OTP verification section
                this.showSection('otp-section');
                document.getElementById('otp-email-display').textContent = email;
                
                // Focus OTP input
                setTimeout(() => document.getElementById('otp-input').focus(), 100);
                
                // Show success message
                this.showAlert('OTP sent to your email', 'success');
            } else {
                this.showAlert(data.error || 'Failed to send OTP', 'error');
                sendOtpBtn.innerHTML = originalBtnText;
                sendOtpBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error sending OTP:', error);
            this.showAlert('Network error. Please try again.', 'error');
            sendOtpBtn.innerHTML = originalBtnText;
            sendOtpBtn.disabled = false;
        }
    },

    // Verify the OTP entered by the user
    async verifyOtp() {
        const otpInput = document.getElementById('otp-input');
        const otp = otpInput.value.trim();
        
        if (!otp) {
            this.showAlert('Please enter the OTP sent to your email', 'error');
            return;
        }

        // Show loading state
        const verifyOtpBtn = document.getElementById('verify-otp-btn');
        const originalBtnText = verifyOtpBtn.innerHTML;
        verifyOtpBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verifying...';
        verifyOtpBtn.disabled = true;
        
        try {
            const email = localStorage.getItem('attendance_email');
            const response = await fetch('/hr/mark-attendance/', {
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
                // Store device trust token
                this.setTrustToken(data.device_id, email);
                
                // Show scanner section
                this.showSection('scanner-section');
                
                // Initialize QR scanner
                this.initQrScanner();
                
                // Show success message
                this.showAlert('Device verified successfully', 'success');
            } else {
                this.showAlert(data.error || 'Invalid OTP', 'error');
                verifyOtpBtn.innerHTML = originalBtnText;
                verifyOtpBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error verifying OTP:', error);
            this.showAlert('Network error. Please try again.', 'error');
            verifyOtpBtn.innerHTML = originalBtnText;
            verifyOtpBtn.disabled = false;
        }
    },

    // Initialize the QR scanner
    initQrScanner() {
        const qrContainer = document.getElementById('qr-scanner');
        if (!qrContainer) return;
        
        try {
            // First, request location permission explicitly before starting the scanner
            this.requestLocationPermission().then(() => {
                this.html5QrCode = new Html5Qrcode("qr-scanner");
                
                // Improved QR scanning configuration
                const config = {
                    fps: 15, // Increased from 10 for more responsive scanning
                    qrbox: (viewfinderWidth, viewfinderHeight) => {
                        // Make QR box responsive and wider based on container size
                        const minEdgePercentage = 0.7; // 70% of the smaller dimension
                        const minEdge = Math.min(viewfinderWidth, viewfinderHeight);
                        const qrboxSize = Math.floor(minEdge * minEdgePercentage);
                        return { width: qrboxSize, height: qrboxSize };
                    },
                    aspectRatio: 1.0,
                    // Use a simple format specification to avoid reference errors
                    formatsToSupport: [0] // 0 is the value for QR_CODE in Html5QrcodeSupportedFormats
                };
                
                // Start scanning
                this.isScanning = true;
                this.html5QrCode.start(
                    { facingMode: "environment" },
                    config,
                    this.onQrCodeSuccess.bind(this),
                    this.onQrCodeError.bind(this)
                ).catch(err => {
                    console.error("QR Scanner init error:", err);
                    this.showAlert('Error accessing camera: ' + err.message, 'error');
                    this.showSection('error-section');
                });
                
                // Update scanning status
                document.getElementById('scan-status').innerHTML = 
                    '<span class="w-2 h-2 bg-green-500 rounded-full inline-block mr-1"></span> Scanner active - position QR code in the center';
            }).catch(error => {
                console.error("Location permission error:", error);
                this.showAlert('Location permission is required to mark attendance. Please enable location services and try again.', 'error');
                this.showSection('error-section');
                document.getElementById('error-message').textContent = 'Location permission is required to mark attendance. Please enable location services and try again.';
            });
            
        } catch (error) {
            console.error("Error initializing QR scanner:", error);
            this.showAlert('Error initializing scanner: ' + error.message, 'error');
            this.showSection('error-section');
        }
    },

    // Request location permission explicitly
    requestLocationPermission() {
        return new Promise((resolve, reject) => {
            this.updateLocationStatus('pending', 'Requesting location permission...');
            
            if (!navigator.geolocation) {
                this.updateLocationStatus('error', 'Geolocation not supported');
                reject(new Error('Geolocation is not supported by your browser'));
                return;
            }
            
            // Request a single position to trigger the permission prompt
            navigator.geolocation.getCurrentPosition(
                position => {
                    // Permission granted
                    this.updateLocationStatus('success', 'Location permission granted');
                    resolve(position);
                },
                error => {
                    // Permission denied or error
                    this.updateLocationStatus('error', 'Location permission denied');
                    reject(error);
                },
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
            );
        });
    },

    // Handle successful QR code scan
    async onQrCodeSuccess(decodedText, decodedResult) {
        try {
            // Check if this is a URL QR code for attendance
            if (typeof decodedText === 'string' && 
                (decodedText.startsWith('http') || decodedText.startsWith('/')) && 
                decodedText.includes('/hr/attend/')) {
                
                // This is a direct attendance URL - navigate to it
                console.log("Detected attendance URL:", decodedText);
                
                // Show a message about redirect
                this.showAlert('Redirecting to attendance page...', 'info');
                
                // Stop scanner before redirecting
                this.stopScanner();
                
                // Give a short delay for the user to see the message
                setTimeout(() => {
                    window.location.href = decodedText;
                }, 1000);
                
                return;
            }
            
            // Handle other QR code formats (JSON data)
            let qrData;
            try {
                // Try to parse as JSON first
                qrData = JSON.parse(decodedText);
            } catch (e) {
                // If not valid JSON, create a basic structure
                qrData = {
                    raw_data: decodedText,
                    timestamp: new Date().toISOString()
                };
            }
            
            // Ensure qrData has required properties
            if (!qrData.company_id && !qrData.qr_code_id) {
                if (qrData.raw_data && typeof qrData.raw_data === 'string') {
                    // Try to extract an ID from the raw data
                    const idMatch = qrData.raw_data.match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i);
                    if (idMatch) {
                        qrData.qr_code_id = idMatch[0];
                    }
                }
            }
            
            // Handle the case where the QR code doesn't include all required info
            // This is mainly for testing or QR codes from other systems
            if (!qrData.location_data) {
                qrData.location_data = {
                    name: "Unknown Location",
                    coordinates: {}
                };
            }
            
            // Get user's location and mark attendance
            await this.markAttendance(qrData);
            
        } catch (error) {
            console.error('Error processing QR code:', error);
            this.showAlert(`Error processing QR code: ${error.message}`, 'error');
        }
    },

    // Handle QR code scanning errors
    onQrCodeError(error) {
        // Don't show every frame error as it fills the console
        if (!error.includes("No MultiFormat Readers") && 
            !error.includes("No barcode or QR code detected")) {
            console.log(`QR scan error: ${error}`);
        }
    },

    // Mark attendance with the scanned QR code
    async markAttendance(qrData) {
        // If we're already in the process of marking attendance, prevent duplicate submissions
        if (document.getElementById('attendance-processing')) {
            return;
        }
        
        // Create a processing indicator
        const processingIndicator = document.createElement('div');
        processingIndicator.id = 'attendance-processing';
        processingIndicator.style.display = 'none';
        document.body.appendChild(processingIndicator);
        
        try {
            // Stop the scanner
            this.stopScanner();
            
            // Prepare data to send to the server
            const position = await this.getCurrentPosition();
            const trustToken = this.getTrustToken();
            const email = localStorage.getItem('attendance_email') || '';
            
            // If we don't have location and the QR code doesn't provide it, show an error
            if (!position && (!qrData.location_data || !qrData.location_data.coordinates)) {
                this.showAlert('Location is required to mark attendance. Please enable location services.', 'error');
                this.showSection('scanner-section');
                document.body.removeChild(processingIndicator);
                this.initQrScanner();
                return;
            }
            
            // Create attendance data to send
            const attendanceData = {
                action: 'mark_attendance',
                email: email,
                device_id: trustToken,
                timestamp: new Date().toISOString(),
                method: 'qr',
                qr_code: qrData,
                location: position || {
                    // Use QR code location if device location is not available
                    latitude: qrData.location_data.coordinates.latitude,
                    longitude: qrData.location_data.coordinates.longitude,
                    accuracy: 0 // Not available when using QR code location
                }
            };
            
            // Get current attendance state
            attendanceData.action = localStorage.getItem('last_attendance_action') === 'check_in' ? 'check_out' : 'check_in';
            
            // Make request to the server
            const response = await fetch('/hr/mark-attendance/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(attendanceData)
            });
            
            const result = await response.json();
            
            // Remove processing indicator
            document.body.removeChild(processingIndicator);
            
            if (result.success) {
                // Save the last action for next time
                localStorage.setItem('last_attendance_action', attendanceData.action);
                
                // Update the success message based on action
                const actionDisplay = attendanceData.action === 'check_in' ? 'Checked In' : 'Checked Out';
                const timeDisplay = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                
                // Show success message
                const successMessage = document.getElementById('success-message');
                if (successMessage) {
                    successMessage.innerHTML = `You have successfully ${actionDisplay.toLowerCase()} at ${timeDisplay}.`;
                }
                
                // Additional details for the success page
                const companyDisplay = document.getElementById('company-display');
                if (companyDisplay) {
                    companyDisplay.textContent = qrData.company_name || 'Your Company';
                }
                
                const locationDisplay = document.getElementById('location-display');
                if (locationDisplay && qrData.location_data && qrData.location_data.name) {
                    locationDisplay.textContent = qrData.location_data.name;
                }
                
                // Show success section
                this.showSection('success-section');
                
                // Register this device if not already registered
                if (!trustToken) {
                    // Generate a unique device ID
                    const deviceId = `device_${Math.random().toString(36).substring(2, 15)}`;
                    this.setTrustToken(deviceId, email);
                }
            } else {
                this.showAlert(result.message || 'Failed to mark attendance. Please try again.', 'error');
                this.showSection('scanner-section');
                this.initQrScanner();
            }
        } catch (error) {
            console.error('Error marking attendance:', error);
            document.body.removeChild(processingIndicator);
            this.showAlert('Error marking attendance. Please try again later.', 'error');
            this.showSection('scanner-section');
            this.initQrScanner();
        }
    },

    // Get current position with enhanced accuracy
    getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation is not supported by your browser'));
                return;
            }
            
            // Update location status indicator
            this.updateLocationStatus('pending', 'Getting your location...');
            
            // Show location tracking status
            const statusElement = document.getElementById('scan-status');
            if (statusElement) {
                statusElement.innerHTML = '<span class="w-2 h-2 bg-blue-500 rounded-full inline-block mr-1 animate-pulse"></span> Getting your location...';
            }
            
            // Request location with high accuracy
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    // Check if position has acceptable accuracy
                    if (position.coords.accuracy > 100) { // More than 100 meters accuracy is poor
                        console.warn('Low location accuracy:', position.coords.accuracy, 'meters');
                        // Still resolve but with a warning
                        this.updateLocationStatus('warning', `Location obtained (accuracy: ${Math.round(position.coords.accuracy)}m)`);
                    } else {
                        this.updateLocationStatus('success', `Location obtained (accuracy: ${Math.round(position.coords.accuracy)}m)`);
                    }
                    
                    if (statusElement) {
                        statusElement.innerHTML = '<span class="w-2 h-2 bg-green-500 rounded-full inline-block mr-1"></span> Location obtained';
                    }
                    
                    resolve(position);
                },
                (error) => {
                    console.error('Geolocation error:', error.message);
                    this.updateLocationStatus('error', 'Location error');
                    
                    if (statusElement) {
                        statusElement.innerHTML = '<span class="w-2 h-2 bg-red-500 rounded-full inline-block mr-1"></span> Location error';
                    }
                    
                    // Provide more specific error messages based on the error code
                    switch(error.code) {
                        case error.PERMISSION_DENIED:
                            reject(new Error('Location access denied. Please enable location services in your browser settings.'));
                            break;
                        case error.POSITION_UNAVAILABLE:
                            reject(new Error('Your location is currently unavailable. Please try again in an open area.'));
                            break;
                        case error.TIMEOUT:
                            reject(new Error('Location request timed out. Please try again.'));
                            break;
                        default:
                            reject(error);
                    }
                },
                {
                    enableHighAccuracy: true,
                    timeout: 15000, // Increased from 10000 to allow more time for accurate location
                    maximumAge: 0
                }
            );
        });
    },

    // Update location status indicator
    updateLocationStatus(status, message) {
        const locationStatus = document.getElementById('location-status');
        if (!locationStatus) return;
        
        // Reset classes
        locationStatus.className = 'p-2 rounded-lg mb-4 flex items-center justify-center text-sm';
        
        // Set icon and colors based on status
        let icon = '<span class="w-2 h-2 bg-gray-400 rounded-full inline-block mr-2"></span>';
        
        switch(status) {
            case 'pending':
                locationStatus.classList.add('bg-blue-100', 'text-blue-700');
                icon = '<span class="w-2 h-2 bg-blue-500 rounded-full inline-block mr-2 animate-pulse"></span>';
                break;
            case 'success':
                locationStatus.classList.add('bg-green-100', 'text-green-700');
                icon = '<i class="fas fa-check-circle text-green-500 mr-2"></i>';
                break;
            case 'warning':
                locationStatus.classList.add('bg-yellow-100', 'text-yellow-700');
                icon = '<i class="fas fa-exclamation-triangle text-yellow-500 mr-2"></i>';
                break;
            case 'error':
                locationStatus.classList.add('bg-red-100', 'text-red-700');
                icon = '<i class="fas fa-times-circle text-red-500 mr-2"></i>';
                break;
            default:
                locationStatus.classList.add('bg-gray-100', 'text-gray-700');
        }
        
        locationStatus.innerHTML = `${icon}<span>${message}</span>`;
    },

    // Stop the QR scanner
    stopScanner() {
        if (this.html5QrCode && this.isScanning) {
            this.html5QrCode.stop().then(() => {
                console.log("QR Scanner stopped");
                this.isScanning = false;
            }).catch(err => {
                console.error("Error stopping QR Scanner:", err);
            });
        }
    },

    // Get device trust token from local storage
    getTrustToken() {
        const token = localStorage.getItem('attendance_trust_token');
        if (!token) return null;
        
        try {
            return JSON.parse(token);
        } catch (error) {
            console.error('Error parsing trust token:', error);
            return null;
        }
    },

    // Set device trust token in local storage
    setTrustToken(deviceId, email) {
        const token = {
            device_id: deviceId,
            email: email,
            created_at: new Date().toISOString()
        };
        
        localStorage.setItem('attendance_trust_token', JSON.stringify(token));
        // Also store email separately for backward compatibility
        localStorage.setItem('attendance_email', email);
        localStorage.setItem('attendance_device_id', deviceId);
    },

    // Clear device trust token
    clearTrustToken() {
        localStorage.removeItem('attendance_trust_token');
        localStorage.removeItem('attendance_email');
        localStorage.removeItem('attendance_device_id');
    },

    // Show alert message
    showAlert(message, type = 'info') {
        const alertBox = document.getElementById('alert-box');
        if (!alertBox) return;
        
        // Set appropriate styles
        alertBox.className = 'p-4 mb-4 rounded-lg text-sm';
        if (type === 'error') {
            alertBox.classList.add('bg-red-100', 'text-red-800');
        } else if (type === 'success') {
            alertBox.classList.add('bg-green-100', 'text-green-800');
        } else {
            alertBox.classList.add('bg-blue-100', 'text-blue-800');
        }
        
        // Set message
        alertBox.textContent = message;
        
        // Show alert
        alertBox.classList.remove('hidden');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            alertBox.classList.add('hidden');
        }, 5000);
    },

    // Generate a test QR code (for demonstration purposes)
    generateTestQR() {
        if (!this.isScanning) return;
        
        // Stop the scanner temporarily
        this.stopScanner();
        
        // Create a sample QR code data object with proper location data
        const testQRData = {
            qr_code_id: "test-" + Math.random().toString(36).substring(2, 15),
            company_id: "demo-company",
            company_name: "Demo Company",
            location_data: {
                name: "Test Office Location",
                coordinates: {
                    latitude: 0,
                    longitude: 0
                }
            },
            secret_key: "test-key-" + Math.random().toString(36).substring(2, 15),
            created_at: new Date().toISOString(),
            timestamp: new Date().toISOString()
        };
        
        // Convert to string
        const qrDataString = JSON.stringify(testQRData);
        
        // Simulate a successful QR code scan
        this.showAlert("Test QR code generated - processing", "info");
        
        // Process the test QR code as if it was scanned
        setTimeout(() => {
            this.onQrCodeSuccess(qrDataString, {});
        }, 500);
    },

    // Set up debug mode keyboard shortcut (press 'd' three times quickly)
    setupDebugMode() {
        let keyPresses = [];
        let debugKeyPattern = ['d', 'd', 'd']; // Press 'd' three times
        
        document.addEventListener('keydown', (e) => {
            // Only respond to 'd' key
            if (e.key.toLowerCase() === 'd') {
                const now = new Date().getTime();
                
                // Remove old keypresses (older than 2 seconds)
                keyPresses = keyPresses.filter(press => now - press.time < 2000);
                
                // Add this keypress
                keyPresses.push({ key: 'd', time: now });
                
                // Check if the pattern matches
                if (keyPresses.length >= 3 && 
                    keyPresses.slice(-3).every((press, i) => press.key === debugKeyPattern[i])) {
                    this.toggleDebugTools();
                    keyPresses = []; // Reset after success
                }
            }
        });
    },
    
    // Toggle debug tools visibility
    toggleDebugTools() {
        const debugTools = document.getElementById('debug-tools');
        if (debugTools) {
            debugTools.classList.toggle('hidden');
            console.log("Debug tools toggled");
        }
    }
};

// Initialize the attendance system when the document is loaded
document.addEventListener('DOMContentLoaded', () => attendanceSystem.init()); 