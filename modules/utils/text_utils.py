"""Text processing utilities."""
import re
import json
import streamlit as st

def parse_article(article_json, add_affiliate_note=False):
    """
    Parses the generated article JSON into structured elements with robust error handling.
    Returns a dict with keys needed for WordPress upload.
    If add_affiliate_note=True, append the affiliate disclosure shortcode after the conclusion.
    
    Args:
        article_json: JSON representation of the article (string or dict)
        add_affiliate_note: Whether to add the affiliate disclosure note
        
    Returns:
        dict: Structured article data for WordPress upload
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
                            # Handle list/tuple based table
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
                # Clean up any temporary resources
                pass
                
        # Handle conclusion
        conclusion = content.get('conclusion', 'Article conclusion.')
        content_parts.append(str(conclusion))

        # If user included promotional content, add the affiliate disclosure note
        if add_affiliate_note:
            content_parts.append("[su_note note_color=\"#FEFEEE\"] เรามุ่งมั่นในการสร้างความโปร่งใสอย่างเต็มที่กับผู้อ่านของเรา บางเนื้อหาในเว็บไซต์อาจมีลิงก์พันธมิตร ซึ่งเราอาจได้รับค่าคอมมิชชั่นจากความร่วมมือเหล่านี้ [/su_note]")

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

def construct_endpoint(wp_url, endpoint_path):
    """
    Construct the WordPress endpoint.
    
    Args:
        wp_url (str): Base WordPress URL
        endpoint_path (str): API endpoint path
        
    Returns:
        str: Complete endpoint URL
    """
    wp_url = wp_url.rstrip('/')
    # Skip adding /th for Bitcoinist and NewsBTC
    if not any(domain in wp_url for domain in ["bitcoinist.com", "newsbtc.com"]) and "/th" not in wp_url:
        wp_url += "/th"
    return f"{wp_url}{endpoint_path}"
