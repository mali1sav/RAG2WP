"""Image generation using Direct API calls to Together AI."""
import os
import logging
import requests
import json
import base64
import streamlit as st
from typing import Optional, Dict
from PIL import Image
from io import BytesIO
import uuid
import time

def generate_image(prompt: str, style: str = "photorealistic") -> Optional[Dict]:
    """
    Generate an image using Together AI's API directly.
    
    Args:
        prompt (str): Image generation prompt
        style (str): Style modifier for the image
        
    Returns:
        dict: Dictionary containing image URL and metadata, or None if generation fails
    """
    try:
        # Get API key from environment variable
        api_key = os.getenv('TOGETHER_API_KEY')
        if not api_key:
            st.warning("Together AI API key not found. Please set TOGETHER_API_KEY environment variable.")
            return None
        
        # Enhance prompt with style
        enhanced_prompt = f"{prompt} Style: {style}, high quality, detailed, professional photograph"
        
        # API configuration
        model = "stabilityai/stable-diffusion-xl-base-1.0"
        api_url = "https://api.together.xyz/inference"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Prepare payload for image generation
        payload = {
            "model": model,
            "prompt": enhanced_prompt,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "max_tokens": 512,
            "repetition_penalty": 1.0,
            "stream": False,
        }
        
        st.info(f"Generating image with prompt: {enhanced_prompt}")
        
        # Make API request
        response = requests.post(api_url, headers=headers, json=payload)
        
        # Check if successful
        if response.status_code != 200:
            st.error(f"Image generation failed: {response.status_code} {response.text}")
            logging.error(f"Together API error: {response.status_code} {response.text}")
            return None
        
        response_data = response.json()
        
        # Check if output exists
        if not response_data.get('output'):
            st.error("No image output received")
            return None
        
        # Extract image data
        output = response_data.get('output')
        image_output = output[0] if isinstance(output, list) else output
        
        # If image_output is a base64 string, decode it
        if isinstance(image_output, str):
            try:
                # Save to a temporary file
                unique_id = str(uuid.uuid4())[:8]
                img_filename = f"article_image_{unique_id}_{int(time.time())}.png"
                
                # Save in a directory accessible to Streamlit
                img_dir = os.path.join(os.getcwd(), "static", "images")
                os.makedirs(img_dir, exist_ok=True)
                img_path = os.path.join(img_dir, img_filename)
                
                # Create the image from base64
                img_data = base64.b64decode(image_output)
                with open(img_path, "wb") as img_file:
                    img_file.write(img_data)
                
                # Get image dimensions
                img = Image.open(BytesIO(img_data))
                width, height = img.size
                
                st.success(f"Image generated successfully and saved to {img_path}")
                
                # Create relative URL
                relative_url = f"/static/images/{img_filename}"
                
                return {
                    'url': relative_url,
                    'width': width,
                    'height': height,
                    'prompt': prompt,
                    'alt_text': prompt
                }
            except Exception as e:
                st.error(f"Error processing image data: {str(e)}")
                logging.exception("Image processing error")
                return None
        else:
            st.error(f"Unexpected output format: {type(image_output)}")
            return None

            
    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        logging.error(f"Image generation error: {str(e)}")
        return None

def generate_images_for_article(article_data: Dict) -> Dict:
    """
    Generate images for an article based on its content.
    
    Args:
        article_data (dict): Article data containing title, content, and SEO info
        
    Returns:
        dict: Updated article data with generated images
    """
    try:
        # Validate input article data
        if not article_data or not isinstance(article_data, dict):
            st.warning("Invalid article data provided to image generator")
            logging.warning(f"Invalid article data: {type(article_data)}")
            return article_data or {}
            
        # Display article title being processed
        if 'title' in article_data:
            st.info(f"Processing images for article: {article_data['title']}")
            
        # Ensure media structure exists
        if 'media' not in article_data:
            article_data['media'] = {}
            
        if 'images' not in article_data['media']:
            article_data['media']['images'] = []
            
        # Get image prompt from SEO data
        seo = article_data.get('seo', {})
        image_prompt = seo.get('imagePrompt')
        
        if not image_prompt:
            st.warning("No image prompt found in SEO data, skipping image generation")
            return article_data
            
        # Log the image prompt being used
        st.info(f"Generating article image with prompt: {image_prompt}")
        logging.info(f"Generating image for article with prompt: {image_prompt}")
        
        # Generate the image
        image_data = generate_image(image_prompt)
        
        if image_data:
            # Add the image to article data
            article_data['media']['images'].append(image_data)
            st.success(f"Successfully generated image: {image_data['url']}")
            
            # Display the image in Streamlit
            try:
                if image_data.get('url'):
                    st.image(image_data['url'], caption=image_data.get('alt_text', ''))
            except Exception as e:
                st.warning(f"Unable to preview image: {str(e)}")
        else:
            st.warning("Failed to generate image for article. Continuing without one.")
        
        return article_data
        
    except Exception as e:
        st.error(f"Error in generate_images_for_article: {str(e)}")
        logging.error(f"Article image generation error: {str(e)}")
        return article_data
