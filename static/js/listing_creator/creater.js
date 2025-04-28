function showImagePopup() {
    const popup = document.getElementById('imagePopup');
    popup.style.display = 'flex';
    // Prevent scrolling when popup is open
    document.body.style.overflow = 'hidden';
    
    // Close popup when clicking outside the image
    popup.addEventListener('click', function(e) {
        if (e.target === popup) {
            closeImagePopup();
        }
    });

    // Close popup with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeImagePopup();
        }
    });
}

function closeImagePopup() {
    const popup = document.getElementById('imagePopup');
    popup.style.display = 'none';
    // Restore scrolling
    document.body.style.overflow = 'auto';
}

// #2
async function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

function formatBulletPoints(text) {
    return text.replace(/•\s*(.*?)(?=(?:•|\n|$))/g, '<div class="pl-4 py-1 relative before:content-[\'•\'] before:absolute before:left-0 before:text-gray-400">$1</div>');
}

function animateText(element, text) {
    element.innerHTML = '';
    let delay = 0;
    const formattedText = formatBulletPoints(text);
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = formattedText;
    
    const processNode = (node) => {
        if (node.nodeType === 3) { // Text node
            const chars = node.textContent.split('');
            chars.forEach(char => {
                const span = document.createElement('span');
                span.textContent = char;
                span.className = 'opacity-0 transition-opacity duration-100';
                span.style.animationDelay = `${delay}ms`;
                element.appendChild(span);
                setTimeout(() => span.classList.remove('opacity-0'), delay);
                delay += 10;
            });
        } else if (node.nodeType === 1) { // Element node
            const newElement = document.createElement(node.tagName);
            newElement.className = node.className;
            element.appendChild(newElement);
            node.childNodes.forEach(child => processNode(child));
        }
    };
    
    tempDiv.childNodes.forEach(node => processNode(node));
}

function handlePaste(e, input) {
    const items = e.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
            const file = items[i].getAsFile();
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            input.files = dataTransfer.files;
            
            const reader = new FileReader();
            const previewId = input.id === 'keyword-screenshot1' ? 'preview1' : 'preview2';
            const containerId = input.id === 'keyword-screenshot1' ? 'preview-container1' : 'preview-container2';
            
            reader.onload = function(e) {
                const preview = document.getElementById(previewId);
                preview.src = e.target.result;
                document.getElementById(containerId).classList.remove('hidden');
            };
            reader.readAsDataURL(file);
            break;
        }
    }
}

function removeImage(inputId, containerId) {
    document.getElementById(inputId).value = '';
    document.getElementById(containerId).classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', function() {
    const screenshot1 = document.getElementById('keyword-screenshot1');
    const screenshot2 = document.getElementById('keyword-screenshot2');
    
    if (screenshot1) {
        screenshot1.addEventListener('paste', function(e) {
            handlePaste(e, this);
        });
    }
    
    if (screenshot2) {
        screenshot2.addEventListener('paste', function(e) {
            handlePaste(e, this);
        });
    }
});

async function generateListing() {
    // Get all required elements first
    const elements = {
        platform: document.getElementById('platform'),
        brand: document.getElementById('brand'),
        url1: document.getElementById('url1'),
        url2: document.getElementById('url2'),
        url3: document.getElementById('url3'),
        url4: document.getElementById('url4'),
        description: document.getElementById('additional-specs'),
        productPhoto1: document.getElementById('product-photo1'),
        productPhoto2: document.getElementById('product-photo2'),
        errorField: document.getElementById('error-field'),
        errorMessage: document.getElementById('error-message'),
        resultsSection: document.getElementById('results-section')
    };

    // Validate that all required elements exist
    for (const [key, element] of Object.entries(elements)) {
        if (!element) {
            console.error(`Required element not found: ${key}`);
            return;
        }
    }

    const urls = [
        elements.url1.value,
        elements.url2.value,
        elements.url3.value,
        elements.url4.value
    ].filter(url => url.trim() !== '');

    let product_images = [];
    if (elements.productPhoto1.files[0]) {
        product_images.push(await readFileAsBase64(elements.productPhoto1.files[0]));
    }
    if (elements.productPhoto2.files[0]) {
        product_images.push(await readFileAsBase64(elements.productPhoto2.files[0]));
    }

    // Validation
    if (!elements.platform.value || !elements.brand.value || urls.length < 2 || !elements.description.value) {
        elements.errorField.classList.remove('hidden');
        elements.errorMessage.textContent = 'Please fill in all required fields (including at least 2 URLs)';
        elements.resultsSection.classList.add('hidden');
        return;
    }

    // Hide error and show loading state
    elements.errorField.classList.add('hidden');
    elements.resultsSection.classList.remove('hidden');
    
    const sections = ['amazon-title', 'expert-title', 'bullet-points', 'description', 'search-terms'];
    sections.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.innerHTML = '<div class="animate-pulse">Generating...</div>';
        }
    });

    try {
        const response = await fetch('/listing_creater/ai-chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                platform_type: elements.platform.value,
                brand: elements.brand.value,
                urls,
                description: elements.description.value,
                product_images,
                product_specs: {}
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            elements.errorField.classList.remove('hidden');
            elements.errorMessage.textContent = data.error;
            elements.resultsSection.classList.add('hidden');
            return;
        }

        // Update the results
        const updateSection = (id, content) => {
            const element = document.getElementById(id);
            if (element) {
                if (id === 'search-terms') {
                    // Format search terms with proper spacing and line breaks
                    const terms = content.split(' ').filter(term => term.trim()).join(' ');
                    element.innerHTML = `<strong>Search Terms:</strong><br>${terms || 'No search terms generated'}`;
                } else if (id === 'bullet-points') {
                    element.innerHTML = (content || []).map(point => `• ${point}`).join('<br>');
                } else {
                    element.innerHTML = content || `No ${id.replace('-', ' ')} generated`;
                }
            }
        };

        updateSection('amazon-title', data.response.amazon_title);
        updateSection('expert-title', data.response.expert_title);
        updateSection('bullet-points', data.response.bullet_points);
        updateSection('description', data.response.description?.trim());
        updateSection('search-terms', data.response.search_terms);

    } catch (error) {
        elements.errorField.classList.remove('hidden');
        elements.errorMessage.textContent = `Error: ${error.message}`;
        elements.resultsSection.classList.add('hidden');
    }
}

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