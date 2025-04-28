function toggleAllCompanies(selectAllCheckbox) {
    const companyCheckboxes = document.querySelectorAll('.company-checkbox');
    companyCheckboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
}

function updateSelectAll() {
    const selectAllCheckbox = document.getElementById('select_all');
    const companyCheckboxes = document.querySelectorAll('.company-checkbox');
    const allChecked = Array.from(companyCheckboxes).every(checkbox => checkbox.checked);
    selectAllCheckbox.checked = allChecked;
}

// #2
const shareButton = document.getElementById('shareButton');
            const shareModal = document.getElementById('shareModal');
            const modalContent = shareModal.querySelector('.transform');
            
            shareButton.addEventListener('click', () => {
                shareModal.classList.remove('hidden');
                setTimeout(() => {
                    shareModal.classList.remove('opacity-0');
                    modalContent.classList.remove('opacity-0', 'scale-95');
                    modalContent.classList.add('opacity-100', 'scale-100');
                }, 50);
            });
            
            function closeShareModal() {
                modalContent.classList.remove('opacity-100', 'scale-100');
                modalContent.classList.add('opacity-0', 'scale-95');
                shareModal.classList.add('opacity-0');
                setTimeout(() => {
                    shareModal.classList.add('hidden');
                }, 300);
            }
            
            function copyShareLink() {
                const shareLink = document.getElementById('shareLink');
                shareLink.select();
                document.execCommand('copy');
                
                const button = event.target;
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                setTimeout(() => {
                    button.textContent = originalText;
                }, 2000);
            }
            
            document.getElementById('shareForm').addEventListener('submit', (e) => {
                e.preventDefault();
                const mobile = document.getElementById('recipientMobile').value;
                const securityCode = document.getElementById('securityCode').value;
                const passcode = document.getElementById('passcode').value;
                
                // Get selected companies
                const selectedCompanies = Array.from(document.querySelectorAll('input[name="selected_companies"]:checked')).map(cb => cb.value);
                
                if (selectedCompanies.length === 0) {
                    alert('Please select at least one company');
                    return;
                }
                
                // Send data to backend
                const formData = new FormData();
                formData.append('mobile_number', mobile);
                formData.append('security_code', securityCode);
                formData.append('passcode', passcode);
                
                // Append each selected company ID
                selectedCompanies.forEach(companyId => {
                    formData.append('selected_companies[]', companyId);
                });
                
                fetch('/invoicing/create-recipient/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Invoice shared successfully! Recipient can now access it with the provided credentials.');
                        closeShareModal();
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while sharing the invoice.');
                });
            });
            
            // Close modal when clicking outside
            shareModal.addEventListener('click', (e) => {
                if (e.target === shareModal) {
                    closeShareModal();
                }
            });

// #3
function toggleDatePicker() {
    const select = document.getElementById('dateRangeSelect');
    const customDateRange = document.getElementById('customDateRange');
    
    if (select.value === 'custom') {
        customDateRange.classList.remove('hidden');
        customDateRange.classList.add('flex');
    } else if (select.value === 'last7') {
        applyLast7DaysFilter();
    } else {
        customDateRange.classList.add('hidden');
        customDateRange.classList.remove('flex');
        showAllInvoices();
    }
}

function closeDatePicker() {
    const customDateRange = document.getElementById('customDateRange');
    customDateRange.classList.add('hidden');
    customDateRange.classList.remove('flex');
}
function applyDateFilter() {
    const dateFrom = new Date(document.getElementById('dateFrom').value);
    const dateTo = new Date(document.getElementById('dateTo').value);
    dateTo.setHours(23, 59, 59); // Include the entire "to" date

    const invoiceRows = document.querySelectorAll('tbody tr[data-company-id]');
    const noInvoicesRow = document.querySelector('tbody tr:not([data-company-id])');
    let visibleCount = 0;

    invoiceRows.forEach(row => {
        const dateCell = row.querySelector('td:nth-child(2)').textContent;
        const invoiceDate = new Date(dateCell);

        if (invoiceDate >= dateFrom && invoiceDate <= dateTo) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    // Show/hide "No invoices found" message
    if (noInvoicesRow) {
        noInvoicesRow.style.display = visibleCount === 0 ? '' : 'none';
    }
}

function applyLast7DaysFilter() {
    const today = new Date();
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(today.getDate() - 7);

    const invoiceRows = document.querySelectorAll('tbody tr[data-company-id]');
    const noInvoicesRow = document.querySelector('tbody tr:not([data-company-id])');
    let visibleCount = 0;

    invoiceRows.forEach(row => {
        const dateCell = row.querySelector('td:nth-child(2)').textContent;
        const invoiceDate = new Date(dateCell);

        if (invoiceDate >= sevenDaysAgo && invoiceDate <= today) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    // Show/hide "No invoices found" message
    if (noInvoicesRow) {
        noInvoicesRow.style.display = visibleCount === 0 ? '' : 'none';
    }
}

function showAllInvoices() {
    const invoiceRows = document.querySelectorAll('tbody tr[data-company-id]');
    const noInvoicesRow = document.querySelector('tbody tr:not([data-company-id])');
    let visibleCount = 0;

    invoiceRows.forEach(row => {
        row.style.display = '';
        visibleCount++;
    });

    // Show/hide "No invoices found" message
    if (noInvoicesRow) {
        noInvoicesRow.style.display = visibleCount === 0 ? '' : 'none';
    }
}

function filterInvoicesByCompany() {
    const selectedCompanyId = document.getElementById('companySelect').value;
    const invoiceRows = document.querySelectorAll('tbody tr[data-company-id]');
    const noInvoicesRow = document.querySelector('tbody tr:not([data-company-id])');
    let visibleCount = 0;
    
    invoiceRows.forEach(row => {
        const rowCompanyId = row.getAttribute('data-company-id');
        if (selectedCompanyId === 'all' || rowCompanyId === selectedCompanyId) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    // Show/hide "No invoices found" message
    if (noInvoicesRow) {
        noInvoicesRow.style.display = visibleCount === 0 ? '' : 'none';
    }
}

// Initialize filtering on page load
document.addEventListener('DOMContentLoaded', filterInvoicesByCompany);

function viewScreenshot(url) {
    if(url) {
        window.open(url, '_blank');
    }
}

// #4
function toggleDatePicker() {
    const select = document.getElementById('dateRangeSelect');
    const customDateRange = document.getElementById('customDateRange');
    
    if (select.value === 'custom') {
        customDateRange.classList.remove('hidden');
        customDateRange.classList.add('flex');
    } else {
        customDateRange.classList.add('hidden');
        customDateRange.classList.remove('flex');
    }
}
function updatePaymentStatus(invoiceId, newStatus) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    if (!csrfToken) {
        console.error('CSRF token not found');
        alert('Error: CSRF token not found. Please refresh the page and try again.');
        return;
    }

    fetch('/invoicing/reports/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            invoice_id: invoiceId,
            status: newStatus
        })
    })
    .then(response => {
        if (response.ok) {
            // Refresh the page to show updated status
            window.location.reload();
        } else {
            console.error('Error updating payment status');
            alert('Error updating payment status. Please try again.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error updating payment status. Please try again.');
    });
}

// #4
function viewScreenshot(url) {
    const modalId = event.target.closest('tr').querySelector('[id^="screenshotModal"]').id;
    document.getElementById(modalId).classList.remove('hidden');
    document.getElementById(modalId).classList.add('flex');
}

function closeScreenshot(invoiceId) {
    document.getElementById('screenshotModal-' + invoiceId).classList.add('hidden');
    document.getElementById('screenshotModal-' + invoiceId).classList.remove('flex');
}