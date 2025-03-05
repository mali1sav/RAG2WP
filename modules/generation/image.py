"""Image generation using Together AI Python client."""
import os
import logging
import json
import base64
import re
import streamlit as st
from typing import Optional, Dict
from PIL import Image
from io import BytesIO
import uuid
import time

# Import the Together client
try:
    from together import Together
except ImportError:
    st.error("Together AI Python client not installed. Please run: pip install together")
    logging.error("Missing Together Python client library")

def generate_image(prompt: str, style: str = "photorealistic") -> Optional[Dict]:
    """
    Generate an image using Together AI Python client.
    
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
        
        # Clean prompt to ensure it's in English (if needed)
        enhanced_prompt_english = re.sub(r'[\u0E00-\u0E7F]+', '', enhanced_prompt).strip()
        if not enhanced_prompt_english:
            enhanced_prompt_english = "A photo-realistic scene depicting the subject matter"
            st.warning("Using fallback image prompt since no English text was found")
        
        st.info(f"Generating image with prompt: '{enhanced_prompt_english}'")
        
        # Initialize Together client
        try:
            together_client = Together(api_key=api_key)
            
            # Make the API call using the library
            response = together_client.images.generate(
                prompt=enhanced_prompt_english,
                model="black-forest-labs/FLUX.1-schnell-free",  # Using a reliable model
                width=1024,
                height=768,
                steps=4,  # Faster generation
                n=1,
                response_format="b64_json"
            )
            
            # Process the response
            if response and hasattr(response, 'data') and len(response.data) > 0:
                # Extract base64 data
                b64_data = response.data[0].b64_json
                
                # Save the image
                unique_id = str(uuid.uuid4())[:8]
                img_filename = f"article_image_{unique_id}_{int(time.time())}.png"
                
                # Save in a directory accessible to Streamlit
                img_dir = os.path.join(os.getcwd(), "static", "images")
                os.makedirs(img_dir, exist_ok=True)
                img_path = os.path.join(img_dir, img_filename)
                
                # Create the image from base64
                img_data = base64.b64decode(b64_data)
                with open(img_path, "wb") as img_file:
                    img_file.write(img_data)
                
                # Get image dimensions
                img = Image.open(BytesIO(img_data))
                width, height = img.size
                
                # Display image in Streamlit
                st.image("data:image/png;base64," + b64_data, caption=prompt)
                st.success(f"Image generated successfully and saved to {img_path}")
                
                # Create relative URL
                relative_url = f"/static/images/{img_filename}"
                
                return {
                    'url': relative_url,
                    'width': width,
                    'height': height,
                    'prompt': prompt,
                    'alt_text': prompt,
                    'b64_data': b64_data
                }
            else:
                st.error("No image data received from Together AI.")
                logging.error(f"No image data received. Response: {response}")
                return None
                
        except AttributeError as e:
            st.error(f"Error with Together client: {str(e)}")
            logging.error(f"Together client attribute error: {str(e)}")
            st.warning("This may be caused by an outdated version of the 'together' package. Please run: pip install -U together")
            return None
            
        except Exception as e:
            st.error(f"Error generating image with Together client: {str(e)}")
            logging.exception("Together client error")
            return None
            
    except Exception as e:
        st.error(f"Error in image generation process: {str(e)}")
        logging.exception("Image generation error")
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
