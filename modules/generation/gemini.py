"""Gemini model initialization and generation functions."""
import streamlit as st
import google.genai
import json
import time
import logging
import os
from config.settings import GEMINI_API_KEY
from modules.generation.validation import clean_gemini_response, validate_article_json


def init_gemini_client():
    """Initialize Google Gemini client."""
    try:
        if not GEMINI_API_KEY:
            st.error("Gemini API key not found. Please set GEMINI_API_KEY in your environment variables.")
            return None
        client = google.genai.Client(
            api_key=GEMINI_API_KEY,
        )
        return client
    except Exception as e:
        st.error(f"Failed to initialize Gemini client: {str(e)}")
        return None


def make_gemini_request(client, prompt, generation_config=None):
    """Make request to Gemini API with updated configuration handling"""
    try:
        model = "gemini-2.0-flash"
        contents = [
            google.genai.types.Content(
                role="user",
                parts=[
                    google.genai.types.Part.from_text(
                        text=prompt,
                    ),
                ],
            ),
        ]
        generate_content_config = google.genai.types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_mime_type="text/plain",
        )
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        return response.text
    except Exception as e:
        st.error(f"Gemini API Error: {str(e)}")
        return None
