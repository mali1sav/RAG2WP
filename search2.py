import os
import re
import json
import time
import base64
import html
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict
from urllib.parse import urlparse

import requests
import streamlit as st
import markdown
import tenacity
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from requests.auth import HTTPBasicAuth
from together import Together
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api.formatters import TextFormatter

load_dotenv()

# Define site-specific edit URLs (ensure every site gets an edit link)
SITE_EDIT_URLS = {
    "BITCOINIST": "https://bitcoinist.com/wp-admin/post.php?post={post_id}&action=edit&classic-editor",
    "NEWSBTC": "https://www.newsbtc.com/wp-admin/post.php?post={post_id}&action=edit&classic-editor",
    "ICOBENCH": "https://icobench.com/th/wp-admin/post.php?post={post_id}&action=edit&classic-editor",
    "CRYPTONEWS": "https://cryptonews.com/th/wp-admin/post.php?post={post_id}&action=edit&classic-editor",
    "INSIDEBITCOINS": "https://insidebitcoins.com/th/wp-admin/post.php?post={post_id}&action=edit&classic-editor",
    "COINDATAFLOW": "https://coindataflow.com/th/blog/wp-admin/post.php?post={post_id}&action=edit&classic-editor"
}

# Promotional Images Data Structure
PROMOTIONAL_IMAGES = {
    "Best Wallet": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/best-wallet-1024x952-1.png",
        "alt": "Best Wallet",
        "width": "600",
        "height": "558"
    },
    "Solaxy": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/solaxy-1.png",
        "alt": "Solaxy Thailand",
        "width": "600",
        "height": "520"
    },
    "BTC Bull Token": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/btc-bull-token.png",
        "alt": "BTC Bull Token",
        "width": "600",
        "height": "408"
    },
    "Mind of Pepe": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/mind-of-pepe-e1740672348698.png",
        "alt": "Mind of Pepe",
        "width": "600",
        "height": "490"
    },
    "Meme Index": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/memeindex.png",
        "alt": "Meme Index",
        "width": "600",
        "height": "468"
    },
    "Catslap": {
        "url": "https://icobench.com/th/wp-content/uploads/sites/17/2025/02/catslap.png",
        "alt": "Catslap Token",
        "width": "600",
        "height": "514"
    }
}

# Affiliate Links Data Structure
AFFILIATE_LINKS = {
    "ICOBENCH": {
        "Best Wallet": "https://icobench.com/th/visit/bestwallettoken",
        "Solaxy": "https://icobench.com/th/visit/solaxy",
        "BTC Bull Token": "https://icobench.com/th/visit/bitcoin-bull",
        "Mind of Pepe": "https://icobench.com/th/visit/mindofpepe",
        "Meme Index": "https://icobench.com/th/visit/memeindex",
        "Catslap": "https://icobench.com/th/visit/catslap"
    },
    "BITCOINIST": {
        "Best Wallet": "https://bs_332b25fb.bitcoinist.care/",
        "Solaxy": "https://bs_ddfb0f8c.bitcoinist.care/",
        "BTC Bull Token": "https://bs_919798f4.bitcoinist.care/",
        "Mind of Pepe": "https://bs_1f5417eb.bitcoinist.care/",
        "Meme Index": "https://bs_89e992a3.bitcoinist.care",
        "Catslap": "https://bs_362f7e64.bitcoinist.care/"
    },
    "COINDATAFLOW": {
        "Best Wallet": "https://bs_75a55063.Cryptorox.care",
        "Solaxy": "https://bs_baf1ac7c.Cryptorox.care",
        "BTC Bull Token": "https://bs_d3f9bf50.Cryptorox.care",
        "Mind of Pepe": "https://bs_770fab4c.Cryptorox.care",
        "Meme Index": "https://bs_89204fe5.Cryptorox.care",
        "Best Wallet Token": "https://bs_9f0cd602.Cryptorox.care",
        "Catslap": "https://bs_7425c4d9.Cryptorox.care"
    },
    "CRYPTONEWS": {
        "Best Wallet": "https://bestwallettoken.com/th?tid=156",
        "Solaxy": "https://solaxy.io/th/?tid=156",
        "BTC Bull Token": "https://btcbulltoken.com/th?tid=156",
        "Mind of Pepe": "https://mindofpepe.com/th?tid=156",
        "Meme Index": "https://memeindex.com/?tid=156",
        "Catslap": "https://catslaptoken.com/th?tid=156"
    },
    "INSIDEBITCOINS": {
        "Best Wallet": "https://insidebitcoins.com/th/visit/best-wallet-token",
        "Solaxy": "https://insidebitcoins.com/th/visit/solaxy",
        "BTC Bull Token": "https://insidebitcoins.com/th/visit/bitcoin-bull",
        "Mind of Pepe": "https://insidebitcoins.com/th/visit/mindofpepe",
        "Meme Index": "https://insidebitcoins.com/th/visit/memeindex",
        "Catslap": "https://insidebitcoins.com/th/visit/catslap"
    }
}


def process_affiliate_links(content, website, project_name=None):
    """
    Scan content for anchor texts and replace with appropriate affiliate links.
    If project_name is provided, also add the corresponding promotional image in the third section.

    Args:
        content (str): The article content
        website (str): The website to publish to (e.g., "ICOBENCH")
        project_name (str, optional): Name of the promotional project to add image for

    Returns:
        str: Content with affiliate links and promotional image inserted
    """
    if website not in AFFILIATE_LINKS:
        return content

    # Process affiliate links
    for anchor_text, link_url in AFFILIATE_LINKS[website].items():
        # Use regex to ensure we're matching whole words only
        pattern = r'\b' + re.escape(anchor_text) + r'\b'
        replacement = f'<a href="{link_url}" target="_blank" rel="sponsored noopener">{anchor_text}</a>'
        content = re.sub(pattern, replacement, content)

    # Add promotional image if project name is provided
    if project_name and project_name in PROMOTIONAL_IMAGES:
        img_data = PROMOTIONAL_IMAGES[project_name]
        img_html = f'<img '
        img_html += f'src="{img_data["url"]}" '
        img_html += f'alt="{img_data["alt"]}" '
        img_html += f'width="{img_data["width"]}" '
        img_html += f'height="{img_data["height"]}" />\n\n'

        # Find the promotional section (typically the third section)
        # Look for the third <h2> tag in the content
        h2_tags = re.findall(r'<h2[^>]*>(.*?)</h2>', content)
        if len(h2_tags) >= 3:
            # Insert the image after the third heading
            third_heading = h2_tags[2]
            pattern = f'<h2[^>]*>{re.escape(third_heading)}</h2>'
            replacement = f'<h2>{third_heading}</h2>\n\n{img_html}'
            content = re.sub(pattern, replacement, content)
        else:
            # If we can't find the third heading, add it before the conclusion
            conclusion_pattern = r'<p>บทความนี้นำเสนอข้อมูลเกี่ยวกับ|<h2[^>]*>บทสรุป|<h2[^>]*>สรุป'
            match = re.search(conclusion_pattern, content)
            if match:
                # Insert before the conclusion
                pos = match.start()
                content = content[:pos] + img_html + content[pos:]
            else:
                # If all else fails, add it at the end
                content += "\n\n" + img_html

    return content


# ------------------------------
# Utility Functions
# ------------------------------

def escape_special_chars(text):
    """Escape special characters that might interfere with Markdown formatting."""
    text = re.sub(r'(?<!\$)\$(?!\$)', r'\$', text)
    chars_to_escape = ['*', '_', '`', '#', '~', '|', '<', '>', '[', ']']
    for char in chars_to_escape:
        text = text.replace(char, '\\' + char)
    return text


def construct_endpoint(wp_url, endpoint_path):
    """Construct the WordPress endpoint."""
    wp_url = wp_url.rstrip('/')
    # Skip adding /th for Bitcoinist and NewsBTC if not any(domain in wp_url for domain in ["bitcoinist.com", "newsbtc.com"]) and "/th" not in wp_url:
    if not any(domain in wp_url for domain in ["bitcoinist.com", "newsbtc.com"]) and "/th" not in wp_url:
        wp_url += "/th"
    return f"{wp_url}{endpoint_path}"


# ------------------------------
# YouTube Transcript Fetcher
# ------------------------------

class TranscriptFetcher:
    """Fetches YouTube transcripts."""

    def get_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        try:
            video_id = re.search(r'(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11}).*', url)
            return video_id.group(1) if video_id else None
        except Exception as e:
            logging.error(f"Error extracting video ID: {str(e)}")
            return None

    def get_transcript(self, url: str) -> Optional[Dict]:
        """Get English transcript from YouTube."""
        try:
            video_id = self.get_video_id(url)
            if not video_id:
                logging.error(f"Could not extract video ID from URL: {url}")
                return None

            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                full_text = " ".join(segment['text'] for segment in transcript)
                logging.info(f"Successfully got YouTube transcript for video {video_id}")
                return {
                    'text': full_text,
                    'segments': transcript
                }
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                logging.error(f"No transcript available for video {video_id}: {str(e)}")
                return None
        except Exception as e:
            logging.error(f"Error getting YouTube transcript: {str(e)}")
            return None


# ------------------------------
# Data Models
# ------------------------------

class ArticleSection(BaseModel):
    """Data model for an article section."""
    heading: str = Field(..., description="H2 heading with power words in Thai")
    paragraphs: List[str] = Field(..., min_items=2, max_items=4, description="2-4 detailed paragraphs")


class ArticleContent(BaseModel):
    """Data model for article content."""
    intro: str = Field(..., description="First paragraph with primary keyword")
    sections: List[ArticleSection]
    conclusion: str = Field(..., description="Summary emphasizing news angle")


class Source(BaseModel):
    """Data model for article source."""
    domain: str
    url: str


class ArticleSEO(BaseModel):
    """Data model for article SEO."""
    slug: str = Field(..., description="English URL-friendly with primary keyword")
    metaTitle: str = Field(..., description="Thai SEO title with primary keyword")
    metaDescription: str = Field(..., description="Thai meta desc with primary keyword")
    excerpt: str = Field(..., description="One Thai sentence summary")
    imagePrompt: str = Field(..., description="English photo description")
    altText: str = Field(..., description="Thai ALT text with English terms")


class Article(BaseModel):
    """Data model for a complete article."""
    title: str = Field(..., description="Thai news-style title with primary keyword")
    content: ArticleContent
    sources: List[Source]
    seo: ArticleSEO


# ------------------------------
# SEO Parsing Functions
# ------------------------------

def parse_article(article_json, add_affiliate_note=False):
    """
    Parses the generated article JSON into structured elements with robust error handling.
    Returns a dict with keys needed for WordPress upload.
    If add_affiliate_note=True, append the affiliate disclosure shortcode after the conclusion.
    """
    try:
        # Ensure we have valid JSON data
        article = json.loads(article_json) if isinstance(article_json, str) else article_json
        if not isinstance(article, dict):
            raise ValueError("Article data must be a dictionary")

        content_parts = []

        # Validate and handle required top-level keys
        if 'content' not in article:
            raise ValueError("Missing required 'content' field in article")
        content = article['content']
        if not isinstance(content, dict):
            raise ValueError("Article content must be a dictionary")

        # Handle intro with validation
        intro = content.get('intro', '')
        if isinstance(intro, dict):
            content_parts.append(intro.get('Part 1', 'Introduction Part 1'))
            content_parts.append(intro.get('Part 2', 'Introduction Part 2'))
        else:
            content_parts.append(str(intro))

        # Handle sections with comprehensive validation
        sections = content.get('sections', [])
        if not isinstance(sections, list):
            sections = []
        for section in sections:
            if not isinstance(section, dict):
                continue

            # Add section heading
            heading = section.get('heading', 'Section Heading')
            content_parts.append(f"## {heading}")

            # Get format type with validation
            format_type = section.get('format', 'paragraph')
            paragraphs = section.get('paragraphs', [])

            # Ensure paragraphs is a list
            if not isinstance(paragraphs, list):
                paragraphs = [str(paragraphs)]

            # Handle empty paragraphs
            if not paragraphs:
                content_parts.append("*Content for this section is being processed.*")
                content_parts.append("")
                continue

            try:
                if format_type == 'list':
                    # Handle list format
                    content_parts.extend([f"* {str(item)}" for item in paragraphs])
                elif format_type == 'table':
                    # Handle table format with validation
                    if paragraphs:
                        first_item = paragraphs[0]
                        if isinstance(first_item, str) and first_item.startswith('|'):
                            content_parts.extend(paragraphs)
                        elif isinstance(first_item, (list, tuple)):
                            # Handle list/tuple based table headers
                            headers = [str(h) for h in first_item]
                            content_parts.append('| ' + ' | '.join(headers) + ' |')
                            content_parts.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
                            for row in paragraphs[1:]:
                                if isinstance(row, (list, tuple)):
                                    content_parts.append('| ' + ' | '.join(str(cell) for cell in row) + ' |')
                        elif isinstance(first_item, dict):
                            # Handle dict based table
                            headers = list(first_item.keys())
                            content_parts.append('| ' + ' | '.join(str(h) for h in headers) + ' |')
                            content_parts.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
                            for row in paragraphs:
                                if isinstance(row, dict):
                                    content_parts.append('| ' + ' | '.join(str(row.get(h, '')) for h in headers) + ' |')
                else:
                    # Handle regular paragraphs
                    for para in paragraphs:
                        content_parts.append(str(para))
                content_parts.append("")

            except Exception as e:
                st.error(f"Error processing section content: {str(e)}")
            finally:
                pass  # Clean up any temporary resources

        # Handle conclusion
        conclusion = content.get('conclusion', 'Article conclusion.')
        content_parts.append(str(conclusion))

        # If user included promotional content, add the affiliate disclosure note
        if add_affiliate_note:
            content_parts.append(
                "[su_note note_color=\"#FEFEEE\"] เรามุ่งมั่นในการสร้างความโปร่งใสอย่างเต็มที่กับผู้อ่านของเรา บางเนื้อหาในเว็บไซต์อาจมีลิงก์พันธมิตร ซึ่งเราอาจได้รับค่าคอมมิชชั่นจากความร่วมมือเหล่านี้ [/su_note]")

        # Initialize result with default values
        result = {
            "main_title": "Untitled Article",
            "main_content": "\n\n".join(content_parts),
            "yoast_title": "",
            "yoast_metadesc": "",
            "seo_slug": "",
            "excerpt": "",
            "image_prompt": "",
            "image_alt": ""
        }

        # Safely extract SEO fields with error handling
        try:
            result["main_title"] = article.get('title', "Untitled Article")
            # Check if SEO data exists and is a dictionary
            seo_data = article.get('seo', {})
            if not isinstance(seo_data, dict):
                seo_data = {}

            # Extract SEO fields with appropriate validation and defaults
            result["yoast_title"] = seo_data.get('metaTitle', result["main_title"])
            meta_desc = seo_data.get('metaDescription', '')
            if meta_desc and len(meta_desc) > 160:
                meta_desc = meta_desc[:157] + "..."
            result["yoast_metadesc"] = meta_desc
            result["seo_slug"] = seo_data.get('slug', '')
            result["excerpt"] = seo_data.get('excerpt', '')
            result["image_prompt"] = seo_data.get('imagePrompt', '')
            result["image_alt"] = seo_data.get('altText', '')
        except Exception as e:
            st.warning(f"Error extracting SEO fields: {str(e)}. Using default values.")

        return result

    except (json.JSONDecodeError, KeyError) as e:
        st.error(f"Failed to parse article JSON: {str(e)}")
        return {}


# ------------------------------
# WordPress Uploader Functions
# ------------------------------

def upload_image_to_wordpress(b64_data, wp_url, username, wp_app_password, filename="generated_image.png",
                              alt_text="Generated Image"):
    """
    Uploads an image (base64 string) to WordPress via the REST API.
    Returns a dict with 'media_id' and 'source_url'.
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
            update_response = requests.patch(update_endpoint, json=update_data,
                                             auth=HTTPBasicAuth(username, wp_app_password))
            st.write(f"[Upload] Update response status: {update_response.status_code}")

            if update_response.status_code in (200, 201):
                st.success(f"[Upload] Image uploaded and alt text updated. Media ID: {media_id}")
                return {"media_id": media_id, "source_url": source_url}
            else:
                st.error(
                    f"[Upload] Alt text update failed. Status: {update_response.status_code}, Response: {update_response.text}")
                return {"media_id": media_id, "source_url": source_url}
        else:
            st.error(f"[Upload] Image upload failed. Status: {response.status_code}, Response: {response.text}")
            return None

    except Exception as e:
        st.error(f"[Upload] Exception during image upload: {e}")
        return None


def convert_to_gutenberg_format(content):
    """
    Convert standard HTML content to Gutenberg blocks format.

    Args:
        content (str): Standard HTML content

    Returns:
        str: Content formatted as Gutenberg blocks
    """
    # If content already contains Gutenberg blocks, return as is
    if '<!-- wp:' in content:
        return content

    try:
        # Try to import BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            use_bs4 = True
        except ImportError:
            st.warning("BeautifulSoup (bs4) is not installed. Using fallback HTML parsing method.")
            use_bs4 = False

        if use_bs4:
            # Process the content sequentially to maintain the original order using BeautifulSoup
            gutenberg_content = []
            # Use BeautifulSoup to parse the HTML content
            soup = BeautifulSoup(content, 'html.parser')

            # Process each element in order
            for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'img', 'figure']):
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # Convert all headings to h2 for consistency
                    level = 2
                    gutenberg_content.append(f'<!-- wp:heading -->')
                    gutenberg_content.append(f'<h{level}>{element.get_text()}</h{level}>')
                    gutenberg_content.append(f'<!-- /wp:heading -->')
                elif element.name == 'p':
                    # Process paragraphs
                    gutenberg_content.append('<!-- wp:paragraph -->')
                    gutenberg_content.append(f'<p>{element.decode_contents()}</p>')
                    gutenberg_content.append('<!-- /wp:paragraph -->')
                elif element.name == 'ul':
                    # Process unordered lists
                    gutenberg_content.append('<!-- wp:list -->')
                    gutenberg_content.append(str(element))
                    gutenberg_content.append('<!-- /wp:list -->')
                elif element.name == 'ol':
                    # Process ordered lists
                    gutenberg_content.append('<!-- wp:list {"ordered":true} -->')
                    gutenberg_content.append(str(element))
                    gutenberg_content.append('<!-- /wp:list -->')
                elif element.name == 'img':
                    # Process images
                    align = 'center' if 'aligncenter' in element.get('class', []) else ''
                    attrs = {}
                    if align:
                        attrs['align'] = align
                    gutenberg_content.append(f'<!-- wp:image {json.dumps(attrs)} -->')
                    gutenberg_content.append(
                        f'<figure class="wp-block-image{" align" + align if align else ""}">{str(element)}</figure>')
                    gutenberg_content.append('<!-- /wp:image -->')
                elif element.name == 'figure':
                    # Process figure elements (which may contain images)
                    img = element.find('img')
                    if img:
                        align = 'center' if 'aligncenter' in element.get('class', []) else ''
                        attrs = {}
                        if align:
                            attrs['align'] = align
                        gutenberg_content.append(f'<!-- wp:image {json.dumps(attrs)} -->')
                        gutenberg_content.append(str(element))
                        gutenberg_content.append('<!-- /wp:image -->')

            # If no blocks were created, wrap the entire content in a paragraph block
            if not gutenberg_content:
                gutenberg_content.append('<!-- wp:paragraph -->')
                gutenberg_content.append(f'<p>{content}</p>')
                gutenberg_content.append('<!-- /wp:paragraph -->')

            return '\n'.join(gutenberg_content)

        else:
            # Fallback method using regex for basic HTML parsing
            gutenberg_content = []

            # Process headings
            heading_pattern = r'<h[1-6][^>]*>(.*?)</h[1-6]>'
            for match in re.finditer(heading_pattern, content, re.DOTALL):
                heading_text = re.sub(r'<.*?>', '', match.group(1))  # Remove any HTML tags inside heading
                gutenberg_content.append('<!-- wp:heading -->')
                gutenberg_content.append(f'<h2>{heading_text}</h2>')
                gutenberg_content.append('<!-- /wp:heading -->')

            # Process paragraphs
            paragraph_pattern = r'<p[^>]*>(.*?)</p>'
            for match in re.finditer(paragraph_pattern, content, re.DOTALL):
                paragraph_content = match.group(1)
                gutenberg_content.append('<!-- wp:paragraph -->')
                gutenberg_content.append(f'<p>{paragraph_content}</p>')
                gutenberg_content.append('<!-- /wp:paragraph -->')

            # Process lists
            list_pattern = r'<(ul|ol)[^>]*>(.*?)</\1>'
            for match in re.finditer(list_pattern, content, re.DOTALL):
                list_type = match.group(1)
                list_content = match.group(0)
                if list_type == 'ul':
                    gutenberg_content.append('<!-- wp:list -->')
                    gutenberg_content.append(list_content)
                    gutenberg_content.append('<!-- /wp:list -->')
                else:  # ol
                    gutenberg_content.append('<!-- wp:list {"ordered":true} -->')
                    gutenberg_content.append(list_content)
                    gutenberg_content.append('<!-- /wp:list -->')

            # If no blocks were created or if we couldn't parse the HTML properly,
            # wrap the entire content in a paragraph block
            if not gutenberg_content:
                gutenberg_content.append('<!-- wp:paragraph -->')
                gutenberg_content.append(f'<p>{content}</p>')
                gutenberg_content.append('<!-- /wp:paragraph -->')

            return '\n'.join(gutenberg_content)

    except Exception as e:
        st.error(f"Error converting to Gutenberg format: {str(e)}")
        # Return the original content wrapped in a paragraph block as a fallback
        return f'<!-- wp:paragraph -->\n<p>{content}</p>\n<!-- /wp:paragraph -->'


def submit_article_to_wordpress(article, wp_url, username, wp_app_password, primary_keyword="", site_name=None,
                                 content_type="post"):
    """
    Submits the article to WordPress using the WP REST API.
    Choose between 'post' and 'page' via the content_type parameter.
    Sets Yoast SEO meta fields and auto-selects the featured image.
    Always displays the edit link for every article.
    For posts, content is converted to Gutenberg blocks format.
    If site_name is provided, affiliate links are inserted based on the site's configuration.
    """
    try:
        # Deep normalization for article data
        while isinstance(article, list) and len(article) > 0:
            article = article[0]
        if not isinstance(article, dict):
            article = {}

        # Determine endpoint based on content_type
        if content_type.lower() == "page":
            endpoint = construct_endpoint(wp_url, "/wp-json/wp/v2/pages")
        else:
            endpoint = construct_endpoint(wp_url, "/wp-json/wp/v2/posts")

        st.write("Submitting article with Yoast SEO fields...")
        st.write("Yoast Title:", article.get("yoast_title"))
        st.write("Yoast Meta Description:", article.get("yoast_metadesc"))
        st.write("Selected site:", site_name)  # Debug: Show the site name being used

        # Get the content and apply affiliate links
        content = article.get("main_content", "")
        if site_name and content:
            content = process_affiliate_links(content, site_name)

        # Convert to Gutenberg format if it's a post
        if content_type.lower() == "post":
            content = convert_to_gutenberg_format(content)

        # Get the original article JSON if available in session state
        article_json = None
        if "article" in st.session_state and st.session_state.article:
            try:
                article_json = json.loads(st.session_state.article)
            except json.JSONDecodeError as e:
                st.warning(f"Could not parse article JSON for media placement: {str(e)}")

        # Initialize data dictionary with article content and meta fields
        data = {
            "title": article.get("main_title", "Untitled"),
            "content": content,
            "slug": article.get("seo_slug", ""),
            "excerpt": article.get("excerpt", ""),
            "status": "draft",
            "meta_input": {
                "_yoast_wpseo_title": article.get("yoast_title", ""),
                "_yoast_wpseo_metadesc": article.get("yoast_metadesc", ""),
                "_yoast_wpseo_focuskw": primary_keyword
            }
        }

        if "image" in article:
            image_data = article["image"]
            if isinstance(image_data, list) and len(image_data) > 0:
                image_data = image_data[0]
            if isinstance(image_data, dict) and image_data.get("media_id"):
                data["featured_media"] = image_data["media_id"]

        # Set categories and tags if keyword matches
        keyword_to_cat_tag = {"Dogecoin": 527, "Bitcoin": 7}
        if primary_keyword in keyword_to_cat_tag:
            cat_tag_id = keyword_to_cat_tag[primary_keyword]
            data["categories"] = [cat_tag_id]
            data["tags"] = [cat_tag_id]

        # Submit the article
        response = requests.post(endpoint, json=data, auth=HTTPBasicAuth(username, wp_app_password))

        if response.status_code in (200, 201):
            post = response.json()
            post_id = post.get('id')
            st.success(f"Article '{data['title']}' submitted successfully! ID: {post_id}")

            # Debug: Show available edit URLs
            st.write("Available edit URLs:", list(SITE_EDIT_URLS.keys()))

            # Always generate and display the edit URL for every article.
            edit_url = SITE_EDIT_URLS.get(site_name,
                                          f"{wp_url.rstrip('/')}/wp-admin/post.php?post={{post_id}}&action=edit&classic-editor").format(
                post_id=post_id)
            st.markdown(f"[Click here to edit your draft article]({edit_url})")
            st.session_state.pending_edit_url = edit_url
            return post
        else:
            st.error(f"Failed to submit article. Status: {response.status_code}")
            st.error(f"Response: {response.text}")
            return None

    except Exception as e:
        st.error(f"Exception during article submission: {str(e)}")
        return None


# ------------------------------
# Jina-Based Fallback Extraction (Using Jina API)
# ------------------------------

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
        st.error(f"Jina request error: {e}")
        return {
            "title": "Extracted Content",
            "content": {"intro": "", "sections": [], "conclusion": ""},
            "media": {
                "images": [],
                "twitter_embeds": []
            },
            "seo": {
                "slug": "",
                "metaTitle": "",
                "metaDescription": "",
                "excerpt": "",
                "imagePrompt": "",
                "altText": ""
            }
        }

    if r.status_code == 200:
        text = r.text
        md_index = text.find("Markdown Content:")
        md_content = text[md_index + len("Markdown Content:"):].strip() if md_index != -1 else text.strip()

        title_match = re.search(r"Title:\s*(.*)", text)
        title = title_match.group(1).strip() if title_match else "Extracted Content"

        # Extract images
        images = []
        img_matches = re.finditer(r'!\[(.*?)\]\((.*?)\)', md_content)
        for match in img_matches:
            alt_text = match.group(1)
            img_url = match.group(2)
            surrounding_text = ""
            # Get surrounding paragraph text for context
            para_match = re.search(r'([^\n]+' + re.escape(match.group(0)) + r'[^\n]+)', md_content)
            if para_match:
                surrounding_text = para_match.group(1)
            images.append({
                "url": img_url,
                "alt_text": alt_text,
                "context": surrounding_text
            })

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

        # Clean up the content by removing the raw URLs of extracted tweets for embed
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
        st.error(f"Jina extraction failed with status code {r.status_code}")
        return {
            "title": "Extracted Content",
            "content": {"intro": "", "sections": [], "conclusion": ""},
            "seo": {
                "slug": "",
                "metaTitle": "",
                "metaDescription": "",
                "excerpt": "",
                "imagePrompt": "",
                "altText": ""
            }
        }


def extract_url_content(gemini_client, url, messages_placeholder):
    """
    Extracts article content from a URL.
    Handles YouTube URLs (using transcript) and regular web pages (using Jina REST API).
    """
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
                'author': None
            }
        else:
            st.warning("Could not extract transcript from YouTube video. Falling back to Jina extraction...")

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


# ------------------------------
# Gemini Article Generation Functions
# ------------------------------

def init_gemini_client():
    """Initialize Google Gemini client."""
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            st.error("Gemini API key not found. Please set GEMINI_API_KEY in your environment variables.")
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        return {'model': model, 'name': 'gemini-2.0-flash-exp'}
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


def make_gemini_request(client, prompt):
    """
    Make Gemini API request with retries and proper error handling.
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
                st.warning(f"Retrying Gemini request (attempt {attempt + 2}/3)...")
                time.sleep(2 ** attempt)
        raise Exception("Failed to get valid response from Gemini API after all retries")

    except Exception as e:
        st.error(f"Error making Gemini request: {str(e)}")
        raise


def load_promotional_content():
    """Loads promotional content from text files in the 'pr' folder."""
    import random
    pr_folder = os.path.join(os.path.dirname(__file__), "pr")
    if not os.path.isdir(pr_folder):
        return ""

    promo_files = [f for f in os.listdir(pr_folder) if f.endswith(".txt")]
    if not promo_files:
        return ""

    promo_files = ["None"] + promo_files
    selected_promo = "None"
    promotional_text = None
    return promotional_text


def clean_source_content(content):
    """Clean source content by handling special characters and escape sequences"""
    content = content.replace(r'!\[', '![')
    content = content.replace(r'\[', '[')
    content = content.replace(r'\]', ']')
    content = content.replace(r'\(', '(')
    content = content.replace(r'\)', ')')
    return content


def get_promotional_image(promotional_text):
    """
    Get the promotional image URL based on the promotional text.
    Returns empty string if no matching image found.
    """
    return PROMOTIONAL_IMAGES.get(promotional_text, {}).get("url", "")


def generate_article(client, transcripts, keywords=None, news_angle=None, section_count=3, promotional_text=None,
                     selected_site=None):
    """
    Generates a comprehensive news article in Thai using the Gemini API.
    Uses the extracted source content (via Jina) in the prompt.
    Returns a JSON-structured article following the Article schema.
    Handles media content (images and Twitter/X embeds) extracted from source articles.
    """
    try:
        if not transcripts:
            return None
        if promotional_text is None:
            promotional_text = ""

        keyword_list = keywords if keywords else []
        primary_keyword = keyword_list[0] if keyword_list else ""
        secondary_keywords = ", ".join(keyword_list[1:]) if len(keyword_list) > 1 else ""

        # Extract media content from transcripts
        images = []
        twitter_embeds = []
        source_texts = ""
        seen_sources = set()
        for t in transcripts:
            content = clean_source_content(t.get('content') or "")
            source = t.get('source', 'Unknown')

            # Extract media if available
            if 'media' in t:
                if 'images' in t['media'] and t['media']['images']:
                    images.extend(t['media']['images'])
                if 'twitter_embeds' in t['media'] and t['media']['twitter_embeds']:
                    twitter_embeds.extend(t['media']['twitter_embeds'])

            if source not in seen_sources:
                seen_sources.add(source)
                source_texts += f"\n---\nSource: {source}\nURL: {t.get('url', '')}\n\n{content}\n---\n"
            else:
                source_texts += f"\n{content}\n"

        # Prepare media instructions for the prompt
        media_instructions = ""
        if images or twitter_embeds:
            media_instructions = "\nMedia Content:\n"
            if images:
                media_instructions += "1. Images to include:\n"
                for i, img in enumerate(images):
                    media_instructions += f" Image {i + 1}: URL: {img['url']}\n"
                    media_instructions += f" Alt Text: {img['alt_text']}\n"
                    if img.get('context'):
                        media_instructions += f" Context: {img['context']}\n"
                media_instructions += " Instructions: Place these images at appropriate locations within relevant paragraphs.\n"
            if twitter_embeds:
                media_instructions += "\n2. Twitter/X Posts to Embed:\n"
                for i, embed in enumerate(twitter_embeds):
                    media_instructions += f" Embed {i + 1}: {embed['url']}\n"
                    if embed.get('context'):
                        media_instructions += f" Context: {embed['context']}\n"
                media_instructions += " Instructions: Embed these Twitter/X posts at appropriate locations within the article.\n"

        promo_instructions = f'''The LAST section (before conclusion) MUST be dedicated to this promotional content: {promotional_text}. This section should:
- Naturally flow with the article
- Mention {primary_keyword} at least twice
- Include the following promotional image: {get_promotional_image(promotional_text)} in the first paragraph
- Use a format that best presents the content (paragraph, list, or table)''' if promotional_text else ''

        prompt = f'''
You are an expert Thai crypto journalist and SEO specialist. Using ONLY the exact source content provided below, craft an SEO-optimized article in Thai.
DO NOT invent or modify any factual details. Your article must faithfully reflect the provided source text.
Keep technical terms and entity names in English but the rest should be in Thai.

Primary Keyword: {primary_keyword}
Secondary Keywords: {secondary_keywords}
News Angle: {news_angle}

SEO Guidelines:
1. Primary Keyword ({primary_keyword}) Distribution:
    - Title: Include naturally in the first half (1x)
    - First Paragraph: Include naturally (1x)
    - H2 Headings: Include in at least 2 headings
    - Body content: Include naturally 5 times where relevant
    - Meta Description: Include naturally (1x)
    - Maintain original form (Thai/English) consistently but make sure it makes sense as part of sentence structure.
2. Secondary Keywords ({secondary_keywords}) Usage:
    - Include in 2 H2 headings where relevant
    - Use naturally in supporting paragraphs
    - Maximum density: 3% (3 mentions per 100 words)

{media_instructions}
{promo_instructions}

Structure your output as valid JSON with the following keys:
- title: An engaging and click-worthy title (max 60 characters) with {primary_keyword} in first half.
- content: An object with:
    - intro: Two-part introduction:
        - Part 1 (meta description): Compelling 160-character that will also represent as Meta Description with {primary_keyword} included. This part must be click-worthy and stimulate curiosity
        - Part 2: another paragraph that expands on the introduction, providing overview of the article.
    - sections: An array of exactly {section_count} objects, each with:
        - heading: H2 heading using power words (include {primary_keyword} and {secondary_keywords} where natural). Ensure the heading reads naturally for Thai readers.
        - format: Choose the most appropriate format for this section:
            - 'paragraph': For explanatory content (default). Each section MUST have 2-3 detailed paragraphs (at least 3-4 sentences each) with in-depth analysis, data points, examples, and thorough explanations.
            - 'list': For steps, features, or benefits. Each list item MUST be comprehensive with 2-3 sentences of explanation. Use numbers for the list.
            - 'table': For comparisons or data. Each cell MUST contain detailed explanations (2-3 sentences) with context and examples.
        - media: If applicable, include image URLs or Twitter embeds that should be placed within this section.
    - conclusion: A concluding paragraph summarizing the key points of the article while mentioning the {primary_keyword} naturally.
- sources: An array of objects with keys "domain" and "url" for each source.
- media: An object with:
    - images: Array of image objects with url, alt_text, and placement (which section to place in).
        * **Relevancy is Key:** Select ONLY 2-3 images that are HIGHLY RELEVANT to the article's main content and news angle. Focus on images that directly illustrate key data points, events, or concepts discussed in the article.
        * **Context Analysis:** Analyze the text immediately surrounding each image (captions, preceding and following paragraphs) to determine its relevance. Images should visually reinforce the textual content and provide added understanding or evidence.
        * **Avoid Logos & Irrelevant Graphics:** Do NOT include logos. Focus on images that are integral to understanding the news story, such as charts, graphs, or photos directly related to the main content.
    - twitter_embeds: Array of Twitter/X embed objects with url and placement
- seo: An object with keys:
    - slug: English URL-friendly slug that MUST include {primary_keyword}{' and end with "-thailand"' if selected_site in ["BITCOINIST", "NEWSBTC"] else ''}
    - metaTitle: Thai title with {primary_keyword}
    - metaDescription: Use the same text as the Part 1 of the intro.
    - excerpt: One Thai sentence summary
    - imagePrompt: The Image Prompt must be in English only. Create a photorealistic scene that fits the article, focusing on 1-2 main objects.
    - altText: Thai ALT text with {primary_keyword} while keeping technical terms and entities in English

Ensure {primary_keyword} appears exactly once in title, metaTitle, and metaDescription.

IMPORTANT NOTES:
1. Content Balance Guidelines:
    - Main Content (70%): Focus on news, analysis, and key information.
    - Promotional Content (30%): Integrate promotional content naturally.
2. Promotional Content Integration:
    - Create a dedicated section for promotional content that transitions smoothly. Keep technical terms and entity names in English but the rest should be in Thai.
    - To ensure the section is semantically related to the main content, find a way to mention the {primary_keyword} naturally in the section.
3. Media Integration Guidelines:
    - Place images near relevant content that relates to the image.
4. General Guidelines:
    - Maintain consistent tone and style.
    - Preserve any image markdown exactly as provided.

Below is the source content (in markdown):
{source_texts}

Return ONLY valid JSON, no additional commentary.
        '''
        with st.expander("Prompt being sent to Gemini API", expanded=False):
            st.code(prompt, language='python')

        response = make_gemini_request(client, prompt)
        if not response:
            return {}

        if isinstance(response, dict):
            response = json.dumps(response)

        try:
            content = json.loads(response)
            if isinstance(content, list):
                content = content[0]
            if content else {}:
                pass
            if not isinstance(content, dict):
                st.error("Response is not a valid dictionary")
                return {}

            if 'title' not in content:
                content['title'] = f"Latest News about {primary_keyword}"
            if 'content' not in content:
                content['content'] = {}
            if 'sections' not in content['content']:
                content['content']['sections'] = []
            for section in content['content'].get('sections', []):
                if 'format' not in section:
                    section['format'] = 'paragraph'
                if 'paragraphs' not in section:
                    section['paragraphs'] = []
            if 'conclusion' not in content['content']:
                content['content']['conclusion'] = 'บทความนี้นำเสนอข้อมูลเกี่ยวกับ ' + primary_keyword + ' ซึ่งเป็นประเด็นสำคัญในตลาดคริปโตที่ควรติดตาม'

            seo_field = next((k for k in content.keys() if k.lower() == 'seo'), 'seo')
            if seo_field not in content:
                content[seo_field] = {
                    'slug': primary_keyword.lower().replace(' ', '-'),
                    'metaTitle': f"Latest Updates on {primary_keyword}",
                    'metaDescription': content.get('content', {}).get('intro', {}).get('Part 1',
                                                                                        f"Latest news and updates about {primary_keyword}"),
                    'excerpt': f"Stay updated with the latest {primary_keyword} developments",
                    'imagePrompt': f"A photorealistic scene showing {primary_keyword} in a professional setting",
                    'altText': f"{primary_keyword} latest updates and developments"
                }
            return content

        except json.JSONDecodeError as e:
            st.error(f"JSON parsing error: {str(e)}")
            st.error("Raw response:")
            st.code(response)
            return {}

    except Exception as e:
        st.error(f"Error generating article: {str(e)}")
        return {}
    finally:
        if promotional_text:
            image_url = get_promotional_image(promotional_text)
            if image_url:
                content['media']['images'].append({
                    'url': image_url,
                    'alt': PROMOTIONAL_IMAGES.get(promotional_text, {}).get("alt", ""),
                    'width': PROMOTIONAL_IMAGES.get(promotional_text, {}).get("width", ""),
                    'height': PROMOTIONAL_IMAGES.get(promotional_text, {}).get("height", "")
                })
        return content


# ------------------------------
# Main App Function
# ------------------------------

def handle_browser_redirect():
    """Handles browser redirection to the edit URL if available."""
    if 'pending_edit_url' in st.session_state:
        import webbrowser
        try:
            webbrowser.open(st.session_state.pending_edit_url)
        except Exception as e:
            st.warning(f"Could not open browser automatically: {str(e)}")
        st.markdown(f"Please manually open this link: [{st.session_state.pending_edit_url}]({st.session_state.pending_edit_url})")
        del st.session_state.pending_edit_url  # Don't rerun here to prevent blank screen


def main():
    handle_browser_redirect()
    st.title("Article Generator and Publisher")

    default_url = ""
    default_keyword = "Bitcoin"
    default_news_angle = ""

    gemini_client = init_gemini_client()
    if not gemini_client:
        st.error("Failed to initialize Gemini client")
        return

    urls_input = st.sidebar.text_area("Enter URLs (one per line) to extract from:", value=default_url)
    keywords_input = st.sidebar.text_area("Keywords (one per line):", value=default_keyword, height=100)
    news_angle = st.sidebar.text_input("News Angle:", value=default_news_angle)
    section_count = st.sidebar.slider("Number of sections:", 2, 8, 3)
    additional_content = st.sidebar.text_area(
        "Additional Content", placeholder="Paste any extra content here. It will be treated as an additional source.",
        height=150)

    st.sidebar.header("Promotional Content")
    pr_folder = os.path.join(os.path.dirname(__file__), "pr")
    if os.path.isdir(pr_folder):
        promo_files = [f for f in os.listdir(pr_folder) if f.endswith(".txt")]
        if promo_files:
            promo_files = ["None"] + promo_files
            selected_promo = st.sidebar.selectbox("Select promotional content:", list(PROMOTIONAL_IMAGES.keys()) + ["None"])
            if selected_promo != "None":
                promotional_text = selected_promo
            else:
                promotional_text = None
        else:
            st.sidebar.warning("No promotional content files found in 'pr' folder")
            promotional_text = None
    else:
        st.sidebar.warning("'pr' folder not found")
        promotional_text = None

    st.sidebar.header("Select WordPress Site to Upload")
    sites = {
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
    site_options = list(sites.keys())
    selected_site = st.sidebar.selectbox("Choose a site:", site_options)
    wp_url = sites[selected_site]["url"]
    wp_username = sites[selected_site]["username"]
    wp_app_password = sites[selected_site]["password"]

    # Radio button to choose between Post or Page
    content_type_choice = st.sidebar.radio("Upload as:", ("Post", "Page"))

    messages_placeholder = st.empty()

    if st.sidebar.button("Generate Article"):
        transcripts = []
        if urls_input.strip():
            urls = [line.strip() for line in urls_input.splitlines() if line.strip()]
            for url in urls:
                extracted = extract_url_content(gemini_client, url, messages_placeholder)
                if extracted:
                    transcripts.append(extracted)
        if additional_content.strip():
            transcripts.append({
                'content': additional_content.strip(),
                'source': 'Additional Content',
                'url': ''
            })

        if not transcripts:
            st.error("Please provide either URLs or Additional Content to generate an article")
            return

        keywords = [k.strip() for k in keywords_input.splitlines() if k.strip()]

        if transcripts:
            article_content = generate_article(
                gemini_client,
                transcripts,
                keywords=keywords,
                news_angle=news_angle,
                section_count=section_count,
                promotional_text=promotional_text,
                selected_site=selected_site
            )

            if article_content:
                st.session_state.article = json.dumps(article_content, ensure_ascii=False, indent=2)
                st.success("Article generated successfully!")
            else:
                st.error("Failed to generate article.")
        else:
            st.error("No content extracted from provided URLs.")

    if "article" in st.session_state and st.session_state.article:
        st.subheader("Generated Article (JSON)")
        try:
            article_json = json.loads(st.session_state.article)
            st.json(article_json)

            # Display article with comprehensive error handling
            st.subheader("Article Content Preview")

            # Display title with validation
            title = article_json.get('title', 'Untitled Article')
            st.markdown(f"# {title}")
            st.markdown("")

            # Handle intro content
            content = article_json.get('content', {})
            intro = content.get('intro', '')
            if isinstance(intro, dict):
                st.markdown(intro.get('Part 1', 'Introduction Part 1'))
                st.markdown("")
                st.markdown(intro.get('Part 2', 'Introduction Part 2'))
            else:
                st.markdown(str(intro))
            st.markdown("")

            # Process sections with validation
            sections = content.get('sections', [])
            if not isinstance(sections, list):
                sections = []
            for i, section in enumerate(sections):
                if not isinstance(section, dict):
                    continue

                # Display section heading
                heading = section.get('heading', f'Section {i + 1}')
                st.markdown(f"## {heading}")
                st.markdown("")

                # Handle media with validation
                media = article_json.get('media', {})
                images = media.get('images', [])
                if isinstance(images, list):
                    section_images = [img for img in images if
                                      isinstance(img, dict) and img and img.get('placement', '').startswith(
                                          f'sections[{i}]')]
                    # Display images within the section
                    for img in section_images:
                        if img and img.get('url'):
                            st.image(img['url'], caption=img.get('alt_text', ''))
                        st.markdown("")

                # Handle section content with format validation
                format_type = section.get('format', 'paragraph')
                paragraphs = section.get('paragraphs', [])
                if not isinstance(paragraphs, list):
                    st.warning(f"Invalid paragraph format in section {i}. Expected list, got {type(paragraphs)}")
                    paragraphs = [str(paragraphs)]

                if not paragraphs:  # If paragraphs list is empty, check for 'content' key for paragraph format
                    section_content = section.get('content')
                    if section_content:
                        st.markdown(str(section_content))  # Display content from 'content' key
                        st.markdown("")
                    else:
                        st.markdown("*Content for this section is being processed.*")
                        st.markdown("")
                    continue

                try:
                    if format_type == 'list':
                        for item in paragraphs:
                            if not item:
                                continue
                            st.markdown(f"* {str(item)}")
                            st.markdown("")
                    elif format_type == 'table':
                        if paragraphs:
                            first_item = paragraphs[0]
                            if isinstance(first_item, str) and first_item.startswith('|'):
                                for row in paragraphs:
                                    if not row:
                                        continue
                                    st.markdown(str(row))
                            else:
                                try:
                                    import pandas as pd
                                    if isinstance(first_item, (list, tuple)):
                                        df = pd.DataFrame(paragraphs[1:], columns=first_item)
                                    elif isinstance(first_item, dict):
                                        df = pd.DataFrame(paragraphs)
                                    st.table(df)
                                except Exception as e:
                                    st.error(f"Error displaying table: {str(e)}")
                                    st.markdown("*Could not display table content*")
                            st.markdown("")
                    else:  # format_type == 'paragraph' or default
                        for para in paragraphs:
                            if not para:
                                continue
                            st.markdown(str(para))
                            st.markdown("")

                except Exception as e:
                    st.error(f"Error processing section content: {str(e)}")

                # Try to display Twitter embeds
                try:
                    if 'media' in article_json and 'twitter_embeds' in article_json['media']:
                        section_tweets = [tweet for tweet in article_json['media']['twitter_embeds'] if
                                          tweet.get('placement', '').startswith(f'sections[{i}]')]
                        for tweet in section_tweets:
                            if tweet.get('url'):
                                st.markdown(f"**Twitter/X Post**: {tweet['url']}")
                            st.markdown("")
                except Exception as e:
                    st.error(f"Error processing Twitter embeds: {str(e)}")

            # Display promotional content before conclusion
            if 'media' in article_json and 'images' in article_json['media']:
                remaining_images = [img for img in article_json['media']['images'] if 'placement' not in img or not any(
                    img.get('placement', '').startswith(f'sections[{j}]') for j in
                    range(len(article_json['content']['sections'])))]
                if remaining_images:
                    st.markdown("## Promotional Content")
                    st.markdown("")
                    for img in remaining_images:
                        if img and img.get('url'):
                            st.image(img['url'], caption=img.get('alt_text', ''))
                        st.markdown("")

            # Display remaining Twitter embeds if any
            if 'media' in article_json and 'twitter_embeds' in article_json['media']:
                remaining_tweets = [tweet for tweet in article_json['media']['twitter_embeds'] if
                                    'placement' not in tweet or not any(
                                        tweet.get('placement', '').startswith(f'sections[{j}]') for j in
                                        range(len(article_json['content']['sections'])))]
                if remaining_tweets:
                    for tweet in remaining_tweets:
                        if tweet.get('url'):
                            st.markdown(f"**Twitter/X Post**: {tweet['url']}")
                        st.markdown("")

            # Display conclusion
            st.markdown("## บทสรุป:")
            st.markdown(article_json['content']['conclusion'])

        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format: {str(e)}")
            st.text_area("Raw Content", value=st.session_state.article, height=300)

        if "article_data" not in st.session_state:
            st.session_state.article_data = {}
        if "processed_article" not in st.session_state.article_data:
            # Determine if we should add the affiliate note
            include_promotional = promotional_text is not None
            parsed = parse_article(st.session_state.article, add_affiliate_note=include_promotional)
            st.session_state.article_data["processed_article"] = parsed

        # Together AI Image Generation
        if "image" not in st.session_state.article_data:
            parsed_for_image = parse_article(st.session_state.article)
            image_prompt = parsed_for_image.get("image_prompt")
            alt_text = parsed_for_image.get("image_alt")

            if image_prompt:
                st.info(f"Original image prompt: '{image_prompt}'")
                image_prompt_english = re.sub(r'[\u0E00-\u0E7F]+', '', image_prompt).strip()
                if not image_prompt_english:
                    image_prompt_english = "A photo-realistic scene of cryptocurrencies floating in the air, depicting the Crypto news"
                    st.warning("Using fallback image prompt since no English text was found")
                st.info(f"Cleaned English prompt for Together AI: '{image_prompt_english}'")
            else:
                image_prompt_english = None

            if image_prompt_english:
                together_client = Together()
                try:
                    response = together_client.images.generate(
                        prompt=image_prompt_english,
                        model="black-forest-labs/FLUX.1-schnell-free",
                        width=1200,
                        height=800,
                        steps=4,
                        n=1,
                        response_format="b64_json"
                    )
                    if response and response.data and len(response.data) > 0:
                        b64_data = response.data[0].b64_json
                        if not alt_text:
                            primary_kw = keywords_input.splitlines()[0] if keywords_input.splitlines() else "Crypto"
                            alt_text = f"Featured image related to {primary_kw}"
                        st.image("data:image/png;base64," + b64_data, caption=alt_text)
                        st.session_state.article_data["image"] = {"b64_data": b64_data, "alt_text": alt_text,
                                                                   "media_id": None}
                    else:
                        st.error("Failed to generate supplementary image from Together AI.")
                except Exception as e:
                    st.error(f"Error generating supplementary image: {str(e)}")
            else:
                st.info("No valid image prompt found in generated article for supplementary image.")
        else:
            st.info("Using previously generated image.")

        # Create a separate column area for the upload button outside the Generate Article flow
        # This separation helps prevent the blank screen issue
        col1, col2 = st.columns([1, 1])

        # Place the upload button in its own column
        with col1:
            upload_button = st.button("Upload Article to WordPress")
            if upload_button:
                if not all([wp_url, wp_username, wp_app_password]):
                    st.error("Please ensure your .env file has valid credentials for the selected site.")
                else:
                    try:
                        with st.spinner("Processing article for upload..."):
                            # Verify we have processed article data
                            if "article_data" not in st.session_state or not st.session_state.article_data:
                                st.error("No article data found. Please generate the article first.")
                                return
                            if "processed_article" not in st.session_state.article_data or not st.session_state.article_data[
                                "processed_article"]:
                                st.error("Article hasn't been properly processed. Try regenerating the article.")
                                return

                            parsed = st.session_state.article_data["processed_article"]
                            if not parsed or not isinstance(parsed, dict):
                                st.error("Invalid article data format. Please regenerate the article.")
                                return

                            media_info = None
                            alt_text = ""
                            # Handle image upload with comprehensive error handling
                            try:
                                if "image" in st.session_state.article_data and st.session_state.article_data["image"]:
                                    image_data = st.session_state.article_data["image"]
                                    if image_data and isinstance(image_data, dict) and image_data.get("b64_data"):
                                        try:
                                            # Try to get alt text from article JSON first
                                            article_json = json.loads(st.session_state.article) if st.session_state.article else {}
                                            if isinstance(article_json, dict) and "seo" in article_json and isinstance(article_json["seo"], dict):
                                                alt_text = article_json["seo"].get("altText", "Generated Image")
                                            else:
                                                alt_text = image_data.get("alt_text", "Generated Image")
                                        except json.JSONDecodeError as e:
                                            st.warning(f"Could not parse article JSON for alt text: {str(e)}")
                                            alt_text = image_data.get("alt_text", "Generated Image")

                                        st.info(f"Uploading featured image with alt text: {alt_text}")
                                        media_info = upload_image_to_wordpress(
                                            image_data["b64_data"],
                                            wp_url,
                                            wp_username,
                                            wp_app_password,
                                            filename="generated_image.png",
                                            alt_text=alt_text
                                        )
                            except Exception as img_error:
                                st.warning(
                                    f"Error uploading image: {str(img_error)}. Continuing with article upload without featured image.")

                            # Prepare article data with validation
                            article_data = {
                                "main_title": parsed.get("main_title", "No Title"),
                                "main_content": parsed.get("main_content", ""),
                                "seo_slug": parsed.get("seo_slug", ""),
                                "excerpt": parsed.get("excerpt", ""),
                                "yoast_title": parsed.get("yoast_title", ""),
                                "yoast_metadesc": parsed.get("yoast_metadesc", ""),
                                "image": st.session_state.article_data.get("image", {}) if isinstance(
                                    st.session_state.article_data.get("image"), dict) else {}
                            }

                            # Add featured image if available
                            if media_info and isinstance(media_info, dict) and "media_id" in media_info:
                                article_data["image"]["media_id"] = media_info["media_id"]

                            # Get primary keyword for upload with validation
                            primary_keyword_upload = ""
                            if isinstance(keywords_input, str) and keywords_input.strip():
                                lines = keywords_input.splitlines()
                                if lines and lines[0].strip():
                                    primary_keyword_upload = lines[0].strip()

                            # Convert markdown to HTML with error handling
                            try:
                                if "main_content" in article_data and article_data["main_content"]:
                                    article_data["main_content"] = markdown.markdown(article_data["main_content"])
                            except Exception as md_error:
                                st.warning(
                                    f"Error converting markdown to HTML: {str(md_error)}. Using plain text instead.")

                            # Process content with promotional image and affiliate links
                            if selected_promo != "None" and selected_site:
                                try:
                                    article_data["main_content"] = process_affiliate_links(
                                        article_data["main_content"],
                                        selected_site,
                                        selected_promo  # Pass the selected promotional content name
                                    )
                                    st.success(f"Added promotional content for {selected_promo}")
                                except Exception as aff_error:
                                    st.warning(
                                        f"Error processing affiliate links: {str(aff_error)}. Continuing without promotional content.")

                            # Final validation before submission
                            if not article_data["main_content"] or not article_data["main_title"]:
                                st.error("Article content or title is empty. Cannot proceed with upload.")
                                return

                            # Submit article to WordPress
                            st.info("Submitting article to WordPress...")
                            result = submit_article_to_wordpress(
                                article_data,
                                wp_url,
                                wp_username,
                                wp_app_password,
                                primary_keyword=primary_keyword_upload,
                                site_name=selected_site,
                                content_type=content_type_choice  # Pass selected content type ("Post" or "Page")
                            )
                            if not result:
                                st.error("Upload failed. Please check the error messages above.")

                    except Exception as e:
                        st.error(f"Error during upload process: {str(e)}")
                        # Add logging for debugging
                        import traceback
                        st.error(f"Error details: {traceback.format_exc()}")

        # In the second column, we can add other controls or information
        with col2:
            if "pending_edit_url" in st.session_state:
                st.success("Article uploaded successfully!")
                st.markdown(f"[Edit your article]({st.session_state.pending_edit_url})")


if __name__ == "__main__":
    main()
