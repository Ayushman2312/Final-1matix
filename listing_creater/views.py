from django.shortcuts import render
import google.generativeai as genai
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
from .models import Listing
from masteradmin.models import AI_Prompt
import base64
from PIL import Image
import io
import logging
import re
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('listing_creator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure API key
logger.info("Configuring Gemini API")
try:
    genai.configure(api_key="AIzaSyDsXH-_ftI5xn4aWfkwpw__4ixUMs7a7fM")
    
    # Try to initialize both models for flexibility
    try:
        # Use Gemini Pro Vision model which supports image processing
        vision_model = genai.GenerativeModel("gemini-1.5-flash")
        logger.info("Gemini Vision API configured successfully for image analysis")
    except Exception as e:
        vision_model = None
        logger.error(f"Failed to configure Gemini Vision API: {str(e)}")
    
    try:
        # Also initialize text-only model as fallback
        text_model = genai.GenerativeModel("gemini-1.5-flash")
        logger.info("Gemini Text API configured successfully as fallback")
    except Exception as e:
        text_model = None
        logger.error(f"Failed to configure Gemini Text API: {str(e)}")
    
    # Default to vision model if available
    model = vision_model or text_model
    
    if not model:
        raise Exception("No Gemini models could be initialized")
        
except Exception as e:
    logger.error(f"Failed to configure any Gemini API: {str(e)}")
    raise

# Context cache file path - use a more reliable path
context_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "context_cache.json")
logger.info(f"Using context file at: {context_file}")

# Load cached context from file (if exists)
def load_conversation_history():
    try:
        if os.path.exists(context_file):
            logger.debug(f"Loading conversation history from {context_file}")
            with open(context_file, "r") as file:
                history = json.load(file)
            logger.info(f"Loaded {len(history)} conversation entries")
            return history
        else:
            logger.info("No existing conversation history found, starting fresh")
            return []
    except Exception as e:
        logger.error(f"Error loading conversation history: {str(e)}")
        return []

# Function to safely save conversation history
def save_conversation_history(history):
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(context_file), exist_ok=True)
        
        with open(context_file, "w") as file:
            json.dump(history, file)
        logger.debug(f"Successfully saved {len(history)} conversation entries")
        return True
    except Exception as e:
        logger.error(f"Error saving conversation history: {str(e)}")
        return False

# Initialize conversation history
conversation_history = load_conversation_history()

# Start chat session
try:
    chat = model.start_chat(history=conversation_history)
    logger.info("Chat session started successfully")
except Exception as e:
    logger.error(f"Failed to start chat session: {str(e)}")
    raise

def get_platforms():
    """Get all available platforms from AI_Prompt model"""
    try:
        platforms = AI_Prompt.objects.values_list('platform', flat=True)
        return list(platforms)
    except Exception as e:
        logger.error(f"Error fetching platforms: {str(e)}")
        return []

# Function to initialize or reset the chat session
def init_chat_session():
    global chat, conversation_history
    try:
        # Load fresh conversation history
        conversation_history = load_conversation_history()
        
        # Limit history size if needed
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]
            logger.debug("Trimmed conversation history to last 20 exchanges")
        
        # Start new chat session with history
        # Note: Vision models may handle history differently
        try:
            chat = model.start_chat(history=conversation_history)
            logger.info("Chat session initialized successfully with history")
        except Exception as e:
            logger.warning(f"Could not initialize chat with history: {str(e)}")
            # Fall back to no history for vision model
            chat = model.start_chat()
            logger.info("Chat session initialized without history (vision model)")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize chat session: {str(e)}")
        # Fallback to empty history if there's an issue
        conversation_history = []
        try:
            chat = model.start_chat()
            logger.info("Chat session initialized with empty history")
            return True
        except Exception as e2:
            logger.error(f"Failed to initialize chat session with empty history: {str(e2)}")
            return False

# Initialize chat session
chat = None
init_chat_session()

# Function to convert base64 images to format compatible with Gemini API
def process_images_for_gemini(image_list):
    try:
        processed_images = []
        for i, img_data in enumerate(image_list):
            if isinstance(img_data, str) and img_data.startswith('data:'):
                try:
                    # Extract image data without the prefix
                    img_format = img_data.split(';')[0].split('/')[1] if ';' in img_data and '/' in img_data.split(';')[0] else 'jpeg'
                    base64_data = img_data.split(',')[1] if ',' in img_data else img_data
                    
                    # Create image object for Gemini
                    image = {
                        "mime_type": f"image/{img_format}",
                        "data": base64_data
                    }
                    processed_images.append(image)
                    logger.info(f"Successfully processed image #{i+1} for Gemini API with format {img_format}")
                except Exception as e:
                    logger.error(f"Error processing image #{i+1}: {str(e)}")
                    # Try alternative approach for problematic images
                    try:
                        if ',' in img_data:
                            base64_data = img_data.split(',')[1]
                            image = {
                                "mime_type": "image/jpeg",  # Default to JPEG if format detection fails
                                "data": base64_data
                            }
                            processed_images.append(image)
                            logger.info(f"Successfully processed image #{i+1} using fallback method")
                    except Exception as fallback_error:
                        logger.error(f"Fallback processing also failed for image #{i+1}: {str(fallback_error)}")
            else:
                logger.warning(f"Image #{i+1} is not in proper base64 format: {type(img_data)}")
                if isinstance(img_data, str):
                    logger.debug(f"Image data prefix: {img_data[:30]}...")
        
        logger.info(f"Processed {len(processed_images)} images for Gemini API")
        return processed_images
    except Exception as e:
        logger.error(f"Error in process_images_for_gemini: {str(e)}")
        return []

@csrf_exempt
def ai_chat_view(request):
    logger.info(f"Received {request.method} request")
    
    # Access the global variables
    global conversation_history, chat, model
    
    # Make sure chat is initialized
    if chat is None:
        if not init_chat_session():
            return JsonResponse({
                "error": "Unable to initialize AI chat session",
                "listing_id": None,
                "log": "Chat initialization failed"
            }, status=500)
    
    if request.method == "GET":
        # For GET requests, return the template with platforms
        platforms = get_platforms()
        return render(request, "listing_creater/listingcreater.html", {"platforms": platforms})
    
    elif request.method == "POST":
        try:
            # Parse the request body as JSON
            data = json.loads(request.body)
            logger.debug(f"Received data: {data}")

            # Extract data from the request
            platform_type = data.get('platform_type', '')
            brand = data.get('brand', '')
            urls = data.get('urls', [])
            description = data.get('description', '')
            product_images = data.get('product_images', [])
            product_specs = data.get('product_specs', {})
            keyword_screenshots = data.get('keyword_screenshots', [])

            # Log image information
            logger.info(f"Received {len(keyword_screenshots)} keyword screenshots")
            for i, screenshot in enumerate(keyword_screenshots):
                if screenshot and isinstance(screenshot, str):
                    data_type = screenshot.split(';')[0] if ';' in screenshot else 'unknown'
                    data_length = len(screenshot)
                    logger.info(f"Keyword screenshot #{i+1}: Type={data_type}, Size={data_length} bytes")
                else:
                    logger.warning(f"Keyword screenshot #{i+1}: Invalid format")
            
            logger.info(f"Received {len(product_images)} product images")
            for i, image in enumerate(product_images):
                if image and isinstance(image, str):
                    data_type = image.split(';')[0] if ';' in image else 'unknown'
                    data_length = len(image)
                    logger.info(f"Product image #{i+1}: Type={data_type}, Size={data_length} bytes")
                else:
                    logger.warning(f"Product image #{i+1}: Invalid format")

            # Validate required fields
            if not brand:
                logger.warning("Missing required field: brand")
                return JsonResponse({"error": "Brand name is required"}, status=400)
            
            if not urls or not isinstance(urls, list) or len(urls) < 1:
                logger.warning(f"Invalid or missing URLs: {urls}")
                return JsonResponse({"error": "At least one competitor URL is required"}, status=400)
            
            # Log all URLs for debugging
            for i, url in enumerate(urls):
                logger.debug(f"URL {i+1}: {url}")

            # Validate product specs
            if not product_specs or not isinstance(product_specs, dict):
                logger.warning(f"Invalid product specifications format: {product_specs}")
                product_specs = {}
            
            # Check if size, material, and color are present in product_specs
            required_specs = ["size", "material", "color"]
            missing_specs = [spec for spec in required_specs if spec not in product_specs or not product_specs[spec]]
            
            if missing_specs:
                logger.warning(f"Missing required product specifications: {missing_specs}")
                return JsonResponse({"error": f"Missing required product specifications: {', '.join(missing_specs)}"}, status=400)
            
            # Validate product images - at least 1 required
            if not product_images or len(product_images) < 1:
                logger.warning("Not enough product images provided")
                return JsonResponse({"error": "At least 1 product image is required"}, status=400)
            
            logger.debug(f"Validation passed: {len(urls)} URLs and {len(product_images)} images")

            # Format product specs for better display in the prompt
            specs_text = ""
            for key, value in product_specs.items():
                if value:
                    specs_text += f"{key.capitalize()}: {value}\n"
            
            # Log the extracted data
            logger.debug(f"Platform: {platform_type}")
            logger.debug(f"Brand: {brand}")
            logger.debug(f"URLs count: {len(urls)}")
            logger.debug(f"URLs: {urls}")
            logger.debug(f"Description length: {len(description)}")
            logger.debug(f"Product images count: {len(product_images)}")
            logger.debug(f"Product specs: {product_specs}")
            logger.debug(f"Formatted specs: {specs_text}")
            logger.debug(f"Keyword screenshots count: {len(keyword_screenshots)}")

            # Get the stored prompt for the selected platform
            try:
                prompt_obj = AI_Prompt.objects.get(platform=platform_type)
                prompt = prompt_obj.prompt
                logger.debug(f"Using stored prompt for platform: {platform_type}")
            except AI_Prompt.DoesNotExist:
                logger.warning(f"No stored prompt found for platform: {platform_type}")
                # Fallback to default prompts
                if platform_type == "Amazon":
                    logger.debug("Using Amazon-specific prompt")
                    prompt = (
                        '{\n'
                        '  "system_prompt": "You are an expert Amazon product listing generator trained as per Brandise Box LLP\'s strategies. Follow these strict rules:\\n\\n'
                        '1. Input Variables:\\n'
                        '   - Brand: {brand}\\n'
                        '   - Competitor URLs: {urls} - Analyze these competitor listings to understand market positioning\\n' 
                        '   - Product Description Input: {description}\\n'
                        '   - Product Specifications: {product_specs}\\n\\n'
                        '2. Output Structure (FOLLOW THIS EXACTLY):\\n'
                        '   - Two Titles: (Format titles exactly as shown below)\\n'
                        '     a. AMAZON_TITLE_HERE (Amazon-Compliant Title - short, clear, policy-compliant)\\n'
                        '     b. EXPERT_TITLE_HERE (Expert Title - long, keyword-optimized, descriptive)\\n\\n'
                        '   - Bullet Points: (use * for each point)\\n'
                        '     * First point here\\n'
                        '     * Second point here\\n'
                        '     etc.\\n\\n'
                        '   - Product Description: 1000 characters max, optimized for the platform\\n\\n'
                        '   - Search Terms: under 200 bytes, optimized with keywords\\n\\n'
                        '3. Guidelines:\\n'
                        '   - For titles: Use the brand name, color, material, size, and key features\\n'
                        '   - For bullet points: Create 5-7 points highlighting benefits, features and use cases\\n'
                        '   - For description: Focus on benefits, uses, and what sets it apart\\n'
                        '   - For search terms: Include relevant keywords, synonyms, no punctuation\\n\\n'
                        'IMPORTANT: Format your response exactly as shown in point 2 above. Start with titles labeled as a. and b., then bullet points with *, then description, then search terms.'
                        '}'
                    )
                else:
                    logger.debug(f"Using generic prompt for platform: {platform_type}")
                    prompt = "Generate a professional product listing optimized for the specified platform."

            # Send message and get AI response
            try:
                logger.info("Sending message to AI model")
                
                # Process and format the prompt with user data
                # Check if the prompt contains placeholders for variables
                formatted_prompt = prompt
                print(formatted_prompt)
                try:
                    # Try to format the prompt with the variables
                    url_str = ', '.join(urls)
                    specs_str = json.dumps(product_specs)
                    formatted_prompt = prompt.format(
                        brand=brand,
                        urls=url_str,
                        description=description,
                        product_specs=specs_str
                    )
                    logger.debug("Successfully formatted prompt with user data")
                except (KeyError, ValueError) as e:
                    # If formatting fails, we'll append the data instead
                    logger.warning(f"Could not format prompt with variables: {str(e)}")
                
                # Prepare additional context to ensure all necessary information is included
                additional_context = f"""
                ANALYZE THESE COMPETITOR URLS CAREFULLY:
                {', '.join(urls)}
                
                BRAND NAME: {brand}
                
                PRODUCT SPECIFICATIONS:
                {specs_text}
                
                DESCRIPTION FROM USER:
                {description}
                
                IMAGE ANALYSIS INSTRUCTIONS:
                - {len(keyword_screenshots)} keyword screenshots have been provided. These show search terms and trending keywords.
                - {len(product_images)} product images have been provided. These show the actual product appearance.
                - IMPORTANT: Analyze these images to understand product features, appearance, and relevant keywords.
                - Use the keyword screenshots to identify high-performing search terms to include in your listing.
                
                USE ALL THE ABOVE INFORMATION TO CREATE A COMPLETE PRODUCT LISTING.
                
                FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:
                a. [Amazon Title Here]
                b. [Expert Title Here]
                
                Bullet Points:
                * [First point]
                * [Second point]
                * [Third point]
                * [Fourth point]
                * [Fifth point]
                
                Description:
                [Description here]
                
                Search Terms:
                [search terms here]
                """
                
                # Combine prompt and additional context if needed
                if "{brand}" not in prompt and "{urls}" not in prompt and "{description}" not in prompt and "{product_specs}" not in prompt:
                    # If prompt doesn't have placeholders, append the additional context
                    detailed_message = formatted_prompt + "\n\n" + additional_context
                    logger.debug("Appending additional context to prompt")
                else:
                    # If prompt already has placeholders and was formatted, use it as is
                    detailed_message = formatted_prompt
                    logger.debug("Using formatted prompt with placeholders")
                
                # Log message length for debugging
                logger.debug(f"Message length: {len(detailed_message)} characters")
                
                # Try to send message with retries
                max_retries = 2
                retry_count = 0
                success = False
                
                # Process images for Gemini API
                try:
                    # Process more keyword screenshots (up to 3) if available
                    max_keyword_images = min(3, len(keyword_screenshots))
                    keyword_images = process_images_for_gemini(keyword_screenshots[:max_keyword_images] if keyword_screenshots else [])
                    logger.info(f"Processed {len(keyword_images)}/{len(keyword_screenshots)} keyword screenshots")
                    
                    # Process product images (up to 2) as before
                    product_images_processed = process_images_for_gemini(product_images[:2] if product_images else [])
                    logger.info(f"Processed {len(product_images_processed)}/{len(product_images)} product images")
                    
                    # Log detailed information about each processed image
                    for i, img in enumerate(keyword_images):
                        logger.debug(f"Keyword image #{i+1} - mime_type: {img.get('mime_type')}, data length: {len(img.get('data', ''))}")
                    
                    for i, img in enumerate(product_images_processed):
                        logger.debug(f"Product image #{i+1} - mime_type: {img.get('mime_type')}, data length: {len(img.get('data', ''))}")
                    
                    # Combine all images
                    all_images = keyword_images + product_images_processed
                    logger.info(f"Total images to send to Gemini API: {len(all_images)}")
                except Exception as img_process_error:
                    logger.error(f"Error during image processing: {str(img_process_error)}")
                    # Fallback to empty lists if image processing fails
                    keyword_images = []
                    product_images_processed = []
                    all_images = []
                    logger.warning("Using empty image lists due to processing error")
                
                # Flag to track if we need to fall back to text-only model
                use_vision_model = isinstance(model, type(vision_model)) and len(all_images) > 0
                use_text_fallback = False
                
                while retry_count <= max_retries and not success:
                    try:
                        if retry_count > 0:
                            logger.info(f"Retry attempt {retry_count}/{max_retries}")
                            # If first attempt with vision model failed, try text model
                            if retry_count == 1 and use_vision_model and text_model is not None:
                                logger.warning("Vision model failed, falling back to text-only model")
                                model = text_model
                                use_vision_model = False
                                use_text_fallback = True
                                # Reinitialize chat with text model
                                init_chat_session()
                            else:
                                # Regular retry with current model
                                init_chat_session()
                        
                        # Create content parts with text and images
                        if use_vision_model:
                            content_parts = [detailed_message]
                            
                            # Add images if available
                            for img in all_images:
                                try:
                                    content_parts.append(img)
                                    logger.debug(f"Added image to content: {img.get('mime_type', 'unknown')}")
                                except Exception as e:
                                    logger.error(f"Error adding image to content: {str(e)}")
                            
                            # Log content structure for debugging
                            logger.info(f"Sending {len(content_parts)} content parts to Gemini Vision API")
                            
                            # Send message with text and images
                            response = chat.send_message(content_parts)
                        else:
                            # If using text-only model, just send the text
                            image_instruction = f"\nNote: {len(all_images)} images were provided but cannot be processed. They include {len(keyword_images)} keyword screenshots and {len(product_images_processed)} product images."
                            text_message = detailed_message + image_instruction if use_text_fallback else detailed_message
                            logger.info("Sending text-only message to Gemini API")
                            response = chat.send_message(text_message)
                            
                        logger.debug("Received response from AI model")
                        success = True
                    except Exception as e:
                        retry_count += 1
                        logger.error(f"Error sending message (attempt {retry_count}/{max_retries}): {str(e)}")
                        if retry_count > max_retries:
                            raise
                        # Wait briefly before retrying
                        time.sleep(1)
                
                # Update conversation history only if successful
                if success:
                    logger.debug("Updating conversation history")
                    try:
                        # For vision models, we only store the text part in history
                        conversation_history.append({"role": "user", "parts": [detailed_message]})
                        conversation_history.append({"role": "model", "parts": [response.text]})
                        logger.debug("Added conversation entries to history")
                    except Exception as e:
                        logger.error(f"Error updating conversation history: {str(e)}")

                    # Keep conversation history manageable (last 20 exchanges)
                    if len(conversation_history) > 20:
                        conversation_history = conversation_history[-20:]
                        logger.debug("Trimmed conversation history to last 10 exchanges")

                    # Save updated context to file
                    logger.debug("Saving conversation history to file")
                    save_conversation_history(conversation_history)
                else:
                    logger.error("Failed to get response from AI model after retries")
                    raise Exception("Failed to get response from AI model after retries")

                # Initialize listing_id variable
                listing_id = None
                
                # Save to Listing model
                logger.info("Saving listing to database")
                try:
                    listing = Listing.objects.create(
                        platform_type=platform_type,
                        brand=brand,
                        urls=json.dumps(urls),  # Convert list to JSON string
                        product_specs=json.dumps(product_specs),  # Convert dict to JSON string
                        keyword_screenshots=json.dumps(keyword_screenshots[:1] if keyword_screenshots else []),  # Save only first screenshot
                        product_images=json.dumps(product_images[:2] if product_images else [])  # Save only first two images
                    )
                    logger.debug(f"Created listing with ID: {listing.id}")
                    listing_id = str(listing.id)
                except Exception as e:
                    logger.error(f"Failed to save listing to database: {str(e)}")
                    # Don't return error response, just continue with None listing_id
                    listing_id = None

                # Format the response as structured JSON
                logger.debug("Formatting AI response")
                ai_response = response.text
                logger.debug(f"Raw AI response: {ai_response}")
                print(ai_response)

                # Initialize the formatted response structure
                formatted_response = {
                    "amazon_title": "",
                    "expert_title": "",
                    "bullet_points": [],
                    "description": "",
                    "search_terms": ""
                }

                # Process the response - improved parser
                lines = ai_response.strip().split('\n')
                current_section = None

                # Check for title format like "a. Title" and "b. Title"
                title_patterns = [
                    (r'(?:^|\n)a\.[\s]*(.+?)(?:\n|$)', "amazon_title"),
                    (r'(?:^|\n)b\.[\s]*(.+?)(?:\n|$)', "expert_title"),
                    (r'(?i)amazon[\s\-]*compliant[\s\-]*title[\s]*:[\s]*(.+?)(?:\n|$)', "amazon_title"),
                    (r'(?i)expert[\s\-]*title[\s]*:[\s]*(.+?)(?:\n|$)', "expert_title"),
                    (r'(?i)amazon[\s\-]*title[\s]*:[\s]*(.+?)(?:\n|$)', "amazon_title"),
                ]

                # Try to extract titles using patterns
                for pattern, field in title_patterns:
                    match = re.search(pattern, ai_response)
                    if match and match.group(1).strip():
                        formatted_response[field] = match.group(1).strip()
                        logger.debug(f"Extracted {field} using pattern: {match.group(1).strip()}")

                # Continue with standard line-by-line processing
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Determine which section we're in
                    lower_line = line.lower()
                    
                    # Skip lines that have already been processed as titles
                    if (formatted_response["amazon_title"] and line.find(formatted_response["amazon_title"]) != -1) or \
                       (formatted_response["expert_title"] and line.find(formatted_response["expert_title"]) != -1):
                        continue
                    
                    if "bullet point" in lower_line or "bullet points" in lower_line:
                        current_section = "bullet_points"
                        continue
                    elif "description" in lower_line:
                        current_section = "description"
                        continue
                    elif "search term" in lower_line or "search terms" in lower_line:
                        current_section = "search_terms"
                        continue
                    elif "amazon" in lower_line and ("title" in lower_line or "compliant" in lower_line):
                        current_section = "amazon_title"
                        # Extract title if it's on the same line
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip():
                            formatted_response["amazon_title"] = parts[1].strip()
                            continue
                    elif "expert" in lower_line and "title" in lower_line:
                        current_section = "expert_title"
                        # Extract title if it's on the same line
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip():
                            formatted_response["expert_title"] = parts[1].strip()
                            continue
                            
                    # Process content based on current section
                    if current_section == "amazon_title" and not formatted_response["amazon_title"]:
                        formatted_response["amazon_title"] = line
                    elif current_section == "expert_title" and not formatted_response["expert_title"]:
                        formatted_response["expert_title"] = line
                    elif current_section == "bullet_points" and (line.startswith("*") or line.startswith("•") or line.startswith("-")):
                        formatted_response["bullet_points"].append(line.lstrip("*•- ").strip())
                    elif current_section == "description" and not line.lower().startswith("description"):
                        formatted_response["description"] += " " + line
                    elif current_section == "search_terms" and not line.lower().startswith("search term"):
                        formatted_response["search_terms"] += " " + line
                
                # Log the structured response after parsing
                logger.debug(f"Structured response after parsing: {formatted_response}")

                # Clean up search terms
                if formatted_response["search_terms"]:
                    # Remove duplicate words and clean up spacing
                    search_terms_list = formatted_response["search_terms"].split()
                    search_terms_unique = []
                    [search_terms_unique.append(x) for x in search_terms_list if x not in search_terms_unique]
                    formatted_response["search_terms"] = " ".join(search_terms_unique)
                
                # Ensure titles are non-empty
                if not formatted_response["amazon_title"]:
                    formatted_response["amazon_title"] = f"{brand} {product_specs.get('color', '')} {product_specs.get('material', '')} {product_specs.get('size', '')}"
                    formatted_response["amazon_title"] = formatted_response["amazon_title"].strip()
                    logger.warning("Generated fallback Amazon title as original was empty")
                
                if not formatted_response["expert_title"]:
                    formatted_response["expert_title"] = formatted_response["amazon_title"]
                    logger.warning("Used Amazon title as fallback for empty Expert title")

                # Ensure bullet points are properly processed
                if not formatted_response["bullet_points"]:
                    # Try to extract bullet points from the description if none were found
                    desc_lines = formatted_response["description"].split("\n")
                    for line in desc_lines:
                        line = line.strip()
                        if line.startswith("•") or line.startswith("*") or line.startswith("-"):
                            formatted_response["bullet_points"].append(line.lstrip("•*- ").strip())
                
                # Ensure at least 5 bullet points for better product display
                while len(formatted_response["bullet_points"]) < 5:
                    formatted_response["bullet_points"].append("Product by " + brand)
                
                # Truncate to max 7 bullet points
                formatted_response["bullet_points"] = formatted_response["bullet_points"][:7]
                
                logger.debug(f"Formatted search terms: {formatted_response['search_terms']}")
                logger.debug(f"Formatted bullet points count: {len(formatted_response['bullet_points'])}")
                logger.debug(f"Formatted response: {formatted_response}")

                # Log the raw response for debugging
                logger.debug(f"Raw AI response: {response.text}")
                
                # Check if response mentions image analysis
                if "image" in response.text.lower() or "screenshot" in response.text.lower() or "photo" in response.text.lower():
                    logger.info("AI response contains references to images/screenshots/photos")
                else:
                    logger.warning("AI response does not mention images/screenshots/photos")
                
                # Simple text analysis to see if response seems to incorporate image data
                if len(keyword_screenshots) > 0 and not any(kw in response.text.lower() for kw in ["keyword", "screenshot", "search term"]):
                    logger.warning("AI response may not have analyzed keyword screenshots properly")
                
                if len(product_images) > 0 and not any(kw in response.text.lower() for kw in ["image", "photo", "picture", "color", "design", "appearance"]):
                    logger.warning("AI response may not have analyzed product images properly")

                # Create app name for AI listing creator
                # Initialize context at the start
                return JsonResponse({
                    "response": formatted_response,
                    "listing_id": listing_id,
                    "log": "Successfully generated listing"
                })
                
            except Exception as e:
                logger.error(f"AI service error: {str(e)}", exc_info=True)
                return JsonResponse({
                    "error": f"AI service error: {str(e)}",
                    "listing_id": None,
                    "log": f"AI service error: {str(e)}"
                }, status=500)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}", exc_info=True)
            return JsonResponse({
                "error": "Invalid JSON data in request",
                "listing_id": None,
                "log": f"JSON decode error: {str(e)}"
            }, status=400)
        except Exception as e:
            logger.error(f"Server error: {str(e)}", exc_info=True)
            return JsonResponse({
                "error": f"Server error: {str(e)}",
                "listing_id": None,
                "log": f"Server error: {str(e)}"
            }, status=500)

    return render(request, "listing_creater/listingcreater.html", {"platforms": get_platforms()})
