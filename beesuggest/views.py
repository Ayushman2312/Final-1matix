from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import ProductDetailsForm
from .serializers import ProductDetailsSerializer, ProductCreateSerializer, ProductSearchSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
from .models import ProductDetails, BeesuggestAgreement
from .permissions import AllowOnlyCorsOrigin
import json
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)



def product_form_view(request):
    """
    Handle product form submission - requires user authentication
    """
    agreement = BeesuggestAgreement.objects.filter(is_active=True).first()

    if request.method == 'POST':
        try:
            # Create a new ProductDetails instance
            product_details = ProductDetails(user=request.session.get('user_id'))
            
            # Basic fields
            product_details.focus_keywords = request.POST.get('focus_keywords', '')
            product_details.alt_keyword_1 = request.POST.get('alt_keyword_1', '')
            product_details.alt_keyword_2 = request.POST.get('alt_keyword_2', '')
            product_details.product_title = request.POST.get('product_title', '')
            product_details.short_description = request.POST.get('short_description', '')
            
            # Handle file uploads
            for i in range(1, 6):
                image_field = f'product_image_{i}'
                alt_field = f'product_image_{i}_alt'
                if image_field in request.FILES:
                    setattr(product_details, image_field, request.FILES[image_field])
                setattr(product_details, alt_field, request.POST.get(alt_field, ''))
            
            product_details.video_url_1 = request.POST.get('video_url_1', '')
            product_details.video_url_2 = request.POST.get('video_url_2', '')
            product_details.video_url_3 = request.POST.get('video_url_3', '')
            
            if 'size_chart' in request.FILES:
                product_details.size_chart = request.FILES['size_chart']
            
            # Text fields
            product_details.product_description = request.POST.get('product_description', '')
            product_details.uses = request.POST.get('uses', '')
            product_details.best_suited_for = request.POST.get('best_suited_for', '')
            product_details.social_media_facebook = request.POST.get('social_media_facebook', '')
            product_details.social_media_twitter = request.POST.get('social_media_twitter', '')
            product_details.social_media_instagram = request.POST.get('social_media_instagram', '')
            product_details.website_url = request.POST.get('website_url', '')
            product_details.contact_number = request.POST.get('contact_number', '')
            product_details.email = request.POST.get('email', '')
            product_details.address = request.POST.get('address', '')
            product_details.organization = request.POST.get('organization', '')
            product_details.gst_details = request.POST.get('gst_details', '')
            product_details.map_location = request.POST.get('map_location', '')
            product_details.why_choose_us = request.POST.get('why_choose_us', '')
            product_details.comparison = request.POST.get('comparison', '')

            # Process variations
            variations = []
            variation_count = 1
            while f'variation_name_{variation_count}' in request.POST:
                name = request.POST.get(f'variation_name_{variation_count}')
                values_str = request.POST.get(f'variation_value_{variation_count}')
                if name and values_str:
                    # Split the string by comma and strip whitespace from each value
                    values = [v.strip() for v in values_str.split(',') if v.strip()]
                    if values:
                        variations.append({'name': name, 'values': values})
                variation_count += 1
            product_details.variations = variations

            # Process dynamic comparisons
            comparisons = []
            comparison_count = 1
            while f'comparison_us_{comparison_count}' in request.POST or f'comparison_others_{comparison_count}' in request.POST:
                us_text = request.POST.get(f'comparison_us_{comparison_count}', '').strip()
                others_text = request.POST.get(f'comparison_others_{comparison_count}', '').strip()
                if us_text or others_text:
                    comparisons.append({'us': us_text, 'others': others_text})
                comparison_count += 1
            product_details.comparisons = comparisons

            # Process FAQs
            faqs = []
            faq_count = 1
            while f'faq_question_{faq_count}' in request.POST:
                question = request.POST.get(f'faq_question_{faq_count}')
                answer = request.POST.get(f'faq_answer_{faq_count}')
                if question and answer:
                    faqs.append({'question': question, 'answer': answer})
                faq_count += 1
            product_details.faqs = faqs
            
            # Save the product
            product_details.save()

            # Send email with agreement
            if agreement and request.session.get('user_id').email:
                subject = f'Product Submission Agreement: {product_details.product_title or "Untitled Product"}'
                user = request.session.get('user_id')
                
                html_message = f"""
                <p>Hello {user.first_name or user.username},</p>
                <p>Thank you for submitting your product '{product_details.product_title or "Untitled Product"}'.</p>
                <p>As part of the submission, you have accepted the following agreement:</p>
                <hr>
                <h3>{agreement.title}</h3>
                <div>{agreement.content}</div>
                <hr>
                <p>Your product is now under review. We will notify you once it is published.</p>
                <p>Thank you,<br>The 1matrix Team</p>
                """
                
                plain_message = f"""
                Hello {user.first_name or user.username},

                Thank you for submitting your product '{product_details.product_title or 'Untitled Product'}'.
                As part of the submission, you have accepted the following agreement:

                ---
                {agreement.title}
                ---
                {agreement.content}

                Your product is now under review. We will notify you once it is published.

                Thank you,
                The 1matrix Team
                """

                try:
                    send_mail(
                        subject,
                        plain_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        html_message=html_message,
                        fail_silently=False
                    )
                    logger.info(f"Agreement email sent to {user.email} for product {product_details.id}")
                except Exception as email_error:
                    logger.error(f"Failed to send agreement email to {user.email} for product {product_details.id}: {str(email_error)}")

            
            messages.success(request, 'Product details submitted successfully! Your submission is under review.')
            logger.info(f"Product created successfully by user {request.session.get('user_id').username} (ID: {product_details.id})")
            
            return redirect('product_form_success')
            
        except Exception as e:
            logger.error(f"Error saving product details: {str(e)}")
            messages.error(request, 'There was an error submitting your product details. Please try again.')
            
    return render(request, 'beesuggest/product_form.html', {'agreement': agreement})

def product_form_success(request):
    """Success page after form submission"""
    return render(request, 'beesuggest/product_form_success.html')



def user_products_view(request):
    """Display user's submitted products"""
    user=request.session.get('user_id')
    products = ProductDetails.objects.filter(user=user).order_by('-submitted_at')
    paginator = Paginator(products, 10)  # Show 10 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'beesuggest/user_products.html', {'page_obj': page_obj})

# API Views
@api_view(['GET'])
@permission_classes([AllowOnlyCorsOrigin])
def published_products_api(request):
    """
    API endpoint to retrieve all published products with pagination and search.
    Restricted by CORS to allowed domains only.
    """
    try:
        # Get query parameters
        search = request.GET.get('search', '')
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 20)), 100)  # Max 100 items per page
        
        # Base queryset
        queryset = ProductDetails.objects.filter(is_published=True)
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(organization__icontains=search) |
                Q(focus_keywords__icontains=search) |
                Q(product_description__icontains=search) |
                Q(alt_keyword_1__icontains=search) |
                Q(alt_keyword_2__icontains=search)
            )
        
        # Pagination
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        # Serialize data
        serializer = ProductDetailsSerializer(page_obj, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data,
            'pagination': {
                'current_page': page_obj.number,
                'total_pages': paginator.num_pages,
                'per_page': per_page,
                'total_items': paginator.count,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in published_products_api: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error retrieving products',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowOnlyCorsOrigin])
def product_detail_api(request, product_id):
    """
    API endpoint to retrieve a single published product by ID.
    """
    try:
        product = get_object_or_404(ProductDetails, id=product_id, is_published=True)
        serializer = ProductDetailsSerializer(product, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in product_detail_api: {str(e)}")
        return Response({
            'success': False,
            'message': 'Product not found',
            'error': str(e)
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_products_api(request):
    """
    API endpoint to retrieve authenticated user's products.
    """
    try:
        products = ProductDetails.objects.filter(user=request.session.get('user_id')).order_by('-submitted_at')
        serializer = ProductDetailsSerializer(products, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': len(serializer.data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in user_products_api: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error retrieving user products',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_product_api(request):
    """
    API endpoint to create a new product via API.
    """
    try:
        serializer = ProductCreateSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save(user=request.session.get('user_id'))
            response_serializer = ProductDetailsSerializer(product, context={'request': request})
            
            return Response({
                'success': True,
                'message': 'Product created successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'message': 'Validation error',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error in create_product_api: {str(e)}")
        return Response({
            'success': False,
            'message': 'Error creating product',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProductDetailByUUID(generics.RetrieveAPIView):
    """
    API endpoint to retrieve full product details by UUID.
    """
    queryset = ProductDetails.objects.filter(is_published=True)
    serializer_class = ProductDetailsSerializer
    lookup_field = 'id'
    permission_classes = [AllowOnlyCorsOrigin]

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Product not found or invalid UUID.'
            }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowOnlyCorsOrigin])
def ProductSearchAPI(request):
    """
    API endpoint to search for products by name (focus_keywords).
    Returns a list of products with name and UUID.
    """
    query = request.query_params.get('q', None)
    if not query:
        return Response({
            'success': False,
            'message': 'A search query (`q` parameter) is required.'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        products = ProductDetails.objects.filter(
            focus_keywords__icontains=query,
            is_published=True
        )[:10]  # Limit to 10 results

        if not products.exists():
            return Response({
                'success': True,
                'data': [],
                'message': 'No products found matching the query.'
            }, status=status.HTTP_200_OK)

        serializer = ProductSearchSerializer(products, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in ProductSearchAPI: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred during search.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
