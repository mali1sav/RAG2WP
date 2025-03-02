"""Configuration settings for the application."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TOGETHER_API_KEY = os.getenv('TOGETHER_API_KEY', '')

# WordPress site configurations
WORDPRESS_SITES = {
    "ICOBENCH": {
        "url": os.getenv("ICOBENCH_WP_URL"),
        "username": os.getenv("ICOBENCH_WP_USERNAME"),
        "password": os.getenv("ICOBENCH_WP_APP_PASSWORD")
    },
    "BITCOINIST": {
        "url": os.getenv("BITCOINIST_WP_URL"),
        "username": os.getenv("BITCOINIST_WP_USERNAME"),
        "password": os.getenv("BITCOINIST_WP_APP_PASSWORD")
    },
    "NEWSBTC": {
        "url": os.getenv("NEWSBTC_WP_URL"),
        "username": os.getenv("NEWSBTC_WP_USERNAME"),
        "password": os.getenv("NEWSBTC_WP_APP_PASSWORD")
    },
    "CRYPTONEWS": {
        "url": os.getenv("CRYPTONEWS_WP_URL"),
        "username": os.getenv("CRYPTONEWS_WP_USERNAME"),
        "password": os.getenv("CRYPTONEWS_WP_APP_PASSWORD")
    },
    "INSIDEBITCOINS": {
        "url": os.getenv("INSIDEBITCOINS_WP_URL"),
        "username": os.getenv("INSIDEBITCOINS_WP_USERNAME"),
        "password": os.getenv("INSIDEBITCOINS_WP_APP_PASSWORD")
    },
    "COINDATAFLOW": {
        "url": os.getenv("COINDATAFLOW_WP_URL"),
        "username": os.getenv("COINDATAFLOW_WP_USERNAME"),
        "password": os.getenv("COINDATAFLOW_WP_APP_PASSWORD")
    }
}

# Logging configuration
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
