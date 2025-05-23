import re

def fix_version_check():
    file_path = 'data_miner/web_scrapper.py'
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Define replacements - both instances of the version check
    replacements = [
        (
            r'import playwright\s+print\(f"Playwright version: {playwright.__version__}"\)', 
            '''import playwright
            try:
                print(f"Playwright version: {playwright.__version__}")
            except AttributeError:
                print("Playwright is installed (version not available)")'''
        ),
        (
            r'import playwright\s+from playwright.async_api import async_playwright\s+print\(f"Using Playwright version {playwright.__version__}"\)', 
            '''import playwright
                    from playwright.async_api import async_playwright
                    try:
                        print(f"Using Playwright version {playwright.__version__}")
                    except AttributeError:
                        print("Using Playwright (version not available)")'''
        )
    ]
    
    # Apply replacements
    new_content = content
    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, new_content)
    
    # Write the updated content
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    print("Playwright version check issues fixed.")

if __name__ == "__main__":
    fix_version_check() 