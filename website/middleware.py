from django.http import HttpResponseNotFound
from django.shortcuts import render
from .models import CustomDomain, DomainLog, WebsitePage
import os
from django.utils.deprecation import MiddlewareMixin
import re

class CustomDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().lower()
        
        # Skip middleware for admin, static URLs and app-specific paths
        if self._should_skip_middleware(request):
            return self.get_response(request)
        
        try:
            # Check if this is a custom domain request
            domain = CustomDomain.objects.get(
                domain=host, 
                verification_status='verified'
            )
            
            # Add website context to the request
            request.website = domain.website
            
            # Ensure required fields exist in website content
            required_fields = [
                'meta_description', 'meta_keywords', 'site_name', 
                'hero_title', 'hero_subtitle', 'hero_button',
                'features_title', 'features_subtitle', 'features',
                'about_title', 'about_content', 'about_image', 'about_button',
                'cta_title', 'cta_subtitle', 'cta_main_button'
            ]
            
            # Copy description to meta_description if available
            if 'meta_description' not in domain.website.content and 'description' in domain.website.content:
                domain.website.content['meta_description'] = domain.website.content['description']
            
            # Ensure websiteName is copied to site_name if needed
            if 'site_name' not in domain.website.content and 'websiteName' in domain.website.content:
                domain.website.content['site_name'] = domain.website.content['websiteName']
            
            # Set default empty values for all required fields if missing
            for field in required_fields:
                if field not in domain.website.content:
                    if field == 'hero_button' or field == 'about_button' or field == 'cta_main_button':
                        domain.website.content[field] = {'url': '#', 'label': 'Learn More'} 
                    elif field == 'features':
                        domain.website.content[field] = [
                            {
                                'icon': 'palette',
                                'title': 'Beautiful Design',
                                'description': 'Modern and elegant designs that capture attention and create memorable experiences.'
                            },
                            {
                                'icon': 'mobile-alt',
                                'title': 'Responsive Layout',
                                'description': 'Our websites look amazing on all devices, from desktops to smartphones.'
                            },
                            {
                                'icon': 'bolt',
                                'title': 'Performance Optimized',
                                'description': 'Fast loading times and smooth performance for the best user experience.'
                            }
                        ]
                    elif field == 'about_image':
                        domain.website.content[field] = 'https://via.placeholder.com/600x400'
                    else:
                        domain.website.content[field] = ""
            
            # Get the page path from the URL
            path = request.path.strip('/')
            
            # Handle root path as homepage
            if not path:
                # Get homepage
                homepage = WebsitePage.objects.filter(
                    website=domain.website,
                    is_homepage=True
                ).first()
                
                if homepage:
                    # Ensure required fields exist in page content
                    if homepage.content is None:
                        homepage.content = {}
                        
                    # Set default empty values for all required fields if missing in page content
                    for field in required_fields:
                        if field not in homepage.content:
                            if field == 'hero_button' or field == 'about_button' or field == 'cta_main_button':
                                homepage.content[field] = {'url': '#', 'label': 'Learn More'}
                            elif field == 'features':
                                homepage.content[field] = [
                                    {
                                        'icon': 'palette',
                                        'title': 'Beautiful Design',
                                        'description': 'Modern and elegant designs that capture attention and create memorable experiences.'
                                    },
                                    {
                                        'icon': 'mobile-alt',
                                        'title': 'Responsive Layout',
                                        'description': 'Our websites look amazing on all devices, from desktops to smartphones.'
                                    },
                                    {
                                        'icon': 'bolt',
                                        'title': 'Performance Optimized',
                                        'description': 'Fast loading times and smooth performance for the best user experience.'
                                    }
                                ]
                            elif field == 'about_image':
                                homepage.content[field] = 'https://via.placeholder.com/600x400'
                            else:
                                homepage.content[field] = ""
                    
                    # Render homepage
                    template_path = os.path.join(
                        domain.website.template.template_path.strip('/'),
                        homepage.template_file
                    )
                    return render(request, template_path, {
                        'website': domain.website,
                        'page': homepage,
                        'content': homepage.content,
                        'global_content': domain.website.content,
                        'seo_data': self._prepare_seo_data(domain.website, homepage)
                    })
                else:
                    # No specific homepage set, use default template home.html
                    template_path = os.path.join(
                        domain.website.template.template_path.strip('/'),
                        'home.html'
                    )
                    return render(request, template_path, {
                        'website': domain.website,
                        'content': domain.website.content,
                        'seo_data': self._prepare_seo_data(domain.website)
                    })
            else:
                # Try to find a matching page by slug
                try:
                    page = WebsitePage.objects.get(
                        website=domain.website,
                        slug=path
                    )
                    
                    # Ensure required fields exist in page content
                    if page.content is None:
                        page.content = {}
                        
                    # Set default empty values for all required fields if missing in page content
                    for field in required_fields:
                        if field not in page.content:
                            if field == 'hero_button' or field == 'about_button' or field == 'cta_main_button':
                                page.content[field] = {'url': '#', 'label': 'Learn More'}
                            elif field == 'features':
                                page.content[field] = [
                                    {
                                        'icon': 'palette',
                                        'title': 'Beautiful Design',
                                        'description': 'Modern and elegant designs that capture attention and create memorable experiences.'
                                    },
                                    {
                                        'icon': 'mobile-alt',
                                        'title': 'Responsive Layout',
                                        'description': 'Our websites look amazing on all devices, from desktops to smartphones.'
                                    },
                                    {
                                        'icon': 'bolt',
                                        'title': 'Performance Optimized',
                                        'description': 'Fast loading times and smooth performance for the best user experience.'
                                    }
                                ]
                            elif field == 'about_image':
                                page.content[field] = 'https://via.placeholder.com/600x400'
                            else:
                                page.content[field] = ""
                    
                    # Render the page using its template
                    template_path = os.path.join(
                        domain.website.template.template_path.strip('/'),
                        page.template_file
                    )
                    return render(request, template_path, {
                        'website': domain.website,
                        'page': page,
                        'content': page.content,
                        'global_content': domain.website.content,
                        'seo_data': self._prepare_seo_data(domain.website, page)
                    })
                except WebsitePage.DoesNotExist:
                    # Check if there's a template file matching the path
                    template_path = os.path.join(
                        domain.website.template.template_path.strip('/'),
                        f"{path}.html"
                    )
                    template_full_path = os.path.join('templates', template_path)
                    
                    if os.path.exists(template_full_path):
                        # Render the template with the global content
                        return render(request, template_path, {
                            'website': domain.website,
                            'content': domain.website.content,
                            'seo_data': self._prepare_seo_data(domain.website)
                        })
                    else:
                        # Return 404 for non-existent pages
                        DomainLog.objects.create(
                            domain=host, 
                            status_code=404,
                            message=f'Page not found: {path}'
                        )
                        return HttpResponseNotFound('Page not found')
            
        except CustomDomain.DoesNotExist:
            # Only log and return 404 for custom domains, not the main domain
            if not self._is_local_domain(host):
                DomainLog.objects.create(
                    domain=host, 
                    status_code=404,
                    message='Domain not found or not verified'
                )
                return HttpResponseNotFound('Website not found')
        
        response = self.get_response(request)
        return response
    
    def _should_skip_middleware(self, request):
        """Check if the request should skip custom domain processing"""
        path = request.path_info.lstrip('/')
        for prefix in ['admin/', 'alavi07/', 'static/', 'media/', 'api/']:
            if path.startswith(prefix):
                return True
                
        # Skip for specific apps
        for app in ['masteradmin/', 'agents/', 'customersupport/', 'user/', 'employee/', 'fee_calculator/', 
                    'listing_creater/', 'product_card/', 'invoicing/', 'hr_management/', 'blackbox/', 'trends/', 'data_miner/','business_analytics/']:
            if path.startswith(app):
                return True
                
        host = request.get_host().lower()
        
        # Skip for the main domain
        if self._is_main_domain(host) and not path.startswith('s/'):
            return True
            
        return False
    
    def _is_local_domain(self, host):
        """Check if this is a local/development domain"""
        local_domains = [
            'localhost:8000',
            '127.0.0.1:8000',
            '[::1]',
            '.test',
            '.local',
            '.devtunnels.ms',
            '1matrix.io',
            'www.1matrix.io',
            '195.35.20.151',
            # '1matrix.io'  # Removed from local domains to treat it as a custom domain
        ]
        
        for domain in local_domains:
            if host.endswith(domain) or host == domain:
                return True
        
        return False

    def _is_main_domain(self, host):
        main_domains = ['1matrix.io', 'www.1matrix.io', '195.35.20.151']
        return host in main_domains or host.startswith('localhost') or host.startswith('127.0.0.1')
        
    def _prepare_seo_data(self, website, page=None):
        """Prepare SEO data for templates"""
        
        # Get website content or initialize empty dict
        website_content = website.content or {}
        
        # Get page content if available
        page_content = page.content if page else {}
        
        # Prepare SEO data dictionary
        seo_data = {
            # Meta title: Page title if available, otherwise website title
            'meta_title': page_content.get('meta_title', 
                          website_content.get('meta_title', 
                          page_content.get('title', 
                          website_content.get('site_name', 'Website')))),
                          
            # Meta description: Page description if available, otherwise website description
            'meta_description': page_content.get('meta_description', 
                               website_content.get('meta_description', 
                               website_content.get('hero_subtitle', ''))),
                               
            # Meta keywords
            'meta_keywords': page_content.get('meta_keywords', 
                            website_content.get('meta_keywords', '')),
                            
            # Open Graph data
            'og_title': page_content.get('og_title', 
                       website_content.get('og_title', 
                       page_content.get('meta_title', 
                       website_content.get('meta_title', '')))),
                       
            'og_description': page_content.get('og_description', 
                            website_content.get('og_description', 
                            page_content.get('meta_description', 
                            website_content.get('meta_description', '')))),
                            
            'og_image': page_content.get('og_image', 
                      website_content.get('og_image', '')),
                      
            # Structured data
            'structured_data': website_content.get('structured_data', {}),
            
            # Social links
            'social_links': website_content.get('social_links', {})
        }
        
        return seo_data

class NoCacheMiddleware(MiddlewareMixin):
    """
    Middleware to set no-cache headers on template1 page responses
    to ensure dynamic content is always fresh.
    """
    
    def process_response(self, request, response):
        # Check if the request is for a template1 page
        if 'template1' in request.path:
            # Set cache control headers
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response

class PerformanceOptimizationMiddleware:
    """
    Middleware for website performance optimization
    Adds cache headers, content compression, and other performance optimizations
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Only apply optimizations to website routes
        if '/website/' in request.path or '/s/' in request.path:
            # Add cache control headers
            if not response.get('Cache-Control') and response.status_code == 200:
                # Cache static assets longer
                if any(ext in request.path.lower() for ext in ['.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']):
                    response['Cache-Control'] = 'public, max-age=86400'  # 1 day
                else:
                    response['Cache-Control'] = 'public, max-age=3600'  # 1 hour
                    
            # Add ETag for efficient caching
            if not response.get('ETag') and hasattr(response, 'content'):
                import hashlib
                etag = hashlib.md5(response.content).hexdigest()
                response['ETag'] = f'"{etag}"'
            
        return response

class LazyLoadingMiddleware:
    """
    Middleware to inject lazy loading attributes to images and iframes
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        response = self.get_response(request)
        
        # Only process HTML responses for website routes
        is_website_route = '/website/' in request.path or '/s/' in request.path
        is_html = response.get('Content-Type', '').lower().startswith('text/html')
        
        if is_website_route and is_html and hasattr(response, 'content'):
            content = response.content.decode('utf-8')
            
            # Add lazy loading to images
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Add lazy loading to images (exclude small icons and logos)
            for img in soup.find_all('img'):
                if not img.get('loading') and not img.get('class') in ['logo', 'icon', 'avatar']:
                    img['loading'] = 'lazy'
            
            # Add lazy loading to iframes
            for iframe in soup.find_all('iframe'):
                if not iframe.get('loading'):
                    iframe['loading'] = 'lazy'
            
            # Auto-optimize image markup for responsiveness
            for img in soup.find_all('img'):
                if not img.get('class') in ['logo', 'icon', 'avatar']:
                    # Add srcset for responsive images
                    src = img.get('src', '')
                    if src and not img.get('srcset') and (src.endswith('.jpg') or src.endswith('.jpeg') or src.endswith('.png')):
                        # Only add srcset for local images
                        if '/media/' in src:
                            # Fix path duplication by extracting just the filename
                            base_path = src.rsplit('/', 1)[0]  # Get the directory path
                            filename = src.rsplit('/', 1)[1]   # Get the filename
                            basename = filename.rsplit('.', 1)[0]  # Get filename without extension
                            ext = filename.rsplit('.', 1)[1]   # Get extension
                            
                            # Create srcset with proper paths
                            img['srcset'] = f"{src} 1x, {base_path}/{basename}-2x.{ext} 2x"
                    # Add responsive width attributes
                    if not img.get('width') and not img.get('height'):
                        img['width'] = '100%'
                        img['style'] = 'max-width: 100%; height: auto;'
                        
            # Update response content
            response.content = soup.encode()
            
        return response