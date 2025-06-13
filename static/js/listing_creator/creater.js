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
    console.log('Running creater.js generateListing function');
    
    // Get all required elements first
    const elements = {
        platform: document.getElementById('platform'),
        brand: document.getElementById('brand'),
        url1: document.getElementById('url1'),
        url2: document.getElementById('url2') || { value: '' },
        url3: document.getElementById('url3') || { value: '' },
        url4: document.getElementById('url4') || { value: '' },
        description: document.getElementById('additional-specs') || document.getElementById('other-specs'),
        productPhoto1: document.getElementById('product-photo1'),
        productPhoto2: document.getElementById('product-photo2') || document.createElement('input'),
        errorField: document.getElementById('error-field'),
        errorMessage: document.getElementById('error-message'),
        resultsSection: document.getElementById('results-section') || document.createElement('div')
    };

    // Check for critical missing elements and provide fallbacks
    let missingElements = [];
    for (const [key, element] of Object.entries(elements)) {
        if (!element) {
            console.error(`Required element not found: ${key}`);
            missingElements.push(key);
            
            // Create dummy element to prevent errors
            elements[key] = document.createElement(key.includes('photo') ? 'input' : 'div');
            if (key.includes('photo')) {
                elements[key].type = 'file';
                elements[key].files = new DataTransfer().files;
            }
        }
    }

    // If critical elements are missing, handle gracefully
    if (missingElements.length > 0) {
        console.warn(`Missing critical elements: ${missingElements.join(', ')}. Using fallbacks.`);
        
        // Check if we have our custom implementation available
        if (window.customGenerateListing) {
            console.log('Using custom implementation instead');
            return window.customGenerateListing();
        }
    }

    const urls = [
        elements.url1.value,
        elements.url2.value,
        elements.url3.value,
        elements.url4.value
    ].filter(url => url && url.trim() !== '');

    // Look for dynamic URLs if available
    const dynamicUrlInputs = document.querySelectorAll('#url-indicators input[type="url"]');
    if (dynamicUrlInputs.length > 0) {
        console.log(`Found ${dynamicUrlInputs.length} dynamic URL inputs`);
        dynamicUrlInputs.forEach(input => {
            if (input.value && input.value.trim() !== '') {
                urls.push(input.value.trim());
                console.log(`Added dynamic URL: ${input.value.trim()}`);
            }
        });
    }

    let product_images = [];
    
    // Get product images from standard inputs
    if (elements.productPhoto1.files && elements.productPhoto1.files[0]) {
        try {
            product_images.push(await readFileAsBase64(elements.productPhoto1.files[0]));
            console.log('Added product photo 1');
        } catch (error) {
            console.error('Error reading product photo 1:', error);
        }
    }
    
    if (elements.productPhoto2.files && elements.productPhoto2.files[0]) {
        try {
            product_images.push(await readFileAsBase64(elements.productPhoto2.files[0]));
            console.log('Added product photo 2');
        } catch (error) {
            console.error('Error reading product photo 2:', error);
        }
    }
    
    // Look for dynamic photo inputs if available
    const dynamicPhotoInputs = document.querySelectorAll('input[type="file"][id^="dynamic-photo-"]');
    if (dynamicPhotoInputs.length > 0) {
        console.log(`Found ${dynamicPhotoInputs.length} dynamic photo inputs`);
        for (const input of dynamicPhotoInputs) {
            if (input.files && input.files[0]) {
                try {
                    product_images.push(await readFileAsBase64(input.files[0]));
                    console.log(`Added dynamic photo: ${input.id}`);
                } catch (error) {
                    console.error(`Error reading dynamic photo ${input.id}:`, error);
                }
            }
        }
    }

    // Check if we have description in other-specs if additional-specs is empty
    if (!elements.description.value && document.getElementById('other-specs')) {
        elements.description.value = document.getElementById('other-specs').value;
    }
    
    // Prepare product specs from individual fields
    const product_specs = {};
    const sizeElement = document.getElementById('size');
    const materialElement = document.getElementById('material');
    const colorElement = document.getElementById('color');
    
    if (sizeElement) product_specs.size = sizeElement.value;
    if (materialElement) product_specs.material = materialElement.value;
    if (colorElement) product_specs.color = colorElement.value;

    // Validation - adjusted to be more flexible
    if (!elements.platform.value || !elements.brand.value) {
        elements.errorField.classList.remove('hidden');
        elements.errorMessage.textContent = 'Please fill in all required fields (Brand and Platform are required)';
        if (elements.resultsSection) elements.resultsSection.classList.add('hidden');
        return;
    }
    
    if (urls.length < 1) {
        elements.errorField.classList.remove('hidden');
        elements.errorMessage.textContent = 'Please add at least one URL';
        if (elements.resultsSection) elements.resultsSection.classList.add('hidden');
        return;
    }
    
    if (product_images.length < 1) {
        elements.errorField.classList.remove('hidden');
        elements.errorMessage.textContent = 'Please upload at least one product photo';
        if (elements.resultsSection) elements.resultsSection.classList.add('hidden');
        return;
    }

    // Hide error and show loading state
    elements.errorField.classList.add('hidden');
    if (elements.resultsSection) elements.resultsSection.classList.remove('hidden');
    
    const sections = ['amazon-title', 'expert-title', 'bullet-points', 'description', 'search-terms'];
    sections.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.innerHTML = '<div class="animate-pulse">Generating...</div>';
        }
    });

    try {
        console.log(`Sending request with ${urls.length} URLs and ${product_images.length} photos`);
        
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
                description: elements.description.value || '',
                product_images,
                product_specs
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            elements.errorField.classList.remove('hidden');
            elements.errorMessage.textContent = data.error;
            if (elements.resultsSection) elements.resultsSection.classList.add('hidden');
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
                    if (Array.isArray(content)) {
                        element.innerHTML = content.map(point => `• ${point}`).join('<br>');
                    } else if (typeof content === 'string') {
                        element.innerHTML = content.split('\n').map(point => `• ${point.trim()}`).join('<br>');
                    } else {
                        element.innerHTML = 'No bullet points generated';
                    }
                } else {
                    element.innerHTML = content || `No ${id.replace('-', ' ')} generated`;
                }
            }
        };

        // Log the received response data
        console.log('Received response data:', data.response);

        updateSection('amazon-title', data.response.amazon_title);
        updateSection('expert-title', data.response.expert_title);
        updateSection('bullet-points', data.response.bullet_points);
        updateSection('description', data.response.description?.trim());
        updateSection('search-terms', data.response.search_terms);
        
        // Also update the standard form fields
        const updateFormField = (id, content) => {
            const element = document.getElementById(id);
            if (element && (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA')) {
                element.value = content || '';
                console.log(`Updated form field ${id} with value: ${content}`);
            } else {
                console.warn(`Form field ${id} not found or not an input/textarea element`);
            }
        };
        
        // Update form fields - adding direct access to form fields by name
        document.getElementById('amazon-title').value = data.response.amazon_title || '';
        document.getElementById('expert-title').value = data.response.expert_title || '';
        
        // Fallback for updating fields by query selector if IDs don't work
        if (!document.getElementById('amazon-title').value && data.response.amazon_title) {
            const amazonTitleInputs = document.querySelectorAll('input[placeholder="Amazon"]');
            if (amazonTitleInputs.length > 0) {
                amazonTitleInputs[0].value = data.response.amazon_title;
                console.log('Updated amazon-title via selector');
            }
        }
        
        if (!document.getElementById('expert-title').value && data.response.expert_title) {
            const expertTitleInputs = document.querySelectorAll('input[placeholder="Amazon"]:not(#amazon-title)');
            if (expertTitleInputs.length > 0) {
                expertTitleInputs[0].value = data.response.expert_title;
                console.log('Updated expert-title via selector');
            }
        }
        
        // Use the more general update function for other fields
        updateFormField('description', data.response.description?.trim());
        
        if (Array.isArray(data.response.bullet_points)) {
            updateFormField('bullet-points', data.response.bullet_points.join('\n'));
        } else {
            updateFormField('bullet-points', data.response.bullet_points);
        }
        
        updateFormField('search-terms', data.response.search_terms);
        
        // Show copy buttons if they exist
        if (typeof showCopyButtons === 'function') {
            showCopyButtons();
        }

    } catch (error) {
        console.error('Error during listing generation:', error);
        elements.errorField.classList.remove('hidden');
        elements.errorMessage.textContent = `Error: ${error.message}`;
        if (elements.resultsSection) elements.resultsSection.classList.add('hidden');
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