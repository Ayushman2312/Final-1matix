import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matrix.settings')
django.setup()

from django.conf import settings
from website.models import Website
from django.contrib.auth.models import User

def fix_image_paths():
    """Fix banner image paths with various issues"""
    
    print("Starting image path fixing process...")
    websites = Website.objects.all()
    print(f"Found {websites.count()} websites to check")
    
    fixed_websites = 0
    fixed_banners = 0
    
    for website in websites:
        print(f"\nWebsite ID: {website.id}, User: {website.user.username if website.user else 'No user'}")
        
        # Check if hero_banners exists
        if 'hero_banners' not in website.content:
            print("  No hero_banners found in website content.")
            continue
            
        hero_banners = website.content['hero_banners']
        print(f"  Found {len(hero_banners)} banner(s)")
        
        website_modified = False
        
        # Process each banner
        for i, banner in enumerate(hero_banners):
            if 'image' not in banner:
                print(f"  Banner {i+1} has no image path.")
                continue
                
            image_path = banner['image']
            
            # Skip external URLs
            if image_path.startswith(('http://', 'https://')):
                print(f"  Banner {i+1} uses external URL: {image_path}")
                continue
            
            # Check for various path issues and fix them
            new_path = image_path
            
            # Case 1: Fix paths starting with "media/"
            if image_path.startswith('media/'):
                old_path = image_path
                new_path = '/' + image_path
                fixed = True
                print(f"  Fixed Banner {i+1} path (media/ prefix):")
                print(f"    Old: {old_path}")
                print(f"    New: {new_path}")
            
            # Case 2: Fix duplicate slashes
            elif '//' in image_path and not image_path.startswith('http'):
                old_path = image_path
                new_path = image_path.replace('//', '/')
                fixed = True
                print(f"  Fixed Banner {i+1} path (duplicate slashes):")
                print(f"    Old: {old_path}")
                print(f"    New: {new_path}")
            
            # Case 3: Fix paths missing leading slash
            elif not image_path.startswith('/') and not image_path.startswith('media/'):
                old_path = image_path
                new_path = '/' + image_path
                fixed = True
                print(f"  Fixed Banner {i+1} path (missing leading slash):")
                print(f"    Old: {old_path}")
                print(f"    New: {new_path}")
            
            # Case 4: No issues found
            else:
                fixed = False
                print(f"  Banner {i+1} path looks correct: {image_path}")
            
            # Update the path if needed
            if fixed:
                website.content['hero_banners'][i]['image'] = new_path
                website_modified = True
                fixed_banners += 1
                
                # Check if the file actually exists
                if new_path.startswith('/'):
                    relative_path = new_path[1:]  # Remove leading slash
                else:
                    relative_path = new_path
                
                if relative_path.startswith('media/'):
                    relative_path = relative_path[6:]  # Remove "media/" prefix
                
                absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                if os.path.exists(absolute_path):
                    print(f"    ✅ File exists: {absolute_path}")
                else:
                    print(f"    ❌ File does not exist: {absolute_path}")
                    
                    # Try to find the file in the MEDIA_ROOT directory
                    filename = os.path.basename(relative_path)
                    found_files = []
                    
                    for root, dirs, files in os.walk(settings.MEDIA_ROOT):
                        if filename in files:
                            found_path = os.path.join(root, filename)
                            found_files.append(found_path)
                    
                    if found_files:
                        print(f"      Found similar files:")
                        for found_file in found_files:
                            print(f"        {found_file}")
                    else:
                        print(f"      No similar files found in MEDIA_ROOT")
        
        # Save the website if any changes were made
        if website_modified:
            website.save()
            fixed_websites += 1
            print(f"  Website saved with fixed banner paths.")
    
    print(f"\nSummary: Fixed {fixed_banners} banner paths across {fixed_websites} websites.")

if __name__ == "__main__":
    fix_image_paths() 