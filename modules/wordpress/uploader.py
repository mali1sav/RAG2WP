"""WordPress media upload functionality."""
import base64
import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
from modules.utils.text_utils import construct_endpoint

def upload_image_to_wordpress(b64_data, wp_url, username, wp_app_password, filename="generated_image.png", alt_text="Generated Image"):
    """
    Uploads an image (base64 string) to WordPress via the REST API.
    
    Args:
        b64_data (str): Base64 encoded image data
        wp_url (str): WordPress site URL
        username (str): WordPress username
        wp_app_password (str): WordPress application password
        filename (str): Name for the uploaded file
        alt_text (str): Alt text for the image
        
    Returns:
        dict or None: Media info with 'media_id' and 'source_url', or None on failure
    """
    try:
        image_bytes = base64.b64decode(b64_data)
    except Exception as e:
        st.error(f"[Upload] Decoding error: {e}")
        return None

    media_endpoint = construct_endpoint(wp_url, "/wp-json/wp/v2/media")
    st.write(f"[Upload] Uploading image to {media_endpoint} with alt text: {alt_text}")
    try:
        files = {'file': (filename, image_bytes, 'image/png')}
        data = {'alt_text': alt_text, 'title': alt_text}
        response = requests.post(media_endpoint, files=files, data=data, auth=HTTPBasicAuth(username, wp_app_password))
        st.write(f"[Upload] Response status: {response.status_code}")
        if response.status_code in (200, 201):
            media_data = response.json()
            media_id = media_data.get('id')
            source_url = media_data.get('source_url', '')
            st.write(f"[Upload] Received Media ID: {media_id}")
            # Update alt text via PATCH
            update_endpoint = f"{media_endpoint}/{media_id}"
            update_data = {'alt_text': alt_text, 'title': alt_text}
            update_response = requests.patch(update_endpoint, json=update_data, auth=HTTPBasicAuth(username, wp_app_password))
            st.write(f"[Upload] Update response status: {update_response.status_code}")
            if update_response.status_code in (200, 201):
                st.success(f"[Upload] Image uploaded and alt text updated. Media ID: {media_id}")
                return {"media_id": media_id, "source_url": source_url}
            else:
                st.error(f"[Upload] Alt text update failed. Status: {update_response.status_code}, Response: {update_response.text}")
                return {"media_id": media_id, "source_url": source_url}
        else:
            st.error(f"[Upload] Image upload failed. Status: {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        st.error(f"[Upload] Exception during image upload: {e}")
        return None
