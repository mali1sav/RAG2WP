"""HTML processing utilities."""
import re
import json
import streamlit as st
from config.constants import AFFILIATE_LINKS, PROMOTIONAL_IMAGES

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

def escape_special_chars(text):
    """Escape special characters that might interfere with Markdown formatting."""
    text = re.sub(r'(?<!\$)\$(?!\$)', r'\$', text)
    chars_to_escape = ['*', '_', '`', '#', '~', '|', '<', '>', '[', ']']
    for char in chars_to_escape:
        text = text.replace(char, '\\' + char)
    return text

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
