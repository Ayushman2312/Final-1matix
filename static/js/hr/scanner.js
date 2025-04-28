document.addEventListener('DOMContentLoaded', function() {
    const video = document.getElementById('qr-video');
    const canvas = document.getElementById('qr-canvas');
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const resultElement = document.getElementById('result');
    const statusElement = document.getElementById('status');
    const videoContainer = document.getElementById('video-container');
    
    let scanning = false;
    let lastResult = null;
    let lastResultTime = 0;
    const scanInterval = 100; // Scan every 100ms
    
    // Start scanner automatically
    startScanner();
    
    function startScanner() {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            statusElement.textContent = 'Requesting camera access...';
            
            const constraints = {
                video: {
                    facingMode: "environment",
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };
            
            navigator.mediaDevices.getUserMedia(constraints)
                .then(function(stream) {
                    video.srcObject = stream;
                    video.setAttribute('playsinline', true);
                    
                    video.onloadedmetadata = function() {
                        video.play();
                        scanning = true;
                        scanQRCode();
                        statusElement.textContent = 'Scanner active - point camera at a QR code';
                    };
                })
                .catch(function(error) {
                    console.error('Error accessing camera:', error);
                    statusElement.textContent = 'Error accessing camera: ' + error.message;
                });
        } else {
            statusElement.textContent = 'Sorry, your browser does not support accessing the camera';
        }
    }
    
    function scanQRCode() {
        if (!scanning) return;
        
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
                    if (lastResult !== code.data || now - lastResultTime > 2000) {
                        lastResult = code.data;
                        lastResultTime = now;
                        
                        resultElement.textContent = code.data;
                        statusElement.textContent = 'QR code detected!';
                        
                        // Add strong vibration for feedback (works on mobile devices)
                        if (navigator.vibrate) {
                            navigator.vibrate([200, 100, 200]); // Vibrate, pause, vibrate pattern
                        }
                        
                        // Visual feedback
                        videoContainer.classList.add('detected');
                        setTimeout(() => {
                            videoContainer.classList.remove('detected');
                        }, 1000);
                        
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
        
        // Continue scanning after a short delay
        setTimeout(scanQRCode, scanInterval);
    }
});