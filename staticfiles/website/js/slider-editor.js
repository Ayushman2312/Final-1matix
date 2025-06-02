$(document).ready(function() {
    // Initialize slide template
    const slideTemplate = $('#slide-template').html();
    let slideCount = $('.slide-container').length;

    // Add new slide
    $('#add-slide').click(function() {
        const newSlide = slideTemplate.replace(/\{index\}/g, slideCount);
        $('#slides-container').append(newSlide);
        slideCount++;
        initializeSlideEvents();
        updateSlideNumbers();
    });

    // Initialize existing slides
    initializeSlideEvents();

    // Handle form submission
    $('#website-form').submit(function(e) {
        e.preventDefault();
        saveWebsiteContent();
    });

    // Function to collect slide data for submission
    function collectSlideData() {
        const slides = [];
        $('.slide-container').each(function(index) {
            const $slide = $(this);
            slides.push({
                heading: $slide.find('.slide-heading').val(),
                subheading: $slide.find('.slide-subheading').val(),
                content: $slide.find('.slide-content').val(),
                button_text: $slide.find('.slide-button-text').val(),
                button_url: $slide.find('.slide-button-url').val(),
                image: $slide.find('.current-slide-image').attr('data-image-url') || ''
            });
        });
        return slides;
    }

    // Function to initialize slide events (used for both existing and new slides)
    function initializeSlideEvents() {
        // Remove slide button
        $('.remove-slide').off('click').on('click', function() {
            $(this).closest('.slide-container').remove();
            updateSlideNumbers();
        });

        // Slide move up
        $('.move-slide-up').off('click').on('click', function() {
            const currentSlide = $(this).closest('.slide-container');
            const prevSlide = currentSlide.prev('.slide-container');
            if (prevSlide.length) {
                prevSlide.before(currentSlide);
                updateSlideNumbers();
            }
        });

        // Slide move down
        $('.move-slide-down').off('click').on('click', function() {
            const currentSlide = $(this).closest('.slide-container');
            const nextSlide = currentSlide.next('.slide-container');
            if (nextSlide.length) {
                nextSlide.after(currentSlide);
                updateSlideNumbers();
            }
        });

        // Slide image preview
        $('.slide-image').off('change').on('change', function(e) {
            const file = e.target.files[0];
            const reader = new FileReader();
            const preview = $(this).siblings('.slide-image-preview');
            
            reader.onload = function(e) {
                preview.html(`<img src="${e.target.result}" class="img-thumbnail mt-2" alt="Slide image preview">`);
            }
            
            if (file) {
                reader.readAsDataURL(file);
            }
        });
    }

    // Update slide numbers after reordering
    function updateSlideNumbers() {
        $('.slide-container').each(function(index) {
            $(this).find('.slide-number').text(index + 1);
        });
    }

    // Save website content via AJAX
    function saveWebsiteContent() {
        const formData = new FormData($('#website-form')[0]);
        
        // Add slides data as JSON
        const slidesData = collectSlideData();
        formData.append('slides', JSON.stringify(slidesData));
        
        // Add slide images with proper keys
        $('.slide-container').each(function(index) {
            const slideImageInput = $(this).find('.slide-image')[0];
            if (slideImageInput && slideImageInput.files.length > 0) {
                formData.append(`slide_image_${index}`, slideImageInput.files[0]);
            }
        });

        $.ajax({
            url: $('#website-form').attr('action'),
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function(response) {
                if (response.status === 'success') {
                    showToast('Success', response.message, 'success');
                } else {
                    showToast('Error', response.message, 'danger');
                }
            },
            error: function(xhr, status, error) {
                showToast('Error', 'Failed to save website content', 'danger');
            }
        });
    }

    // Function to show toast notifications
    function showToast(title, message, type) {
        const toast = `
            <div class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="5000">
                <div class="toast-header bg-${type} text-white">
                    <strong class="me-auto">${title}</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        $('#toast-container').append(toast);
        const toastElement = $('#toast-container .toast').last();
        const bsToast = new bootstrap.Toast(toastElement);
        bsToast.show();
        
        // Remove toast after it's hidden
        toastElement.on('hidden.bs.toast', function() {
            $(this).remove();
        });
    }
}); 