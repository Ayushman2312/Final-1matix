import re
import os

def fix_employee_lookups():
    """
    Find and replace all occurrences of Employee.objects.get(id=employee_id)
    with Employee.objects.get(employee_id=employee_id) in hr/views.py
    """
    file_path = 'hr/views.py'
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Replace the pattern
    pattern = r'Employee\.objects\.get\(id=employee_id\)'
    replacement = 'Employee.objects.get(employee_id=employee_id)'
    
    new_content, count = re.subn(pattern, replacement, content)
    
    if count > 0:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(new_content)
        print(f"Successfully replaced {count} occurrences in {file_path}")
    else:
        print(f"No occurrences found in {file_path}")

if __name__ == "__main__":
    fix_employee_lookups() 