from django.views.generic import TemplateView
from .models import *
from django.shortcuts import redirect
from django.contrib import messages
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
import logging
from django.conf import settings
from rest_framework import viewsets
from .serializers import ProductSerializer
from rest_framework.permissions import BasePermission

# Configure logger
logger = logging.getLogger(__name__)

class CreateProductCardView(TemplateView):
    template_name = 'product_card/card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Product Card'
        context['categories'] = ProductCategory.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        logger.debug("Processing product card creation request")
        
        # Get form data
        product_title = request.POST.get('title')
        product_description = request.POST.get('description')
        product_price = request.POST.get('price')  # This will be the default price
        product_image1 = request.FILES.get('image1')
        product_image2 = request.FILES.get('image2', None)
        product_image3 = request.FILES.get('image3', None)
        product_image4 = request.FILES.get('image4', None)
        category_id = request.POST.get('category')
        youtube_link = request.POST.get('youtube_link')
        product_hsc_code = request.POST.get('hsn_code')
        product_gst_percentage = request.POST.get('gst_percentage')
        
        logger.debug(f"Received product data: title={product_title}, price={product_price}, category={category_id}")
        logger.debug(f"Images received: primary={bool(product_image1)}, secondary={bool(product_image2)}, tertiary={bool(product_image3)}, quaternary={bool(product_image4)}")
        
        # Get variant data if available
        variant_data = {}
        if request.POST.get('variants'):
            try:
                variant_data = json.loads(request.POST.get('variants'))
                # Log the variant data for debugging
                logger.debug(f"Parsed variant data: {variant_data}")
            except json.JSONDecodeError:
                logger.error("Failed to parse variant data JSON")
                messages.error(request, 'Invalid variant data format')
                return self.render_to_response(self.get_context_data())
        
        try:
            # Get category if specified
            category = None
            if category_id:
                try:
                    category = ProductCategory.objects.get(category_id=category_id)
                except ProductCategory.DoesNotExist:
                    logger.warning(f"Category with ID {category_id} not found")
            
            # Create product with variant data including prices
            product = Product.objects.create(
                category=category,
                product_title=product_title,
                product_description=product_description,
                product_price=product_price,  # Default price
                product_image1=product_image1,
                product_image2=product_image2,
                product_image3=product_image3,
                product_image4=product_image4,
                product_variant=variant_data,  # This will now include prices
                product_video_link=youtube_link,
                product_hsc_code=product_hsc_code,
                product_gst_percentage=product_gst_percentage,
                product_available=True
            )
            
            # Create product card
            logger.debug(f"Creating product card for product ID: {product.product_id}")
            ProductCard.objects.create(
                product=product,
                card_image=product_image1
            )
            
            logger.info(f"Product card created successfully for '{product_title}'")
            messages.success(request, 'Product card created successfully!')
            return JsonResponse({
                'success': True,
                'message': 'Product card created successfully!',
                'redirect_url': reverse('all_product_card')
            })
        except Exception as e:
            logger.error(f"Error creating product card: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'Error creating product card: {str(e)}'
            }, status=400)
        

class AllProductCardView(TemplateView):
    template_name = 'product_card/all_card.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'All Product Cards'
        context['product_cards'] = Product.objects.all().order_by('-product_created_at')
        context['categories'] = ProductCategory.objects.all()
        return context

class ProductCardDetailView(TemplateView):
    template_name = 'product_card/product.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Get the product and product card
            product = Product.objects.get(product_id=kwargs['product_id'])
            product_card = ProductCard.objects.get(product__product_id=kwargs['product_id'])
            
            # Convert product_variant from string to dict if needed
            variants = product.product_variant
            if isinstance(variants, str):
                variants = json.loads(variants)

            context.update({
                'app_name': 'Product Card Details',
                'product': product,
                'product_card': product_card,
                'variants': variants or {},  # Ensure variants is a dict even if None
            })

            # Add the variants directly to the product object for easier template access
            product.variants = variants or {}

            logger.debug(f"Product detail context: {context}")
            return context
            
        except (Product.DoesNotExist, ProductCard.DoesNotExist) as e:
            logger.error(f"Error fetching product details: {str(e)}")
            messages.error(self.request, 'Product not found')
            return context
        
def delete_product(request, product_id, *args, **kwargs):
    try:
        # Get the product card by product_id
        product = Product.objects.get(product_id=product_id)
        product_name = product.product_title
        
        # Delete the product card
        product.delete()
        
        # Add success message
        messages.success(request, f'Product card "{product_name}" deleted successfully!')
        logger.info(f"Product card for '{product_name}' deleted successfully")
    except Product.DoesNotExist:
        # Handle case where product card doesn't exist
        messages.error(request, 'Product card not found')
        logger.error(f"Attempted to delete non-existent product card with ID: {product_id}")
    except Exception as e:
        # Handle any other exceptions
        messages.error(request, f'Error deleting product card: {str(e)}')
        logger.error(f"Error deleting product card: {str(e)}", exc_info=True)
    
    return redirect('all_product_card')

class CategoryView(TemplateView):
    template_name = 'product_card/category.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Category'
        context['categories'] = ProductCategory.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        try:
            category_name = request.POST.get('category_name')
            if category_name:
                ProductCategory.objects.create(category_name=category_name)
                messages.success(request, f'Category "{category_name}" created successfully!')
                logger.info(f"Category '{category_name}' created successfully")
            else:
                messages.error(request, 'Category name is required')
                logger.error("Attempted to create category without name")
        except Exception as e:
            messages.error(request, f'Error creating category: {str(e)}')
            logger.error(f"Error creating category: {str(e)}", exc_info=True)
        return redirect('category')


def edit_category(request, category_id, *args, **kwargs):
    try:
        category = ProductCategory.objects.get(category_id=category_id)
        
        if request.method == 'POST':
            category_name = request.POST.get('category_name')
            if category_name:
                category.category_name = category_name
                category.save()
                messages.success(request, f'Category updated to "{category_name}" successfully!')
                logger.info(f"Category updated to '{category_name}' successfully")
                return redirect('category')
            else:
                messages.error(request, 'Category name is required')
                logger.error("Attempted to update category without name")
        
        context = {
            'category': category,
            'app_name': 'Edit Category',
            'categories': ProductCategory.objects.all()
        }
        
    except ProductCategory.DoesNotExist:
        messages.error(request, 'Category not found')
        logger.error(f"Attempted to edit non-existent category with ID: {category_id}")
        return redirect('category')
    except Exception as e:
        messages.error(request, f'Error updating category: {str(e)}')
        logger.error(f"Error updating category: {str(e)}", exc_info=True)
        return redirect('category')
    
    return render(request, 'product_card/category.html', context)
class DeleteCategoryView(TemplateView):
    template_name = 'product_card/category.html'

    def post(self, request, *args, **kwargs):
        try:
            category_id = kwargs.get('category_id')
            category = ProductCategory.objects.get(category_id=category_id)
            category_name = category.category_name
            category.delete()
            messages.success(request, f'Category "{category_name}" deleted successfully!')
            logger.info(f"Category '{category_name}' deleted successfully")
        except ProductCategory.DoesNotExist:
            messages.error(request, 'Category not found')
            logger.error(f"Attempted to delete non-existent category with ID: {category_id}")
        except Exception as e:
            messages.error(request, f'Error deleting category: {str(e)}')
            logger.error(f"Error deleting category: {str(e)}", exc_info=True)
        return redirect('category')

def update_product_card(request, product_id, *args, **kwargs):
    try:
        logger.debug(f"Received update request for product ID: {product_id}")
        product = Product.objects.get(product_id=product_id)
        categories = ProductCategory.objects.all()

        if request.method == 'GET':
            logger.debug(f"Processing GET request for product ID: {product_id}")
            # Pre-fill form data
            form_data = {
                'category': product.category,
                'title': product.product_title,
                'description': product.product_description,
                'youtube_link': product.product_video_link or '',
                'price': product.product_price,
                'stock': 'yes' if product.product_available else 'no',
                'current_image': product.product_image1.url if product.product_image1 else None,
                'variations': product.product_variant
            }
            logger.debug(f"Form data prepared: {form_data}")

            context = {
                'product': product,
                'categories': categories,
                'form_data': form_data,
                'app_name': 'Edit Product',
                'is_edit': True
            }

            return render(request, 'product_card/card.html', context)

        elif request.method == 'POST':
            logger.debug(f"Processing POST request for product ID: {product_id}")
            
            # Update basic fields
            product.product_title = request.POST.get('product_title')
            product.product_description = request.POST.get('product_description')
            
            try:
                price = float(request.POST.get('product_price'))
                if price < 0:
                    raise ValueError("Price cannot be negative")
                product.product_price = price
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid price value provided: {request.POST.get('product_price')}")
                messages.error(request, 'Please enter a valid positive price')
                return redirect('all_product_card')

            # Handle image update
            if 'product_image1' in request.FILES:
                logger.debug("Processing new product image upload")
                product.product_image1 = request.FILES['product_image1']

            product.save()
            logger.info(f"Product '{product.product_title}' (ID: {product_id}) updated successfully")
            messages.success(request, 'Product updated successfully!')
            return redirect('all_product_card')

    except Product.DoesNotExist:
        logger.error(f"Attempted to update non-existent product with ID: {product_id}")
        messages.error(request, 'Product not found')
    except Exception as e:
        logger.error(f"Error updating product {product_id}: {str(e)}", exc_info=True)
        messages.error(request, f'Error updating product: {str(e)}')
    
    return redirect('all_product_card')


def search_products(request):
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    
    products = Product.objects.all()
    
    if query:
        products = products.filter(
            Q(product_title__icontains=query) |
            Q(product_description__icontains=query)
        )
    
    if category:
        products = products.filter(category__category_id=category)
    
    products_data = [{
        'id': product.product_id,
        'title': product.product_title,
        'price': str(product.product_price),
        'category_name': product.category.category_name if product.category else '',
        'category_id': str(product.category.category_id) if product.category else '',
        'description': product.product_description,
        'hsc_code': product.product_hsc_code
    } for product in products[:10]]  # Limit to 10 results
    
    return JsonResponse({'products': products_data})

# class AllowedHostsPermission(BasePermission):
#     def has_permission(self, request, view):
#         # Get the origin from the request headers
#         origin = request.META.get('HTTP_ORIGIN', '')
        
#         # Get allowed hosts from settings
#         allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
#         allowed_cors_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        
#         # Check if the origin is in allowed hosts or CORS origins
#         for host in allowed_hosts + allowed_cors_origins:
#             if origin.endswith(host):
#                 return True
#         return False

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    # permission_classes = [AllowedHostsPermission]

