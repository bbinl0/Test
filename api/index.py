from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import types
from PIL import Image, ImageDraw
import io
import base64
import json
import numpy as np
import os
import requests
import logging
import uuid
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.INFO)

# Define available styles for image generation
AVAILABLE_STYLES = {
    "photorealistic": "photorealistic",
    "cartoon": "cartoon style",
    "abstract": "abstract art",
    "impressionistic": "impressionist painting",
    "cyberpunk": "cyberpunk art style",
    "anime": "anime style",
    "oil_painting": "oil painting",
    "watercolor": "watercolor painting",
    "sketch": "pencil sketch",
    "digital_art": "digital art"
}

# Define available aspect ratios with dimensions
AVAILABLE_RATIOS = {
    "1:1": {"desc": "square format", "width": 1024, "height": 1024},
    "4:3": {"desc": "standard landscape format", "width": 1024, "height": 768},
    "3:4": {"desc": "standard portrait format", "width": 768, "height": 1024},
    "16:9": {"desc": "landscape widescreen format", "width": 1024, "height": 576},
    "9:16": {"desc": "portrait vertical format", "width": 576, "height": 1024}
}

def resize_image_to_aspect_ratio(image_path, aspect_ratio):
    """Resize image to the specified aspect ratio"""
    try:
        ratio_info = AVAILABLE_RATIOS.get(aspect_ratio, AVAILABLE_RATIOS["1:1"])
        target_width = ratio_info["width"]
        target_height = ratio_info["height"]
        
        # Open and resize the image
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img_aspect = img.width / img.height
            target_aspect = target_width / target_height
            
            if img_aspect > target_aspect:
                new_width = int(img.height * target_aspect)
                left = (img.width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img.height))
            elif img_aspect < target_aspect:
                new_height = int(img.width / target_aspect)
                top = (img.height - new_height) // 2
                img = img.crop((0, top, img.width, top + new_height))
            
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            img.save(image_path, 'PNG', quality=95)
            
        logging.info(f"Image resized to {target_width}x{target_height} ({aspect_ratio})")
        return True
        
    except Exception as e:
        logging.error(f"Error resizing image: {str(e)}")
        return False

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_change_in_production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Ensure static directory exists
os.makedirs('static/generated_images', exist_ok=True)

# Initialize Gemini client - only if API key exists
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = None
        logging.warning("GEMINI_API_KEY not found in environment variables")
except Exception as e:
    client = None
    logging.error(f"Failed to initialize Gemini client: {str(e)}")

def analyze_image_with_genai(image):
    """Analyze image using Google Generative AI"""
    if not client:
        return "Error: Gemini API client not initialized. Please check your GEMINI_API_KEY."
    
    try:
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=img_byte_arr,
                    mime_type="image/png",
                ),
                "What is this image? Provide a detailed description."
            ]
        )
        
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.text:
                    return part.text
        
        return "Unable to analyze the image."
        
    except Exception as e:
        logging.error(f"Error in analyze_image_with_genai: {str(e)}")
        return f"Error analyzing image: {str(e)}"

def extract_segmentation_masks(image):
    """Extract segmentation masks from image"""
    if not client:
        return {"error": "Gemini API client not initialized"}
    
    try:
        # Placeholder for mask extraction - this would require specific Gemini features
        return []
        
    except Exception as e:
        return {"error": f"Failed to extract segmentation masks: {str(e)}"}

def generate_image_from_text(prompt, style="photorealistic", aspect_ratio="1:1"):
    """Generate image from text prompt using Gemini API"""
    if not client:
        return {
            'status': 'error',
            'error': 'Gemini API client not initialized. Please check your GEMINI_API_KEY environment variable.'
        }
    
    try:
        style_desc = AVAILABLE_STYLES.get(style, AVAILABLE_STYLES["photorealistic"])
        ratio_info = AVAILABLE_RATIOS.get(aspect_ratio, AVAILABLE_RATIOS["1:1"])
        ratio_desc = ratio_info["desc"]
        
        quality_modifiers = "high resolution, sharp focus, highly detailed, masterpiece, best quality, ultra-detailed, 8k, HDR"
        enhanced_prompt = f"Create a {style_desc} image: {prompt}. {ratio_desc}. {quality_modifiers}. Professional lighting and composition."
        
        logging.info(f"Generating image with prompt: {prompt}")
        logging.info(f"Enhanced prompt: {enhanced_prompt}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        image_filename = f"generated_image_{timestamp}_{unique_id}.png"
        image_path = os.path.join("static", "generated_images", image_filename)
        
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=[enhanced_prompt],
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        if not response.candidates:
            logging.error("No candidates returned from Gemini API")
            return {
                'status': 'error',
                'error': 'No image generated by the API. Please try a different prompt.'
            }
        
        content = response.candidates[0].content
        if not content or not content.parts:
            logging.error("No content or parts in API response")
            return {
                'status': 'error',
                'error': 'Invalid response from image generation API'
            }
        
        image_saved = False
        response_text = None
        
        for part in content.parts:
            if part.text:
                response_text = part.text
                logging.info(f"API response text: {part.text}")
            elif part.inline_data and part.inline_data.data:
                try:
                    with open(image_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    image_saved = True
                    logging.info(f"Image saved successfully at: {image_path}")
                    
                    if resize_image_to_aspect_ratio(image_path, aspect_ratio):
                        logging.info(f"Image resized to {aspect_ratio} aspect ratio")
                except Exception as file_error:
                    logging.error(f"Error saving image file: {file_error}")
                    return {
                        'status': 'error',
                        'error': f'Failed to save generated image: {str(file_error)}'
                    }
        
        if not image_saved:
            logging.error("No image data found in API response")
            return {
                'status': 'error',
                'error': 'No image data received from the API. The model may not support this prompt.'
            }
        
        return {
            'status': 'success',
            'image_path': image_path,
            'response_text': response_text,
            'filename': image_filename
        }
        
    except Exception as e:
        logging.error(f"Error in generate_image_from_text: {str(e)}")
        
        if "API_KEY" in str(e).upper():
            error_msg = "Invalid or missing Gemini API key. Please check your GEMINI_API_KEY environment variable."
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_msg = "API quota exceeded or rate limit reached. Please try again later."
        elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
            error_msg = "Permission denied. Please check your API key permissions."
        else:
            error_msg = f"Failed to generate image: {str(e)}"
        
        return {
            'status': 'error',
            'error': error_msg
        }

def edit_image_with_prompt(image_data, edit_prompt, style="photorealistic", aspect_ratio="1:1", edit_strength=0.7):
    """Edit an uploaded image using text prompt with Gemini API"""
    if not client:
        return {
            'status': 'error',
            'error': 'Gemini API client not initialized. Please check your GEMINI_API_KEY environment variable.'
        }
    
    try:
        style_desc = AVAILABLE_STYLES.get(style, AVAILABLE_STYLES["photorealistic"])
        ratio_info = AVAILABLE_RATIOS.get(aspect_ratio, AVAILABLE_RATIOS["1:1"])
        ratio_desc = ratio_info["desc"]
        
        quality_modifiers = "high resolution, sharp focus, highly detailed, masterpiece quality"
        enhanced_prompt = f"Modify this image by: {edit_prompt}. Style: {style_desc}. Format: {ratio_desc}. Maintain {quality_modifiers} and preserve the original composition while making the requested changes."
        
        logging.info(f"Starting image editing with prompt: {edit_prompt}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        image_filename = f"edited_image_{timestamp}_{unique_id}.png"
        image_path = os.path.join("static", "generated_images", image_filename)
        
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=[
                types.Part.from_bytes(
                    data=image_data,
                    mime_type="image/png",
                ),
                enhanced_prompt
            ],
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        if not response.candidates:
            logging.error("No candidates returned from Gemini API for image editing")
            return {
                'status': 'error',
                'error': 'No edited image generated by the API. Please try a different prompt or image.'
            }
        
        content = response.candidates[0].content
        if not content or not content.parts:
            logging.error("No content or parts in API response for image editing")
            return {
                'status': 'error',
                'error': 'Invalid response from image editing API'
            }
        
        image_saved = False
        response_text = None
        
        for part in content.parts:
            if part.text:
                response_text = part.text
                logging.info(f"API response text: {part.text}")
            elif part.inline_data and part.inline_data.data:
                try:
                    with open(image_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    image_saved = True
                    logging.info(f"Edited image saved successfully at: {image_path}")
                    
                    if resize_image_to_aspect_ratio(image_path, aspect_ratio):
                        logging.info(f"Edited image resized to {aspect_ratio} aspect ratio")
                except Exception as file_error:
                    logging.error(f"Error saving edited image file: {file_error}")
                    return {
                        'status': 'error',
                        'error': f'Failed to save edited image: {str(file_error)}'
                    }
        
        if not image_saved:
            logging.error("No image data found in API response for editing")
            return {
                'status': 'error',
                'error': 'No edited image data received from the API. The model may not support this edit.'
            }
        
        return {
            'status': 'success',
            'image_path': image_path,
            'response_text': response_text,
            'filename': image_filename
        }
        
    except Exception as e:
        logging.error(f"Error in edit_image_with_prompt: {str(e)}")
        
        if "API_KEY" in str(e).upper():
            error_msg = "Invalid or missing Gemini API key. Please check your GEMINI_API_KEY environment variable."
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_msg = "API quota exceeded or rate limit reached. Please try again later."
        elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
            error_msg = "Permission denied. Please check your API key permissions."
        else:
            error_msg = f"Failed to edit image: {str(e)}"
        
        return {
            'status': 'error',
            'error': error_msg
        }

def compose_images_with_prompt(images_data, composition_prompt, style="photorealistic", aspect_ratio="1:1"):
    """
    Compose multiple images into one using text prompt with Gemini API
    """
    if not client:
        return {
            'status': 'error',
            'error': 'Gemini API client not initialized. Please check your GEMINI_API_KEY environment variable.'
        }
    
    try:
        style_desc = AVAILABLE_STYLES.get(style, AVAILABLE_STYLES["photorealistic"])
        ratio_info = AVAILABLE_RATIOS.get(aspect_ratio, AVAILABLE_RATIOS["1:1"])
        ratio_desc = ratio_info["desc"]
        
        quality_modifiers = "high resolution, sharp focus, highly detailed, masterpiece quality"
        enhanced_prompt = f"Compose and combine these {len(images_data)} images to create: {composition_prompt}. Style: {style_desc}. Format: {ratio_desc}. Create a cohesive composition with {quality_modifiers} that seamlessly blends the input images according to the description."
        
        logging.info(f"Starting image composition with prompt: {composition_prompt}")
        logging.info(f"Number of input images: {len(images_data)}")
        logging.info(f"Style: {style} ({style_desc})")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        image_filename = f"composed_image_{timestamp}_{unique_id}.png"
        image_path = os.path.join("static", "generated_images", image_filename)
        
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        contents = []
        
        for i, image_data in enumerate(images_data):
            contents.append(
                types.Part.from_bytes(
                    data=image_data,
                    mime_type="image/png",
                )
            )
        
        contents.append(enhanced_prompt)
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        if not response.candidates:
            logging.error("No candidates returned from Gemini API for image composition")
            return {
                'status': 'error',
                'error': 'No composed image generated by the API. Please try a different prompt or images.'
            }
        
        content = response.candidates[0].content
        if not content or not content.parts:
            logging.error("No content or parts in API response for image composition")
            return {
                'status': 'error',
                'error': 'Invalid response from image composition API'
            }
        
        image_saved = False
        response_text = None
        
        for part in content.parts:
            if part.text:
                response_text = part.text
                logging.info(f"API response text: {part.text}")
            elif part.inline_data and part.inline_data.data:
                try:
                    with open(image_path, 'wb') as f:
                        f.write(part.inline_data.data)
                    image_saved = True
                    logging.info(f"Composed image saved successfully at: {image_path}")
                    
                    if resize_image_to_aspect_ratio(image_path, aspect_ratio):
                        logging.info(f"Composed image resized to {aspect_ratio} aspect ratio")
                        
                except Exception as file_error:
                    logging.error(f"Error saving composed image file: {file_error}")
                    return {
                        'status': 'error',
                        'error': f'Failed to save composed image: {str(file_error)}'
                    }
        
        if not image_saved:
            logging.error("No image data found in API response for composition")
            return {
                'status': 'error',
                'error': 'No composed image data received from the API. The model may not support this composition.'
            }
        
        return {
            'status': 'success',
            'image_path': image_path,
            'filename': image_filename,
            'response_text': response_text
        }
        
    except Exception as e:
        logging.error(f"Error in compose_images_with_prompt: {str(e)}")
        
        if "API_KEY" in str(e).upper():
            error_msg = "Invalid or missing Gemini API key. Please check your GEMINI_API_KEY environment variable."
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_msg = "API quota exceeded or rate limit reached. Please try again later."
        elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
            error_msg = "Permission denied. Please check your API key permissions."
        else:
            error_msg = f"Failed to compose images: {str(e)}"
        
        return {
            'status': 'error',
            'error': error_msg
        }

# Routes
@app.route('/', methods=['GET'])
def home():
    """Unified interface for all AI image operations"""
    return render_template('index.html')

@app.route('/analyze_base64', methods=['POST'])
def analyze_base64_image():
    """Endpoint for analyzing Base64 encoded images"""
    try:
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400
        
        base64_image = data['image']
        if base64_image.startswith('data:image'):
            base64_image = base64_image.split(',')[1]
        
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))
        
        analysis = analyze_image_with_genai(image)
        
        segmentation_results = []
        if data.get('extract_masks', False):
            segmentation_results = extract_segmentation_masks(image)
        
        return jsonify({
            "status": "success",
            "analysis": analysis,
            "segmentation_masks": segmentation_results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_url', methods=['POST'])
def analyze_url_image():
    """Endpoint for analyzing images from URLs"""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({"error": "No image URL provided"}), 400
        
        image_url = data['url']
        response = requests.get(image_url)
        response.raise_for_status()
        
        image = Image.open(io.BytesIO(response.content))
        analysis = analyze_image_with_genai(image)
        
        segmentation_results = []
        if data.get('extract_masks', False):
            segmentation_results = extract_segmentation_masks(image)
        
        return jsonify({
            "status": "success",
            "analysis": analysis,
            "segmentation_masks": segmentation_results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate_text_to_image', methods=['POST'])
def generate_text_to_image():
    """Generate image from text prompt"""
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({"error": "No prompt provided"}), 400
        
        prompt = data['prompt']
        style = data.get('style', 'photorealistic')
        aspect_ratio = data.get('aspect_ratio', '1:1')
        
        logging.info(f"Generating image for prompt: {prompt}")
        
        result = generate_image_from_text(prompt, style, aspect_ratio)
        
        if result['status'] == 'success':
            with open(result['image_path'], 'rb') as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            return jsonify({
                "status": "success",
                "prompt": prompt,
                "generated_text": result.get('response_text', ''),
                "generated_image": image_base64,
                "saved_files": [result['filename']],
                "total_images": 1
            })
        else:
            return jsonify({
                "status": "error",
                "error": result['error']
            }), 500
            
    except Exception as e:
        logging.error(f"Error in generate_text_to_image endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/edit_image', methods=['POST'])
def edit_image():
    """Edit image based on text prompt"""
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data or 'image' not in data:
            return jsonify({"error": "Prompt and image are required"}), 400
        
        prompt = data['prompt']
        base64_image = data['image']
        style = data.get('style', 'photorealistic')
        aspect_ratio = data.get('aspect_ratio', '1:1')
        edit_strength = data.get('edit_strength', 0.7)
        
        image_data = base64.b64decode(base64_image)
        
        logging.info(f"Editing image with prompt: {prompt}")
        
        result = edit_image_with_prompt(image_data, prompt, style, aspect_ratio, edit_strength)
        
        if result['status'] == 'success':
            with open(result['image_path'], 'rb') as f:
                edited_image_data = f.read()
            image_base64 = base64.b64encode(edited_image_data).decode('utf-8')
            
            return jsonify({
                "status": "success",
                "prompt": prompt,
                "generated_text": result.get('response_text', ''),
                "generated_image": image_base64,
                "saved_files": [result['filename']],
                "total_images": 1
            })
        else:
            return jsonify({
                "status": "error",
                "error": result['error']
            }), 500
            
    except Exception as e:
        logging.error(f"Error in edit_image endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/compose_images', methods=['POST'])
def compose_images():
    """Compose multiple images into one based on text prompt"""
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data or 'images' not in data:
            return jsonify({"error": "Prompt and images are required"}), 400
        
        prompt = data['prompt']
        base64_images = data['images']
        style = data.get('style', 'photorealistic')
        aspect_ratio = data.get('aspect_ratio', '1:1')
        
        if len(base64_images) < 2:
            return jsonify({"error": "At least 2 images are required for composition"}), 400
        
        images_data = []
        for i, base64_image in enumerate(base64_images):
            try:
                if base64_image.startswith('data:image'):
                    base64_image = base64_image.split(',')[1]
                
                image_data = base64.b64decode(base64_image)
                images_data.append(image_data)
            except Exception as decode_error:
                return jsonify({
                    "error": f"Failed to decode image {i+1}: {str(decode_error)}"
                }), 400
        
        logging.info(f"Composing {len(images_data)} images with prompt: {prompt}")
        
        result = compose_images_with_prompt(images_data, prompt, style, aspect_ratio)
        
        if result['status'] == 'success':
            with open(result['image_path'], 'rb') as f:
                composed_image_data = f.read()
            image_base64 = base64.b64encode(composed_image_data).decode('utf-8')
            
            return jsonify({
                "status": "success",
                "prompt": prompt,
                "input_images_count": len(base64_images),
                "generated_text": result.get('response_text', ''),
                "generated_image": image_base64,
                "saved_files": [result['filename']],
                "total_images": 1
            })
        else:
            return jsonify({
                "status": "error",
                "error": result['error']
            }), 500
            
    except Exception as e:
        logging.error(f"Error in compose_images endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    """Answer text questions using Gemini AI with model selection"""
    try:
        if not client:
            return jsonify({
                "error": "Gemini API client not initialized. Please check your GEMINI_API_KEY."
            }), 503

        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                "error": "Please provide a 'question' in the request body."
            }), 400
        
        user_question = data['question'].strip()
        selected_model = data.get('model', 'gemini-1.5-flash')
        
        if not user_question:
            return jsonify({
                "error": "Question cannot be empty."
            }), 400
        
        available_models = [
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-1.5-flash-8b'
        ]
        
        if selected_model not in available_models:
            selected_model = 'gemini-1.5-flash'
        
        logging.info(f"Processing text question: {user_question}")
        logging.info(f"Using model: {selected_model}")
        
        response = client.models.generate_content(
            model=selected_model,
            contents=user_question
        )
        
        if not response or not response.text:
            return jsonify({
                "error": "No response generated. Please try rephrasing your question."
            }), 500
        
        reply_text = response.text
        logging.info(f"Generated reply: {reply_text[:100]}...")
        
        return jsonify({
            "status": "success",
            "question": user_question,
            "answer": reply_text,
            "model_used": selected_model
        })
        
    except Exception as e:
        logging.error(f"Error in ask_question endpoint: {str(e)}")
        
        if "API_KEY" in str(e).upper():
            error_msg = "Invalid or missing Gemini API key."
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_msg = "API quota exceeded. Please try again later."
        elif "permission" in str(e).lower():
            error_msg = "Permission denied. Please check your API key permissions."
        elif "not found" in str(e).lower() or "invalid" in str(e).lower():
            error_msg = f"Model not available. Please try a different model."
        else:
            error_msg = f"An error occurred: {str(e)}"
        
        return jsonify({"error": error_msg}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    api_status = "available" if client else "unavailable"
    return jsonify({
        "status": "healthy",
        "message": "AI Image & Text API is running",
        "gemini_api": api_status,
        "capabilities": {
            "text_qa": [
                "natural language questions",
                "conversational responses",
                "general knowledge"
            ],
            "image_analysis": [
                "detailed descriptions",
                "object segmentation",
                "base64 and URL support"
            ],
            "image_generation": [
                "text-to-image generation",
                "image editing",
                "multi-image composition",
                "style presets"
            ]
        },
        "models": ["gemini-1.5-flash", "gemini-2.0-flash-preview-image-generation"]
    })

@app.route('/api', methods=['GET'])
def api_docs():
    """Complete API documentation"""
    return jsonify({
        "message": "AI Image Analysis & Generation API",
        "version": "2.0",
        "description": "Complete AI-powered image processing with Google Gemini",
        "base_url": request.host_url,
        "endpoints": {
            "image_analysis": {
                "/analyze_base64": {
                    "method": "POST",
                    "description": "Analyze Base64 encoded images",
                    "payload": {
                        "image": "base64_encoded_image_string (required)",
                        "extract_masks": "boolean (optional)"
                    }
                },
                "/analyze_url": {
                    "method": "POST",
                    "description": "Analyze images from URLs",
                    "payload": {
                        "url": "image_url_string (required)",
                        "extract_masks": "boolean (optional)"
                    }
                }
            },
            "image_generation": {
                "/generate_text_to_image": {
                    "method": "POST",
                    "description": "Generate images from text prompts",
                    "payload": {
                        "prompt": "text_description (required)"
                    }
                },
                "/edit_image": {
                    "method": "POST",
                    "description": "Edit images using text prompts",
                    "payload": {
                        "prompt": "edit_description (required)",
                        "image": "base64_encoded_image (required)"
                    }
                },
                "/compose_images": {
                    "method": "POST",
                    "description": "Compose multiple images",
                    "payload": {
                        "prompt": "composition_description (required)",
                        "images": "array_of_base64_images (required, min 2)"
                    }
                }
            },
            "utility": {
                "/": {
                    "method": "GET",
                    "description": "Web interface"
                },
                "/health": {
                    "method": "GET",
                    "description": "API health check"
                },
                "/api": {
                    "method": "GET",
                    "description": "This documentation"
                }
            }
        },
        "features": [
            "Image Analysis with AI descriptions",
            "Object Segmentation with masks",
            "Text-to-Image Generation",
            "AI-powered Image Editing",
            "Multi-Image Composition",
            "Style Presets and Templates",
            "Base64 and URL support",
            "Real-time processing"
        ]
    })
