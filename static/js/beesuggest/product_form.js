document.addEventListener('DOMContentLoaded', function () {
    // Character counter for product description
    const descriptionTextarea = document.getElementById('product_description');
    const charCount = document.getElementById('char-count');
    
    if (descriptionTextarea && charCount) {
        descriptionTextarea.addEventListener('input', function() {
            charCount.textContent = this.value.length;
        });
    }
    
    // Word counter for short description
    const shortDescTextarea = document.getElementById('short_description');
    const wordCount = document.getElementById('word-count');
    
    if (shortDescTextarea && wordCount) {
        shortDescTextarea.addEventListener('input', function() {
            const words = this.value.trim().split(/\s+/).length;
            wordCount.textContent = words;
            
            // Visual feedback based on word count
            if (words > 70) {
                wordCount.classList.add('text-red-500');
                wordCount.classList.remove('text-gray-500');
            } else {
                wordCount.classList.remove('text-red-500');
                wordCount.classList.add('text-gray-500');
            }
        });
    }

    // Dynamic Variation Fields
    const variationContainer = document.getElementById('variation_fields_container');
    const addVariationBtn = document.getElementById('add_variation_field');
    let variationCount = 0;
    const variationOptions = ['Colour', 'Size', 'Material', 'Grade', 'Custom'];

    function updateHiddenInput(tagsDiv, hiddenInput) {
        const tags = Array.from(tagsDiv.querySelectorAll('span.tag-item > span:first-child')).map(t => t.textContent);
        hiddenInput.value = tags.join(',');
    }

    function createTag(value, tagsDiv, hiddenInput) {
        const tag = document.createElement('span');
        tag.classList.add('tag-item', 'flex', 'items-center', 'bg-cyan-100', 'text-cyan-800', 'text-sm', 'font-medium', 'px-3', 'py-1', 'rounded-full');
        
        const tagText = document.createElement('span');
        tagText.textContent = value;
        tag.appendChild(tagText);

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.classList.add('ml-2', 'text-cyan-600', 'hover:text-cyan-800', 'font-bold');
        removeBtn.innerHTML = '&times;';
        removeBtn.onclick = () => {
            tag.remove();
            updateHiddenInput(tagsDiv, hiddenInput);
        };

        tag.appendChild(removeBtn);
        // The reference node for insertion is the div wrapping the input field
        const inputWrapper = tagsDiv.querySelector('div');
        tagsDiv.insertBefore(tag, inputWrapper);
        updateHiddenInput(tagsDiv, hiddenInput);
    }

    function addVariationField() {
        variationCount++;
        const variationDiv = document.createElement('div');
        variationDiv.classList.add('bg-gradient-to-br', 'from-gray-50', 'to-gray-100', 'p-6', 'rounded-xl', 'border', 'border-gray-200', 'hover:border-cyan-300', 'transition-all', 'duration-300');
        variationDiv.dataset.variationId = variationCount;
        
        // Create header with remove button
        const headerDiv = document.createElement('div');
        headerDiv.classList.add('flex', 'justify-between', 'items-center', 'mb-4');
        
        const headerLabel = document.createElement('h4');
        headerLabel.classList.add('font-medium', 'text-gray-700');
        headerLabel.textContent = `Variation ${variationCount}`;
        
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.classList.add('text-red-500', 'hover:text-red-700', 'text-sm', 'font-medium');
        removeButton.innerHTML = `
            <span class="flex items-center">
                <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
                Remove
            </span>
        `;
        removeButton.addEventListener('click', function() {
            variationDiv.remove();
        });
        
        headerDiv.appendChild(headerLabel);
        headerDiv.appendChild(removeButton);
        variationDiv.appendChild(headerDiv);
        
        // Variation type selection container
        const variationTypeContainer = document.createElement('div');
        variationTypeContainer.classList.add('mb-4');
        
        const gridDiv = document.createElement('div');
        gridDiv.classList.add('grid', 'grid-cols-1', 'md:grid-cols-3', 'gap-4', 'items-start');
        
        // Select element for variation type
        const selectEl = document.createElement('select');
        selectEl.name = `variation_name_${variationCount}`;
        selectEl.id = `variation_name_${variationCount}`;
        selectEl.classList.add('w-full', 'px-4', 'py-3', 'bg-white', 'border-2', 'border-gray-200', 'rounded-xl', 'shadow-sm', 'focus:ring-2', 'focus:ring-cyan-500', 'focus:border-cyan-500');
        
        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select variation type';
        selectEl.appendChild(defaultOption);
        
        variationOptions.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.toLowerCase();
            option.textContent = opt;
            selectEl.appendChild(option);
        });

        // Create container for custom variation type input (initially hidden)
        const customContainer = document.createElement('div');
        customContainer.classList.add('hidden', 'mt-2');
        
        const customInput = document.createElement('input');
        customInput.type = 'text';
        customInput.id = `custom_variation_name_${variationCount}`;
        customInput.name = `custom_variation_name_${variationCount}`;
        customInput.placeholder = 'Enter custom variation type';
        customInput.classList.add('w-full', 'px-4', 'py-2', 'bg-white', 'border-2', 'border-gray-200', 'rounded-xl', 'shadow-sm', 'focus:ring-2', 'focus:ring-cyan-500', 'focus:border-cyan-500');
        
        customContainer.appendChild(customInput);
        
        // Event listener for select element
        selectEl.addEventListener('change', function() {
            if (this.value === 'custom') {
                customContainer.classList.remove('hidden');
                // Clear any previous error styling
                this.classList.remove('border-red-500');
                const errorElement = this.parentNode.querySelector('.error-message');
                if (errorElement) errorElement.remove();
            } else {
                customContainer.classList.add('hidden');
            }
        });
        
        // Create container for both select and custom input
        const selectContainer = document.createElement('div');
        selectContainer.appendChild(selectEl);
        selectContainer.appendChild(customContainer);

        // Tag-based input for variation values
        const tagContainer = document.createElement('div');
        tagContainer.classList.add('md:col-span-2');

        const tagsDiv = document.createElement('div');
        tagsDiv.classList.add('flex', 'flex-wrap', 'gap-2', 'p-2', 'bg-white', 'border-2', 'border-gray-200', 'rounded-xl', 'shadow-sm', 'min-h-[50px]', 'items-center');

        const inputWrapper = document.createElement('div');
        inputWrapper.classList.add('flex', 'items-center', 'flex-grow');

        const tagInput = document.createElement('input');
        tagInput.type = 'text';
        tagInput.placeholder = 'Add a value...';
        tagInput.classList.add('flex-grow', 'p-1', 'border-none', 'focus:ring-0', 'bg-transparent');

        const addButton = document.createElement('button');
        addButton.type = 'button';
        addButton.textContent = 'Add';
        addButton.classList.add('ml-2', 'px-3', 'py-1', 'text-sm', 'bg-cyan-500', 'text-white', 'font-semibold', 'rounded-md', 'hover:bg-cyan-600', 'focus:outline-none', 'focus:ring-2', 'focus:ring-cyan-300');
        
        inputWrapper.appendChild(tagInput);
        inputWrapper.appendChild(addButton);
        tagsDiv.appendChild(inputWrapper);

        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = `variation_value_${variationCount}`;

        tagContainer.appendChild(tagsDiv);
        tagContainer.appendChild(hiddenInput);

        const addAction = () => {
            const value = tagInput.value.trim();
            if (value) {
                createTag(value, tagsDiv, hiddenInput);
                tagInput.value = '';
                tagInput.focus();
            }
        };

        tagInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addAction();
            }
        });

        addButton.addEventListener('click', () => {
            addAction();
        });
        
        gridDiv.appendChild(selectContainer);
        gridDiv.appendChild(tagContainer);
        variationDiv.appendChild(gridDiv);
        variationContainer.appendChild(variationDiv);
    }

    if (addVariationBtn) {
        addVariationBtn.addEventListener('click', addVariationField);
    }

    // Add initial field - only one instead of four
    if (variationContainer) {
        addVariationField();
    }

    // Dynamic Comparison Fields
    const comparisonContainer = document.getElementById('comparison_container');
    const addComparisonBtn = document.getElementById('add_comparison');
    let comparisonCount = 0;

    function addComparisonField() {
        comparisonCount++;
        const comparisonDiv = document.createElement('div');
        comparisonDiv.classList.add('bg-gradient-to-br', 'from-gray-50', 'to-gray-100', 'p-6', 'rounded-xl', 'border', 'border-gray-200', 'hover:border-blue-300', 'transition-all', 'duration-300');
        comparisonDiv.dataset.comparisonId = comparisonCount;
        
        // Create header with remove button
        const headerDiv = document.createElement('div');
        headerDiv.classList.add('flex', 'justify-between', 'items-center', 'mb-4');
        
        const headerLabel = document.createElement('h4');
        headerLabel.classList.add('font-medium', 'text-gray-700', 'flex', 'items-center');
        headerLabel.innerHTML = `
            <svg class="w-4 h-4 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2-2V7a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 002 2h2a2 2 0 012-2V7a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 00-2 2h-2a2 2 0 00-2 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2z"></path>
            </svg>
            Comparison ${comparisonCount}
        `;
        
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.classList.add('text-red-500', 'hover:text-red-700', 'text-sm', 'font-medium', 'flex', 'items-center', 'px-3', 'py-1', 'rounded-lg', 'hover:bg-red-50', 'transition-colors');
        removeButton.innerHTML = `
            <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
            </svg>
            Remove
        `;
        removeButton.addEventListener('click', function() {
            comparisonDiv.remove();
        });
        
        headerDiv.appendChild(headerLabel);
        headerDiv.appendChild(removeButton);
        comparisonDiv.appendChild(headerDiv);
        
        // Create grid for Us vs Others
        const gridDiv = document.createElement('div');
        gridDiv.classList.add('grid', 'grid-cols-1', 'md:grid-cols-2', 'gap-4');
        
        // Us field
        const usContainer = document.createElement('div');
        usContainer.classList.add('group');
        
        const usLabel = document.createElement('label');
        usLabel.htmlFor = `comparison_us_${comparisonCount}`;
        usLabel.classList.add('block', 'text-sm', 'font-semibold', 'text-gray-700', 'mb-2', 'group-hover:text-green-600', 'transition-colors');
        usLabel.innerHTML = `
            <span class="flex items-center">
                <svg class="w-4 h-4 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                Our Product/Service
            </span>
        `;
        
        const usTextarea = document.createElement('textarea');
        usTextarea.name = `comparison_us_${comparisonCount}`;
        usTextarea.id = `comparison_us_${comparisonCount}`;
        usTextarea.rows = 1;
        usTextarea.classList.add('w-full', 'px-3', 'py-2', 'bg-white', 'border-2', 'border-gray-200', 'rounded-xl', 'shadow-sm', 'focus:ring-2', 'focus:ring-green-500', 'focus:border-green-500', 'transition-all', 'duration-200', 'hover:border-gray-300', 'resize-none');
        usTextarea.placeholder = 'Describe your product/service advantages...';
        
        usContainer.appendChild(usLabel);
        usContainer.appendChild(usTextarea);
        
        // Others field
        const othersContainer = document.createElement('div');
        othersContainer.classList.add('group');
        
        const othersLabel = document.createElement('label');
        othersLabel.htmlFor = `comparison_others_${comparisonCount}`;
        othersLabel.classList.add('block', 'text-sm', 'font-semibold', 'text-gray-700', 'mb-2', 'group-hover:text-orange-600', 'transition-colors');
        othersLabel.innerHTML = `
            <span class="flex items-center">
                <svg class="w-4 h-4 mr-2 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                Competitors/Others
            </span>
        `;
        
        const othersTextarea = document.createElement('textarea');
        othersTextarea.name = `comparison_others_${comparisonCount}`;
        othersTextarea.id = `comparison_others_${comparisonCount}`;
        othersTextarea.rows = 1;
        othersTextarea.classList.add('w-full', 'px-3', 'py-2', 'bg-white', 'border-2', 'border-gray-200', 'rounded-xl', 'shadow-sm', 'focus:ring-2', 'focus:ring-orange-500', 'focus:border-orange-500', 'transition-all', 'duration-200', 'hover:border-gray-300', 'resize-none');
        othersTextarea.placeholder = 'Describe competitor limitations or general market issues...';
        
        othersContainer.appendChild(othersLabel);
        othersContainer.appendChild(othersTextarea);
        
        gridDiv.appendChild(usContainer);
        gridDiv.appendChild(othersContainer);
        
        comparisonDiv.appendChild(gridDiv);
        comparisonContainer.appendChild(comparisonDiv);
    }

    if (addComparisonBtn) {
        addComparisonBtn.addEventListener('click', addComparisonField);
        // Add first comparison field by default
        addComparisonField();
    }

    // Dynamic FAQs
    const faqContainer = document.getElementById('faq_container');
    const addFaqBtn = document.getElementById('add_faq');
    let faqCount = 0;

    function addFaqField() {
        faqCount++;
        const faqDiv = document.createElement('div');
        faqDiv.classList.add('bg-gradient-to-br', 'from-amber-50', 'to-orange-50', 'p-6', 'rounded-xl', 'border', 'border-amber-200', 'hover:border-amber-300', 'transition-all', 'duration-300', 'space-y-4');

        const questionLabel = document.createElement('label');
        questionLabel.classList.add('block', 'text-sm', 'font-semibold', 'text-gray-700', 'mb-2');
        questionLabel.innerHTML = `<span class="flex items-center">
            <svg class="w-4 h-4 mr-2 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            Question ${faqCount}
        </span>`;

        const questionInput = document.createElement('input');
        questionInput.type = 'text';
        questionInput.name = `faq_question_${faqCount}`;
        questionInput.placeholder = `Enter your question here...`;
        questionInput.value = '';
        questionInput.classList.add('w-full', 'px-4', 'py-3', 'bg-white', 'border-2', 'border-gray-200', 'rounded-xl', 'shadow-sm', 'focus:ring-2', 'focus:ring-amber-500', 'focus:border-amber-500');

        const answerLabel = document.createElement('label');
        answerLabel.classList.add('block', 'text-sm', 'font-semibold', 'text-gray-700', 'mb-2', 'mt-4');
        answerLabel.innerHTML = `<span class="flex items-center">
            <svg class="w-4 h-4 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            Answer ${faqCount}
        </span>`;

        const answerTextarea = document.createElement('textarea');
        answerTextarea.name = `faq_answer_${faqCount}`;
        answerTextarea.rows = '3';
        answerTextarea.placeholder = `Provide a detailed answer for question ${faqCount}...`;
        answerTextarea.classList.add('w-full', 'px-4', 'py-3', 'bg-white', 'border-2', 'border-gray-200', 'rounded-xl', 'shadow-sm', 'focus:ring-2', 'focus:ring-amber-500', 'focus:border-amber-500', 'resize-none');
        
        faqDiv.appendChild(questionLabel);
        faqDiv.appendChild(questionInput);
        faqDiv.appendChild(answerLabel);
        faqDiv.appendChild(answerTextarea);
        faqContainer.appendChild(faqDiv);
    }
    
    addFaqBtn.addEventListener('click', () => addFaqField());

    // Form validation and enhancement
    const form = document.querySelector('form');
    form.addEventListener('submit', function(e) {
        e.preventDefault(); // Prevent submission until validation is complete

        // Clear previous errors
        form.querySelectorAll('.border-red-500').forEach(el => {
            el.classList.remove('border-red-500');
            // We're not re-adding the original border color here to keep it simple
            // The focus classes will re-apply on focus.
        });
        form.querySelectorAll('.error-message').forEach(el => el.remove());

        let isValid = true;

        const setError = (element, message) => {
            isValid = false;
            element.classList.add('border-red-500');
            const errorElement = document.createElement('p');
            errorElement.className = 'error-message text-red-500 text-xs mt-1';
            errorElement.textContent = message;
            // For file inputs, the structure is different.
            if (element.type === 'file') {
                element.closest('.group > div').appendChild(errorElement);
            } else if (element.parentNode.classList.contains('relative')) {
                element.parentNode.parentNode.appendChild(errorElement);
            }
            else {
                element.parentNode.appendChild(errorElement);
            }
        };
        
        // --- FIELD VALIDATION ---

        // Keywords
        const focusKeywords = document.getElementById('focus_keywords');
        if (!focusKeywords.value.trim()) setError(focusKeywords, 'Focus keywords are required.');
        
        // Product Title and Short Description
        const productTitle = document.getElementById('product_title');
        if (!productTitle.value.trim()) setError(productTitle, 'Product title is required.');
        
        const shortDescription = document.getElementById('short_description');
        if (!shortDescription.value.trim()) {
            setError(shortDescription, 'Short description is required.');
        } else if (shortDescription.value.trim().split(/\s+/).length > 70) {
            setError(shortDescription, 'Short description should be around 60 words. Currently exceeds 70 words.');
        }

        // Product Images (at least 5)
        for (let i = 1; i <= 5; i++) {
            const imgInput = document.getElementById(`product_image_${i}`);
            const altInput = document.getElementById(`product_image_${i}_alt`);
            if (imgInput.files.length === 0) setError(imgInput, `Product image ${i} is required.`);
            if (!altInput.value.trim()) setError(altInput, `Alt text for image ${i} is required.`);
        }

        // Product Description
        const productDescription = document.getElementById('product_description');
        if (!productDescription.value.trim()) setError(productDescription, 'Product description is required.');

        // YouTube Video URLs
        const youtubeUrlPattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
        const videoUrl1 = document.getElementById('video_url_1');
        const videoUrl2 = document.getElementById('video_url_2');
        const videoUrl3 = document.getElementById('video_url_3');

        if (!videoUrl1.value.trim()) {
            setError(videoUrl1, 'At least one YouTube video URL is required.');
        } else if (!youtubeUrlPattern.test(videoUrl1.value)) {
            setError(videoUrl1, 'Please enter a valid YouTube video URL.');
        }

        if (videoUrl2.value.trim() && !youtubeUrlPattern.test(videoUrl2.value)) {
            setError(videoUrl2, 'Please enter a valid YouTube video URL.');
        }

        if (videoUrl3.value.trim() && !youtubeUrlPattern.test(videoUrl3.value)) {
            setError(videoUrl3, 'Please enter a valid YouTube video URL.');
        }

        // Variations - check each field
        document.querySelectorAll('#variation_fields_container > div').forEach((field, i) => {
            const select = field.querySelector('select');
            const hiddenInput = field.querySelector('input[type="hidden"]');
            const tagInputContainer = field.querySelector('.flex.flex-wrap');
            const customInput = field.querySelector(`input[id^="custom_variation_name_"]`);

            if (!select.value) {
                setError(select, `Variation type ${i + 1} is required.`);
            } else if (select.value === 'custom' && (!customInput.value || !customInput.value.trim())) {
                setError(customInput, `Custom variation type name is required.`);
            }

            if (!hiddenInput.value.trim()) {
                setError(tagInputContainer, `At least one value for variation ${i + 1} is required.`);
                tagInputContainer.classList.add('border-red-500');
            }
        });
        
        // Ensure at least one variation is provided
        if (document.querySelectorAll('#variation_fields_container > div').length === 0) {
            const addVariationBtn = document.getElementById('add_variation_field');
            setError(addVariationBtn, 'At least one product variation is required.');
        }

        // Usage
        const uses = document.getElementById('uses');
        if (!uses.value.trim()) setError(uses, 'Primary uses are required.');
        const bestSuitedFor = document.getElementById('best_suited_for');
        if (!bestSuitedFor.value.trim()) setError(bestSuitedFor, 'This field is required.');

        // Contact & Social Media
        const contactNumber = document.querySelector('input[name="contact_number"]');
        if (!contactNumber.value.trim()) setError(contactNumber, 'Contact number is required.');
        const email = document.querySelector('input[name="email"]');
        if (!email.value.trim()) {
            setError(email, 'Business email is required.');
        } else if (!/^\S+@\S+\.\S+$/.test(email.value)) {
            setError(email, 'Please enter a valid email address.');
        }
        const website = document.querySelector('input[name="website_url"]');
        if (website.value.trim() && !/^(https?:\/\/)(www\.)?[a-zA-Z0-9]+([-.][a-zA-Z0-9]+)*\.[a-zA-Z]{2,}(\/.*)?$/.test(website.value)) {
            setError(website, 'Please enter a valid website URL (e.g., https://example.com).');
        }
        const address = document.querySelector('textarea[name="address"]');
        if (!address.value.trim()) setError(address, 'Business address is required.');

        // Organization
        const organization = document.querySelector('input[name="organization"]');
        if (!organization.value.trim()) setError(organization, 'Organization name is required.');
        
        // FAQs - if any are added, their fields are required.
        document.querySelectorAll('#faq_container > div').forEach((field, i) => {
            const question = field.querySelector('input[type="text"]');
            const answer = field.querySelector('textarea');
            if (!question.value.trim()) setError(question, `FAQ question ${i + 1} is required.`);
            if (!answer.value.trim()) setError(answer, `FAQ answer ${i + 1} is required.`);
        });

        // Miscellaneous
        const whyChooseUs = document.getElementById('why_choose_us');
        if (!whyChooseUs.value.trim()) setError(whyChooseUs, 'This field is required.');
        const comparison = document.getElementById('comparison');
        if (!comparison.value.trim()) setError(comparison, 'Product comparison is required.');

        // Process custom variation types
        document.querySelectorAll('#variation_fields_container > div').forEach(field => {
            const select = field.querySelector('select');
            const customInput = field.querySelector(`input[id^="custom_variation_name_"]`);
            
            if (select.value === 'custom' && customInput && customInput.value.trim()) {
                // Create a hidden input to store the actual variation name for submission
                const actualNameInput = document.createElement('input');
                actualNameInput.type = 'hidden';
                actualNameInput.name = select.name + '_actual';
                actualNameInput.value = customInput.value.trim();
                field.appendChild(actualNameInput);
            }
        });

        const submitBtn = form.querySelector('button[type="submit"]');

        if (!isValid) {
            // Find first error and scroll to it
            const firstError = form.querySelector('.border-red-500');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            // Optional: show a summary error message
            return; // Stop the submission
        }
        
        // Add loading state to submit button
        submitBtn.innerHTML = `
            <svg class="animate-spin w-6 h-6 mr-3" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...
        `;
        submitBtn.disabled = true;

        // If validation is successful, submit the form
        form.submit();
    });

    // Enhanced file input preview (optional)
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const fileName = this.files[0].name;
                const fileSize = (this.files[0].size / 1024 / 1024).toFixed(2);
                
                // Create or update file info display
                let fileInfo = this.parentNode.querySelector('.file-info');
                if (!fileInfo) {
                    fileInfo = document.createElement('div');
                    fileInfo.classList.add('file-info', 'mt-2', 'text-xs', 'text-gray-600', 'bg-blue-50', 'px-3', 'py-2', 'rounded-lg', 'border', 'border-blue-200');
                    this.parentNode.appendChild(fileInfo);
                }
                fileInfo.innerHTML = `
                    <div class="flex items-center">
                        <svg class="w-4 h-4 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                        <span class="font-medium">${fileName}</span>
                        <span class="ml-2 text-gray-500">(${fileSize} MB)</span>
                    </div>
                `;
            }
        });
    });
});