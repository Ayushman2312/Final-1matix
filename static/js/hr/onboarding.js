// Tab switching functionality
function switchTab(tab) {
    const addEmployeeTab = document.getElementById('addEmployeeTab');
    const viewEmployeesTab = document.getElementById('viewEmployeesTab');
    const employeeForm = document.getElementById('employeeForm');
    const viewEmployeesSection = document.getElementById('viewEmployeesSection');

    if (tab === 'add') {
        // Switch to Add Employee tab
        addEmployeeTab.classList.add('bg-[#7B3DF3]');
        addEmployeeTab.classList.remove('bg-gray-100');
        addEmployeeTab.classList.add('text-white');
        viewEmployeesTab.classList.remove('bg-[#7B3DF3]');
        viewEmployeesTab.classList.remove('text-white');
        viewEmployeesTab.classList.add('bg-gray-100');
        
        // Show the form
        if (employeeForm) {
            employeeForm.classList.remove('hidden');
        }
        
        // Hide the employees section
        if (viewEmployeesSection) {
            viewEmployeesSection.classList.add('hidden');
        }
    } else {
        // Switch to View Employees tab
        viewEmployeesTab.classList.add('bg-[#7B3DF3]');
        viewEmployeesTab.classList.remove('bg-gray-100');
        viewEmployeesTab.classList.add('text-white');
        addEmployeeTab.classList.remove('text-white');
        addEmployeeTab.classList.remove('bg-[#7B3DF3]');
        addEmployeeTab.classList.add('bg-gray-100');
        
        // Show the employees section
        if (viewEmployeesSection) {
            viewEmployeesSection.classList.remove('hidden');
            populateEmployeesTable();
        }
    }
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

// Employee table management
function populateEmployeesTable() {
    const viewEmployeesSection = document.getElementById('viewEmployeesSection');
    if (!viewEmployeesSection) return;
    
    viewEmployeesSection.innerHTML = `
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
                <tr>
                    <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">John Smith</td>
                    <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-500">john.smith@example.com</td>
                    <td class="px-4 py-2 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                            Pending
                        </span>
                    </td>
                </tr>
                <tr>
                    <td class="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">Sarah Johnson</td>
                    <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-500">sarah.j@example.com</td>
                    <td class="px-4 py-2 whitespace-nowrap">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                            Submitted
                        </span>
                    </td>
                </tr>
            </tbody>
        </table>
    `;
}

// Offer letter preview
function previewTemplate() {
    const select = document.getElementById('offerLetterSelect');
    const selectedOption = select.options[select.selectedIndex];
    
    if (selectedOption && selectedOption.value) {
        const previewContainer = document.getElementById('offerLetterPreview');
        if (previewContainer) {
            const content = selectedOption.getAttribute('data-content');
            previewContainer.innerHTML = `
                <div class="p-4 h-full overflow-auto">
                    <h3 class="text-lg font-semibold text-gray-800 mb-2">${selectedOption.text}</h3>
                    <div class="text-gray-700">${content}</div>
                </div>
            `;
        }
    }
}

// Initialize page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Set default tab
    switchTab('add');
    
    // Policy input handling
    const policyInput = document.querySelector('input[placeholder="Attach Upload (Min. 2)"]');
    const addPolicyButton = policyInput ? policyInput.nextElementSibling : null;
    
    if (addPolicyButton) {
        // Add policy on button click
        addPolicyButton.addEventListener('click', function() {
            const policyText = policyInput.value.trim();
            if (policyText) {
                addPolicy(policyText);
                policyInput.value = '';
            }
        });
        
        // Add policy on Enter key
        policyInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const policyText = policyInput.value.trim();
                if (policyText) {
                    addPolicy(policyText);
                    policyInput.value = '';
                }
            }
        });
    }
    
    // Offer letter dropdown handling
    const offerLetterSelect = document.getElementById('offerLetterSelect');
    const previewButtons = document.getElementById('previewButtons');
    
    if (offerLetterSelect) {
        offerLetterSelect.addEventListener('change', function() {
            if(this.value) {
                previewButtons.classList.remove('hidden');
            } else {
                previewButtons.classList.add('hidden');
            }
        });
        
        offerLetterSelect.addEventListener('focus', function() {
            if(this.value) {
                previewButtons.classList.remove('hidden');
            }
        });
        
        offerLetterSelect.addEventListener('blur', function(e) {
            // Small delay to allow clicking the preview button
            setTimeout(() => {
                if(!e.relatedTarget || !e.relatedTarget.closest('#previewButtons')) {
                    previewButtons.classList.add('hidden');
                }
            }, 100);
        });
    }
    
    // Send button handling
    const sendButton = document.getElementById('sendButton');
    if (sendButton) {
        sendButton.addEventListener('click', function(e) {
            e.preventDefault();
            // Submission logic would go here
            alert('Employee details submitted successfully!');
        });
    }
});

// #2
function updateOfferLetterContent() {
    const select = document.getElementById('offerLetterSelect');
    const textarea = document.getElementById('offerLetterContent');
    const selectedOption = select.options[select.selectedIndex];
    
    if (selectedOption.value) {
      textarea.value = selectedOption.dataset.content;
    } else {
      textarea.value = '';
    }
}

// #3
function toggleForm() {
    const form = document.getElementById('employeeForm');
    form.classList.toggle('hidden');  
}