function switchTab(tab) {
    const addEmployeeTab = document.getElementById('addEmployeeTab');
    const viewEmployeesTab = document.getElementById('viewEmployeesTab');
    const employeeForm = document.getElementById('employeeForm');
    const viewEmployeesSection = document.getElementById('viewEmployeesSection');
    const addEmployeeButton = document.querySelector('button[onclick="toggleForm()"]');

    if (tab === 'add') {
        // Switch to Add Employee
        addEmployeeTab.classList.add('bg-white', 'shadow-sm');
        viewEmployeesTab.classList.remove('bg-white', 'shadow-sm');
        viewEmployeesSection.classList.add('hidden');
        employeeForm.classList.remove('hidden');
        addEmployeeButton.classList.remove('hidden');
    } else {
        // Switch to View Employees
        viewEmployeesTab.classList.add('bg-white', 'shadow-sm');
        addEmployeeTab.classList.remove('bg-white', 'shadow-sm');
        employeeForm.classList.add('hidden')
        viewEmployeesSection.classList.remove('hidden');
        addEmployeeButton.classList.add('hidden');
    }
}

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