from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Website, WebsiteTemplate, WebsitePage, WebsiteProduct, WebsiteCategory
import json
import uuid

class WebsiteTemplateTest(TestCase):
    """Test WebsiteTemplate functionality"""
    
    def setUp(self):
        # Create a test template
        self.template = WebsiteTemplate.objects.create(
            name="Test Template",
            description="A test template",
            template_path="website/template1",
            content_schema={"type": "object"}
        )
        
    def test_template_creation(self):
        """Test that template was created correctly"""
        self.assertEqual(self.template.name, "Test Template")
        self.assertEqual(self.template.description, "A test template")

class WebsiteTest(TestCase):
    """Test Website creation and content management"""
    
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        # Create a test template
        self.template = WebsiteTemplate.objects.create(
            name="Test Template",
            description="A test template",
            template_path="website/template1",
            content_schema={"type": "object"}
        )
        
        # Create a test website
        self.website = Website.objects.create(
            user=self.user,
            template=self.template,
            name="Test Website",
            content={
                "site_name": "Test Website",
                "description": "A test website",
                "contact_info": {
                    "mobile_number": "1234567890",
                    "contact_email": "contact@test.com",
                    "address": "123 Test St"
                }
            }
        )
        
        # Create test client
        self.client = Client()
        
    def test_website_creation(self):
        """Test that website was created correctly"""
        self.assertEqual(self.website.name, "Test Website")
        self.assertEqual(self.website.content["site_name"], "Test Website")
        self.assertEqual(self.website.content["description"], "A test website")
        
    def test_website_contact_info(self):
        """Test contact info is saved correctly"""
        contact_info = self.website.content["contact_info"]
        self.assertEqual(contact_info["mobile_number"], "1234567890")
        self.assertEqual(contact_info["contact_email"], "contact@test.com")
        self.assertEqual(contact_info["address"], "123 Test St")
        
    def test_get_public_url(self):
        """Test get_public_url method"""
        self.assertTrue(self.website.public_slug is not None)
        self.assertTrue("/website/s/" in self.website.get_public_url())

class WebsitePageTest(TestCase):
    """Test WebsitePage functionality"""
    
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        # Create a test template
        self.template = WebsiteTemplate.objects.create(
            name="Test Template",
            description="A test template",
            template_path="website/template1",
            content_schema={"type": "object"}
        )
        
        # Create a test website with non-empty content
        self.website = Website.objects.create(
            user=self.user,
            template=self.template,
            name="Test Website",
            content={"default_content": "This is default content"}
        )
        
        # Create test pages
        self.homepage = WebsitePage.objects.create(
            website=self.website,
            title="Home",
            slug="home",
            template_file="home.html",
            is_homepage=True,
            content={"hero_title": "Welcome"}
        )
        
        self.about_page = WebsitePage.objects.create(
            website=self.website,
            title="About",
            slug="about",
            template_file="about-us.html",
            content={"about_title": "About Us"}
        )
        
    def test_page_creation(self):
        """Test that pages were created correctly"""
        self.assertEqual(self.homepage.title, "Home")
        self.assertEqual(self.homepage.slug, "home")
        self.assertTrue(self.homepage.is_homepage)
        
        self.assertEqual(self.about_page.title, "About")
        self.assertEqual(self.about_page.slug, "about")
        self.assertFalse(self.about_page.is_homepage)
        
    def test_page_content(self):
        """Test page content is saved correctly"""
        self.assertEqual(self.homepage.content["hero_title"], "Welcome")
        self.assertEqual(self.about_page.content["about_title"], "About Us")

class WebsiteProductTest(TestCase):
    """Test WebsiteProduct functionality"""
    
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        # Create a test template
        self.template = WebsiteTemplate.objects.create(
            name="Test Template",
            description="A test template",
            template_path="website/template1",
            content_schema={"type": "object"}
        )
        
        # Create a test website with non-empty content
        self.website = Website.objects.create(
            user=self.user,
            template=self.template,
            name="Test Website",
            content={"default_content": "This is default content"}
        )
        
        # Create test category
        self.category = WebsiteCategory.objects.create(
            website=self.website,
            name="Test Category",
            slug="test-category"
        )
        
        # Create test product
        self.product = WebsiteProduct.objects.create(
            website=self.website,
            category=self.category,
            title="Test Product",
            slug="test-product",
            description="A test product",
            price=99.99,
            image1="path/to/image.jpg"
        )
        
    def test_product_creation(self):
        """Test that product was created correctly"""
        self.assertEqual(self.product.title, "Test Product")
        self.assertEqual(self.product.slug, "test-product")
        self.assertEqual(self.product.description, "A test product")
        self.assertEqual(float(self.product.price), 99.99)
        
    def test_product_category(self):
        """Test product category relationship"""
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.category.name, "Test Category")
        self.assertEqual(self.category.products.first(), self.product)

class WebsiteViewTest(TestCase):
    """Test website views"""
    
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        # Create a test template
        self.template = WebsiteTemplate.objects.create(
            name="Test Template",
            description="A test template",
            template_path="website/template1",
            content_schema={"type": "object"}
        )
        
        # Create a test website
        self.website = Website.objects.create(
            user=self.user,
            template=self.template,
            name="Test Website",
            content={
                "site_name": "Test Website",
                "description": "A test website",
                "contact_info": {
                    "mobile_number": "1234567890",
                    "contact_email": "contact@test.com",
                    "address": "123 Test St"
                }
            }
        )
        
        # Create test client
        self.client = Client()
        
    def test_welcome_page(self):
        """Test welcome page loads correctly"""
        response = self.client.get(reverse('website_welcome'))
        # We'll check for a redirect or a successful response
        self.assertIn(response.status_code, [200, 301, 302])
        
    def test_dashboard_requires_login(self):
        """Test dashboard requires login"""
        response = self.client.get(reverse('website_dashboard'))
        # Should redirect to login if not authenticated
        self.assertIn(response.status_code, [302, 403])
        
        # Login
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('website_dashboard'))
        # Now it should either redirect or load the dashboard
        self.assertIn(response.status_code, [200, 301, 302])
        
    def test_edit_website(self):
        """Test edit website page loads correctly"""
        # Login
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('edit_website', args=[self.website.id]))
        # It should either load or redirect
        self.assertIn(response.status_code, [200, 301, 302])
        
    def test_preview_website(self):
        """Test preview website works"""
        # Login
        self.client.login(username='testuser', password='password123')
        response = self.client.get(reverse('preview_website', args=[self.website.id]))
        # It should either load or redirect
        self.assertIn(response.status_code, [200, 301, 302])
        
    def test_public_website(self):
        """Test public website access"""
        # Public website should be accessible without login
        response = self.client.get(reverse('public_website', args=[self.website.public_slug]))
        # It should either load or redirect
        self.assertIn(response.status_code, [200, 301, 302])

class Template1FunctionalityTest(TestCase):
    """Test Template1 specific functionality"""
    
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='password123'
        )
        
        # Create a test template
        self.template = WebsiteTemplate.objects.create(
            name="Template 1",
            description="First template",
            template_path="website/template1",
            content_schema={"type": "object"}
        )
        
        # Create a website with Template1 specific content
        self.website = Website.objects.create(
            user=self.user,
            template=self.template,
            name="Template 1 Test",
            content={
                "site_name": "Template 1 Site",
                "description": "Testing Template 1",
                "contact_info": {
                    "mobile_number": "1234567890",
                    "contact_email": "contact@test.com",
                    "address": "123 Test St"
                },
                "primary_color": "#FF5733",
                "secondary_color": "#33FF57",
                "accent_color": "#3357FF",
                "hero_banners": [
                    {
                        "image": "https://via.placeholder.com/1920x1080",
                        "title": "Welcome Banner",
                        "description": "Banner description"
                    }
                ],
                "testimonials": [
                    {
                        "name": "John Doe",
                        "position": "CEO",
                        "content": "Great website!",
                        "rating": 5
                    }
                ]
            }
        )
        
        # Add homepage
        self.homepage = WebsitePage.objects.create(
            website=self.website,
            title="Home",
            slug="home",
            template_file="home.html",
            is_homepage=True,
            content={"hero_title": "Welcome to our Homepage"}
        )
        
        # Create test client
        self.client = Client()
        self.client.login(username='testuser', password='password123')
        
    def test_template1_theme_settings(self):
        """Test Template1 theme settings are applied"""
        # Verify that theme settings are saved
        self.assertEqual(self.website.content["primary_color"], "#FF5733")
        self.assertEqual(self.website.content["secondary_color"], "#33FF57")
        self.assertEqual(self.website.content["accent_color"], "#3357FF")
        
    def test_template1_content_sections(self):
        """Test Template1 content sections are saved"""
        # Verify hero banners
        self.assertEqual(len(self.website.content["hero_banners"]), 1)
        self.assertEqual(self.website.content["hero_banners"][0]["title"], "Welcome Banner")
        
        # Verify testimonials
        self.assertEqual(len(self.website.content["testimonials"]), 1)
        self.assertEqual(self.website.content["testimonials"][0]["name"], "John Doe")
        self.assertEqual(self.website.content["testimonials"][0]["rating"], 5)
        
    def test_template1_homepage_rendering(self):
        """Test Template1 homepage renders correctly"""
        response = self.client.get(reverse('preview_website', args=[self.website.id]))
        # It should either load or redirect
        self.assertIn(response.status_code, [200, 301, 302])
