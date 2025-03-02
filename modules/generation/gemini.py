"""Gemini model initialization and generation functions."""
import streamlit as st
import google.generativeai as genai
import json
import time
import logging
from config.settings import GEMINI_API_KEY
from modules.generation.validation import clean_gemini_response, validate_article_json

def init_gemini_client():
    """Initialize Google Gemini client."""
    try:
        if not GEMINI_API_KEY:
            st.error("Gemini API key not found. Please set GEMINI_API_KEY in your environment variables.")
            return None
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        return {'model': model, 'name': 'gemini-2.0-flash-exp'}
    except Exception as e:
        st.error(f"Failed to initialize Gemini client: {str(e)}")
        return None

def make_gemini_request(client, prompt):
    """Make Gemini API request with retries and proper error handling.
    If Gemini's response isn't valid JSON, return a fallback JSON structure using the raw text.
    """
    try:
        for attempt in range(3):
            try:
                response = client['model'].generate_content(prompt)
                if response and response.text:
                    cleaned_text = clean_gemini_response(response.text)
                    if not cleaned_text.strip().startswith("{"):
                        st.warning("Gemini response is not valid JSON. Using raw text fallback.")
                        lines = cleaned_text.splitlines()
                        title = lines[0].strip() if lines else "Untitled"
                        fallback_json = {
                            "title": title,
                            "content": {"intro": cleaned_text, "sections": [], "conclusion": ""},
                            "seo": {
                                "slug": title.lower().replace(' ', '-'),
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
