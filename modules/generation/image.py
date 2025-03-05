"""Image generation using Together AI."""
import os
import logging
import together
import streamlit as st
from typing import Optional, Dict
from PIL import Image
import requests
from io import BytesIO

def init_together_client():
    """Initialize Together AI client with API key."""
    api_key = os.getenv('TOGETHER_API_KEY')
    if not api_key:
        st.warning("Together AI API key not found. Please set TOGETHER_API_KEY environment variable.")
        return None
    
    together.api_key = api_key
    return together

def generate_image(prompt: str, style: str = "photorealistic") -> Optional[Dict]:
    """
    Generate an image using Together AI's Stable Diffusion.
    
    Args:
        prompt (str): Image generation prompt
        style (str): Style modifier for the image
        
    Returns:
        dict: Dictionary containing image URL and metadata, or None if generation fails
    """
    try:
        client = init_together_client()
        if not client:
            return None
            
        # Enhance prompt with style
        enhanced_prompt = f"{prompt} Style: {style}, high quality, detailed, professional"
        
        # Generate image using raw API call
        response = together.Inference.create(
            model='stabilityai/stable-diffusion-xl-base-1.0',
            prompt=enhanced_prompt,
            max_tokens=512,
            temperature=0.7,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1,
            stream=False,
            image_width=1024,
            image_height=1024,
            seed=42
        )
        
        if not response or not response.output:
            st.error("No image generated from Together AI")
            return None
            
        # Get the image data from response
        image_data = response.output[0] if isinstance(response.output, list) else response.output
        
        # Convert base64 to image and save
        try:
            import base64
            img_data = base64.b64decode(image_data)
            img = Image.open(BytesIO(img_data))
            
            # Save image to a temporary file
            import tempfile
            import os
            
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, f"article_image_{hash(prompt)}.png")
            img.save(temp_path, 'PNG')
            
            return {
                'url': temp_path,  # Local file path instead of URL
                'width': img.width,
                'height': img.height,
                'prompt': prompt,
                'alt_text': prompt
            }
        except Exception as e:
            st.error(f"Error downloading generated image: {str(e)}")
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
        # Ensure media structure exists
        if 'media' not in article_data:
            article_data['media'] = {}
        if 'images' not in article_data['media']:
            article_data['media']['images'] = []
            
        # Get image prompt from SEO data
        seo = article_data.get('seo', {})
        image_prompt = seo.get('imagePrompt')
        
        if not image_prompt:
            st.warning("No image prompt found in SEO data")
            return article_data
            
        # Generate the image
        image_data = generate_image(image_prompt)
        if image_data:
            article_data['media']['images'].append(image_data)
            st.success("Successfully generated image for article")
        
        return article_data
        
    except Exception as e:
        st.error(f"Error in generate_images_for_article: {str(e)}")
        logging.error(f"Article image generation error: {str(e)}")
        return article_data
