"""Web content extraction using Jina API."""
import re
import requests
import streamlit as st
import logging

def jina_extract_via_r(url: str) -> dict:
    """
    Uses the Jina REST API endpoint (https://r.jina.ai/) to extract LLM-ready text, images, and social media embeds.
    Returns the extracted content with media elements.
    """
    JINA_BASE_URL = "https://r.jina.ai/"
    full_url = JINA_BASE_URL + url
    try:
        r = requests.get(full_url)
    except Exception as e:
        logging.error(f"Jina request error: {e}")
        return {
            "title": "Extracted Content",
            "content": {"intro": "", "sections": [], "conclusion": ""},
            "media": {
                "images": [],
                "twitter_embeds": []
            },
            "seo": {
                "slug": "", "metaTitle": "", "metaDescription": "", "excerpt": "", "imagePrompt": "", "altText": ""
            }
        }

    if r.status_code == 200:
        text = r.text
        md_index = text.find("Markdown Content:")
        md_content = text[md_index + len("Markdown Content:"):].strip() if md_index != -1 else text.strip()
        title_match = re.search(r"Title:\s*(.*)", text)
        title = title_match.group(1).strip() if title_match else "Extracted Content"

        # Extract images, filtering out likely sidebar or promotional images
        images = []
        img_matches = re.finditer(r'!\[(.*?)\]\((.*?)\)', md_content)
        
        # Define patterns for likely sidebar or promotional images
        sidebar_patterns = [
            r'icon|logo|sidebar|banner|ad-|advertisement|promo-|sponsor',
            r'\d+x\d+',  # Dimension patterns like 300x250
            r'tracking|pixel',
            r'\.(svg|gif)$'  # SVG files are often icons/logos, GIFs often ads
        ]
        
        MAX_IMAGES = 5  # Limit number of images
        image_count = 0
        
        for match in img_matches:
            alt_text = match.group(1)
            img_url = match.group(2)
            
            # Skip if we already have enough images
            if image_count >= MAX_IMAGES:
                break
                
            # Skip if the image appears to be a sidebar/promotional image
            is_sidebar_image = False
            for pattern in sidebar_patterns:
                if re.search(pattern, img_url.lower()) or re.search(pattern, alt_text.lower()):
                    is_sidebar_image = True
                    break
            
            if is_sidebar_image:
                continue
                
            # Get surrounding paragraph text for context
            surrounding_text = ""
            para_match = re.search(r'([^\n]+' + re.escape(match.group(0)) + r'[^\n]+)', md_content)
            if para_match:
                surrounding_text = para_match.group(1)
                
            # If context is short, it's likely not part of main content
            if len(surrounding_text) < 50:
                continue
                
            images.append({
                "url": img_url,
                "alt_text": alt_text,
                "context": surrounding_text
            })
            image_count += 1

        # Extract Twitter/X embeds
        twitter_embeds = []
        twitter_urls = re.finditer(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\s]+/status/\d+', md_content)
        for match in twitter_urls:
            url = match.group(0)
            surrounding_text = ""
            # Get surrounding paragraph text for context
            para_match = re.search(r'([^\n]+' + re.escape(url) + r'[^\n]+)', md_content)
            if para_match:
                surrounding_text = para_match.group(1)
            twitter_embeds.append({
                "url": url,
                "context": surrounding_text
            })

        # Clean up the content by removing the raw URLs of extracted tweets
        for embed in twitter_embeds:
            md_content = md_content.replace(embed["url"], "")

        fallback_json = {
            "title": title,
            "content": {"intro": md_content, "sections": [], "conclusion": ""},
            "media": {
                "images": images,
                "twitter_embeds": twitter_embeds
            },
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
    else:
        logging.error(f"Jina extraction failed with status code {r.status_code}")
        return {
            "title": "Extracted Content",
            "content": {"intro": "", "sections": [], "conclusion": ""},
            "seo": {
                "slug": "", "metaTitle": "", "metaDescription": "", "excerpt": "", "imagePrompt": "", "altText": ""
            }
        }

def extract_url_content(gemini_client, url, messages_placeholder):
    """
    Extracts article content from a URL.
    Handles YouTube URLs (using transcript) and regular web pages (using Jina REST API).
    """
    from modules.content_extraction.transcript import TranscriptFetcher
    
    fetcher = TranscriptFetcher()
    video_id = fetcher.get_video_id(url)

    if video_id:
        with messages_placeholder:
            st.info(f"Extracting YouTube transcript from {url}...")
        transcript_data = fetcher.get_transcript(url)
        if transcript_data:
            with st.expander("Debug: YouTube Transcript", expanded=False):
                st.write("Transcript data:", transcript_data)
            return {
                'title': "YouTube Video Transcript",
                'url': url,
                'content': transcript_data['text'],
                'published_date': None,
                'source': f"YouTube Video ({video_id})",
                'author': None,
                'media': {"images": [], "twitter_embeds": []}
            }
        else:
            st.warning("Performing content extraction via Jina AI...")

    with messages_placeholder:
        st.info(f"Extracting content from {url} using Jina REST API...")
    fallback_data = jina_extract_via_r(url)
    with st.expander("Debug: Jina Extraction", expanded=False):
        st.write("Jina extracted JSON:", fallback_data)
    content_text = fallback_data.get("content", {}).get("intro", "")
    with st.expander("Debug: Jina Extracted Content", expanded=False):
        st.write("Extracted content:", content_text)
    return {
        'title': fallback_data.get("title", "Extracted Content"),
        'url': url,
        'content': content_text,
        'published_date': None,
        'source': url,
        'author': None,
        'media': fallback_data.get('media', {})  # Include extracted media
    }
