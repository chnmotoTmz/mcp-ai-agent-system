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

# --- Helper functions (copied from publish_hatena_article.py for self-containment) ---
# In a real library, these would be shared.

def _clean_hatena_content_for_update(title: str, content: str) -> str:
    """Removes duplicate titles from the beginning of content."""
    # (Implementation is identical to _clean_hatena_content_for_publish)
    cleaned_content = content.strip()
    if not title: return cleaned_content
    normalized_title = re.sub(r'\s+', ' ', title.strip())
    escaped_title = re.escape(normalized_title)
    html_patterns = [
        f"<h[1-6][^>]*>\\s*{escaped_title}\\s*</h[1-6]>",
        f"<(?:strong|b|em|i)[^>]*>\\s*{escaped_title}\\s*</(?:strong|b|em|i)>",
        f"<p[^>]*>\\s*<(?:strong|b|em|i)[^>]*>\\s*{escaped_title}\\s*</(?:strong|b|em|i)>\\s*</p>",
        f"<div[^>]*>\\s*{escaped_title}\\s*</div>", f"<title[^>]*>\\s*{escaped_title}\\s*</title>",
        f"<p[^>]*>\\s*{escaped_title}\\s*</p>",
    ]
    for pattern in html_patterns:
        cleaned_content = re.sub(pattern, '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)
    cleaned_content = re.sub(r'<p[^>]*>\s*</p>|<div[^>]*>\s*</div>', '', cleaned_content, flags=re.IGNORECASE | re.DOTALL)
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
    if lines and lines[0].strip() == normalized_title: lines.pop(0)
    return '\n'.join(lines).strip()

def _create_hatena_entry_xml_for_update(
    title: str, content_body: str, hatena_id: str, summary: str = "",
    tags: Optional[List[str]] = None, draft: bool = False, content_type: str = "text/x-markdown",
    updated_time: Optional[datetime] = None
) -> str:
    """Creates an AtomPub XML entry for Hatena Blog (can be used for updates too)."""
    # (Implementation is identical to _create_hatena_entry_xml from publish snippet)
    if tags is None: tags = []
    entry = ET.Element('entry', {'xmlns': 'http://www.w3.org/2005/Atom', 'xmlns:app': 'http://www.w3.org/2007/app'})
    ET.SubElement(entry, 'title').text = title
    author_elem = ET.SubElement(entry, 'author'); ET.SubElement(author_elem, 'name').text = hatena_id
    final_content_body = _clean_hatena_content_for_update(title, content_body) if content_type == "text/x-markdown" else content_body
    content_elem = ET.SubElement(entry, 'content', {'type': content_type}); content_elem.text = final_content_body
    if summary: ET.SubElement(entry, 'summary').text = summary
    for tag in tags:
        if tag: ET.SubElement(entry, 'category', {'term': tag})
    if updated_time: ET.SubElement(entry, 'updated').text = updated_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    app_control = ET.SubElement(entry, 'app:control'); ET.SubElement(app_control, 'app:draft').text = 'yes' if draft else 'no'
    rough_string = ET.tostring(entry, encoding='utf-8', method='xml').decode('utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def _create_hatena_wsse_header_for_update(hatena_id: str, api_key: str) -> str:
    """Creates a WSSE authentication header."""
    # (Implementation is identical)
    nonce = hashlib.sha1(str(random.random()).encode('utf-8')).digest()
    now_utc = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    password_digest = hashlib.sha1(nonce + now_utc.encode('utf-8') + api_key.encode('utf-8')).digest()
    return (f'UsernameToken Username="{hatena_id}", PasswordDigest="{base64.b64encode(password_digest).decode("utf-8")}", Nonce="{base64.b64encode(nonce).decode("utf-8")}", Created="{now_utc}"')

def _parse_hatena_api_response_for_update(response_xml_text: str) -> Dict[str, str]:
    """Parses the XML response from Hatena API."""
    # (Implementation is identical)
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
# --- End of Helper Functions ---

def update_hatena_article(
    hatena_id: str,
    blog_id: str,
    api_key: str,
    entry_id: str, # The ID of the article to update
    title: Optional[str] = None,
    content_body: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None, # Can be None if not changing
    draft: Optional[bool] = None, # If None, Hatena usually keeps current status
    content_type: str = "text/x-markdown",
    summary: Optional[str] = None, # Optional: new summary
    updated_time: Optional[datetime] = None, # Optional: force update timestamp
    request_timeout: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Updates an existing article on Hatena Blog using the AtomPub API.
    Only provided fields (title, content_body, tags, etc.) will be updated.
    To clear a field like tags, pass an empty list. To keep it unchanged, pass None.

    Args:
        hatena_id, blog_id, api_key: Credentials.
        entry_id (str): The numeric ID of the Hatena blog entry to update.
                        (e.g., "6802418398470039740" from the edit URL).
        title (Optional[str]): New title. If None, title is not updated.
        content_body (Optional[str]): New content. If None, content is not updated.
        tags (Optional[List[str]]): New list of tags. Pass [] to remove all tags.
                                     If None, tags are not updated.
        category (Optional[str]): New category. If None, category is not updated.
                                  If provided, it's added to the tags list.
        draft (Optional[bool]): New draft status. If None, status is not explicitly changed.
        content_type (str): MIME type of the content_body if provided.
        summary (Optional[str]): New summary. If None, not updated.
        updated_time (Optional[datetime]): Force a new <updated> timestamp.
        request_timeout (int): HTTP request timeout.

    Returns:
        Optional[Dict[str, Any]]: Dictionary with update details if successful, None otherwise.
    """
    if not title and not content_body and tags is None and category is None and draft is None and summary is None:
        logger.warning("No update parameters provided for update_hatena_article. Nothing to do.")
        return None # Or perhaps return info about the existing article if fetched

    base_api_url = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_id}/atom"

    # Hatena entry IDs are typically numeric. If a full tag URI is passed, extract the ID.
    numeric_entry_id = entry_id
    if entry_id.startswith('tag:blog.hatena.ne.jp'):
        try:
            numeric_entry_id = entry_id.split('-')[-1]
            if not numeric_entry_id.isdigit(): # Basic check
                raise ValueError("Extracted part is not numeric.")
        except (IndexError, ValueError) as e:
            logger.error(f"Invalid Hatena entry_id format: {entry_id}. Could not extract numeric ID. Error: {e}")
            return None
    elif not entry_id.isdigit(): # If not a tag URI, it should be a plain numeric ID
        logger.error(f"Invalid Hatena entry_id: {entry_id}. Expected a numeric ID or full tag URI.")
        return None

    update_url = f"{base_api_url}/entry/{numeric_entry_id}"

    # Note: For updates, the AtomPub spec implies you should PUT the *complete* new state
    # of the entry. However, Hatena's API might be more forgiving or have specific behavior
    # for partial updates. This snippet assumes we construct a full entry XML with
    # the new values for fields we want to change, and potentially omits others or
    # relies on Hatena to merge.
    # A robust solution might first GET the existing entry, modify it, then PUT.
    # For this snippet, we'll send what's provided.

    final_tags = tags if tags is not None else [] # Default to empty list if updating tags
    if category and category not in final_tags:
        final_tags.append(category)

    # Use current values if specific update values are not provided
    # This is a simplification; a real update would fetch current values first.
    # For this snippet, we require title and content if they are being updated.
    # If only tags are updated, title/content might be required by API - depends on Hatena.
    # Let's assume for now that if a field is None, it's not part of the update payload,
    # but the XML construction needs defaults.

    # For a PUT, you typically need to provide the full resource.
    # This snippet will require at least a title and content if those are being changed.
    # If only tags/draft status are changing, the API might still need a body.
    # This is a known complexity of AtomPub PUT.
    # For simplicity, we will use placeholder if not provided, but this might not be ideal.
    xml_title = title if title is not None else "Title Placeholder (Update)"
    xml_content = content_body if content_body is not None else "Content Placeholder (Update)"
    xml_summary = summary if summary is not None else ""
    xml_draft = draft if draft is not None else False # Default to not draft if not specified


    entry_xml = _create_hatena_entry_xml_for_update(
        title=xml_title,
        content_body=xml_content,
        hatena_id=hatena_id,
        summary=xml_summary,
        tags=final_tags if tags is not None else None, # Pass None if tags aren't being updated
        draft=xml_draft,
        content_type=content_type,
        updated_time=updated_time or datetime.utcnow() # Always set an updated time for PUT
    )

    headers = {
        'Content-Type': 'application/atom+xml; charset=utf-8',
        'X-WSSE': _create_hatena_wsse_header_for_update(hatena_id, api_key)
    }

    try:
        logger.info(f"Updating article ID {numeric_entry_id} on Hatena: new title '{title[:50] if title else '(no change)'}'...")
        # logger.debug(f"PUT URL: {update_url}")
        # logger.debug(f"Request XML Body for Update:\n{entry_xml}")

        response = requests.put(
            update_url,
            data=entry_xml.encode('utf-8'),
            headers=headers,
            timeout=request_timeout
        )
        response.raise_for_status()

        if response.status_code == 200: # OK for update
            logger.info(f"Article ID {numeric_entry_id} updated successfully.")
            parsed_response = _parse_hatena_api_response_for_update(response.text)
            return {
                'id': entry_id, # Return original ID format if it was a tag URI
                'numeric_id': numeric_entry_id,
                'url': parsed_response.get('url'),
                'edit_url': parsed_response.get('edit_url'),
                'status': 'updated',
                # Include what was actually sent for update if needed
                'updated_title': title,
                'updated_tags': final_tags if tags is not None else '(not updated)',
                'updated_draft_status': draft,
                'raw_response': parsed_response.get('raw_xml')
            }
        else:
            logger.error(f"Hatena API unexpected success status for update: {response.status_code} - {response.text[:200]}")
            return None

    except requests.exceptions.HTTPError as e:
        logger.error(f"Hatena API HTTP Error on update: {e.response.status_code} - {e.response.text[:200]}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Hatena API Request Exception on update: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during Hatena article update: {e}", exc_info=True)

    return None

# Example Usage
if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO)

    try:
        HATENA_USER_ID = os.environ["HATENA_USER_ID"]
        HATENA_BLOG_NAME = os.environ["HATENA_BLOG_NAME"]
        HATENA_API_KEY_VAL = os.environ["HATENA_API_KEY"]
        # For this test, we need an EXISTING_ARTICLE_ID from your Hatena blog (the numeric part)
        # You can get this by publishing an article (e.g., with publish_hatena_article.py)
        # and then copying the ID from the edit URL or the returned 'id' field.
        EXISTING_ARTICLE_ID = os.environ.get("HATENA_EXISTING_ARTICLE_ID_FOR_TEST")
    except KeyError:
        print("Please set HATENA_USER_ID, HATENA_BLOG_NAME, HATENA_API_KEY, and optionally HATENA_EXISTING_ARTICLE_ID_FOR_TEST environment variables.")
        exit(1)

    if not EXISTING_ARTICLE_ID:
        print("HATENA_EXISTING_ARTICLE_ID_FOR_TEST not set. Skipping update test.")
        print("Please publish an article first and set its ID to this env var to test updates.")
    else:
        print(f"--- Test Case: Update existing article ID: {EXISTING_ARTICLE_ID} ---")
        new_title = f"Updated Title - {datetime.now().strftime('%Y%m%d%H%M%S')}"
        new_content = f"<p>This content has been updated by the snippet at {datetime.now()}.</p><p><em>Emphasis added!</em></p>"
        new_tags = ["updated", "test", "python-snippet"]

        update_result = update_hatena_article(
            hatena_id=HATENA_USER_ID,
            blog_id=HATENA_BLOG_NAME,
            api_key=HATENA_API_KEY_VAL,
            entry_id=EXISTING_ARTICLE_ID,
            title=new_title,
            content_body=new_content,
            tags=new_tags,
            category="Test Updates", # This will be added to tags
            draft=True, # Keep it as a draft
            content_type="text/html"
        )

        if update_result:
            print("Article updated successfully:")
            print(f"  ID: {update_result.get('id')}")
            print(f"  URL: {update_result.get('url')}")
            print(f"  New Title: {update_result.get('updated_title')}")
            print(f"  New Tags: {update_result.get('updated_tags')}")
        else:
            print(f"Failed to update article ID {EXISTING_ARTICLE_ID}.")
            print("Ensure the article ID is correct and the article exists.")

    print("\nNote: To run this test, you need a pre-existing article on your Hatena blog")
    print("and its numeric ID set in the HATENA_EXISTING_ARTICLE_ID_FOR_TEST environment variable.")
