"""
Article Generator and Publisher - Main Streamlit Application

This application allows users to:
1. Extract content from URLs or pasted text
2. Generate SEO-optimized articles using Gemini
3. Generate promotional images using Together AI
4. Upload articles to different WordPress sites
"""
import json
import os
import webbrowser
import streamlit as st
import markdown
from config.settings import WORDPRESS_SITES
from config.constants import DEFAULT_KEYWORD, DEFAULT_NEWS_ANGLE, DEFAULT_SECTION_COUNT, DEFAULT_URL, PROMOTIONAL_IMAGES
from modules.generation.gemini import init_gemini_client
from modules.content_extraction.web_extract import extract_url_content
from modules.generation.article import generate_article
from modules.utils.text_utils import parse_article
from modules.wordpress.api import submit_article_to_wordpress
from modules.wordpress.uploader import upload_image_to_wordpress
from modules.image.together_ai import generate_image_from_prompt
from modules.wordpress.converter import markdown_to_html

def handle_browser_redirect():
    """Handle redirecting to edit URL after WordPress upload."""
    if 'pending_edit_url' in st.session_state:
        try:
            webbrowser.open(st.session_state.pending_edit_url)
        except Exception as e:
            st.warning(f"Could not open browser automatically: {str(e)}")
            st.markdown(f"Please manually open this link: [{st.session_state.pending_edit_url}]({st.session_state.pending_edit_url})")
        del st.session_state.pending_edit_url
        # Don't rerun here to prevent blank screen

def load_promotional_content():
    """Load promotional content options."""
    pr_folder = os.path.join(os.path.dirname(__file__), "pr")
    if os.path.isdir(pr_folder):
        promo_files = [f for f in os.listdir(pr_folder) if f.endswith(".txt")]
        if promo_files:
            return list(PROMOTIONAL_IMAGES.keys()) + ["None"]
    return ["None"]

def render_article_preview(article_json):
    """Render a preview of the generated article."""
    try:
        st.subheader("Article Content Preview")
        
        # Display title
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
        
        # Process sections
        sections = content.get('sections', [])
        if not isinstance(sections, list):
            sections = []
            
        for i, section in enumerate(sections):
            if not isinstance(section, dict):
                continue
                
            # Display section heading
            heading = section.get('heading', f'Section {i+1}')
            st.markdown(f"## {heading}")
            st.markdown("")
            
            # Handle media
            media = article_json.get('media', {})
            images = media.get('images', [])
            if isinstance(images, list):
                section_images = [img for img in images
                                if isinstance(img, dict) and img and 
                                img.get('placement', '').startswith(f'sections[{i}]')]
                for img in section_images:
                    if img and img.get('url'):
                        st.image(img['url'], caption=img.get('alt_text', ''))
                        st.markdown("")
            
            # Handle section content based on format
            format_type = section.get('format', 'paragraph')
            paragraphs = section.get('paragraphs', [])
            
            if not isinstance(paragraphs, list):
                st.warning(f"Invalid paragraph format in section {i}.")
                paragraphs = [str(paragraphs)]
                
            if not paragraphs:
                section_content = section.get('content')
                if section_content:
                    st.markdown(str(section_content))
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
                else: # paragraph format
                    for para in paragraphs:
                        if not para:
                            continue
                        st.markdown(str(para))
                        st.markdown("")
            except Exception as e:
                st.error(f"Error processing section content: {str(e)}")
                
            # Display Twitter embeds
            try:
                if 'twitter_embeds' in media:
                    section_tweets = [tweet for tweet in media['twitter_embeds']
                                    if tweet.get('placement', '').startswith(f'sections[{i}]')]
                    for tweet in section_tweets:
                        if tweet.get('url'):
                            st.markdown(f"**Twitter/X Post**: {tweet['url']}")
                            st.markdown("")
            except Exception as e:
                st.error(f"Error processing Twitter embeds: {str(e)}")
                
        # Display promotional content before conclusion
        if 'media' in article_json and 'images' in article_json['media']:
            remaining_images = [img for img in article_json['media']['images']
                              if 'placement' not in img or
                              not any(img.get('placement', '').startswith(f'sections[{j}]')
                                    for j in range(len(article_json['content']['sections'])))]
                                    
            if remaining_images:
                st.markdown("## Promotional Content")
                st.markdown("")
                for img in remaining_images:
                    if img and img.get('url'):
                        st.image(img['url'], caption=img.get('alt_text', ''))
                        st.markdown("")
                        
        # Display remaining Twitter embeds if any
        if 'media' in article_json and 'twitter_embeds' in article_json['media']:
            remaining_tweets = [tweet for tweet in article_json['media']['twitter_embeds']
                              if 'placement' not in tweet or
                              not any(tweet.get('placement', '').startswith(f'sections[{j}]')
                                    for j in range(len(article_json['content']['sections'])))]
                                    
            if remaining_tweets:
                for tweet in remaining_tweets:
                    if tweet.get('url'):
                        st.markdown(f"**Twitter/X Post**: {tweet['url']}")
                        st.markdown("")
                        
        # Display conclusion
        st.markdown("## บทสรุป:")
        st.markdown(article_json['content']['conclusion'])
        
    except Exception as e:
        st.error(f"Error rendering article preview: {str(e)}")
        st.text_area("Raw Content", value=json.dumps(article_json, indent=2), height=300)

def main():
    """Main application function."""
    # Handle redirect if needed
    handle_browser_redirect()
    
    st.title("Article Generator and Publisher")
    
    # Initialize Gemini client
    gemini_client = init_gemini_client()
    if not gemini_client:
        st.error("Failed to initialize Gemini client. Please check your API keys.")
        return
        
    # Sidebar inputs
    with st.sidebar:
        st.header("Article Generation")
        urls_input = st.text_area("Enter URLs (one per line):", value=DEFAULT_URL)
        keywords_input = st.text_area("Keywords (one per line):", value=DEFAULT_KEYWORD, height=100)
        news_angle = st.text_input("News Angle:", value=DEFAULT_NEWS_ANGLE)
        section_count = st.slider("Number of sections:", 2, 8, DEFAULT_SECTION_COUNT)
        
        additional_content = st.text_area(
            "Additional Content",
            placeholder="Paste any extra content here. It will be treated as an additional source.",
            height=150
        )
        
        st.header("Promotional Content")
        promo_options = load_promotional_content()
        selected_promo = st.selectbox("Select promotional content:", promo_options)
        promotional_text = selected_promo if selected_promo != "None" else None
        
        st.header("WordPress Upload")
        site_options = list(WORDPRESS_SITES.keys())
        selected_site = st.selectbox("Choose a site:", site_options)
        content_type_choice = st.radio("Upload as:", ("Post", "Page"))
        
        generate_button = st.button("Generate Article")
    
    # Main content area
    messages_placeholder = st.empty()
    
    if generate_button:
        with st.spinner("Extracting content and generating article..."):
            transcripts = []
            
            # Extract content from URLs
            if urls_input.strip():
                urls = [line.strip() for line in urls_input.splitlines() if line.strip()]
                for url in urls:
                    extracted = extract_url_content(gemini_client, url, messages_placeholder)
                    if extracted:
                        transcripts.append(extracted)
                        
            # Add additional content if provided
            if additional_content.strip():
                transcripts.append({
                    'content': additional_content.strip(),
                    'source': 'Additional Content',
                    'url': ''
                })
                
            # Validate we have content to work with
            if not transcripts:
                st.error("Please provide either URLs or Additional Content to generate an article")
                return
                
            # Process keywords
            keywords = [k.strip() for k in keywords_input.splitlines() if k.strip()]
            
            # Generate the article
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
                return
    
    # Display generated article if available
    if "article" in st.session_state and st.session_state.article:
        st.subheader("Generated Article (JSON)")
        try:
            article_json = json.loads(st.session_state.article)
            with st.expander("View JSON", expanded=False):
                st.json(article_json)
            
            # Render article preview
            render_article_preview(article_json)
            
            # Parse article for WordPress
            if "article_data" not in st.session_state:
                st.session_state.article_data = {}
                
            if "processed_article" not in st.session_state.article_data:
                include_promotional = promotional_text is not None
                parsed = parse_article(st.session_state.article, add_affiliate_note=include_promotional)
                st.session_state.article_data["processed_article"] = parsed
            
            # Generate image if not already done
            if "image" not in st.session_state.article_data:
                parsed_for_image = parse_article(st.session_state.article)
                image_prompt = parsed_for_image.get("image_prompt")
                alt_text = parsed_for_image.get("image_alt")
                
                if image_prompt:
                    st.info(f"Generating image with prompt: '{image_prompt}'")
                    image_data = generate_image_from_prompt(image_prompt, alt_text)
                    if image_data:
                        st.session_state.article_data["image"] = image_data
                    else:
                        st.warning("Failed to generate image. Will proceed without one.")
                else:
                    st.info("No image prompt found in generated article.")
            
            # Create a separate column area for the upload button
            col1, col2 = st.columns([1, 1])
            
            with col1:
                upload_button = st.button("Upload Article to WordPress")
                
                if upload_button:
                    wp_site = WORDPRESS_SITES[selected_site]
                    wp_url = wp_site["url"]
                    wp_username = wp_site["username"]
                    wp_app_password = wp_site["password"]
                    
                    if not all([wp_url, wp_username, wp_app_password]):
                        st.error("Please ensure your .env file has valid credentials for the selected site.")
                        return
                        
                    with st.spinner("Uploading article to WordPress..."):
                        # Verify we have processed article data
                        if "article_data" not in st.session_state or not st.session_state.article_data:
                            st.error("No article data found. Please generate the article first.")
                            return
                            
                        if "processed_article" not in st.session_state.article_data:
                            st.error("Article hasn't been properly processed. Try regenerating the article.")
                            return
                            
                        parsed = st.session_state.article_data["processed_article"]
                        
                        # Upload image if available
                        media_info = None
                        try:
                            if "image" in st.session_state.article_data and st.session_state.article_data["image"]:
                                image_data = st.session_state.article_data["image"]
                                if image_data and "b64_data" in image_data:
                                    alt_text = image_data.get("alt_text", "Generated Image")
                                    st.info(f"Uploading featured image with alt text: {alt_text}")
                                    media_info = upload_image_to_wordpress(
                                        image_data["b64_data"],
                                        wp_url,
                                        wp_username,
                                        wp_app_password,
                                        alt_text=alt_text
                                    )
                        except Exception as img_error:
                            st.warning(f"Error uploading image: {str(img_error)}. Continuing without featured image.")
                        
                        # Prepare article data
                        article_data = {
                            "main_title": parsed.get("main_title", "No Title"),
                            "main_content": parsed.get("main_content", ""),
                            "seo_slug": parsed.get("seo_slug", ""),
                            "excerpt": parsed.get("excerpt", ""),
                            "yoast_title": parsed.get("yoast_title", ""),
                            "yoast_metadesc": parsed.get("yoast_metadesc", ""),
                            "image": st.session_state.article_data.get("image", {})
                        }
                        
                        # Add featured image if available
                        if media_info and "media_id" in media_info:
                            article_data["image"]["media_id"] = media_info["media_id"]
                            
                        # Get primary keyword for upload
                        primary_keyword_upload = ""
                        if keywords_input.strip():
                            lines = keywords_input.splitlines()
                            if lines and lines[0].strip():
                                primary_keyword_upload = lines[0].strip()
                                
                        # Convert markdown to HTML
                        try:
                            if "main_content" in article_data and article_data["main_content"]:
                                article_data["main_content"] = markdown_to_html(article_data["main_content"])
                        except Exception as md_error:
                            st.warning(f"Error converting markdown to HTML: {str(md_error)}. Using plain text.")
                            
                        # Submit article to WordPress
                        st.info("Submitting article to WordPress...")
                        result = submit_article_to_wordpress(
                            article_data,
                            wp_url,
                            wp_username,
                            wp_app_password,
                            primary_keyword=primary_keyword_upload,
                            site_name=selected_site,
                            content_type=content_type_choice
                        )
                        
                        if not result:
                            st.error("Upload failed. Please check the error messages above.")
            
            # Display edit link if available
            with col2:
                if "pending_edit_url" in st.session_state:
                    st.success("Article uploaded successfully!")
                    st.markdown(f"[Edit your article]({st.session_state.pending_edit_url})")
                    
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format: {str(e)}")
            st.text_area("Raw Content", value=st.session_state.article, height=300)

if __name__ == "__main__":
    main()
