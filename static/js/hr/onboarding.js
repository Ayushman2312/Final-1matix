// Tab switching functionality
function switchTab(tab) {
    console.log(`Switching to tab: ${tab}`);
    const addEmployeeTab = document.getElementById('addEmployeeTab');
    const viewEmployeesTab = document.getElementById('viewEmployeesTab');
    const viewEmployeesSection = document.getElementById('viewEmployeesSection');
    const submittedProfilesTitle = document.getElementById('submittedProfilesTitle');
    const mainContainer = document.querySelector('.two-column-layout');

    if (tab === 'add') {
        console.log("Switching to ADD tab");
        // Switch to Add Employee tab
        addEmployeeTab.classList.add('bg-[#7B3DF3]', 'text-white');
        addEmployeeTab.classList.remove('bg-gray-100', 'text-gray-800');
        viewEmployeesTab.classList.remove('bg-[#7B3DF3]', 'text-white');
        viewEmployeesTab.classList.add('bg-gray-100', 'text-gray-800');
        
        // Remove view mode class - CSS handles the layout restoration
        if (mainContainer) {
            mainContainer.classList.remove('view-mode');
        }
        
        // Update title
        if (submittedProfilesTitle) {
            submittedProfilesTitle.textContent = 'RECENTLY SUBMITTED PROFILES';
        }
    } else {
        console.log("Switching to VIEW tab");
        // Switch to View Employees tab
        viewEmployeesTab.classList.add('bg-[#7B3DF3]', 'text-white');
        viewEmployeesTab.classList.remove('bg-gray-100', 'text-gray-800');
        addEmployeeTab.classList.remove('bg-[#7B3DF3]', 'text-white');
        addEmployeeTab.classList.add('bg-gray-100', 'text-gray-800');
        
        // Add view mode class - CSS handles the layout changes
        if (mainContainer) {
            mainContainer.classList.add('view-mode');
        }
        
        // Update title
        if (submittedProfilesTitle) {
            submittedProfilesTitle.textContent = 'EMPLOYEE INVITATIONS';
        }
        
        // Load employee data
        populateEmployeesTable();
    }
}

// Helper function to capture the original layout
function captureOriginalLayout() {
    const employeeForm = document.getElementById('employeeForm');
    const offerPreviewSection = document.getElementById('offerPreviewSection');
    const recentSubmissionsSection = document.getElementById('recentSubmissionsSection');
    const mainContainer = document.querySelector('.two-column-layout');
    const rightColumn = offerPreviewSection ? offerPreviewSection.parentElement : null;
    
    // Create a deep copy of the original layout
    window.originalLayoutState = {
        mainContainer: {
            className: mainContainer ? mainContainer.className : '',
            outerHTML: mainContainer ? mainContainer.outerHTML : ''
        },
        employeeForm: {
            className: employeeForm ? employeeForm.className : '',
            style: {
                width: employeeForm ? window.getComputedStyle(employeeForm).width : '',
                display: employeeForm ? window.getComputedStyle(employeeForm).display : ''
            }
        },
        rightColumn: {
            className: rightColumn ? rightColumn.className : '',
            style: {
                width: rightColumn ? window.getComputedStyle(rightColumn).width : '',
                display: rightColumn ? window.getComputedStyle(rightColumn).display : '',
                flex: rightColumn ? window.getComputedStyle(rightColumn).flex : ''
            }
        },
        offerPreviewSection: {
            className: offerPreviewSection ? offerPreviewSection.className : '',
            style: {
                display: offerPreviewSection ? window.getComputedStyle(offerPreviewSection).display : ''
            }
        },
        recentSubmissionsSection: {
            className: recentSubmissionsSection ? recentSubmissionsSection.className : '',
            style: {
                width: recentSubmissionsSection ? window.getComputedStyle(recentSubmissionsSection).width : '',
                maxWidth: recentSubmissionsSection ? window.getComputedStyle(recentSubmissionsSection).maxWidth : ''
            }
        }
    };
    
    console.log("Original layout captured:", window.originalLayoutState);
}

// Helper function to restore the original layout
function restoreOriginalLayout() {
    if (!window.originalLayoutState) {
        console.error("Cannot restore layout: Original state not captured");
        return;
    }
    
    const employeeForm = document.getElementById('employeeForm');
    const offerPreviewSection = document.getElementById('offerPreviewSection');
    const recentSubmissionsSection = document.getElementById('recentSubmissionsSection');
    const mainContainer = document.querySelector('.two-column-layout');
    const rightColumn = offerPreviewSection ? offerPreviewSection.parentElement : null;
    const submittedProfilesTitle = document.getElementById('submittedProfilesTitle');
    
    // Restore main container
    if (mainContainer) {
        mainContainer.className = window.originalLayoutState.mainContainer.className;
        mainContainer.classList.remove('view-mode'); // Make sure view-mode is removed
    }
    
    // Restore employee form (left column)
    if (employeeForm) {
        employeeForm.className = window.originalLayoutState.employeeForm.className;
        employeeForm.style.display = 'block';
        employeeForm.style.width = '';  // Reset to CSS default
    }
    
    // Restore right column
    if (rightColumn) {
        rightColumn.className = window.originalLayoutState.rightColumn.className;
        rightColumn.style.width = '';  // Reset to CSS default
        rightColumn.style.maxWidth = '';
        rightColumn.style.flex = '';
    }
    
    // Restore offer preview section
    if (offerPreviewSection) {
        offerPreviewSection.className = window.originalLayoutState.offerPreviewSection.className;
        offerPreviewSection.style.display = 'block';
    }
    
    // Restore recent submissions section
    if (recentSubmissionsSection) {
        recentSubmissionsSection.className = window.originalLayoutState.recentSubmissionsSection.className;
        recentSubmissionsSection.style.width = '';  // Reset to CSS default
        recentSubmissionsSection.style.maxWidth = '';
        recentSubmissionsSection.style.flex = '';
    }
    
    // Update title
    if (submittedProfilesTitle) {
        submittedProfilesTitle.textContent = 'RECENTLY SUBMITTED PROFILES';
    }
    
    console.log("Original layout restored");
}

// Policy tag management
function addPolicy(policyText) {
    const policyContainer = document.querySelector('.flex.flex-wrap.gap-2');
    if (!policyContainer) return;
    
    const policyTag = document.createElement('span');
    policyTag.className = 'inline-flex items-center px-3 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800';
    policyTag.innerHTML = `${policyText} <button class="ml-1 text-gray-500 hover:text-gray-700" onclick="removePolicy(this)">&times;</button>`;
    
    policyContainer.appendChild(policyTag);
}

function removePolicy(button) {
    const tag = button.parentElement;
    if (tag) {
        tag.remove();
    }
}

// Send invitation functionality
function sendInvitation() {
    // Show loading state
    const sendButton = document.getElementById('sendButton');
    if (!sendButton) return;
    
    const originalText = sendButton.innerHTML;
    sendButton.innerHTML = '<span class="inline-flex items-center"><svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Sending...</span>';
    sendButton.disabled = true;
    
    // Get form data
    const companySelect = document.querySelector('select[name="company"]');
    const nameInput = document.getElementById('employeeName');
    const emailInput = document.getElementById('employeeEmail');
    const departmentSelect = document.getElementById('departmentSelect');
    const designationSelect = document.getElementById('designationSelect');
    const roleSelect = document.getElementById('roleSelect');
    const offerLetterSelect = document.getElementById('offerLetterSelect');
    
    // Get document checkboxes and selects
    const hiringAgreementCheckbox = document.getElementById('hiringAgreementCheckbox');
    const handbookCheckbox = document.getElementById('handbookCheckbox');
    const hrPoliciesCheckbox = document.getElementById('hrPoliciesCheckbox');
    const trainingMaterialCheckbox = document.getElementById('trainingMaterialCheckbox');
    
    const hiringAgreementSelect = document.getElementById('hiringAgreementSelect');
    const handbookSelect = document.getElementById('handbookSelect');
    const hrPoliciesSelect = document.getElementById('hrPoliciesSelect');
    const trainingMaterialSelect = document.getElementById('trainingMaterialSelect');
    const photoUpload = document.getElementById('photoUpload');
    
    // Debug log to check field values
    console.log('Form values:', {
        company: companySelect ? companySelect.value : 'Not found',
        name: nameInput ? nameInput.value : 'Not found',
        email: emailInput ? emailInput.value : 'Not found',
        department: departmentSelect ? departmentSelect.value : 'Not found',
        designation: designationSelect ? designationSelect.value : 'Not found',
        role: roleSelect ? roleSelect.value : 'Not found',
        offerLetter: offerLetterSelect ? offerLetterSelect.value : 'Not found',
        hiringAgreement: hiringAgreementCheckbox && hiringAgreementCheckbox.checked ? hiringAgreementSelect.value : 'Not selected',
        handbook: handbookCheckbox && handbookCheckbox.checked ? handbookSelect.value : 'Not selected',
        hrPolicies: hrPoliciesCheckbox && hrPoliciesCheckbox.checked ? hrPoliciesSelect.value : 'Not selected',
        trainingMaterial: trainingMaterialCheckbox && trainingMaterialCheckbox.checked ? trainingMaterialSelect.value : 'Not selected'
    });
    
    // Validate required fields
    if (!nameInput || !nameInput.value.trim()) {
        Swal.fire({
            icon: 'error',
            title: 'Missing Information',
            text: 'Please enter a name for the employee',
            confirmButtonColor: '#7B3DF3'
        });
        sendButton.innerHTML = originalText;
        sendButton.disabled = false;
        return;
    }
    
    if (!emailInput || !emailInput.value.trim()) {
        Swal.fire({
            icon: 'error',
            title: 'Missing Information',
            text: 'Please enter an email address for the employee',
            confirmButtonColor: '#7B3DF3'
        });
        sendButton.innerHTML = originalText;
        sendButton.disabled = false;
        return;
    }
    
    if (!companySelect || !companySelect.value || companySelect.value === 'Company') {
        Swal.fire({
            icon: 'error',
            title: 'Missing Information',
            text: 'Please select a company',
            confirmButtonColor: '#7B3DF3'
        });
        sendButton.innerHTML = originalText;
        sendButton.disabled = false;
        return;
    }
    
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailInput.value.trim())) {
        Swal.fire({
            icon: 'error',
            title: 'Invalid Email',
            text: 'Please enter a valid email address',
            confirmButtonColor: '#7B3DF3'
        });
        sendButton.innerHTML = originalText;
        sendButton.disabled = false;
        return;
    }
    
    // Get all policy tags
    const policyContainer = document.querySelector('.flex.flex-wrap.gap-2');
    const policies = [];
    if (policyContainer) {
        const policyTags = policyContainer.querySelectorAll('span');
        policyTags.forEach(tag => {
            // Extract only the policy text (remove the "×" button)
            const policyText = tag.textContent.trim().replace('×', '').trim();
            if (policyText) {
                policies.push(policyText);
            }
        });
    }
    
    // Create FormData object
    const formData = new FormData();
    
    // Add form fields to FormData with correct field names
    formData.append('company', companySelect.value);
    formData.append('name', nameInput.value.trim());
    formData.append('email', emailInput.value.trim());
    
    if (departmentSelect && departmentSelect.value) {
        formData.append('department', departmentSelect.value);
    }
    
    if (designationSelect && designationSelect.value) {
        formData.append('designation', designationSelect.value);
    }
    
    if (roleSelect && roleSelect.value) {
        formData.append('role', roleSelect.value);
    }
    
    if (offerLetterSelect && offerLetterSelect.value) {
        formData.append('offer_letter', offerLetterSelect.value);
    }
    
    // Create an array to track selected additional documents
    const additionalDocuments = [];
    
    // Only add document templates if their checkbox is checked
    if (hiringAgreementCheckbox && hiringAgreementCheckbox.checked && hiringAgreementSelect && hiringAgreementSelect.value) {
        formData.append('hiring_agreement', hiringAgreementSelect.value);
        additionalDocuments.push({
            type: 'hiring_agreement',
            id: hiringAgreementSelect.value,
            name: hiringAgreementSelect.options[hiringAgreementSelect.selectedIndex].text
        });
        console.log('Adding hiring agreement:', hiringAgreementSelect.value);
    }
    
    if (handbookCheckbox && handbookCheckbox.checked && handbookSelect && handbookSelect.value) {
        formData.append('handbook', handbookSelect.value);
        additionalDocuments.push({
            type: 'handbook',
            id: handbookSelect.value,
            name: handbookSelect.options[handbookSelect.selectedIndex].text
        });
        console.log('Adding handbook:', handbookSelect.value);
    }
    
    if (hrPoliciesCheckbox && hrPoliciesCheckbox.checked && hrPoliciesSelect && hrPoliciesSelect.value) {
        formData.append('hr_policies', hrPoliciesSelect.value);
        additionalDocuments.push({
            type: 'hr_policies',
            id: hrPoliciesSelect.value,
            name: hrPoliciesSelect.options[hrPoliciesSelect.selectedIndex].text
        });
        console.log('Adding HR policies:', hrPoliciesSelect.value);
    }
    
    if (trainingMaterialCheckbox && trainingMaterialCheckbox.checked && trainingMaterialSelect && trainingMaterialSelect.value) {
        formData.append('training_material', trainingMaterialSelect.value);
        additionalDocuments.push({
            type: 'training_material',
            id: trainingMaterialSelect.value,
            name: trainingMaterialSelect.options[trainingMaterialSelect.selectedIndex].text
        });
        console.log('Adding training material:', trainingMaterialSelect.value);
    }
    
    // Add all additional documents as a JSON string
    if (additionalDocuments.length > 0) {
        formData.append('additional_documents', JSON.stringify(additionalDocuments));
    }
    
    // Add policies as JSON string
    if (policies.length > 0) {
        formData.append('policies', JSON.stringify(policies));
    }
    
    // Add photo if selected
    if (photoUpload && photoUpload.files.length > 0) {
        formData.append('photo', photoUpload.files[0]);
    }
    
    // For debugging, log the form data entries
    for (const pair of formData.entries()) {
        console.log(pair[0], pair[1]);
    }
    
    // Send data to server
    fetch('/hr/onboarding/send-invitation/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        sendButton.innerHTML = originalText;
        sendButton.disabled = false;
        
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Invitation Sent',
                text: data.message || 'The onboarding invitation has been sent successfully',
                confirmButtonColor: '#7B3DF3'
            }).then(() => {
                // Reset form
                resetForm();
                
                // Refresh employees table
                populateEmployeesTable();
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.message || 'There was an error sending the invitation. Please try again.',
                confirmButtonColor: '#7B3DF3'
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        sendButton.innerHTML = originalText;
        sendButton.disabled = false;
        
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'There was an error sending the invitation. Please try again.',
            confirmButtonColor: '#7B3DF3'
        });
    });
}

// Add debug helper function
function debugElements() {
    console.log("Debug Elements:");
    console.log("addEmployeeTab:", document.getElementById('addEmployeeTab'));
    console.log("viewEmployeesTab:", document.getElementById('viewEmployeesTab'));
    console.log("employeeForm:", document.getElementById('employeeForm'));
    console.log("viewEmployeesSection:", document.getElementById('viewEmployeesSection'));
    console.log("offerPreviewSection:", document.getElementById('offerPreviewSection'));
    console.log("recentSubmissionsSection:", document.getElementById('recentSubmissionsSection'));
    console.log("mainContainer:", document.querySelector('.two-column-layout'));
}

// Add event listener for page load
document.addEventListener('DOMContentLoaded', function() {
    const photoUpload = document.getElementById('photoUpload');
    const photoPreview = document.getElementById('photoPreview');
    const photoPlaceholder = document.getElementById('photoPlaceholder');
    const sendButton = document.getElementById('sendButton');
    const policyInput = document.getElementById('policyInput');
    const addPolicyBtn = document.getElementById('addPolicyBtn');
    
    // Debug the page elements
    debugElements();
    
    // Set up photo upload preview
    if (photoUpload && photoPreview && photoPlaceholder) {
        photoUpload.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    photoPreview.src = e.target.result;
                    photoPreview.classList.remove('hidden');
                    photoPlaceholder.classList.add('hidden');
                };
                
                reader.readAsDataURL(this.files[0]);
            }
        });
    }
    
    // Set up send button click handler
    if (sendButton) {
        sendButton.addEventListener('click', sendInvitation);
    }
    
    // Set up add policy button click handler
    if (addPolicyBtn && policyInput) {
        addPolicyBtn.addEventListener('click', function() {
            const policyText = policyInput.value.trim();
            if (policyText) {
                addPolicy(policyText);
                policyInput.value = '';
                policyInput.focus();
            }
        });
        
        // Also allow adding policy with Enter key
        policyInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addPolicyBtn.click();
            }
        });
    }
    
    // Check if URL has tab parameter
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab');
    
    // Initialize with the correct tab active based on URL or default to Add tab
    if (tabParam === 'view') {
        switchTab('view');
    } else {
        switchTab('add');
    }

    const acceptInvitationForm = document.getElementById('acceptInvitationForm');
    if (acceptInvitationForm) {
        acceptInvitationForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const confirmButton = document.getElementById('confirmAcceptButton');
            confirmButton.disabled = true;
            confirmButton.textContent = 'Accepting...';

            const invitationId = document.getElementById('invitationId').value;
            const grossSalary = document.getElementById('grossSalary').value;
            const group = document.getElementById('groupSelect').value;

            if (!grossSalary || parseFloat(grossSalary) <= 0) {
                Swal.fire('Validation Error', 'Please enter a valid Gross Salary.', 'error');
                confirmButton.disabled = false;
                confirmButton.textContent = 'Accept Employee';
                return;
            }

            const payouts = [];
            const payoutRows = document.querySelectorAll('#payoutsContainer > div');
            payoutRows.forEach(row => {
                const select = row.querySelector('.payout-select');
                const amount = row.querySelector('.payout-amount');
                if (select.value && amount.value) {
                    payouts.push({ id: select.value, amount: amount.value });
                }
            });

            const formData = new FormData();
            formData.append('gross_salary', grossSalary);
            formData.append('group', group);
            formData.append('payouts', JSON.stringify(payouts));
            formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

            fetch(`/hr/onboarding/invitation/${invitationId}/accept/`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('acceptInvitationModal').classList.add('hidden');
                confirmButton.disabled = false;
                confirmButton.textContent = 'Accept Employee';

                if (data.success) {
                        Swal.fire({
                            title: 'Success!',
                            text: 'Invitation accepted and employee created successfully.',
                            icon: 'success',
                            confirmButtonColor: '#10B981'
                    }).then(() => {
                        // Here you should probably reload the invitations or update the UI
                        window.location.reload(); // simple reload for now
                    });
                    } else {
                        Swal.fire({
                            title: 'Error!',
                        text: data.message || 'An error occurred.',
                            icon: 'error'
                        });
                    }
            })
            .catch(error => {
                document.getElementById('acceptInvitationModal').classList.add('hidden');
                confirmButton.disabled = false;
                confirmButton.textContent = 'Accept Employee';
                Swal.fire('Request Failed', error.toString(), 'error');
            });
        });
    }
});

// Employee table management
function populateEmployeesTable() {
    console.log("populateEmployeesTable called");
    const viewEmployeesSection = document.getElementById('viewEmployeesSection');
    if (!viewEmployeesSection) {
        console.error("viewEmployeesSection not found");
        return;
    }
    
    // Show loading state
    viewEmployeesSection.innerHTML = '<div class="text-center py-4">Loading invitations...</div>';
    
    // Fetch invitations from context data
    const invitations = window.invitationsData || [];
    console.log("Invitations data:", invitations);
    
    if (invitations.length === 0) {
        viewEmployeesSection.innerHTML = '<div class="text-center py-4 text-gray-500">No invitations found.</div>';
        return;
    }
    
    // Add header section with title and refreshing functionality
    let headerHTML = `
        <div class="flex justify-between items-center mb-4">
            <h1 class="text-xl font-bold text-gray-800">Invitations</h1>
            <button id="refreshInvitationsBtn" class="flex items-center px-3 py-1.5 bg-[#7B3DF3] text-white rounded-md hover:bg-[#6935D3] transition-all duration-200">
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
            </button>
        </div>
        
        <div class="bg-white p-4 rounded-lg shadow-sm mb-4">
            <div class="flex flex-wrap gap-3">
                <div class="flex items-center">
                    <span class="inline-block w-2 h-2 rounded-full bg-gray-100 mr-1"></span>
                    <span class="text-xs text-gray-600">Pending</span>
                </div>
                <div class="flex items-center">
                    <span class="inline-block w-2 h-2 rounded-full bg-yellow-100 mr-1"></span>
                    <span class="text-xs text-gray-600">Sent</span>
                </div>
                <div class="flex items-center">
                    <span class="inline-block w-2 h-2 rounded-full bg-green-100 mr-1"></span>
                    <span class="text-xs text-gray-600">Completed</span>
                </div>
                <div class="flex items-center">
                    <span class="inline-block w-2 h-2 rounded-full bg-red-100 mr-1"></span>
                    <span class="text-xs text-gray-600">Rejected/Expired</span>
                </div>
            </div>
        </div>
    `;
    
    // Generate table HTML
    let tableHTML = `
        <div class="bg-white rounded-lg shadow-md overflow-hidden">
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Department</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sent Date</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
    `;
    
    // Add invitation rows
    invitations.forEach(invitation => {
        // Format date
        const sentDate = invitation.sent_at ? new Date(invitation.sent_at).toLocaleDateString() : 'Not sent';
        
        // Determine status class
        let statusClass = '';
        switch(invitation.status) {
            case 'pending':
                statusClass = 'bg-gray-100 text-gray-800';
                break;
            case 'sent':
                statusClass = 'bg-yellow-100 text-yellow-800';
                break;
            case 'completed':
                statusClass = 'bg-green-100 text-green-800';
                break;
            case 'rejected':
                statusClass = 'bg-red-100 text-red-800';
                break;
            case 'expired':
                statusClass = 'bg-red-100 text-red-800';
                break;
            default:
                statusClass = 'bg-gray-100 text-gray-800';
        }
        
        // Make sure invitation_id is available and not undefined
        const invitationId = invitation.invitation_id || '';
        
        tableHTML += `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${invitation.name || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${invitation.email || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${invitation.department || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}">
                        ${invitation.status.charAt(0).toUpperCase() + invitation.status.slice(1)}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${sentDate}</td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center space-x-3">
                        ${invitation.status === 'completed' ? `
                            <button 
                                class="text-blue-600 hover:text-blue-800 focus:outline-none" 
                                title="View Details"
                                onclick="viewInvitationDetails('${invitationId}')">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                            </button>
                            <button 
                                class="text-green-600 hover:text-green-800 focus:outline-none" 
                                title="Accept" 
                                onclick="acceptInvitation('${invitationId}')">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                                </svg>
                            </button>
                            <button 
                                class="text-red-600 hover:text-red-800 focus:outline-none" 
                                title="Reject" 
                                onclick="rejectInvitation('${invitationId}')">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        ` : `
                            <button 
                                class="text-red-600 hover:text-red-800 focus:outline-none" 
                                title="Delete" 
                                onclick="deleteInvitation('${invitationId}')">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        `}
                    </div>
                </td>
            </tr>
        `;
    });
    
    tableHTML += `
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    // Combine all HTML
    viewEmployeesSection.innerHTML = headerHTML + tableHTML;
    
    // Add refresh button event listener
    const refreshButton = document.getElementById('refreshInvitationsBtn');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            // Show loading state
            viewEmployeesSection.innerHTML = '<div class="text-center py-4">Refreshing invitation data...</div>';
            
            // Force a refresh by calling populateEmployeesTable again
            setTimeout(() => {
                populateEmployeesTable();
            }, 300);
        });
    }
}

// View invitation details
function viewInvitationDetails(invitationId) {
    // Show loading indicator
    Swal.fire({
        title: 'Loading...',
        text: 'Fetching invitation details',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    // Fetch invitation details from the server
    fetch(`/hr/onboarding/invitation/${invitationId}/?format=json`, {
        headers: {
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            Swal.close();
            
            if (data.success) {
                const invitation = data.invitation;
                
                // Format dates for display
                const createdAt = invitation.created_at ? new Date(invitation.created_at).toLocaleString() : 'N/A';
                const sentAt = invitation.sent_at ? new Date(invitation.sent_at).toLocaleString() : 'N/A';
                const completedAt = invitation.completed_at ? new Date(invitation.completed_at).toLocaleString() : 'N/A';
                const rejectedAt = invitation.rejected_at ? new Date(invitation.rejected_at).toLocaleString() : 'N/A';
                const acceptedAt = invitation.accepted_at ? new Date(invitation.accepted_at).toLocaleString() : 'N/A';
                
                // Prepare policies list
                let policiesList = '';
                if (invitation.policies && invitation.policies.length > 0) {
                    policiesList = invitation.policies.map(policy => `<li>${policy}</li>`).join('');
                } else {
                    policiesList = '<li>No policies attached</li>';
                }
                
                // Determine status display class and icon
                let statusDisplay = '';
                if (invitation.status === 'completed') {
                    statusDisplay = `<span class="text-blue-600 font-semibold">Completed</span>`;
                } else if (invitation.status === 'rejected') {
                    statusDisplay = `<span class="text-red-600 font-semibold">Rejected</span>`;
                } else if (invitation.status === 'accepted') {
                    statusDisplay = `<span class="text-green-600 font-semibold">Accepted</span>`;
                } else if (invitation.status === 'need_discussion') {
                    statusDisplay = `<span class="text-purple-600 font-semibold">Needs Discussion</span>`;
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'There was an error fetching the invitation details. Please try again.',
                confirmButtonColor: '#7B3DF3'
            });
        });
}

// Function to accept an invitation
function acceptInvitation(invitationId) {
    // Show the custom modal
    const modal = document.getElementById('acceptInvitationModal');
    modal.classList.remove('hidden');

    // Set the invitation ID in the form
    document.getElementById('invitationId').value = invitationId;

    // Clear previous form state if any
    document.getElementById('grossSalary').value = '';
    document.getElementById('groupSelect').selectedIndex = 0;
    const payoutsContainer = document.getElementById('payoutsContainer');
    payoutsContainer.innerHTML = '';
    addPayoutRow(); // Add one initial payout row
}

// Function to reject an invitation
function rejectInvitation(invitationId) {
    // Show confirmation dialog
    Swal.fire({
        title: 'Reject Invitation',
        text: 'Are you sure you want to reject this invitation? This will mark the invitation as rejected.',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#EF4444',
        cancelButtonColor: '#6B7280',
        confirmButtonText: 'Yes, reject it',
        cancelButtonText: 'Cancel'
    }).then((result) => {
        if (result.isConfirmed) {
            // Show loading indicator
            Swal.fire({
                title: 'Processing...',
                text: 'Rejecting invitation',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });

            // Send the rejection request
            fetch(`/hr/onboarding/invitation/${invitationId}/reject/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    action: 'reject',
                    from_status: 'completed',
                    to_status: 'rejected'
                })
            })
            .then(response => response.json())
            .then(data => {
                Swal.close();
                
                if (data.success) {
                    Swal.fire({
                        title: 'Success!',
                        text: 'Invitation rejected successfully. The applicant will be notified via email.',
                        icon: 'success',
                        confirmButtonColor: '#EF4444'
                    }).then(() => {
                        // Refresh the invitations table
                        populateEmployeesTable();
                    });
                } else {
                    Swal.fire({
                        title: 'Error',
                        text: data.message || 'An error occurred while rejecting the invitation',
                        icon: 'error',
                        confirmButtonColor: '#EF4444'
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                Swal.fire({
                    title: 'Error',
                    text: 'An error occurred while rejecting the invitation. Please try again.',
                    icon: 'error',
                    confirmButtonColor: '#EF4444'
                });
            });
        }
    });
}

// Function to setup offer letter preview
function setupOfferLetterPreview() {
    const select = document.getElementById('offerLetterSelect');
    const previewButtons = document.getElementById('previewButtons');
    const previewButton = document.getElementById('previewButton');
    const previewContent = document.getElementById('offerLetterPreviewContent');
    const previewSection = document.getElementById('offerPreviewSection');
    
    if (!select || !previewButtons || !previewButton || !previewContent) {
        console.error('Could not find all elements for offer letter preview functionality');
        return;
    }
    
    // Make sure the preview section is visible
    if (previewSection) {
        previewSection.style.display = 'block';
    }
    
    // Function to fetch and display offer letter preview
    function fetchOfferLetterPreview(documentId) {
        if (!documentId) {
            console.error('No offer letter ID provided');
            return;
        }
        
        // Show loading state
        previewContent.innerHTML = '<p class="text-gray-500">Loading preview...</p>';
        
        const url = `/hr/offerletters/${documentId}/preview/`;
        console.log('Fetching offer letter from:', url);
        
        // Fetch the document content
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Server responded with status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Display the document content
                    previewContent.innerHTML = data.content;
                    
                    // Ensure the preview section is visible
                    if (previewSection) {
                        previewSection.style.display = 'block';
                        previewSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }
                } else {
                    previewContent.innerHTML = '<p class="text-red-500">Error loading preview: ' + (data.error || 'Unknown error') + '</p>';
                }
            })
            .catch(error => {
                console.error('Error fetching offer letter preview:', error);
                previewContent.innerHTML = '<p class="text-red-500">Failed to load preview. Please try again.</p>';
            });
    }
    
    // Show/hide preview button when select has a value
    select.addEventListener('change', function() {
        if(this.value) {
            previewButtons.classList.remove('hidden');
            
            // Also load the preview when a document is selected
            fetchOfferLetterPreview(this.value);
        } else {
            previewButtons.classList.add('hidden');
            previewContent.innerHTML = '<p class="text-gray-500">Select a template and click the preview button to see it here.</p>';
        }
    });
    
    select.addEventListener('focus', function() {
        if(this.value) {
            previewButtons.classList.remove('hidden');
        }
    });
    
    select.addEventListener('blur', function(e) {
        // Small delay to allow clicking the preview button
        setTimeout(() => {
            if(!e.relatedTarget || !e.relatedTarget.closest(`#previewButtons`)) {
                previewButtons.classList.add('hidden');
            }
        }, 100);
    });
    
    // Preview button click handler
    previewButton.addEventListener('click', function() {
        fetchOfferLetterPreview(select.value);
    });
}

// Function to delete an invitation
function deleteInvitation(invitationId) {
    // Show confirmation dialog
    Swal.fire({
        title: 'Are you sure?',
        text: "This invitation will be permanently deleted.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#7B3DF3',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Yes, delete it!'
    }).then((result) => {
        if (result.isConfirmed) {
            // Show loading state
            Swal.fire({
                title: 'Deleting...',
                text: 'Processing your request',
                allowOutsideClick: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });
            
            // Get CSRF token
            const csrftoken = getCookie('csrftoken');
            
            // Send delete request
            fetch(`/hr/onboarding/invitation/${invitationId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    Swal.fire({
                        icon: 'success',
                        title: 'Deleted!',
                        text: 'The invitation has been deleted.',
                        confirmButtonColor: '#7B3DF3'
                    }).then(() => {
                        // Refresh the table to reflect the change
                        populateEmployeesTable();
                    });
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: data.message || 'Failed to delete the invitation.',
                        confirmButtonColor: '#7B3DF3'
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'There was an error deleting the invitation. Please try again.',
                    confirmButtonColor: '#7B3DF3'
                });
            });
        }
    });
}

// Helper function to get cookies (needed for CSRF token)
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