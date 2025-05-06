import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matrix.settings')
django.setup()

from django.conf import settings
from website.models import Website
from django.contrib.auth.models import User

def check_media_files():
    print(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
    print(f"MEDIA_URL: {settings.MEDIA_URL}")
    
    # Check if MEDIA_ROOT exists
    if not os.path.exists(settings.MEDIA_ROOT):
        print(f"WARNING: MEDIA_ROOT directory does not exist: {settings.MEDIA_ROOT}")
        try:
            os.makedirs(settings.MEDIA_ROOT)
            print(f"Created MEDIA_ROOT directory: {settings.MEDIA_ROOT}")
        except Exception as e:
            print(f"ERROR: Could not create MEDIA_ROOT directory: {str(e)}")
    else:
        print(f"MEDIA_ROOT directory exists: {settings.MEDIA_ROOT}")
    
    # List websites with banner images
    websites = Website.objects.all()
    print(f"Found {websites.count()} websites")
    
    for website in websites:
        print(f"\nWebsite ID: {website.id}, User: {website.user.username if website.user else 'No user'}")
        
        # Check hero_banners
        hero_banners = website.content.get('hero_banners', [])
        print(f"Number of hero banners: {len(hero_banners)}")
        
        for i, banner in enumerate(hero_banners):
            image_path = banner.get('image', None)
            print(f"Banner {i+1} image path: {image_path}")
            
            if image_path:
                # Check if the file path is relative or absolute
                if image_path.startswith(('http://', 'https://')):
                    print(f"  External URL, cannot verify file existence")
                else:
                    # Handle both relative and absolute paths
                    if image_path.startswith(settings.MEDIA_URL):
                        relative_path = image_path[len(settings.MEDIA_URL):]
                    else:
                        relative_path = image_path.lstrip('/')
                    
                    # Construct absolute path
                    absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                    
                    # Check if file exists
                    if os.path.exists(absolute_path):
                        file_size = os.path.getsize(absolute_path)
                        print(f"  File exists: {absolute_path} (Size: {file_size} bytes)")
                    else:
                        print(f"  ERROR: File does not exist: {absolute_path}")
                        
                        # Try to find the file in the MEDIA_ROOT directory
                        filename = os.path.basename(relative_path)
                        found_files = []
                        
                        for root, dirs, files in os.walk(settings.MEDIA_ROOT):
                            if filename in files:
                                found_path = os.path.join(root, filename)
                                found_files.append(found_path)
                        
                        if found_files:
                            print(f"  Found similar files:")
                            for found_file in found_files:
                                print(f"    {found_file}")
                        else:
                            print(f"  No similar files found in MEDIA_ROOT")

if __name__ == "__main__":
    check_media_files() 