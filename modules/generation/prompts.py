"""
Templates and utilities for article generation prompts.
This module contains functions to build structured prompts for the LLM.
"""
from config.constants import PROMOTIONAL_IMAGES

def get_promotional_image(promotional_text):
    """
    Get the promotional image URL based on the promotional text.
    
    Args:
        promotional_text (str): Name of the promotional content
        
    Returns:
        str: URL of the promotional image, or empty string if not found
    """
    return PROMOTIONAL_IMAGES.get(promotional_text, {}).get("url", "")

def build_seo_guidelines(primary_keyword, secondary_keywords):
    """
    Create SEO guideline instructions for article generation.
    
    Args:
        primary_keyword (str): The main keyword for SEO
        secondary_keywords (str): Comma-separated secondary keywords
        
    Returns:
        str: Formatted SEO guidelines
    """
    return f"""
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
"""

def build_promotional_instructions(promotional_text, primary_keyword):
    """
    Create instructions for promotional content integration.
    
    Args:
        promotional_text (str): The promotional content to integrate
        primary_keyword (str): The main keyword for SEO
        
    Returns:
        str: Formatted promotional instructions or empty string if no promotion
    """
    if not promotional_text:
        return ""
        
    return f"""
The LAST section (before conclusion) MUST be dedicated to this promotional content: {promotional_text}. This section should:
- Naturally flow with the article
- Mention {primary_keyword} at least twice
- Include the following promotional image: {get_promotional_image(promotional_text)} in the first paragraph
- Use a format that best presents the content (paragraph, list, or table)
"""

def build_media_instructions(images, twitter_embeds):
    """
    Create instructions for media content integration.
    
    Args:
        images (list): List of image objects to include
        twitter_embeds (list): List of Twitter embed objects to include
        
    Returns:
        str: Formatted media instructions or empty string if no media
    """
    if not (images or twitter_embeds):
        return ""
        
    media_instructions = "\nMedia Content:\n"
    
    if images:
        media_instructions += "1. Images to include:\n"
        for i, img in enumerate(images):
            media_instructions += f"   Image {i+1}: URL: {img['url']}\n"
            media_instructions += f"   Alt Text: {img.get('alt_text', '')}\n"
            if img.get('context'):
                media_instructions += f"   Context: {img['context']}\n"
        media_instructions += "   Instructions: Place these images at appropriate locations within relevant paragraphs.\n"
    
    if twitter_embeds:
        media_instructions += "\n2. Twitter/X Posts to Embed:\n"
        for i, embed in enumerate(twitter_embeds):
            media_instructions += f"   Embed {i+1}: {embed['url']}\n"
            if embed.get('context'):
                media_instructions += f"   Context: {embed['context']}\n"
        media_instructions += "   Instructions: Embed these Twitter/X posts at appropriate locations within the article.\n"
    
    return media_instructions

def build_output_structure_guidelines(primary_keyword, section_count, selected_site):
    """
    Create guidelines for the expected output structure.
    
    Args:
        primary_keyword (str): The main keyword for SEO
        section_count (int): Number of sections in the article
        selected_site (str): The site that will publish the article
        
    Returns:
        str: Formatted structure guidelines
    """
    thailand_suffix = ' and end with "-thailand"' if selected_site in ["BITCOINIST", "NEWSBTC"] else ''
    
    return f"""
Structure your output as valid JSON with the following keys:
- title: An engaging and click-worthy title (max 60 characters) with {primary_keyword} in first half.
- content: An object with:
   - intro: Two-part introduction:
     - Part 1 (meta description): Compelling 160-character that will also represent as Meta Description with {primary_keyword} included. This part must be click-worthy and stimulate curiosity
     - Part 2: another paragraph that expands on the introduction, providing overview of the article.
   - sections: An array of exactly {section_count} objects, each with:
     - heading: H2 heading using power words (include {primary_keyword} where natural)
     - format: Choose the most appropriate format for this section:
       - 'paragraph': For explanatory content (default). Each section MUST have 2-3 detailed paragraphs (at least 3-4 sentences each).
       - 'list': For steps, features, or benefits. Each list item MUST be comprehensive with 2-3 sentences of explanation.
       - 'table': For comparisons or data. Each cell MUST contain detailed explanations (2-3 sentences).
     - media: If applicable, include image URLs or Twitter embeds that should be placed within this section.
   - conclusion: A concluding paragraph summarizing key points while mentioning {primary_keyword} naturally.
- sources: An array of objects with keys "domain" and "url" for each source.
- media: An object with:
   - images: Array of image objects with url, alt_text, and placement (which section to place in).
   - twitter_embeds: Array of Twitter/X embed objects with url and placement
- seo: An object with keys:
   - slug: English URL-friendly slug that MUST include {primary_keyword}{thailand_suffix}
   - metaTitle: Thai title with {primary_keyword}
   - metaDescription: Use the same text as the Part 1 of the intro.
   - excerpt: One Thai sentence summary
   - imagePrompt: The Image Prompt must be in English only. Create a photorealistic scene that fits the article.
   - altText: Thai ALT text with {primary_keyword} while keeping technical terms in English
"""

def build_content_guidelines():
    """
    Create general content guidelines for the article.
    
    Returns:
        str: Formatted content guidelines
    """
    return """
IMPORTANT NOTES:
1. Content Balance Guidelines:
   - Main Content (70%): Focus on news, analysis, and key information.
   - Promotional Content (30%): Integrate promotional content naturally if provided.
2. Media Integration Guidelines:
   - Place images near relevant content that relates to the image.
3. General Guidelines:
   - Maintain consistent tone and style.
   - Preserve any image markdown exactly as provided.
   - Keep technical terms and entity names in English but the rest should be in Thai.
"""

def generate_article_prompt(params):
    """
    Generate a complete prompt for article creation.
    
    Args:
        params (dict): Parameters for prompt generation with the following keys:
            - source_texts (str): Source content to base the article on
            - primary_keyword (str): Main SEO keyword
            - secondary_keywords (str): Additional SEO keywords
            - news_angle (str): Angle for the article
            - section_count (int): Number of sections
            - promotional_text (str): Promotional content to include
            - selected_site (str): Publishing site
            - images (list): List of images to include
            - twitter_embeds (list): List of Twitter embeds to include
            
    Returns:
        str: Complete prompt for the LLM
    """
    # Extract parameters with defaults
    source_texts = params.get('source_texts', '')
    primary_keyword = params.get('primary_keyword', '')
    secondary_keywords = params.get('secondary_keywords', '')
    news_angle = params.get('news_angle', '')
    section_count = params.get('section_count', 3)
    promotional_text = params.get('promotional_text', '')
    selected_site = params.get('selected_site', '')
    images = params.get('images', [])
    twitter_embeds = params.get('twitter_embeds', [])
    
    # Build prompt components
    seo_guidelines = build_seo_guidelines(primary_keyword, secondary_keywords)
    media_instructions = build_media_instructions(images, twitter_embeds)
    promotional_instructions = build_promotional_instructions(promotional_text, primary_keyword)
    output_structure = build_output_structure_guidelines(primary_keyword, section_count, selected_site)
    content_guidelines = build_content_guidelines()
    
    # Combine into full prompt
    prompt = f"""
You are an expert Thai crypto journalist and SEO specialist. Using ONLY the exact source content provided below, craft an SEO-optimized article in Thai. DO NOT invent or modify any factual details. Your article must faithfully reflect the provided source text.

Primary Keyword: {primary_keyword}
Secondary Keywords: {secondary_keywords}
News Angle: {news_angle}

{seo_guidelines}
{media_instructions}
{promotional_instructions}
{output_structure}
{content_guidelines}

Below is the source content (in markdown):
{source_texts}

Return ONLY valid JSON, no additional commentary.
"""
    
    return prompt
