"""JSON validation and cleaning utilities."""
import re
import json
import streamlit as st
import tenacity
from typing import Dict

@tenacity.retry(
    stop=tenacity.stop_after_attempt(5),
    wait=tenacity.wait_exponential(multiplier=1, min=4, max=20),
    retry=tenacity.retry_if_exception_type((Exception)),
    retry_error_callback=lambda retry_state: None
)
def clean_gemini_response(text):
    """Clean Gemini response to extract valid JSON."""
    # First try to extract JSON from code blocks
    json_match = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', text)
    if json_match:
        extracted_json = json_match.group(1).strip()
        return fix_json_structure(extracted_json)
        
    # Then try to find JSON pattern in the text
    json_match = re.search(r'({[\s\S]*?})', text)
    if json_match:
        extracted_json = json_match.group(1).strip()
        return fix_json_structure(extracted_json)
        
    # Remove code markers
    text = re.sub(r'```(?:json)?\s*|```', '', text)
    text = text.strip()
    
    # If we couldn't extract JSON, fix the whole text
    return fix_json_structure(text)

def fix_json_structure(text):
    """Fix common JSON structure issues and ensure proper formatting."""
    # Special case for intro objects missing closing braces (common pattern in Thai content)
    intro_missing_close = re.search(r'\{\s*"title".*"content"\s*:\s*\{\s*"intro"\s*:\s*\{\s*"Part 1"\s*:.*"Part 2"\s*:.*\}\s*$', text, re.DOTALL)
    if intro_missing_close:
        # Add missing closing braces and return immediately
        fixed_text = text + "}}}" 
        try:
            # Verify it's now valid
            json.loads(fixed_text)
            return fixed_text
        except json.JSONDecodeError:
            # Continue with other fixes
            pass
    
    # Ensure the text starts with { and ends with }
    if not text.startswith('{'):
        text = '{' + text
    
    # Fix common JSON syntax errors
    # 1. Fix missing commas between properties
    text = re.sub(r'"([^"]+)"\s*:\s*"([^"]*)"\s+"', '"\1": "\2", "', text)
    text = re.sub(r'"([^"]+)"\s*:\s*\{([^{}]*)\}\s+"', '"\1": {\2}, "', text)
    
    # 2. Fix line breaks without commas
    text = re.sub(r'}\s*\n\s*"', '}, "', text)
    text = re.sub(r'"\s*\n\s*{', '", {', text)
    
    # 3. Fix issues with nested objects missing closing braces
    # Find all nested objects by examining brace balance
    stack = []
    fixed_text = ""
    in_string = False
    fixed_positions = []
    
    for i, char in enumerate(text):
        fixed_text += char
        
        # Handle string context to avoid misinterpreting braces in strings
        if char == '"' and (i == 0 or text[i-1] != '\\'):
            in_string = not in_string
            
        if not in_string:
            if char == '{':
                stack.append(i)
            elif char == '}':
                if stack:
                    stack.pop()
                else:
                    # This is an unmatched closing brace, we'll remove it later
                    fixed_positions.append(i)
    
    # Remove any positions marked for fixing (unmatched closing braces)
    if fixed_positions:
        for pos in reversed(fixed_positions):
            fixed_text = fixed_text[:pos] + fixed_text[pos+1:]
    
    # Complete the JSON by adding any missing closing braces
    if stack:
        fixed_text += '}' * len(stack)
    
    # Ensure it ends with a closing brace if needed
    if not fixed_text.endswith('}'):
        fixed_text += '}'
    
    # Try to fix Thai content with special characters
    try:
        # Check if we can parse it
        json.loads(fixed_text)
        return fixed_text
    except json.JSONDecodeError as e:
        # Get error position
        error_line = str(e)
        match = re.search(r'char (\d+)', error_line)
        if match:
            pos = int(match.group(1))
            # Check if there's a Thai character nearby that might be causing issues
            nearby = fixed_text[max(0, pos-10):min(len(fixed_text), pos+10)]
            if re.search(r'[\u0E00-\u0E7F]', nearby):  # Thai Unicode range
                # Add proper escaping around Thai characters
                for i in range(max(0, pos-5), min(len(fixed_text), pos+5)):
                    if i < len(fixed_text) and 0xE00 <= ord(fixed_text[i]) <= 0xE7F:
                        # Ensure this Thai character is properly contained in quotes
                        if not is_in_quotes(fixed_text, i):
                            # This is a complex case - let's use a more general approach instead
                            return create_safe_json_from_parts(fixed_text)
        
        # If all else fails, try to extract valid parts and rebuild
        return create_safe_json_from_parts(fixed_text)
        
def is_in_quotes(text, pos):
    """Check if the character at position pos is inside a valid string."""
    quote_positions = [i for i, char in enumerate(text) if char == '"' and (i == 0 or text[i-1] != '\\')]
    if not quote_positions:
        return False
        
    # Group quote positions into pairs
    pairs = []
    for i in range(0, len(quote_positions) - 1, 2):
        if i + 1 < len(quote_positions):
            pairs.append((quote_positions[i], quote_positions[i+1]))
    
    # Check if pos is within any pair
    for start, end in pairs:
        if start < pos < end:
            return True
    return False

def create_safe_json_from_parts(text):
    """Create a safe JSON structure by extracting valid parts."""
    # Extract title if present
    title_match = re.search(r'"title"\s*:\s*"([^"]*)"', text)
    title = title_match.group(1) if title_match else "Untitled Article"
    
    # Try to extract content parts
    content = {}
    
    # Extract intro if present
    intro_match = re.search(r'"intro"\s*:\s*\{([^{}]*)\}', text)
    if intro_match:
        intro_text = intro_match.group(1)
        part1_match = re.search(r'"Part 1"\s*:\s*"([^"]*)"', intro_text)
        part2_match = re.search(r'"Part 2"\s*:\s*"([^"]*)"', intro_text)
        
        if part1_match or part2_match:
            content['intro'] = {}
            if part1_match:
                content['intro']['Part 1'] = part1_match.group(1)
            if part2_match:
                content['intro']['Part 2'] = part2_match.group(1)
    
    # Create a minimum viable JSON structure
    result = {
        "title": title,
        "content": content
    }
    
    return json.dumps(result)

def validate_article_json(json_str) -> Dict:
    """Validate article JSON against schema and return cleaned data."""
    data = {}
    
    # First sanitize JSON strings to handle special characters like $
    sanitized_json = sanitize_json_strings(json_str)
    try:
        data = json.loads(sanitized_json)
        st.success("Successfully sanitized JSON with special characters")
        # We have valid JSON, continue with validation
    except json.JSONDecodeError:
        # Continue with more specific fixes if sanitizing alone doesn't work
        # Check if this is Thai content that needs special handling
        if contains_thai_text(json_str):
            st.info("Detected Thai content, applying specialized fixes")
            # Apply Thai-specific JSON fixes
            fixed_json = fix_thai_json(json_str)
            # Also sanitize the fixed JSON
            fixed_json = sanitize_json_strings(fixed_json)
            try:
                data = json.loads(fixed_json)
                st.success("Successfully fixed Thai JSON structure")
                # We have valid JSON, continue with validation
            except json.JSONDecodeError as e:
                st.warning(f"Thai-specific fixes not sufficient: {str(e)}")
                # Try more general fixes
                try:
                    # Try to fix common JSON formatting issues
                    st.warning(f"Attempting to fix JSON structure")
                    
                    # Fix missing closing braces
                    open_braces = json_str.count('{')
                    close_braces = json_str.count('}')
                    fixed_json = json_str.strip()
                    
                    if open_braces > close_braces:
                        # Add missing closing braces
                        missing_braces = open_braces - close_braces
                        fixed_json += ('}' * missing_braces)
                        st.info(f"Added {missing_braces} missing closing braces")
                    else:
                        # Try adding a single closing brace if needed
                        if not fixed_json.endswith('}'):
                            fixed_json += '}'
                            
                    # Try to fix common JSON issues like missing commas
                    fixed_json = re.sub(r'"\s*\n\s*"', '", "', fixed_json)  # Add missing commas between key-value pairs
                    fixed_json = re.sub(r'\}\s*\n\s*"', '}, "', fixed_json)  # Add missing commas after objects
                    fixed_json = re.sub(r'\}\s*\n\s*\{', '}, {', fixed_json)  # Add missing commas between objects
                    
                    try:
                        data = json.loads(fixed_json)
                        st.success("Successfully fixed JSON structure")
                    except json.JSONDecodeError as e2:
                        st.error(f"Could not fix JSON structure: {str(e2)}")
                        st.code(json_str, language="json")
                        return {}
                except Exception as e:
                    st.error(f"Error during JSON repair: {str(e)}")
                    return {}
        else:
            # If not Thai content, apply general fixes
            try:
                # Try to fix common JSON formatting issues
                st.warning("Attempting to fix general JSON structure issues")
                
                # Fix missing closing braces
                open_braces = json_str.count('{')
                close_braces = json_str.count('}')
                fixed_json = json_str.strip()
                
                if open_braces > close_braces:
                    # Add missing closing braces
                    missing_braces = open_braces - close_braces
                    fixed_json += ('}' * missing_braces)
                    st.info(f"Added {missing_braces} missing closing braces")
                
                # Try to fix common JSON issues like missing commas
                fixed_json = re.sub(r'"\s*\n\s*"', '", "', fixed_json)  # Add missing commas between key-value pairs
                fixed_json = re.sub(r'\}\s*\n\s*"', '}, "', fixed_json)  # Add missing commas after objects
                fixed_json = re.sub(r'\}\s*\n\s*\{', '}, {', fixed_json)  # Add missing commas between objects
                
                try:
                    data = json.loads(fixed_json)
                    st.success("Successfully fixed general JSON structure")
                except json.JSONDecodeError as e2:
                    st.error(f"Could not fix JSON structure: {str(e2)}")
                    st.code(json_str, language="json")
                    return {}
            except Exception as e:
                st.error(f"Error during general JSON repair: {str(e)}")
                return {}
        
        # Handle list or non-dict data
        if isinstance(data, list):
            data = next((item for item in data if isinstance(item, dict)), {})
        elif not isinstance(data, dict):
            data = {}
            
        if not data:
            st.error("Empty or invalid article data")
            return {}
            
        # Validate and auto-fix content structure
        if not data.get('content'):
            data['content'] = {}
            
        content = data['content']
        if isinstance(content.get('intro'), dict):
            content['introduction'] = content.pop('intro')
        elif not content.get('introduction'):
            content['introduction'] = content.get('intro', "")
            
        if 'sections' not in content:
            content['sections'] = []
            
        if 'conclusion' not in content:
            content['conclusion'] = ""
            
        # Ensure SEO structure exists
        if 'seo' not in data:
            data['seo'] = {}
            if data.get('title'):
                data['seo'].update({
                    'slug': re.sub(r'[^\w\s-]', '', data['title'].lower()).replace(' ', '-'),
                    'metaTitle': data['title'],
                    'metaDescription': str(content.get('introduction', {})).strip()[:155],
                    'excerpt': str(content.get('introduction', {})).strip()[:100],
                    'imagePrompt': "",
                    'altText': data['title']
                })
                
        # Ensure media structure exists
        if 'media' not in data:
            data['media'] = {'images': [], 'twitter_embeds': []}
            
        return data
            
    except Exception as e:
        st.error(f"Error validating article data: {str(e)}")
        st.code(json_str, language="json")
        return {}
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {str(e)}")
        st.code(json_str, language="json")
        return {}
    except ValueError as e:
        st.error(f"Validation error: {str(e)}")
        return {}

def contains_thai_text(text):
    """Check if the text contains Thai language characters."""
    # Thai Unicode range: \u0E00-\u0E7F
    return bool(re.search(r'[\u0E00-\u0E7F]', text))

def fix_thai_json(json_str):
    """Apply specific fixes for Thai JSON content which often has incomplete structure."""
    if not contains_thai_text(json_str):
        return json_str
    
    # Pre-process: Escape dollar signs in Thai content
    # This fix handles issues where $ in Thai content like "$MEMEX" causes JSON parsing problems
    dollar_sign_pattern = re.compile(r'(\$\w+)(?=[^"]*")')
    json_str = dollar_sign_pattern.sub(r'\\\1', json_str)  # Escape $ with \
    
    # Fix 1: Handle the specific pattern with intro object missing closing brace
    intro_pattern = re.search(r'\{\s*"title".*"content"\s*:\s*\{\s*"intro"\s*:\s*\{\s*"Part 1"\s*:.*"Part 2"\s*:.*\}\s*$', json_str, re.DOTALL)
    if intro_pattern:
        return json_str + "}}}"  # Add closing braces for intro, content, and main object
    
    # Fix 2: Check if we have any incomplete objects with Thai content
    for match in re.finditer(r'"([^"]+)"\s*:\s*\{([^}]*)$', json_str, re.MULTILINE):
        key = match.group(1)
        value = match.group(2)
        if contains_thai_text(value) and not value.endswith("}"):
            # Found an incomplete Thai object
            pos = match.end()
            json_str = json_str[:pos] + "}" + json_str[pos:]
    
    # Fix 3: Add missing commas between properties in nested objects
    # This regex looks for patterns like "key": "value"
    # followed by "key2": "value2" without a comma
    json_str = re.sub(r'("[^"]+"\s*:\s*"[^"]*")\s*("[^"]+")', r'\1,\2', json_str)
    
    # Fix 4: Add missing commas after closing braces in nested objects
    # This regex looks for patterns like } followed by "key": without a comma
    json_str = re.sub(r'(\})\s*("[^"]+"\s*:)', r'\1,\2', json_str)
    
    # Fix 5: Handle specific case of missing comma after nested object
    # This targets the pattern in the error message (line 7 column 6)
    json_str = re.sub(r'(\})\s*\n\s*("[^"]+")', r'\1,\n\2', json_str)
    
    # Fix 6: Add missing commas between sections and after nested objects
    json_str = re.sub(r'(\})\s*\n\s*([^\s\{\}])', r'\1,\n\2', json_str)
    
    # Fix 7: Handle specific error for Thai content with missing commas before sections
    # This specifically handles the case where a nested object like 'intro' is followed by other properties
    json_str = re.sub(r'("intro"\s*:\s*\{[^\}]+\})\s*("[^"]+")', r'\1,\2', json_str)
    
    # Fix 8: Balance braces overall
    open_count = json_str.count('{')
    close_count = json_str.count('}')
    if open_count > close_count:
        json_str = json_str + ('}' * (open_count - close_count))
    
    return json_str
def sanitize_json_strings(json_str):
    """Sanitize and escape problematic characters in JSON strings."""
    # Pattern to find all string literals in JSON
    string_pattern = re.compile(r'"([^"]*)"')
    
    # Define problematic characters and their replacements
    replacements = [
        # Escape dollar sign in cryptocurrency symbols
        (r'(?<=[^\\])\$(\w+)', r'\\$\1'),
        # Escape all dollar signs more aggressively - especially for Thai content
        (r'\$', r'\\$'),
        # Fix other problematic characters if needed
        (r'(?<=[^\\])\\(?![\\"/bfnrt])', r'\\\\')
    ]
    
    def replace_in_string(match):
        # Get the string content without quotes
        content = match.group(1)
        
        # Apply all replacements to the string content
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
            
        # Return the fixed string with quotes
        return f'"{content}"'
    
    # Apply replacements to all string literals in the JSON
    sanitized = string_pattern.sub(replace_in_string, json_str)
    
    # Also fix missing commas between properties at the top level
    sanitized = re.sub(r'("[^"]+"\s*:\s*"[^"]*")\s*("[^"]+"\s*:)', r'\1,\2', sanitized)
    
    return sanitized
