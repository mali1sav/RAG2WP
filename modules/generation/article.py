"""Article generation functionality."""
import json
import re
import streamlit as st
from modules.generation.gemini import make_gemini_request
from modules.generation.validation import fix_thai_json, contains_thai_text, sanitize_json_strings

def clean_source_content(content):
    """
    Clean and prepare source content for processing.
    """
    if not content:
        return ""
    # Remove extra whitespace and normalize line endings
    content = re.sub(r'\s+', ' ', content).strip()
    # Remove any control characters
    content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\t')
    return content

def prepare_source_data(transcripts):
    """
    Prepare source data from transcripts for prompt generation.
    
    Args:
        transcripts (list): List of transcript objects
        
    Returns:
        tuple: (str, list, list) - source_texts, images, twitter_embeds
    """
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
            
    return source_texts, images, twitter_embeds

def generate_article(client, transcripts, keywords=None, news_angle=None, section_count=3, promotional_text=None, selected_site=None):
    """
    Generates a comprehensive news article in Thai using the Gemini API.
    
    Args:
        client (dict): Initialized Gemini client
        transcripts (list): List of transcript objects
        keywords (list): Keywords for SEO
        news_angle (str): The news angle for the article
        section_count (int): Number of sections in the article
        promotional_text (str): Promotional content to include
        selected_site (str): The site that will publish the article
        
    Returns:
        dict: Generated article content
    """
    try:
        if not transcripts:
            return None
            
        from modules.generation.image import generate_images_for_article
            
        # Prepare keywords
        keyword_list = keywords if keywords else []
        primary_keyword = keyword_list[0] if keyword_list else ""
        secondary_keywords = ", ".join(keyword_list[1:]) if len(keyword_list) > 1 else ""
        
        # Prepare source data
        source_texts, images, twitter_embeds = prepare_source_data(transcripts)
        
        # Generate the prompt
        from modules.generation.prompts import generate_article_prompt
        prompt_params = {
            'source_texts': source_texts,
            'primary_keyword': primary_keyword,
            'secondary_keywords': secondary_keywords,
            'news_angle': news_angle,
            'section_count': section_count,
            'promotional_text': promotional_text,
            'selected_site': selected_site,
            'images': images,
            'twitter_embeds': twitter_embeds
        }
        prompt = generate_article_prompt(prompt_params)
        
        # Display the prompt in an expander
        with st.expander("Prompt being sent to Gemini API", expanded=False):
            st.code(prompt, language='python')
            
        # Make the request to Gemini
        response = make_gemini_request(
            client,
            prompt,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 4096,
                # Removed unsupported parameters
                # Using JSON parsing in make_gemini_request instead
            }
        )
        if not response:
            return {}
            
        # Convert response to JSON if it's not already
        if isinstance(response, dict):
            response = json.dumps(response)
            
        # Parse and validate the response
        try:
            # Check for Thai content first for specialized handling
            if contains_thai_text(response):
                st.info("Detected Thai content in the response, applying specialized fixes")
                fixed_response = fix_thai_json(response)
                try:
                    content = json.loads(fixed_response)
                    st.success("Fixed Thai JSON structure successfully")
                    return content
                except json.JSONDecodeError as e:
                    st.warning(f"Thai-specific fixes not sufficient, will try generic approaches: {str(e)}")
            
            # Check for the specific pattern of intro object without closing brace
            intro_missing_close = re.search(r'\{\s*"title".*"content"\s*:\s*\{\s*"intro"\s*:\s*\{\s*"Part 1"\s*:.*"Part 2"\s*:.*\}\s*$', response, re.DOTALL)
            if intro_missing_close:
                # Direct fix: add the missing closing braces and ensure the JSON is complete
                fixed_response = response + "}}}" 
                try:
                    content = json.loads(fixed_response)
                    st.success("Fixed incomplete intro object structure")
                    return content
                except json.JSONDecodeError:
                    # Continue with other fixes if this specific fix didn't work
                    pass
            
            # Try sanitizing the JSON strings first using our comprehensive sanitizer
            st.info("Sanitizing JSON strings for special characters...")
            # Import here to ensure it's available
            from modules.generation.validation import sanitize_json_strings
            sanitized_response = sanitize_json_strings(response)
            try:
                content = json.loads(sanitized_response)
                st.success("Successfully sanitized JSON with special characters")
                return content
            except json.JSONDecodeError as e:
                st.warning(f"Sanitization alone was not sufficient, trying more specific fixes: {str(e)}")
                # Continue with more specific fixes
                pass
                    
            # First try to parse as-is
            try:
                content = json.loads(response)
            except json.JSONDecodeError as e:
                # Try to fix incomplete JSON structure
                st.warning(f"Trying to fix incomplete JSON: {str(e)}")
                
                # Check for $ sign issues (especially in Thai cryptocurrencies)
                dollar_match = re.search(r'([^\\])\$(\w+)', response)
                if dollar_match:
                    st.info("Detected unescaped $ sign in content, fixing...")
                    # Escape all unescaped $ signs
                    response = re.sub(r'([^\\])\$(\w+)', r'\1\\$\2', response)
                
                # Get error position information if available
                error_match = re.search(r'line (\d+) column (\d+) \(char (\d+)\)', str(e))
                if error_match:
                    line_num = int(error_match.group(1))
                    col_num = int(error_match.group(2))
                    char_pos = int(error_match.group(3))
                    
                    # Check context around the error
                    context_start = max(0, char_pos - 15)
                    context_end = min(len(response), char_pos + 15)
                    error_context = response[context_start:context_end]
                    
                    st.info(f"Error at line {line_num}, column {col_num}: ...{error_context}...")
                    
                    # Specific fix for comma errors
                    if "Expecting ',' delimiter" in str(e):
                        # Insert comma at the error location
                        fixed_response = response[:char_pos] + "," + response[char_pos:]
                        try:
                            content = json.loads(fixed_response)
                            st.success("Fixed by adding comma at error location")
                            return content
                        except json.JSONDecodeError:
                            # Continue with other fixes
                            response = fixed_response
                
                # Fix common formatting issues that might cause problems
                # 1. Check for dangling properties without commas
                response = re.sub(r'"([^"]+)"\s*:\s*"([^"]*?)"\s+"', '"\1": "\2", "', response)
                response = re.sub(r'"([^"]+)"\s*:\s*\{([^{}]*)\}\s+"', '"\1": {\2}, "', response)
                # Add more targeted fixes
                response = re.sub(r'("[^"]*")\s*("[^"]*")', r'\1, \2', response)  # Add comma between string values
                response = re.sub(r'(\})\s*(")', r'\1, \2', response)  # Add comma between } and "
                
                # 2. Fix objects without closing braces (particularly in nested objects)
                response = re.sub(r'\{([^{}]*)"([^"]+)"\s*:', '{\1"\2":', response)
                
                # Count opening and closing braces
                open_braces = response.count('{')
                close_braces = response.count('}')
                
                # Fix missing closing braces
                if open_braces > close_braces:
                    # Add missing closing braces
                    missing_braces = open_braces - close_braces
                    fixed_response = response + ('}' * missing_braces)
                    st.info(f"Added {missing_braces} missing closing braces to JSON")
                    
                    try:
                        # Try parsing with fixed braces
                        content = json.loads(fixed_response)
                    except json.JSONDecodeError as e2:
                        st.warning(f"First fix attempt failed: {str(e2)}")
                        
                        # Try more aggressive fixing:
                        # 1. Fix property patterns that are missing commas
                        fixed_response = re.sub(r'\}\s*"', '}, "', fixed_response)
                        fixed_response = re.sub(r'"\s*\{', '", {', fixed_response)
                        
                        # 2. Find unbalanced quotes
                        quote_count = fixed_response.count('"')
                        if quote_count % 2 != 0:
                            # Add a missing quote at the end of the last valid property
                            last_colon = fixed_response.rfind(':')
                            if last_colon > 0:
                                next_quote = fixed_response.find('"', last_colon)
                                next_brace = fixed_response.find('}', last_colon)
                                if next_quote == -1 or (next_brace > 0 and next_brace < next_quote):
                                    # Insert a quote before the next closing brace
                                    fixed_response = fixed_response[:next_brace] + '"' + fixed_response[next_brace:]
                        
                        try:
                            content = json.loads(fixed_response)
                            st.success("Successfully fixed JSON with advanced repairs")
                        except json.JSONDecodeError as e3:
                            # Last resort - try to extract and rebuild the JSON completely
                            from modules.generation.validation import clean_gemini_response, validate_article_json, sanitize_json_strings
                            
                            # First try the sanitizer
                            from modules.generation.validation import sanitize_json_strings
                            sanitized = sanitize_json_strings(response)
                            try:
                                content = json.loads(sanitized)
                                st.success("Fixed JSON using string sanitization")
                                return content
                            except json.JSONDecodeError:
                                # Then try the full validation approach
                                cleaned_json = clean_gemini_response(response)
                                # Also sanitize the cleaned JSON
                                cleaned_json = sanitize_json_strings(cleaned_json)
                                result = validate_article_json(cleaned_json)
                                if result:
                                    content = result
                                    st.success("Fixed JSON using validation module")
                            else:
                                st.error(f"Could not fix JSON: {str(e3)}")
                                st.code(response, language="json")
                                return {}
                else:
                    # Try to use the validation module to fix it
                    from modules.generation.validation import clean_gemini_response, validate_article_json, sanitize_json_strings
                    
                    # First try with just sanitizing
                    from modules.generation.validation import sanitize_json_strings
                    sanitized = sanitize_json_strings(response)
                    try:
                        content = json.loads(sanitized)
                        st.success("Fixed JSON using string sanitization")
                        return content
                    except json.JSONDecodeError:
                        # Then try the full validation pipeline
                        cleaned_json = clean_gemini_response(response)
                        # Also sanitize the cleaned result
                        cleaned_json = sanitize_json_strings(cleaned_json)
                        result = validate_article_json(cleaned_json)
                        if result:
                            content = result
                            st.success("Fixed JSON using validation module")
                    else:
                        st.error(f"JSON parsing error: {str(e)}")
                        st.code(response, language="json")
                        return {}
            
            if isinstance(content, list):
                content = content[0] if content else {}
            if not isinstance(content, dict):
                st.error("Response is not a valid dictionary")
                return {}
                
            # Ensure required fields exist
            if 'title' not in content:
                content['title'] = f"Latest News about {primary_keyword}"
            if 'content' not in content:
                content['content'] = {}
            if 'sections' not in content['content']:
                content['content']['sections'] = []
                
            # Ensure each section has proper format
            for section in content['content'].get('sections', []):
                if 'format' not in section:
                    section['format'] = 'paragraph'
                if 'paragraphs' not in section:
                    section['paragraphs'] = []
                    
            # Ensure conclusion exists
            if 'conclusion' not in content['content']:
                content['content']['conclusion'] = f'บทความนี้นำเสนอข้อมูลเกี่ยวกับ {primary_keyword} ซึ่งเป็นประเด็นสำคัญในตลาดคริปโตที่ควรติดตาม'
                
            # Ensure SEO fields exist
            seo_field = next((k for k in content.keys() if k.lower() == 'seo'), 'seo')
            if seo_field not in content:
                content[seo_field] = {
                    'slug': primary_keyword.lower().replace(' ', '-'),
                    'metaTitle': f"Latest Updates on {primary_keyword}",
                    'metaDescription': content.get('content', {}).get('intro', {}).get('Part 1', f"Latest news and updates about {primary_keyword}"),
                    'excerpt': f"Stay updated with the latest {primary_keyword} developments",
                    'imagePrompt': f"A photorealistic scene showing {primary_keyword} in a professional setting",
                    'altText': f"{primary_keyword} latest updates and developments"
                }
                
            # Add promotional image if applicable
            if promotional_text:
                from modules.generation.prompts import get_promotional_image
                from config.constants import PROMOTIONAL_IMAGES
                
                image_url = get_promotional_image(promotional_text)
                if image_url and 'media' in content:
                    if 'images' not in content['media']:
                        content['media']['images'] = []
                        
                    content['media']['images'].append({
                        'url': image_url,
                        'alt_text': PROMOTIONAL_IMAGES.get(promotional_text, {}).get("alt", ""),
                        'width': PROMOTIONAL_IMAGES.get(promotional_text, {}).get("width", ""),
                        'height': PROMOTIONAL_IMAGES.get(promotional_text, {}).get("height", "")
                    })
            
            # Generate article images using Together AI
            content = generate_images_for_article(content)
                    
            return content
            
        except json.JSONDecodeError as e:
            st.error(f"JSON parsing error: {str(e)}")
            st.error("Raw response:")
            st.code(response)
            return {}
    except Exception as e:
        st.error(f"Error generating article: {str(e)}")
        return {}

def combine_articles(primary_article, supplementary_articles, max_sections=8):
    """
    Combine a primary article with supplementary articles.
    
    Args:
        primary_article (dict): The main article
        supplementary_articles (list): List of additional articles to incorporate
        max_sections (int): Maximum number of sections in the final article
        
    Returns:
        dict: Combined article
    """
    if not primary_article:
        return primary_article
        
    if not supplementary_articles:
        return primary_article
        
    # Create a copy of primary article to avoid modifying the original
    combined = json.loads(json.dumps(primary_article))
    
    # Get or create necessary structures
    if 'content' not in combined:
        combined['content'] = {}
    if 'sections' not in combined['content']:
        combined['content']['sections'] = []
        
    primary_sections = combined['content']['sections']
    current_sections = len(primary_sections)
    
    # Add sections from supplementary articles up to max_sections
    sections_to_add = max_sections - current_sections
    if sections_to_add <= 0:
        return combined
        
    added_sections = 0
    for article in supplementary_articles:
        if not article or not isinstance(article, dict):
            continue
            
        if 'content' not in article or 'sections' not in article['content']:
            continue
            
        for section in article['content']['sections']:
            if added_sections >= sections_to_add:
                break
                
            # Skip duplicate headings
            if any(s.get('heading') == section.get('heading') for s in primary_sections):
                continue
                
            primary_sections.append(section)
            added_sections += 1
            
        if added_sections >= sections_to_add:
            break
            
    # Merge media content
    for article in supplementary_articles:
        if 'media' in article:
            if 'media' not in combined:
                combined['media'] = {}
                
            # Merge images
            if 'images' in article['media']:
                if 'images' not in combined['media']:
                    combined['media']['images'] = []
                    
                for img in article['media']['images']:
                    # Check if image already exists
                    if not any(i.get('url') == img.get('url') for i in combined['media']['images']):
                        combined['media']['images'].append(img)
                        
            # Merge twitter embeds
            if 'twitter_embeds' in article['media']:
                if 'twitter_embeds' not in combined['media']:
                    combined['media']['twitter_embeds'] = []
                    
                for tweet in article['media']['twitter_embeds']:
                    # Check if tweet already exists
                    if not any(t.get('url') == tweet.get('url') for t in combined['media']['twitter_embeds']):
                        combined['media']['twitter_embeds'].append(tweet)
    
    return combined
