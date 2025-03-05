"""JSON validation and cleaning utilities."""
import re
import json
import streamlit as st
import tenacity
from typing import Dict

@tenacity.retry(
    stop=tenacity.stop_after_attempt(5),
    wait=tenacity.wait_exponential(multiplier=1, min=4, max=20),
    retry=tenacity.retry_if_exception_type((Exception)),
    retry_error_callback=lambda retry_state: None
)
def clean_gemini_response(text):
    """Clean Gemini response to extract valid JSON."""
    json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', text)
    if json_match:
        return json_match.group(1).strip()
    json_match = re.search(r'({[\s\S]*?})', text)
    if json_match:
        return json_match.group(1).strip()
    text = re.sub(r'```(?:json)?\s*|```', '', text)
    text = text.strip()
    if not text.startswith('{'):
        text = '{' + text
    if not text.endswith('}'):
        text = text + '}'
    return text

def validate_article_json(json_str) -> Dict:
    """Validate article JSON against schema and return cleaned data."""
    try:
        # First, try to parse the JSON string
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Try to fix common JSON formatting issues
            fixed_json = json_str.strip()
            if not fixed_json.endswith('}'):
                fixed_json += '}'
            try:
                data = json.loads(fixed_json)
            except json.JSONDecodeError:
                st.error(f"Invalid JSON structure: {str(e)}")
                st.code(json_str, language="json")
                return {}
        
        # Handle list or non-dict data
        if isinstance(data, list):
            data = next((item for item in data if isinstance(item, dict)), {})
        elif not isinstance(data, dict):
            data = {}
            
        if not data:
            st.error("Empty or invalid article data")
            return {}
            
        # Validate and auto-fix content structure
        if not data.get('content'):
            data['content'] = {}
            
        content = data['content']
        if isinstance(content.get('intro'), dict):
            content['introduction'] = content.pop('intro')
        elif not content.get('introduction'):
            content['introduction'] = content.get('intro', "")
            
        if 'sections' not in content:
            content['sections'] = []
            
        if 'conclusion' not in content:
            content['conclusion'] = ""
            
        # Ensure SEO structure exists
        if 'seo' not in data:
            data['seo'] = {}
            if data.get('title'):
                data['seo'].update({
                    'slug': re.sub(r'[^\w\s-]', '', data['title'].lower()).replace(' ', '-'),
                    'metaTitle': data['title'],
                    'metaDescription': str(content.get('introduction', {})).strip()[:155],
                    'excerpt': str(content.get('introduction', {})).strip()[:100],
                    'imagePrompt': "",
                    'altText': data['title']
                })
                
        # Ensure media structure exists
        if 'media' not in data:
            data['media'] = {'images': [], 'twitter_embeds': []}
            
        return data
            
    except Exception as e:
        st.error(f"Error validating article data: {str(e)}")
        st.code(json_str, language="json")
        return {}
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {str(e)}")
        st.code(json_str, language="json")
        return {}
    except ValueError as e:
        st.error(f"Validation error: {str(e)}")
        return {}

def clean_source_content(content):
    """Clean source content by handling special characters and escape sequences"""
    content = content.replace(r'!\[', '![') 
    content = content.replace(r'\[', '[') 
    content = content.replace(r'\]', ']') 
    content = content.replace(r'\(', '(') 
    content = content.replace(r'\)', ')') 
    return content
