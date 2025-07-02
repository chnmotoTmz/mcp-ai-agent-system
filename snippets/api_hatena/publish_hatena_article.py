import logging
import requests
import hashlib
import random
import base64
import re # For _clean_content
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom
from typing import Dict, Optional, List, Any # Added List, Any

logger = logging.getLogger(__name__)

# --- Helper function: _clean_content (from HatenaService) ---
# This is a direct copy from the original HatenaService, modified to be a static function.
# In a real refactoring, this might live in a text_utils module.
def _clean_hatena_content_for_publish(title: str, content: str) -> str:
    """
    Removes duplicate titles from the beginning of content.
    (Copied and adapted from original HatenaService._clean_content)
    """
    cleaned_content = content.strip()
    if not title:
        return cleaned_content
    normalized_title = re.sub(r'\s+', ' ', title.strip())
    escaped_title = re.escape(normalized_title)

    html_patterns = [
        f"<h[1-6][^>]*>\\s*{escaped_title}\\s*</h[1-6]>",
        f"<(?:strong|b|em|i)[^>]*>\\s*{escaped_title}\\s*</(?:strong|b|em|i)>",
        f"<p[^>]*>\\s*<(?:strong|b|em|i)[^>]*>\\s*{escaped_title}\\s*</(?:strong|b|em|i)>\\s*</p>",
        f"<div[^>]*>\\s*{escaped_title}\\s*</div>",
        f"<title[^>]*>\\s*{escaped_title}\\s*</title>",
        f"<p[^>]*>\\s*{escaped_title}\\s*</p>",
    ]
    for pattern in html_patterns:
        cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)
    cleaned_content = re.sub(r'<p[^>]*>\s*</p>', '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)
    cleaned_content = re.sub(r'<div[^>]*>\s*</div>', '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)

    bracket_patterns = [
        f"【\\s*{escaped_title}\\s*】", f"「\\s*{escaped_title}\\s*」", f"『\\s*{escaped_title}\\s*』",
        f"\\[\\s*{escaped_title}\\s*\\]", f"\\(\\s*{escaped_title}\\s*\\)",
    ]
    for pattern in bracket_patterns:
        cleaned_content = re.sub(f"^\\s*{pattern}\\s*$", '', cleaned_content, flags=re.MULTILINE)
        cleaned_content = re.sub(f"^{pattern}\\s*", '', cleaned_content, flags=re.DOTALL)

    lines = cleaned_content.split('\n')
    new_lines = [
        line for line in lines
        if not (line.strip() == normalized_title or
                re.match(f"^{escaped_title}[。、.,：:!?！？]?\\s*$", line.strip()) or
                re.match(f"^{escaped_title}\\s*$", line.strip()))
    ]
    cleaned_content = '\n'.join(new_lines)
    cleaned_content = re.sub(f"^\\s*{escaped_title}\\s*[。、.,：:!?！？]?\\s*\\n?", '', cleaned_content, flags=re.DOTALL)

    markdown_patterns = [f"^#+\\s*{escaped_title}\\s*$", f"^{escaped_title}\\s*\\n[=-]+\\s*$"]
    for pattern in markdown_patterns:
        cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.MULTILINE)

    if '\n' in title:
        title_lines = title.strip().split('\n')
        for title_line in title_lines:
            if title_line.strip():
                cleaned_content = re.sub(f"^\\s*{re.escape(title_line.strip())}\\s*$", '', cleaned_content, flags=re.MULTILINE)

    cleaned_content = cleaned_content.strip()
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    lines = cleaned_content.split('\n')
    if lines and lines[0].strip() == normalized_title:
        lines.pop(0)
    return '\n'.join(lines).strip()

# --- Helper function: _create_hatena_entry_xml ---
def _create_hatena_entry_xml(
    title: str,
    content_body: str, # Renamed from 'content' to avoid confusion with content_type
    hatena_id: str, # Added: needed for author
    summary: str = "",
    tags: Optional[List[str]] = None,
    draft: bool = False,
    content_type: str = "text/x-markdown",
    updated_time: Optional[datetime] = None # For setting <updated>
) -> str:
    """
    Creates an AtomPub XML entry for Hatena Blog.
    (Adapted from original HatenaService._create_entry_xml)
    """
    if tags is None:
        tags = []

    entry = ET.Element('entry', {
        'xmlns': 'http://www.w3.org/2005/Atom',
        'xmlns:app': 'http://www.w3.org/2007/app'
    })

    ET.SubElement(entry, 'title').text = title

    # Author element is often required or good practice
    author_elem = ET.SubElement(entry, 'author')
    ET.SubElement(author_elem, 'name').text = hatena_id # Use Hatena ID as author name

    # Content cleaning is specific to how Hatena handles titles in bodies
    # This might be better handled by the caller if the snippet is truly generic.
    # For now, keeping the cleaning logic for 'text/x-markdown'.
    final_content_body = content_body
    if content_type == "text/x-markdown":
        final_content_body = _clean_hatena_content_for_publish(title, content_body)

    content_elem = ET.SubElement(entry, 'content', {'type': content_type})
    content_elem.text = final_content_body

    if summary:
        ET.SubElement(entry, 'summary').text = summary

    for tag in tags:
        if tag: ET.SubElement(entry, 'category', {'term': tag})

    if updated_time: # Add <updated> if provided
        ET.SubElement(entry, 'updated').text = updated_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    app_control = ET.SubElement(entry, 'app:control')
    ET.SubElement(app_control, 'app:draft').text = 'yes' if draft else 'no'

    rough_string = ET.tostring(entry, encoding='utf-8', method='xml').decode('utf-8') # Ensure utf-8
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


# --- Helper function: _create_wsse_header ---
def _create_hatena_wsse_header(hatena_id: str, api_key: str) -> str:
    """Creates a WSSE authentication header for Hatena Blog API."""
    nonce = hashlib.sha1(str(random.random()).encode('utf-8')).digest()
    now_utc = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    password_digest = hashlib.sha1(nonce + now_utc.encode('utf-8') + api_key.encode('utf-8')).digest()

    return (f'UsernameToken Username="{hatena_id}", '
            f'PasswordDigest="{base64.b64encode(password_digest).decode("utf-8")}", '
            f'Nonce="{base64.b64encode(nonce).decode("utf-8")}", '
            f'Created="{now_utc}"')

# --- Helper function: _parse_hatena_api_response ---
def _parse_hatena_api_response(response_xml_text: str) -> Dict[str, str]:
    """
    Parses the XML response from Hatena API after a successful post/update.
    (Adapted from original HatenaService._parse_response)
    """
    try:
        root = ET.fromstring(response_xml_text)
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}

        entry_id_elem = root.find('atom:id', namespaces)
        entry_id = entry_id_elem.text.split('/')[-1] if entry_id_elem is not None and entry_id_elem.text else ""

        url_elem = root.find('atom:link[@rel="alternate"]', namespaces)
        entry_url = url_elem.get('href', '') if url_elem is not None else ""

        edit_url_elem = root.find('atom:link[@rel="edit"]', namespaces)
        entry_edit_url = edit_url_elem.get('href', '') if edit_url_elem is not None else ""

        return {'entry_id': entry_id, 'url': entry_url, 'edit_url': entry_edit_url, 'raw_xml': response_xml_text}
    except Exception as e:
        logger.error(f"Error parsing Hatena API response XML: {e}")
        return {'entry_id': '', 'url': '', 'edit_url': '', 'raw_xml': response_xml_text, 'error': str(e)}


def publish_hatena_article(
    hatena_id: str,
    blog_id: str,
    api_key: str,
    title: str,
    content_body: str, # Renamed from 'content'
    tags: Optional[List[str]] = None,
    category: str = "", # Often treated as a special tag by Hatena
    draft: bool = False,
    content_type: str = "text/x-markdown", # Options: "text/html", "text/x-hatena-syntax"
    summary: str = "",
    updated_time: Optional[datetime] = None,
    request_timeout: int = 30 # seconds
) -> Optional[Dict[str, Any]]:
    """
    Publishes an article to Hatena Blog using the AtomPub API.

    Args:
        hatena_id (str): Your Hatena ID.
        blog_id (str): Your Hatena Blog ID (e.g., yourblog.hatenablog.com).
        api_key (str): Your Hatena Blog API key.
        title (str): The title of the article.
        content_body (str): The main content/body of the article.
        tags (Optional[List[str]], optional): List of tags for the article.
        category (str, optional): Category for the article. If provided, it's added to tags.
        draft (bool, optional): If True, posts as a draft. Defaults to False.
        content_type (str, optional): The MIME type of the content.
            Defaults to "text/x-markdown".
        summary (str, optional): A short summary of the article.
        updated_time (Optional[datetime], optional): If provided, sets the <updated>
            timestamp in the Atom entry. Useful for backdating or specific timing.
        request_timeout (int, optional): Timeout for the HTTP request in seconds.

    Returns:
        Optional[Dict[str, Any]]: A dictionary with publication details if successful,
                                  e.g., {'id', 'url', 'edit_url', 'title', 'tags', ...},
                                  None on failure.
    """
    if tags is None:
        tags = []
    if category and category not in tags: # Add category to tags if not already present
        tags.append(category)

    base_api_url = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_id}/atom"
    post_url = f"{base_api_url}/entry"

    entry_xml = _create_hatena_entry_xml(
        title=title,
        content_body=content_body,
        hatena_id=hatena_id, # Pass hatena_id for author field
        summary=summary,
        tags=tags,
        draft=draft,
        content_type=content_type,
        updated_time=updated_time
    )

    headers = {
        'Content-Type': 'application/atom+xml; charset=utf-8', # Standard for AtomPub
        'X-WSSE': _create_hatena_wsse_header(hatena_id, api_key)
    }

    try:
        logger.info(f"Publishing article to Hatena: {title[:50]}...")
        logger.debug(f"POST URL: {post_url}")
        logger.debug(f"Request Headers: {headers.get('X-WSSE', 'WSSE MISSING - THIS IS BAD')[:50]}...") # Log only part of WSSE
        # logger.debug(f"Request XML Body:\n{entry_xml}") # Can be very verbose

        response = requests.post(
            post_url,
            data=entry_xml.encode('utf-8'), # Ensure UTF-8 encoding
            headers=headers,
            timeout=request_timeout
        )
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        if response.status_code == 201: # Created
            logger.info(f"Article '{title}' published successfully to Hatena Blog.")
            parsed_response = _parse_hatena_api_response(response.text)
            return {
                'id': parsed_response.get('entry_id'),
                'url': parsed_response.get('url'),
                'edit_url': parsed_response.get('edit_url'),
                'title': title,
                'tags': tags,
                'category': category, # Retain original category if passed
                'draft': draft,
                'status': 'published' if not draft else 'draft',
                'raw_response': parsed_response.get('raw_xml')
            }
        else:
            # This case should be caught by raise_for_status, but as a fallback:
            logger.error(f"Hatena API unexpected success status: {response.status_code} - {response.text[:200]}")
            return None

    except requests.exceptions.HTTPError as e:
        logger.error(f"Hatena API HTTP Error: {e.response.status_code} - {e.response.text[:200]}")
    except requests.exceptions.RequestException as e: # Catches ConnectTimeout, ReadTimeout, etc.
        logger.error(f"Hatena API Request Exception: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during Hatena publication: {e}", exc_info=True)

    return None


# Example Usage (requires Hatena credentials to be set as environment variables)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG) # Use DEBUG for more verbose logs from helpers

    # IMPORTANT: Store these securely, e.g., in environment variables or a config file.
    # DO NOT hardcode them in your script for production use.
    try:
        HATENA_USER_ID = os.environ["HATENA_USER_ID"]
        HATENA_BLOG_NAME = os.environ["HATENA_BLOG_NAME"] # e.g., yourblog.hatenablog.com
        HATENA_API_KEY_VAL = os.environ["HATENA_API_KEY"]
    except KeyError:
        print("Please set HATENA_USER_ID, HATENA_BLOG_NAME, and HATENA_API_KEY environment variables to run this example.")
        exit(1)

    print(f"--- Test Case 1: Publish a new article ---")
    article_title = f"Test Article via Snippet - {datetime.now().strftime('%Y%m%d%H%M%S')}"
    article_content = f"""
<p>This is a test article published using the <code>publish_hatena_article</code> snippet.</p>
<p>Current time: {datetime.now()}</p>
<p>It supports <strong>HTML</strong> directly if <code>content_type</code> is "text/html".</p>
"""
    result1 = publish_hatena_article(
        hatena_id=HATENA_USER_ID,
        blog_id=HATENA_BLOG_NAME,
        api_key=HATENA_API_KEY_VAL,
        title=article_title,
        content_body=article_content,
        tags=["test", "snippet", "python"],
        category="Tech",
        content_type="text/html", # Test with HTML
        draft=True # Post as draft to avoid cluttering public blog
    )

    if result1:
        print("Article published successfully (as draft):")
        print(f"  ID: {result1.get('id')}")
        print(f"  URL: {result1.get('url')}")
        print(f"  Edit URL: {result1.get('edit_url')}")
        print(f"  Tags: {result1.get('tags')}")
    else:
        print("Failed to publish article (Test 1).")

    print(f"\n--- Test Case 2: Publish with Markdown and backdating ---")
    md_title = f"Markdown Test - {datetime.now().strftime('%Y%m%d%H%M%S')}"
    md_content = f"""
# {md_title}

This is a test article written in Markdown.

- Point 1
- Point 2

*Published via snippet.*
"""
    # Simulate a past date for the 'updated' field
    past_date = datetime(2023, 1, 15, 10, 30, 0)

    result2 = publish_hatena_article(
        hatena_id=HATENA_USER_ID,
        blog_id=HATENA_BLOG_NAME,
        api_key=HATENA_API_KEY_VAL,
        title=md_title,
        content_body=md_content, # This will be cleaned if title is duplicated by _clean_hatena_content_for_publish
        tags=["markdown", "backdate"],
        content_type="text/x-markdown",
        draft=True,
        updated_time=past_date
    )
    if result2:
        print("Markdown article published successfully (as draft, backdated):")
        print(f"  URL: {result2.get('url')}")
        print(f"  (Check Hatena dashboard for actual 'updated' time)")
    else:
        print("Failed to publish Markdown article (Test 2).")

    # Note: To fully test, you'd need to check your Hatena blog drafts.
    # Consider adding a cleanup step if these are automated tests (e.g., delete test articles).
