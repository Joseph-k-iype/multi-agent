# -*- coding: utf-8 -*-
"""
Formatter tools for the Multi-Agent RAG application.
These tools handle content formatting in different styles.

File: custom_tools/formatters.py
"""

import re
import html
import json
import logging
from typing import Dict, Any, Optional, List, Union

# Import decorator from langchain to make tools easily accessible
from langchain_core.tools import tool as lc_tool

# Set up logging
logger = logging.getLogger(__name__)

@lc_tool
def format_as_markdown(content: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format content as Markdown with customizable options.
    
    Args:
        content: The raw text content to format
        options: Optional formatting preferences
            - headings_level: starting level for headings (default: 2)
            - add_toc: whether to add table of contents (default: False)
            - code_style: style for code blocks (default: None)
    
    Returns:
        Dict containing the formatted content and metadata
    """
    options = options or {}
    headings_level = options.get("headings_level", 2)
    add_toc = options.get("add_toc", False)
    
    try:
        # Clean and normalize content
        content = content.strip()
        
        # Process structure (add headings if needed)
        if not any(line.strip().startswith('#') for line in content.split('\n')):
            # No headings found, attempt to add some based on paragraphs
            paragraphs = re.split(r'\n\s*\n', content)
            if len(paragraphs) > 3:
                # Try to create document structure
                structured_content = []
                
                # Add title if not present
                if not content.startswith('# '):
                    first_line = paragraphs[0].split('\n')[0]
                    # Use first line as title if it's short enough
                    if len(first_line) < 80:
                        structured_content.append(f"# {first_line}")
                        paragraphs[0] = '\n'.join(paragraphs[0].split('\n')[1:])
                    else:
                        # Create a generic title
                        structured_content.append("# Document")
                
                # Process remaining paragraphs
                current_section = []
                for i, para in enumerate(paragraphs):
                    lines = para.split('\n')
                    if len(lines) > 0 and len(lines[0]) < 80 and i > 0:
                        # This might be a heading
                        if current_section:
                            structured_content.append('\n'.join(current_section))
                            current_section = []
                        structured_content.append(f"{'#' * headings_level} {lines[0]}")
                        if len(lines) > 1:
                            current_section.extend(lines[1:])
                    else:
                        current_section.append(para)
                
                if current_section:
                    structured_content.append('\n'.join(current_section))
                
                content = '\n\n'.join(structured_content)
        
        # Add table of contents if requested
        if add_toc:
            headings = []
            for line in content.split('\n'):
                if line.strip().startswith('#'):
                    # Extract heading text and level
                    match = re.match(r'^(#+)\s+(.+)$', line.strip())
                    if match:
                        level = len(match.group(1))
                        text = match.group(2)
                        # Create anchor ID
                        anchor = text.lower().replace(' ', '-')
                        anchor = re.sub(r'[^\w-]', '', anchor)
                        headings.append((level, text, anchor))
            
            if headings:
                toc = ["## Table of Contents"]
                for level, text, anchor in headings:
                    # Skip the title and TOC itself
                    if text == "Table of Contents" or level == 1:
                        continue
                    indent = "  " * (level - 2)
                    toc.append(f"{indent}- [{text}](#{anchor})")
                
                # Find position after title to insert TOC
                lines = content.split('\n')
                title_index = -1
                for i, line in enumerate(lines):
                    if line.startswith('# '):
                        title_index = i
                        break
                
                if title_index >= 0:
                    # Insert after title
                    content = '\n'.join(lines[:title_index+1] + [''] + toc + [''] + lines[title_index+1:])
                else:
                    # Insert at beginning
                    content = '\n'.join(toc + [''] + lines)
        
        # Enhance code blocks with language hints if missing
        content = re.sub(r'```\n', '```plaintext\n', content)
        
        # Add horizontal rules between major sections
        content = re.sub(r'\n(#+)\s+', r'\n\n---\n\n\1 ', content)
        
        return {
            "formatted_content": content,
            "format": "markdown",
            "headings_count": len(re.findall(r'^#+\s+', content, re.MULTILINE)),
            "paragraphs_count": len(re.findall(r'\n\s*\n', content)) + 1
        }
    
    except Exception as e:
        logger.error(f"Error in markdown formatter: {e}")
        # Return the original content if something goes wrong
        return {
            "formatted_content": content,
            "format": "markdown",
            "error": str(e)
        }

@lc_tool
def format_as_html(content: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format content as HTML with customizable options.
    
    Args:
        content: The raw text or markdown content to convert to HTML
        options: Optional formatting preferences
            - title: document title (default: "Document")
            - add_styles: whether to add basic CSS (default: True)
            - theme: "light" or "dark" (default: "light")
    
    Returns:
        Dict containing the HTML content and metadata
    """
    options = options or {}
    title = options.get("title", "Document")
    add_styles = options.get("add_styles", True)
    theme = options.get("theme", "light")
    
    try:
        # Escape HTML in the content
        escaped_content = html.escape(content)
        
        # Determine if content is already in markdown
        is_markdown = any(line.strip().startswith('#') for line in content.split('\n'))
        
        html_content = []
        if add_styles:
            # Add CSS based on theme
            if theme == "dark":
                styles = """
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #121212; color: #e0e0e0; }
                    h1 { color: #bb86fc; }
                    h2, h3, h4 { color: #03dac6; }
                    a { color: #bb86fc; }
                    code { background-color: #1e1e1e; padding: 2px 4px; border-radius: 3px; }
                    pre { background-color: #1e1e1e; padding: 10px; border-radius: 5px; overflow-x: auto; }
                    blockquote { border-left: 4px solid #03dac6; margin-left: 0; padding-left: 15px; }
                    hr { border: none; height: 1px; background-color: #333; }
                    .container { max-width: 800px; margin: 0 auto; }
                </style>
                """
            else:
                styles = """
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }
                    h1 { color: #2c3e50; }
                    h2, h3, h4 { color: #3498db; }
                    a { color: #3498db; }
                    code { background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; }
                    pre { background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }
                    blockquote { border-left: 4px solid #3498db; margin-left: 0; padding-left: 15px; }
                    hr { border: none; height: 1px; background-color: #eee; }
                    .container { max-width: 800px; margin: 0 auto; }
                </style>
                """
            html_content.append(styles)
        
        # Start HTML document
        html_content.extend([
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>{html.escape(title)}</title>",
            "<meta charset=\"UTF-8\">",
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">",
            "</head>",
            "<body>",
            "<div class=\"container\">"
        ])
        
        if is_markdown:
            # Convert markdown to HTML (simple version)
            paragraphs = []
            in_code_block = False
            code_content = []
            code_lang = "plaintext"
            
            for line in content.split('\n'):
                # Handle code blocks
                if line.startswith('```'):
                    if in_code_block:
                        # End code block
                        code_html = html.escape('\n'.join(code_content))
                        paragraphs.append(f"<pre><code class=\"language-{code_lang}\">{code_html}</code></pre>")
                        code_content = []
                        in_code_block = False
                    else:
                        # Start code block
                        in_code_block = True
                        # Extract language if provided
                        if len(line) > 3:
                            code_lang = line[3:].strip()
                        else:
                            code_lang = "plaintext"
                    continue
                
                if in_code_block:
                    code_content.append(line)
                    continue
                
                # Handle headings
                if line.startswith('#'):
                    match = re.match(r'^(#+)\s+(.+)$', line)
                    if match:
                        level = len(match.group(1))
                        text = match.group(2)
                        if level <= 6:  # HTML only has h1-h6
                            paragraphs.append(f"<h{level}>{html.escape(text)}</h{level}>")
                    continue
                
                # Handle horizontal rule
                if line.strip() == '---':
                    paragraphs.append("<hr>")
                    continue
                
                # Handle lists (simple)
                if line.strip().startswith('- '):
                    item_text = line.strip()[2:]
                    paragraphs.append(f"<ul><li>{html.escape(item_text)}</li></ul>")
                    continue
                
                # Handle numbered lists (simple)
                if re.match(r'^\d+\.\s', line.strip()):
                    item_text = re.sub(r'^\d+\.\s', '', line.strip())
                    paragraphs.append(f"<ol><li>{html.escape(item_text)}</li></ol>")
                    continue
                
                # Handle blockquotes
                if line.strip().startswith('>'):
                    quote_text = line.strip()[1:].strip()
                    paragraphs.append(f"<blockquote>{html.escape(quote_text)}</blockquote>")
                    continue
                
                # Handle links
                line = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', line)
                
                # Handle inline code
                line = re.sub(r'`(.+?)`', r'<code>\1</code>', line)
                
                # Handle bold and italic
                line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)
                
                # Handle regular paragraphs
                if line.strip():
                    paragraphs.append(f"<p>{line}</p>")
                else:
                    # Empty line - paragraph break
                    if paragraphs and not paragraphs[-1].endswith('</p>'):
                        paragraphs.append("<br>")
            
            # Append all the converted content
            html_content.extend(paragraphs)
        else:
            # Treat as plain text, create paragraphs
            for paragraph in re.split(r'\n\s*\n', escaped_content):
                if paragraph.strip():
                    # Replace newlines with <br> tags
                    paragraph = paragraph.replace('\n', '<br>')
                    html_content.append(f"<p>{paragraph}</p>")
        
        # Close HTML document
        html_content.extend([
            "</div>",
            "</body>",
            "</html>"
        ])
        
        return {
            "formatted_content": '\n'.join(html_content),
            "format": "html",
            "title": title,
            "theme": theme
        }
    
    except Exception as e:
        logger.error(f"Error in HTML formatter: {e}")
        # Return a simplified HTML version if something goes wrong
        return {
            "formatted_content": f"<!DOCTYPE html><html><body><pre>{html.escape(content)}</pre></body></html>",
            "format": "html",
            "error": str(e)
        }

@lc_tool
def format_as_json(content: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format content as structured JSON.
    
    Args:
        content: The raw text content to structure as JSON
        options: Optional formatting preferences
            - schema: JSON schema to follow (default: infer)
            - pretty_print: whether to prettify the output (default: True)
    
    Returns:
        Dict containing the JSON content and metadata
    """
    options = options or {}
    pretty_print = options.get("pretty_print", True)
    
    try:
        # Check if content is already valid JSON
        try:
            data = json.loads(content)
            # If we get here, it's already valid JSON
            if pretty_print:
                formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                formatted_json = json.dumps(data, ensure_ascii=False)
            
            return {
                "formatted_content": formatted_json,
                "format": "json",
                "is_array": isinstance(data, list),
                "object_keys": list(data.keys()) if isinstance(data, dict) else None
            }
        except json.JSONDecodeError:
            # Not valid JSON, attempt to structure it
            pass
        
        # Extract key-value pairs from text
        data = {}
        lines = content.split('\n')
        current_key = None
        current_value = []
        
        # First pass - try to identify clear key-value pairs
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for "Key: Value" pattern
            match = re.match(r'^([A-Za-z0-9_\s]+[A-Za-z0-9_]):\s*(.*)$', line)
            if match:
                # Save previous key-value if any
                if current_key and current_value:
                    data[current_key] = '\n'.join(current_value).strip()
                    current_value = []
                
                current_key = match.group(1).strip()
                value = match.group(2).strip()
                
                if value:
                    current_value.append(value)
                else:
                    # Key with no value yet, wait for next lines
                    pass
            elif current_key:
                # Continue previous value
                current_value.append(line)
        
        # Save the last key-value pair
        if current_key and current_value:
            data[current_key] = '\n'.join(current_value).strip()
        
        # If no clear structure found, fallback to a simple object
        if not data:
            data = {
                "content": content.strip()
            }
        
        # Convert to JSON
        if pretty_print:
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            formatted_json = json.dumps(data, ensure_ascii=False)
        
        return {
            "formatted_content": formatted_json,
            "format": "json",
            "is_array": False,
            "object_keys": list(data.keys())
        }
    
    except Exception as e:
        logger.error(f"Error in JSON formatter: {e}")
        # Return a simplified JSON object if something goes wrong
        error_json = {
            "error": str(e),
            "original_content": content
        }
        return {
            "formatted_content": json.dumps(error_json, indent=2),
            "format": "json",
            "error": str(e)
        }

@lc_tool
def format_as_table(data: Union[str, List[Dict[str, Any]]], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Format data as a Markdown or HTML table.
    
    Args:
        data: Either raw text to parse or a list of dictionaries
        options: Optional formatting preferences
            - format: "markdown" or "html" (default: "markdown")
            - headers: list of column headers (default: infer from data)
            - alignment: list of "left", "center", or "right" for columns
    
    Returns:
        Dict containing the table content and metadata
    """
    options = options or {}
    output_format = options.get("format", "markdown")
    headers = options.get("headers")
    alignment = options.get("alignment")
    
    try:
        # Process input data
        rows = []
        if isinstance(data, str):
            # Parse string data
            lines = data.strip().split('\n')
            
            # Try to detect CSV format
            if ',' in lines[0]:
                delimiter = ','
            elif '\t' in lines[0]:
                delimiter = '\t'
            else:
                delimiter = None
            
            # Parse rows
            for line in lines:
                if not line.strip():
                    continue
                
                if delimiter:
                    # Split by delimiter, respecting quotes
                    in_quotes = False
                    current_field = []
                    row = []
                    
                    for char in line:
                        if char == '"':
                            in_quotes = not in_quotes
                        elif char == delimiter and not in_quotes:
                            row.append(''.join(current_field).strip())
                            current_field = []
                        else:
                            current_field.append(char)
                    
                    # Add the last field
                    row.append(''.join(current_field).strip())
                    rows.append(row)
                else:
                    # Split by whitespace
                    row = line.split()
                    rows.append(row)
            
            # Extract headers from first row if not provided
            if not headers and rows:
                headers = rows[0]
                rows = rows[1:]
        elif isinstance(data, list):
            # Already structured data
            if not data:
                return {
                    "formatted_content": "",
                    "format": output_format,
                    "error": "No data provided"
                }
            
            # Extract headers from dict keys if not provided
            if not headers and isinstance(data[0], dict):
                headers = list(data[0].keys())
            
            # Convert list of dicts to list of lists
            if isinstance(data[0], dict):
                for item in data:
                    row = [item.get(header, "") for header in headers]
                    rows.append(row)
            else:
                # Assume it's already a list of lists
                rows = data
        else:
            return {
                "formatted_content": "",
                "format": output_format,
                "error": "Invalid data format"
            }
        
        # Ensure all rows have the same length as headers
        if headers:
            for i, row in enumerate(rows):
                if len(row) < len(headers):
                    rows[i] = row + [""] * (len(headers) - len(row))
                elif len(row) > len(headers):
                    rows[i] = row[:len(headers)]
        
        # Format as requested
        if output_format == "html":
            table_html = ["<table>"]
            
            # Add headers
            if headers:
                table_html.append("<thead>")
                table_html.append("<tr>")
                for header in headers:
                    table_html.append(f"<th>{html.escape(str(header))}</th>")
                table_html.append("</tr>")
                table_html.append("</thead>")
            
            # Add rows
            table_html.append("<tbody>")
            for row in rows:
                table_html.append("<tr>")
                for cell in row:
                    table_html.append(f"<td>{html.escape(str(cell))}</td>")
                table_html.append("</tr>")
            table_html.append("</tbody>")
            
            table_html.append("</table>")
            formatted_content = "\n".join(table_html)
        else:
            # Markdown format
            table_md = []
            
            # Determine column widths
            col_widths = []
            for col_idx in range(len(headers) if headers else len(rows[0])):
                if headers:
                    width = len(str(headers[col_idx]))
                else:
                    width = 0
                
                for row in rows:
                    if col_idx < len(row):
                        width = max(width, len(str(row[col_idx])))
                
                col_widths.append(width + 2)  # Add padding
            
            # Add headers
            if headers:
                header_row = "|"
                for i, header in enumerate(headers):
                    header_str = str(header)
                    padding = col_widths[i] - len(header_str)
                    header_row += " " + header_str + " " * padding + "|"
                table_md.append(header_row)
                
                # Add separator row
                sep_row = "|"
                for i, width in enumerate(col_widths):
                    if alignment:
                        if i < len(alignment):
                            if alignment[i] == "center":
                                sep_row += ":" + "-" * (width - 2) + ":|"
                            elif alignment[i] == "right":
                                sep_row += "-" * (width - 1) + ":|"
                            else:  # left or default
                                sep_row += ":" + "-" * (width - 1) + "|"
                        else:
                            sep_row += "-" * width + "|"
                    else:
                        sep_row += "-" * width + "|"
                table_md.append(sep_row)
            
            # Add data rows
            for row in rows:
                data_row = "|"
                for i, cell in enumerate(row):
                    if i < len(col_widths):
                        cell_str = str(cell)
                        padding = col_widths[i] - len(cell_str)
                        data_row += " " + cell_str + " " * padding + "|"
                    else:
                        break
                table_md.append(data_row)
            
            formatted_content = "\n".join(table_md)
        
        return {
            "formatted_content": formatted_content,
            "format": output_format,
            "rows_count": len(rows),
            "columns_count": len(headers) if headers else (len(rows[0]) if rows else 0)
        }
    
    except Exception as e:
        logger.error(f"Error in table formatter: {e}")
        # Return error message
        return {
            "formatted_content": f"Error creating table: {str(e)}",
            "format": output_format,
            "error": str(e)
        }