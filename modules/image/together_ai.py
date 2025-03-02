"""Together AI image generation functionality."""
import re
import streamlit as st
from together import Together
from config.settings import TOGETHER_API_KEY

def generate_image_from_prompt(image_prompt, alt_text=None):
    """
    Generate an image using Together AI based on a prompt.
    
    Args:
        image_prompt (str): English prompt for image generation
        alt_text (str, optional): Alt text for the image
        
    Returns:
        dict or None: Image data with b64_data, alt_text
    """
    if not image_prompt:
        st.info("No image prompt provided for image generation.")
        return None
    
    # Clean the prompt to ensure it's English-only
    image_prompt_english = re.sub(r'[\u0E00-\u0E7F]+', '', image_prompt).strip()
    if not image_prompt_english:
        image_prompt_english = "A photo-realistic scene of cryptocurrencies floating in the air, depicting the Crypto news"
        st.warning("Using fallback image prompt since no English text was found")
    
    st.info(f"Generating image with prompt: '{image_prompt_english}'")
    
    together_client = Together()
    try:
        response = together_client.images.generate(
            prompt=image_prompt_english,
            model="black-forest-labs/FLUX.1-schnell-free",  
            width=1200,
            height=800,
            steps=4,
            n=1,
            response_format="b64_json"
        )
        
        if response and response.data and len(response.data) > 0:
            b64_data = response.data[0].b64_json
            if not alt_text:
                alt_text = "Generated cryptocurrency image"
                
            st.image("data:image/png;base64," + b64_data, caption=alt_text)
            return {
                "b64_data": b64_data, 
                "alt_text": alt_text, 
                "media_id": None
            }
        else:
            st.error("Failed to generate image. No data returned from Together AI.")
            return None
            
    except Exception as e:
        st.error(f"Error generating image: {str(e)}")
        return None
