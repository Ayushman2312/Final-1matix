function sendOtp() {
    let clientName = document.getElementById("client_name").value;
    let clientEmail = document.getElementById("client_email").value;
    let clientPhone = document.getElementById("client_phone").value;

    console.log("Sending OTP for:", {
        clientName,
        clientEmail,
        clientPhone
    });

    // Validate required fields
    if (!clientName || !clientEmail || !clientPhone) {
        console.error("Missing required fields");
        alert("Please fill in all required fields");
        return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(clientEmail)) {
        console.error("Invalid email format");
        alert("Please enter a valid email address");
        return;
    }

    // Disable the send OTP button to prevent multiple clicks
    const sendOtpBtn = document.getElementById("sendOtpBtn");
    if (sendOtpBtn) {
        sendOtpBtn.disabled = true;
        console.log("Send OTP button disabled");
    }

    fetch("/agents/meetings/", {
        method: "POST",
        body: JSON.stringify({ 
            client_name: clientName, 
            client_email: clientEmail, 
            client_phone: clientPhone 
        }),
        headers: { 
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken()
        }
    })    
    .then(response => {
        console.log("Response status:", response.status);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log("Response data:", data);
        if (data.status === 'success') {
            document.getElementById("otpSection").classList.remove("hidden");
            document.getElementById("verifyOtpBtn").classList.remove("hidden");
            sessionStorage.setItem("demo_id", data.demo_id);
            alert("OTP sent successfully! Please check your email.");
        } else {
            console.error("Error sending OTP:", data.error);
            alert(data.error || "Failed to send OTP");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Failed to send OTP. Please try again.");
    })
    .finally(() => {
        // Re-enable the send OTP button
        if (sendOtpBtn) {
            sendOtpBtn.disabled = false;
            console.log("Send OTP button re-enabled");
        }
    });
}

// Add this helper function for CSRF token
function getCsrfToken() {
    const name = 'csrftoken';
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

function verifyOtp() {
    let otp = document.getElementById("otp_input").value;
    let demoId = sessionStorage.getItem("demo_id");

    console.log("Verifying OTP:", {
        otp,
        demoId
    });

    if (!otp || !demoId) {
        console.error("Missing OTP or demo ID");
        alert("Please enter OTP");
        return;
    }

    fetch("/agents/meetings/", {
        method: "POST",
        body: JSON.stringify({ 
            demo_id: demoId, 

            otp: otp 
        }),
        headers: { 
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken()
        }
    })
    .then(response => {
        console.log("Response status:", response.status);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        console.log("Response data:", data);
        if (data.demo_url) {
            alert("Demo started successfully!");
            window.location.href = data.demo_url;
        } else {
            console.error("Error verifying OTP:", data.error);
            alert(data.error || "Invalid OTP");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Failed to verify OTP. Please try again.");
    });
}

function closeDemoModal() {
    const modal = document.getElementById('demoPopup');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        // Reset form
        document.getElementById("client_name").value = "";
        document.getElementById("client_email").value = "";
        document.getElementById("client_phone").value = "";
        document.getElementById("otp_input").value = "";
        document.getElementById("otpSection").classList.add("hidden");
        document.getElementById("verifyOtpBtn").classList.add("hidden");
        console.log("Demo modal closed and form reset");
    }
}

function openDemoModal() {
    const modal = document.getElementById('demoPopup');
    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        console.log("Demo modal opened");
    }
}

function endDemo() {
    const modal = document.getElementById('demoPopup');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        console.log("Demo ended");
    }
}

function closeEndDemoModal() {
    const modal = document.getElementById('endDemoPopup');
    if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        console.log("End demo modal closed");
    }
}

function confirmEndDemo() {
    // Logic to end the demo session
    alert("Demo session ended.");
    closeEndDemoModal();
    console.log("Demo session confirmed to end");
}
