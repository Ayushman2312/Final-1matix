import os
import sys
import django
import re

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matrix.settings')
django.setup()

from django.conf import settings
from bs4 import BeautifulSoup
import glob

def fix_image_srcset_paths():
    """
    Find and fix srcset paths with duplicated segments in HTML files
    """
    print("Starting srcset path fixing process...")
    
    # Define the directory to search for template files
    template_dirs = [
        os.path.join(settings.BASE_DIR, 'templates', 'website', 'template1'),
        os.path.join(settings.BASE_DIR, 'templates', 'website')
    ]
    
    # Keep track of fixed files
    fixed_files = 0
    fixed_paths = 0
    
    # Create a regex pattern to detect duplicated paths in srcset
    duplicate_path_pattern = re.compile(r'srcset=["\']([^"\']+)/([^/"\']+)/\2/([^"\']+)["\']')
    
    # Process each HTML file in the template directories
    for template_dir in template_dirs:
        for html_file in glob.glob(os.path.join(template_dir, "**/*.html"), recursive=True):
            print(f"Checking file: {html_file}")
            
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if there's a potential duplicate path
            if '/website_' in content and 'srcset' in content:
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find all img tags with srcset
                modified = False
                for img in soup.find_all('img', srcset=True):
                    srcset = img['srcset']
                    
                    # Check for duplicated path segments
                    if re.search(r'/([^/]+)/\1/', srcset):
                        print(f"  Found duplicate path in srcset: {srcset}")
                        
                        # Fix the srcset by rebuilding it
                        srcset_parts = srcset.split(',')
                        fixed_parts = []
                        
                        for part in srcset_parts:
                            url_and_descriptor = part.strip().split(' ')
                            if len(url_and_descriptor) == 2:
                                url, descriptor = url_and_descriptor
                                
                                # Fix duplicate segments in the URL
                                fixed_url = re.sub(r'/([^/]+)/\1/', r'/\1/', url)
                                
                                if fixed_url != url:
                                    print(f"    Fixed: {url} -> {fixed_url}")
                                    fixed_paths += 1
                                
                                fixed_parts.append(f"{fixed_url} {descriptor}")
                        
                        # Update srcset with fixed parts
                        new_srcset = ', '.join(fixed_parts)
                        img['srcset'] = new_srcset
                        modified = True
                
                # Save the file if modified
                if modified:
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(str(soup))
                    fixed_files += 1
                    print(f"  Updated file: {html_file}")
    
    print(f"Completed! Fixed {fixed_paths} srcset paths across {fixed_files} files.")

if __name__ == "__main__":
    fix_image_srcset_paths() 