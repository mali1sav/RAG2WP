"""
WordPress content conversion utilities.
Handles conversion between Markdown, HTML, and Gutenberg blocks.
"""
import re
import json
import logging
import streamlit as st

def markdown_to_html(markdown_content):
    """
    Convert markdown content to HTML.
    
    Args:
        markdown_content (str): Markdown formatted content
        
    Returns:
        str: HTML formatted content
    """
    try:
        import markdown
        html_content = markdown.markdown(markdown_content)
        return html_content
    except Exception as e:
        logging.error(f"Error converting markdown to HTML: {str(e)}")
        st.warning(f"Markdown conversion failed: {str(e)}. Using plain text.")
        return markdown_content

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
            for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'img', 'figure', 'blockquote', 'table', 'pre']):
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    # Get heading level and convert to proper Gutenberg heading
                    level = int(element.name[1])
                    if level == 1:
                        # H1 is typically handled as the post title, not content
                        gutenberg_content.append('<!-- wp:heading -->')
                        gutenberg_content.append(f'<h2>{element.get_text()}</h2>')
                        gutenberg_content.append('<!-- /wp:heading -->')
                    else:
                        # For h2-h6
                        gutenberg_content.append(f'<!-- wp:heading {{"level":{level}}} -->')
                        gutenberg_content.append(f'<h{level}>{element.get_text()}</h{level}>')
                        gutenberg_content.append(f'<!-- /wp:heading -->')
                
                elif element.name == 'p':
                    # Process paragraphs
                    if element.find('img'):
                        # If paragraph contains an image, handle it separately
                        for img in element.find_all('img'):
                            gutenberg_content.append('<!-- wp:image -->')
                            gutenberg_content.append(f'<figure class="wp-block-image"><img src="{img.get("src", "")}" alt="{img.get("alt", "")}" /></figure>')
                            gutenberg_content.append('<!-- /wp:image -->')
                            
                            # Remove the img from paragraph
                            img.decompose()
                    
                    # Only add paragraph if it has content after removing images
                    if element.get_text().strip():
                        gutenberg_content.append('<!-- wp:paragraph -->')
                        gutenberg_content.append(f'<p>{element.decode_contents()}</p>')
                        gutenberg_content.append('<!-- /wp:paragraph -->')
                
                elif element.name == 'blockquote':
                    # Process blockquotes
                    gutenberg_content.append('<!-- wp:quote -->')
                    gutenberg_content.append(f'<blockquote class="wp-block-quote">{str(element.decode_contents())}</blockquote>')
                    gutenberg_content.append('<!-- /wp:quote -->')
                
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
                
                elif element.name == 'pre':
                    # Process code blocks
                    code = element.find('code')
                    if code:
                        language = code.get('class', [''])[0].replace('language-', '') if code.get('class') else ''
                        gutenberg_content.append(f'<!-- wp:code {{"language":"{language}"}} -->')
                        gutenberg_content.append(f'<pre class="wp-block-code"><code>{code.get_text()}</code></pre>')
                        gutenberg_content.append('<!-- /wp:code -->')
                    else:
                        gutenberg_content.append('<!-- wp:preformatted -->')
                        gutenberg_content.append(f'<pre class="wp-block-preformatted">{element.get_text()}</pre>')
                        gutenberg_content.append('<!-- /wp:preformatted -->')
                
                elif element.name == 'table':
                    # Process tables
                    gutenberg_content.append('<!-- wp:table -->')
                    gutenberg_content.append(f'<figure class="wp-block-table"><table>{str(element.decode_contents())}</table></figure>')
                    gutenberg_content.append('<!-- /wp:table -->')
                
                elif element.name == 'img':
                    # Process standalone images
                    align = 'center' if 'aligncenter' in element.get('class', []) else ''
                    attrs = {}
                    if align:
                        attrs['align'] = align
                    
                    gutenberg_content.append(f'<!-- wp:image {json.dumps(attrs)} -->')
                    gutenberg_content.append(f'<figure class="wp-block-image{" align" + align if align else ""}">{str(element)}</figure>')
                    gutenberg_content.append('<!-- /wp:image -->')
                
                elif element.name == 'figure':
                    # Process figure elements (which may contain images)
                    img = element.find('img')
                    if img:
                        align = 'center' if 'aligncenter' in element.get('class', []) else ''
                        attrs = {}
                        if align:
                            attrs['align'] = align
                        
                        caption = element.find('figcaption')
                        caption_text = caption.get_text() if caption else ""
                        
                        gutenberg_content.append(f'<!-- wp:image {json.dumps(attrs)} -->')
                        if caption_text:
                            gutenberg_content.append(f'<figure class="wp-block-image{" align" + align if align else ""}"><img src="{img.get("src", "")}" alt="{img.get("alt", "")}"/><figcaption>{caption_text}</figcaption></figure>')
                        else:
                            gutenberg_content.append(f'<figure class="wp-block-image{" align" + align if align else ""}"><img src="{img.get("src", "")}" alt="{img.get("alt", "")}"/></figure>')
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
            heading_pattern = r'<h([1-6])[^>]*>(.*?)</h\1>'
            for match in re.finditer(heading_pattern, content, re.DOTALL):
                level = match.group(1)
                heading_text = re.sub(r'<.*?>', '', match.group(2))  # Remove any HTML tags inside heading
                
                if level == '1':
                    # Convert h1 to h2 for consistency
                    gutenberg_content.append('<!-- wp:heading -->')
                    gutenberg_content.append(f'<h2>{heading_text}</h2>')
                    gutenberg_content.append('<!-- /wp:heading -->')
                else:
                    # For h2-h6
                    gutenberg_content.append(f'<!-- wp:heading {{"level":{level}}} -->')
                    gutenberg_content.append(f'<h{level}>{heading_text}</h{level}>')
                    gutenberg_content.append(f'<!-- /wp:heading -->')
            
            # Process paragraphs
            paragraph_pattern = r'<p[^>]*>(.*?)</p>'
            for match in re.finditer(paragraph_pattern, content, re.DOTALL):
                paragraph_content = match.group(1)
                # Skip if it's just an image container
                if re.search(r'^\s*<img[^>]*>\s*$', paragraph_content):
                    continue
                gutenberg_content.append('<!-- wp:paragraph -->')
                gutenberg_content.append(f'<p>{paragraph_content}</p>')
                gutenberg_content.append('<!-- /wp:paragraph -->')
            
            # Process images
            image_pattern = r'<img[^>]*src="([^"]*)"[^>]*>'
            for match in re.finditer(image_pattern, content):
                img_tag = match.group(0)
                # Extract alt text
                alt_match = re.search(r'alt="([^"]*)"', img_tag)
                alt_text = alt_match.group(1) if alt_match else ""
                
                gutenberg_content.append('<!-- wp:image -->')
                gutenberg_content.append(f'<figure class="wp-block-image"><img src="{match.group(1)}" alt="{alt_text}" /></figure>')
                gutenberg_content.append('<!-- /wp:image -->')
            
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
            
            # Process blockquotes
            blockquote_pattern = r'<blockquote[^>]*>(.*?)</blockquote>'
            for match in re.finditer(blockquote_pattern, content, re.DOTALL):
                blockquote_content = match.group(1)
                gutenberg_content.append('<!-- wp:quote -->')
                gutenberg_content.append(f'<blockquote class="wp-block-quote">{blockquote_content}</blockquote>')
                gutenberg_content.append('<!-- /wp:quote -->')
            
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

def html_to_plain_text(html_content):
    """
    Convert HTML to plain text by removing all HTML tags.
    
    Args:
        html_content (str): HTML formatted content
        
    Returns:
        str: Plain text content
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_content)
    # Handle HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def create_excerpt(content, max_length=155):
    """
    Create an excerpt from content, limited to a certain length.
    
    Args:
        content (str): Content to create excerpt from
        max_length (int): Maximum length of the excerpt
        
    Returns:
        str: Excerpt limited to max_length
    """
    # If content is HTML, convert to plain text first
    if '<' in content and '>' in content:
        content = html_to_plain_text(content)
    
    # Limit to max_length
    if len(content) <= max_length:
        return content
    
    # Truncate at last complete sentence or word
    excerpt = content[:max_length]
    
    # Try to find the last complete sentence
    last_period = excerpt.rfind('.')
    last_question = excerpt.rfind('?')
    last_exclamation = excerpt.rfind('!')
    
    last_sentence_end = max(last_period, last_question, last_exclamation)
    
    if last_sentence_end > 0:
        # Return the excerpt up to the last sentence end
        return excerpt[:last_sentence_end + 1]
    else:
        # Otherwise find the last complete word
        last_space = excerpt.rfind(' ')
        if last_space > 0:
            return excerpt[:last_space] + "..."
        else:
            return excerpt + "..."
