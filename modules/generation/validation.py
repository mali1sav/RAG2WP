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

def clean_source_content(content):
    """Clean source content by handling special characters and escape sequences"""
    content = content.replace(r'!\[', '![') 
    content = content.replace(r'\[', '[') 
    content = content.replace(r'\]', ']') 
    content = content.replace(r'\(', '(') 
    content = content.replace(r'\)', ')') 
    return content
