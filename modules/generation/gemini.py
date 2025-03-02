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

def make_gemini_request(client, prompt, generation_config=None):
    """Make request to Gemini API with updated configuration handling"""
    try:
        model = client.get_model("models/gemini-pro")
        response = model.generate_content(
            prompt,
            generation_config=generation_config or {
                "temperature": 0.7,
                "max_output_tokens": 4096
            }
        )
        return response.text
    except Exception as e:
        st.error(f"Gemini API Error: {str(e)}")
        return None
