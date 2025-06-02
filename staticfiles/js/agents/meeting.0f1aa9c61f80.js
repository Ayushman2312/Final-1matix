window.startMeeting = startMeeting;
window.closePhotoModal = closePhotoModal;
window.capturePhoto = capturePhoto;
window.fetchMeetingStats = fetchMeetingStats;
window.endMeeting = endMeeting;

let videoStream;
let mediaRecorder;
let position;
let meetingTimer;
let timerInterval;
let startTime;
let audioChunks = [];
let capturedPhotos = [];
let recordedAudio = [];

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
            recordedAudio.push({
                chunk: event.data,
                timestamp: new Date().toISOString()
            });
            console.log('Audio chunk recorded at:', new Date().toISOString());
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
            const formData = new FormData();
            formData.append("audio_file", audioBlob, "meeting_audio.wav");
            formData.append("action", "upload_audio");
            formData.append("meeting_id", sessionStorage.getItem('currentMeetingId'));

            try {
                await fetch("/agents/meetings/", {
                    method: "POST",
                    body: formData,
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
                    }
                });

                console.log('Meeting audio recording summary:', {
                    totalChunks: recordedAudio.length,
                    startTime: recordedAudio[0]?.timestamp,
                    endTime: recordedAudio[recordedAudio.length - 1]?.timestamp,
                    totalSize: `${(audioBlob.size / 1024 / 1024).toFixed(2)} MB`
                });

                audioChunks = [];
            } catch (error) {
                console.error("Error uploading audio:", error);
            }
        };
    } catch (err) {
        console.error("Error starting audio recording:", err);
        Swal.fire({
            icon: 'error',
            title: 'Microphone Access Required',
            text: 'Please enable microphone access to record the meeting'
        });
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
}

function fetchMeetingStats() {
    const startDate = document.getElementById('startDate')?.value;
    const endDate = document.getElementById('endDate')?.value;

    if (!startDate || !endDate) {
        Swal.fire({
            icon: 'error',
            title: 'Date Required',
            text: 'Please select both start and end dates'
        });
        return;
    }

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!csrfToken) {
        console.error('CSRF token not found');
        return;
    }

    fetch('/agents/meetings/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            startDate,
            endDate
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.status === 'success') {
            const attendedMeetings = document.getElementById('attendedMeetings');
            const totalDuration = document.getElementById('totalDuration');
            const avgDuration = document.getElementById('avgDuration');
            
            if (attendedMeetings) attendedMeetings.textContent = data.meetings_count;
            if (totalDuration) totalDuration.textContent = data.total_duration;
            if (avgDuration) avgDuration.textContent = data.average_duration;
        } else {
            throw new Error(data.error || 'Failed to fetch meeting stats');
        }
    })
    .catch(error => {
        console.error('Error fetching meeting stats:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to fetch meeting statistics'
        });
    });
}

async function startMeeting() {
    console.log("Starting meeting...");
    const agentEmail = document.querySelector('[data-agent_email]')?.dataset.agentEmail;

    if (!agentEmail) {
        console.log("No agent email found");
        Swal.fire({
            icon: 'error',
            title: 'Error', 
            text: 'Unable to start meeting. Please try again.'
        });
        return Promise.reject('No agent email found');
    }

    // Get CSRF token from cookie instead of DOM
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    const csrfToken = getCookie('csrftoken');
    if (!csrfToken) {
        console.error('CSRF token not found in cookie');
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'CSRF token not found. Please refresh the page and try again.'
        });
        return Promise.reject('CSRF token not found');
    }

    try {
        if (!navigator.geolocation) {
            throw new Error('Geolocation not supported');
        }

        const pos = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject);
        });

        position = pos;
        const meetingDetails = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            timestamp: new Date().toISOString(),
            agent_email: agentEmail,
            meeting_id: sessionStorage.getItem('currentMeetingId'),
            photo: capturedPhotos,
            audio: recordedAudio,
        };

        const response = await fetch('/agents/meetings/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                action: "start",
                agent_email: agentEmail,
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude,
                timestamp: new Date().toISOString(),
                photo: capturedPhotos,
                audio: recordedAudio,
            })
        });



        const data = await response.json();
        
        if (data.meeting_id) {
            console.log("Meeting created successfully:", data);
            sessionStorage.setItem('currentMeetingId', data.meeting_id);
            
            // Open photo modal first
            openPhotoModal();

            // Start recording and timer
            await startRecording();
            startTime = new Date();
            startMeetingTimer();
            
            // Disable start button
            const startButton = document.getElementById('startMeetingBtn');
            if (startButton) startButton.disabled = true;
            
            // Create timer element if it doesn't exist
            if (!document.getElementById('meetingTimer')) {
                const timerDiv = document.createElement('div');
                timerDiv.id = 'meetingTimer';
                timerDiv.className = 'fixed top-4 right-4 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg';
                document.body.appendChild(timerDiv);
            }
            
            return btoa(JSON.stringify(meetingDetails));
        } else {
            throw new Error('Failed to create meeting');
        }

    } catch (error) {
        console.error('Error in startMeeting:', error);
        
        let errorMessage = 'Failed to start meeting';
        if (error.message.includes('Geolocation')) {
            errorMessage = 'Please enable location access to start the meeting';
        }
        
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: errorMessage
        });
        
        return Promise.reject(error);
    }
}

function openPhotoModal() {
    const photoModal = document.getElementById('photoModal');
    if (!photoModal) {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'No photo data provided'
        });
        return;
    }

    photoModal.classList.remove('hidden');
    photoModal.classList.add('flex');
    
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            videoStream = stream;
            const video = document.getElementById('video');
            if (!video) {
                Swal.fire({
                    icon: 'error', 
                    title: 'Error',
                    text: 'No photo data provided'
                });
                return;
            }
            video.srcObject = stream;
        })
        .catch(err => {
            console.error("Media access error:", err);
            Swal.fire({
                icon: 'error',
                title: 'Camera Access Required',
                text: 'Please enable camera access to start the meeting'
            });
        });
}

function closePhotoModal() {
    const photoModal = document.getElementById('photoModal');
    if (!photoModal) return;

    photoModal.classList.add('hidden');
    photoModal.classList.remove('flex');
    
    if (videoStream) {
        videoStream.getTracks().forEach(track => {
            if (track.kind === 'video') track.stop();
        });
    }
}

function  startMeetingTimer() {
    const startTimestamp = new Date(startTime).getTime();

    timerInterval = setInterval(() => {
        const now = new Date().getTime();
        const elapsedTime = now - startTimestamp;

        const hours = Math.floor(elapsedTime / (1000 * 60 * 60));
        const minutes = Math.floor((elapsedTime % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((elapsedTime % (1000 * 60)) / 1000);

        const timerElement = document.getElementById("meetingTimer");
        if (timerElement) {
            timerElement.innerText = `${hours}h ${minutes}m ${seconds}s`;
        }
    }, 1000);
}

function startTimer() {
    startTime = new Date(parseInt(localStorage.getItem('meetingStartTime')) || new Date().getTime());
    localStorage.setItem('meetingStartTime', startTime.getTime());
    
    let timerDiv = document.getElementById('meetingTimer');
    if (!timerDiv) {
        timerDiv = document.createElement('div');
        timerDiv.id = 'meetingTimer';
        timerDiv.className = 'fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-[#212121] text-white px-4 py-2 rounded-lg shadow-lg text-sm z-50';
        document.body.appendChild(timerDiv);
    }

    if (meetingTimer) {
        clearInterval(meetingTimer);
    }

    meetingTimer = setInterval(() => {
        const now = new Date();
        const diff = now - startTime;
        const minutes = Math.floor(diff / 60000);
        const seconds = Math.floor((diff % 60000) / 1000);
        timerDiv.textContent = `Meeting Duration: ${minutes}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);

    localStorage.setItem('meetingTimerInterval', meetingTimer);
}

// This code initializes the meeting status when the DOM is fully loaded. It fetches the current meeting details from the server and checks if there is an active meeting. If an active meeting is found, it retrieves the start time from local storage or the server response, sets the meeting timer, starts recording audio, and stores the current meeting ID in session storage. If no active meeting is found or an error occurs, it clears any existing meeting data.
window.addEventListener('DOMContentLoaded', () => {
    fetch('/agents/meetings/')
        .then(response => response.json())
        .then(response => {
            if (!response.error && response.id) {
                const storedStartTime = localStorage.getItem('meetingStartTime');
                startTime = storedStartTime ? new Date(parseInt(storedStartTime)) : new Date(response.start_time);
                localStorage.setItem('meetingStartTime', startTime.getTime());
                
                startTimer();
                startRecording();
                sessionStorage.setItem('currentMeetingId', response.id);
            } else {
                clearMeetingData();
            }
        })
        .catch(error => {
            console.error('Error checking meeting status:', error);
            clearMeetingData();
        });
});

function clearMeetingData() {
    clearInterval(meetingTimer);
    localStorage.removeItem('meetingStartTime');
    localStorage.removeItem('meetingTimerInterval');
    const timerDiv = document.getElementById('meetingTimer');
    if (timerDiv) {
        timerDiv.remove();
    }
}

async function capturePhoto() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    if (!video || !canvas) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    const photo = canvas.toDataURL('image/jpeg');
    
    capturedPhotos.push({
        photo,
        timestamp: new Date().toISOString(),
        location: position ? {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
        } : null
    });
    
    const formData = new FormData();
    formData.append('action', 'upload_photo');
    formData.append('meeting_id', sessionStorage.getItem('currentMeetingId'));
    
    // Convert base64 to blob
    const byteString = atob(photo.split(',')[1]);
    const mimeString = photo.split(',')[0].split(':')[1].split(';')[0];
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }
    const blob = new Blob([ab], { type: mimeString });
    formData.append('photo', blob, 'meeting_photo.jpg');
    
    if (position) {
        formData.append('latitude', position.coords.latitude);
        formData.append('longitude', position.coords.longitude);
    }
    formData.append('timestamp', new Date().toISOString());
    
    try {
        await fetch('/agents/meetings/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
            },
            body: formData
        });
        
        closePhotoModal();
        
        Swal.fire({
            icon: 'success',
            title: 'Meeting Started',
            text: 'Your meeting has been successfully started!'
        });

        startTimer();
    } catch (error) {
        console.error('Error uploading photo:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to upload photo'
        });
    }
}

let locationWatcher = null;

async function endMeeting() {
    try {
        const response = await fetch('/agents/meetings/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({ action: 'end' })
        });

        const data = await response.json();
        
        if (data.message) {
            stopMeetingTimer();
            alert("Meeting Ended: " + data.duration);
            
            clearMeetingResources();
            location.reload();
        } else {
            throw new Error(data.error || 'Unknown error');
        }
    } catch (error) {
        console.error("Error ending meeting:", error);
        Swal.fire({
            icon: 'error',
            title: 'Error Ending Meeting',
            text: error.message
        });
    }
}

function clearMeetingResources() {
    clearInterval(meetingTimer);

    localStorage.removeItem('meetingStartTime');
    localStorage.removeItem('meetingTimerInterval');
    
    const timerDiv = document.getElementById('meetingTimer');
    if (timerDiv) {
        timerDiv.remove();
    }

    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
    
    if (locationWatcher) {
        navigator.geolocation.clearWatch(locationWatcher);
        locationWatcher = null;
    }
    
    capturedPhotos = [];
    recordedAudio = [];
    position = null;
    
    const startButton = document.getElementById('startMeetingBtn');
    if (startButton) {
        startButton.disabled = false;
    }
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function stopMeetingTimer() {
    clearInterval(timerInterval);
    clearInterval(meetingTimer);
    localStorage.removeItem('meetingStartTime');
    localStorage.removeItem('meetingTimerInterval');
    
    const timerDiv = document.getElementById('meetingTimer');
    if (timerDiv) {
        timerDiv.textContent = "Meeting Ended";
        setTimeout(() => timerDiv.remove(), 2000);
    }
}
