"""Gemini model initialization and generation functions."""
import streamlit as st
import google.generativeai as genai
import json
import time
import logging
import tenacity
import re
from config.settings import GEMINI_API_KEY

def init_gemini_client():
    """Initialize Google Gemini client."""
    try:
        if not GEMINI_API_KEY:
            st.error("Gemini API key not found. Please set GEMINI_API_KEY in your environment variables.")
            return None
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        return {'model': model, 'name': 'gemini-2.0-flash'}
    except Exception as e:
        st.error(f"Failed to initialize Gemini client: {str(e)}")
        return None

@tenacity.retry(
    stop=tenacity.stop_after_attempt(5),
    wait=tenacity.wait_exponential(multiplier=1, min=4, max=20),
    retry=tenacity.retry_if_exception_type((Exception)),
    retry_error_callback=lambda retry_state: None
)
def clean_gemini_response(text):
    """Clean Gemini response to extract valid JSON with enhanced Thai language support."""
    # First try to extract JSON from code blocks
    json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', text)
    if json_match:
        extracted = json_match.group(1).strip()
        # Check for specific incomplete patterns
        if "intro" in extracted and "Part 1" in extracted and "Part 2" in extracted:
            # Check if the intro object is complete
            if not re.search(r'"intro"\s*:\s*\{[^{}]*\}', extracted):
                # It's incomplete, add closing brace
                extracted = re.sub(r'("Part 2"\s*:\s*"[^"]*")\s*$', r'\1}', extracted)
        return extracted
        
    # Then try to find JSON pattern in the text
    json_match = re.search(r'({[\s\S]*?})', text)
    if json_match:
        extracted = json_match.group(1).strip()
        # Check for specific incomplete patterns
        if "intro" in extracted and "Part 1" in extracted and "Part 2" in extracted:
            # Check if the intro object is complete
            if not re.search(r'"intro"\s*:\s*\{[^{}]*\}', extracted):
                # It's incomplete, add closing brace
                extracted = re.sub(r'("Part 2"\s*:\s*"[^"]*")\s*$', r'\1}', extracted)
        return extracted
        
    # Remove code markers
    text = re.sub(r'```(?:json)?\s*|```', '', text)
    text = text.strip()
    
    # Fix common issues
    # 1. Fix missing commas between properties
    text = re.sub(r'"([^"]+)"\s*:\s*"([^"]*)"\s+"', '"\1": "\2", "', text)
    
    # 2. Check if intro object is incomplete
    intro_match = re.search(r'"intro"\s*:\s*\{\s*"Part 1"[^{}]*"Part 2"[^{}]*$', text)
    if intro_match and not text.endswith("}"):
        text = text + "}"
    
    # Ensure proper JSON structure
    if not text.startswith('{'):
        text = '{' + text
    if not text.endswith('}'):
        text = text + '}'
        
    # Balance brace counts
    open_count = text.count('{')
    close_count = text.count('}')
    
    if open_count > close_count:
        text = text + ('}' * (open_count - close_count))
    
    return text

def validate_article_json(json_str):
    """Validate article JSON against schema and return cleaned data."""
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            data = next((item for item in data if isinstance(item, dict)), {})
        elif not isinstance(data, dict):
            data = {}
        if not data:
            return {}
        if not data.get('title'):
            raise ValueError("Missing required field: title")
        if not data.get('content'):
            raise ValueError("Missing required field: content")
        seo_field = next((k for k in data.keys() if k.lower() == 'seo'), None)
        if not seo_field:
            raise ValueError("Missing required field: seo")
        content = data['content']
        if not content.get('intro'):
            raise ValueError("Missing required field: content.intro")
        if not content.get('sections'):
            raise ValueError("Missing required field: content.sections")
        if not content.get('conclusion'):
            raise ValueError("Missing required field: content.conclusion")
        seo = data[seo_field]
        required_seo = ['slug', 'metaTitle', 'metaDescription', 'excerpt', 'imagePrompt', 'altText']
        for field in required_seo:
            if not seo.get(field):
                raise ValueError(f"Missing required SEO field: {field}")
        return data
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {str(e)}")
        st.code(json_str, language="json")
        return {}
    except ValueError as e:
        st.error(f"Validation error: {str(e)}")
        return {}

def make_gemini_request(client, prompt, generation_config=None):
    """Make Gemini API request with retries and proper error handling.
    If Gemini's response isn't valid JSON, return a fallback JSON structure using the raw text.
    """
    try:
        for attempt in range(3):
            try:
                response = client['model'].generate_content(
                    prompt,
                    generation_config=generation_config or {
                        "temperature": 0.7,
                        "max_output_tokens": 4096
                    }
                )
                if response and response.text:
                    # Pre-process the response to fix incomplete JSON structures
                    raw_text = response.text
                    
                    # Direct fix for the specific case of incomplete intro objects
                    intro_missing_close = re.search(r'\{\s*"title".*"content"\s*:\s*\{\s*"intro"\s*:\s*\{\s*"Part 1"\s*:.*"Part 2"\s*:.*\}\s*$', raw_text, re.DOTALL)
                    if intro_missing_close:
                        # Add the missing closing braces
                        st.info("Detected incomplete intro object, fixing structure...")
                        raw_text = raw_text + "}}}" 
                    
                    cleaned_text = clean_gemini_response(raw_text)
                    if not cleaned_text.strip().startswith("{"):
                        st.warning("Gemini response is not valid JSON. Using raw text fallback.")
                        lines = cleaned_text.splitlines()
                        title = lines[0].strip() if lines else "Untitled"
                        fallback_json = {
                            "title": title,
                            "content": {"intro": cleaned_text, "sections": [], "conclusion": ""},
                            "seo": {
                                "slug": title.lower().replace(" ", "-"),
                                "metaTitle": title,
                                "metaDescription": title,
                                "excerpt": title,
                                "imagePrompt": "",
                                "altText": ""
                            }
                        }
                        return fallback_json
                    try:
                        return validate_article_json(cleaned_text)
                    except (json.JSONDecodeError, ValueError) as e:
                        if attempt == 2:
                            raise e
                        st.warning("Invalid JSON format, retrying...")
                        continue
            except Exception as e:
                if attempt == 2:
                    raise e
                st.warning(f"Retrying Gemini request (attempt {attempt+2}/3)...")
                time.sleep(2**attempt)
        raise Exception("Failed to get valid response from Gemini API after all retries")
    except Exception as e:
        st.error(f"Error making Gemini request: {str(e)}")
        raise
