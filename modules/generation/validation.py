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
    # First try to extract JSON from code blocks
    json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', text)
    if json_match:
        return json_match.group(1).strip()
        
    # Then try to find JSON pattern in the text
    json_match = re.search(r'({[\s\S]*?})', text)
    if json_match:
        return json_match.group(1).strip()
        
    # Remove code markers
    text = re.sub(r'```(?:json)?\s*|```', '', text)
    text = text.strip()
    
    # Ensure the text starts with { and ends with }
    if not text.startswith('{'):
        text = '{' + text
        
    # Count opening and closing braces to ensure structure is complete
    open_braces = text.count('{')
    close_braces = text.count('}')
    
    if open_braces > close_braces:
        # Add missing closing braces
        text = text + ('}' * (open_braces - close_braces))
    elif close_braces > open_braces:
        # Add missing opening braces (less common)
        text = ('{' * (close_braces - open_braces)) + text
    elif not text.endswith('}'):
        # Ensure it ends with a closing brace
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
            st.warning(f"Attempting to fix JSON structure: {str(e)}")
            
            # Fix missing closing braces
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            fixed_json = json_str.strip()
            
            if open_braces > close_braces:
                # Add missing closing braces
                missing_braces = open_braces - close_braces
                fixed_json += ('}' * missing_braces)
                st.info(f"Added {missing_braces} missing closing braces")
            else:
                # Try adding a single closing brace if needed
                if not fixed_json.endswith('}'):
                    fixed_json += '}'
                    
            # Try to fix common JSON issues like missing commas
            fixed_json = re.sub(r'"\s*\n\s*"', '", "', fixed_json)  # Add missing commas between key-value pairs
            fixed_json = re.sub(r'\}\s*\n\s*"', '}, "', fixed_json)  # Add missing commas after objects
            fixed_json = re.sub(r'\}\s*\n\s*\{', '}, {', fixed_json)  # Add missing commas between objects
            
            try:
                data = json.loads(fixed_json)
                st.success("Successfully fixed JSON structure")
            except json.JSONDecodeError as e2:
                st.error(f"Could not fix JSON structure: {str(e2)}")
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
