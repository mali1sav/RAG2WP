"""WordPress API client functions."""
import requests
import streamlit as st
import logging
from requests.auth import HTTPBasicAuth
from modules.utils.text_utils import construct_endpoint
from config.constants import SITE_EDIT_URLS

def submit_article_to_wordpress(article, wp_url, username, wp_app_password, primary_keyword="", site_name=None, content_type="post"):
    """
    Submits the article to WordPress using the WP REST API.
    
    Args:
        article (dict): Article content and metadata
        wp_url (str): WordPress site URL
        username (str): WordPress username
        wp_app_password (str): WordPress application password
        primary_keyword (str): Main keyword for categories/tags
        site_name (str): Site name for affiliate linking
        content_type (str): "post" or "page"
        
    Returns:
        dict or None: WordPress API response or None on failure
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
            from modules.utils.html_utils import process_affiliate_links
            content = process_affiliate_links(content, site_name)

        # Convert to Gutenberg format if it's a post
        if content_type.lower() == "post":
            from modules.utils.html_utils import convert_to_gutenberg_format
            content = convert_to_gutenberg_format(content)

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

            # Always generate and display the edit URL for every article
            edit_url = SITE_EDIT_URLS.get(site_name, f"{wp_url.rstrip('/')}/wp-admin/post.php?post={{post_id}}&action=edit&classic-editor").format(post_id=post_id)
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
