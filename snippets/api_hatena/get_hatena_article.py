import logging
import requests
import hashlib
import random
import base64
from datetime import datetime
from xml.etree import ElementTree as ET
from typing import Dict, Optional, List, Any # Added List, Any

logger = logging.getLogger(__name__)

# --- Helper functions (copied from publish_hatena_article.py for self-containment) ---
def _create_hatena_wsse_header_for_get(hatena_id: str, api_key: str) -> str:
    """Creates a WSSE authentication header."""
    nonce = hashlib.sha1(str(random.random()).encode('utf-8')).digest()
    now_utc = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    password_digest = hashlib.sha1(nonce + now_utc.encode('utf-8') + api_key.encode('utf-8')).digest()
    return (f'UsernameToken Username="{hatena_id}", PasswordDigest="{base64.b64encode(password_digest).decode("utf-8")}", Nonce="{base64.b64encode(nonce).decode("utf-8")}", Created="{now_utc}"')

def _parse_hatena_entry_xml_to_dict(entry_xml_text: str) -> Dict[str, Any]:
    """
    Parses a single Hatena AtomPub entry XML string into a dictionary.
    Extracts common fields like id, title, content, author, updated, published, links, and categories.
    """
    try:
        root = ET.fromstring(entry_xml_text)
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'app': 'http://www.w3.org/2007/app', # For app:control, app:draft
            'hatena': 'http://www.hatena.ne.jp/info/xmlns#' # For hatena:formatted-content
        }

        article_dict: Dict[str, Any] = {}

        # Helper to find text, safely
        def find_text(element, path, namespaces):
            el = element.find(path, namespaces)
            return el.text.strip() if el is not None and el.text else ""

        # Helper to find attribute, safely
        def find_attr(element, path, attr_name, namespaces):
            el = element.find(path, namespaces)
            return el.get(attr_name) if el is not None else ""

        article_dict['id'] = find_text(root, 'atom:id', ns)
        article_dict['title'] = find_text(root, 'atom:title', ns)

        # Content: Hatena often provides formatted-content as well
        content_elem = root.find('atom:content', ns)
        if content_elem is not None:
            article_dict['content'] = content_elem.text.strip() if content_elem.text else ""
            article_dict['content_type'] = content_elem.get('type', 'text/plain')
        else:
            article_dict['content'] = ""
            article_dict['content_type'] = ""

        # Hatena specific formatted content
        formatted_content_elem = root.find('hatena:formatted-content', ns)
        if formatted_content_elem is not None:
            article_dict['formatted_content'] = formatted_content_elem.text.strip() if formatted_content_elem.text else ""
            article_dict['formatted_content_type'] = formatted_content_elem.get('type', 'text/html')


        article_dict['author_name'] = find_text(root, 'atom:author/atom:name', ns)
        article_dict['updated'] = find_text(root, 'atom:updated', ns)
        article_dict['published'] = find_text(root, 'atom:published', ns) # Might not always be present

        # Links
        article_dict['links'] = []
        for link_el in root.findall('atom:link', ns):
            article_dict['links'].append({'rel': link_el.get('rel'), 'href': link_el.get('href'), 'type': link_el.get('type')})

        # Find specific links for convenience
        article_dict['alternate_url'] = next((l['href'] for l in article_dict['links'] if l['rel'] == 'alternate'), "")
        article_dict['edit_url'] = next((l['href'] for l in article_dict['links'] if l['rel'] == 'edit'), "")


        # Categories (Tags)
        article_dict['tags'] = [cat.get('term', '') for cat in root.findall('atom:category', ns) if cat.get('term')]

        # Draft status (app:control/app:draft)
        draft_elem = root.find('app:control/app:draft', ns)
        if draft_elem is not None and draft_elem.text:
            article_dict['is_draft'] = draft_elem.text.lower() == 'yes'
        else:
            article_dict['is_draft'] = False # Assume not draft if element is missing

        article_dict['raw_xml'] = entry_xml_text # Include the raw XML for further processing if needed

        logger.info(f"Parsed article: ID {article_dict.get('id', '')[:50]}, Title: {article_dict.get('title', '')[:50]}")
        return article_dict

    except ET.ParseError as e:
        logger.error(f"XML Parse Error for Hatena entry: {e}")
        return {"error": "XML Parse Error", "details": str(e), "raw_xml": entry_xml_text}
    except Exception as e:
        logger.error(f"Unexpected error parsing Hatena entry XML: {e}", exc_info=True)
        return {"error": "Unexpected parsing error", "details": str(e), "raw_xml": entry_xml_text}
# --- End of Helper Functions ---

def get_hatena_article(
    hatena_id: str,
    blog_id: str,
    api_key: str,
    entry_id: str, # The numeric ID of the article to fetch
    request_timeout: int = 30
) -> Optional[Dict[str, Any]]:
    """
    Retrieves a specific article from Hatena Blog using the AtomPub API.

    Args:
        hatena_id (str): Your Hatena ID.
        blog_id (str): Your Hatena Blog ID (e.g., yourblog.hatenablog.com).
        api_key (str): Your Hatena Blog API key.
        entry_id (str): The numeric ID of the Hatena blog entry to retrieve.
        request_timeout (int, optional): Timeout for the HTTP request in seconds.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the article details
                                  (parsed from Atom XML) if successful, None otherwise.
                                  The dictionary includes keys like 'id', 'title', 'content',
                                  'author_name', 'updated', 'published', 'links', 'tags',
                                  'is_draft', 'formatted_content', and 'raw_xml'.
    """
    base_api_url = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_id}/atom"

    numeric_entry_id = entry_id
    if entry_id.startswith('tag:blog.hatena.ne.jp'):
        try:
            numeric_entry_id = entry_id.split('-')[-1]
            if not numeric_entry_id.isdigit(): raise ValueError("Extracted part not numeric.")
        except (IndexError, ValueError) as e:
            logger.error(f"Invalid Hatena entry_id format: {entry_id}. Error: {e}")
            return None
    elif not entry_id.isdigit():
        logger.error(f"Invalid Hatena entry_id: {entry_id}. Expected numeric ID or full tag URI.")
        return None

    get_url = f"{base_api_url}/entry/{numeric_entry_id}"

    headers = {
        'X-WSSE': _create_hatena_wsse_header_for_get(hatena_id, api_key)
        # 'Accept': 'application/atom+xml' # Good practice, though often not strictly needed by Hatena
    }

    try:
        logger.info(f"Fetching article ID {numeric_entry_id} from Hatena Blog...")
        response = requests.get(get_url, headers=headers, timeout=request_timeout)
        response.raise_for_status() # Raises HTTPError for bad responses

        if response.status_code == 200:
            logger.info(f"Successfully fetched article ID {numeric_entry_id}.")
            # The response is an Atom entry XML document
            return _parse_hatena_entry_xml_to_dict(response.text)
        else:
            # Should be caught by raise_for_status
            logger.error(f"Hatena API unexpected success status for GET: {response.status_code} - {response.text[:200]}")
            return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Article ID {numeric_entry_id} not found on Hatena Blog (404).")
        else:
            logger.error(f"Hatena API HTTP Error on GET: {e.response.status_code} - {e.response.text[:200]}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Hatena API Request Exception on GET: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during Hatena article retrieval: {e}", exc_info=True)

    return None

# Example Usage
if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO)

    try:
        HATENA_USER_ID = os.environ["HATENA_USER_ID"]
        HATENA_BLOG_NAME = os.environ["HATENA_BLOG_NAME"]
        HATENA_API_KEY_VAL = os.environ["HATENA_API_KEY"]
        EXISTING_ARTICLE_ID_GET = os.environ.get("HATENA_EXISTING_ARTICLE_ID_FOR_TEST") # Same as for update test
    except KeyError:
        print("Please set HATENA_USER_ID, HATENA_BLOG_NAME, HATENA_API_KEY, and optionally HATENA_EXISTING_ARTICLE_ID_FOR_TEST environment variables.")
        exit(1)

    if not EXISTING_ARTICLE_ID_GET:
        print("HATENA_EXISTING_ARTICLE_ID_FOR_TEST not set. Skipping get_article test.")
    else:
        print(f"--- Test Case 1: Get existing article ID: {EXISTING_ARTICLE_ID_GET} ---")
        article_data = get_hatena_article(
            hatena_id=HATENA_USER_ID,
            blog_id=HATENA_BLOG_NAME,
            api_key=HATENA_API_KEY_VAL,
            entry_id=EXISTING_ARTICLE_ID_GET
        )

        if article_data and not article_data.get("error"):
            print("Article retrieved successfully:")
            print(f"  ID (from XML): {article_data.get('id')}")
            print(f"  Title: {article_data.get('title')}")
            print(f"  Author: {article_data.get('author_name')}")
            print(f"  Updated: {article_data.get('updated')}")
            print(f"  Published: {article_data.get('published')}")
            print(f"  Alternate URL: {article_data.get('alternate_url')}")
            print(f"  Edit URL: {article_data.get('edit_url')}")
            print(f"  Tags: {article_data.get('tags')}")
            print(f"  Is Draft: {article_data.get('is_draft')}")
            print(f"  Content Type: {article_data.get('content_type')}")
            print(f"  Content (first 100 chars): {article_data.get('content', '')[:100]}...")
            if article_data.get('formatted_content'):
                 print(f"  Formatted Content (first 100 chars): {article_data.get('formatted_content', '')[:100]}...")
        elif article_data and article_data.get("error"):
            print(f"Failed to parse article data: {article_data.get('error')} - {article_data.get('details')}")
        else:
            print(f"Failed to retrieve article ID {EXISTING_ARTICLE_ID_GET}.")

    print("\n--- Test Case 2: Try to get a non-existent article ---")
    non_existent_id = "0000000000000000000" # Highly unlikely to exist
    article_data_non_existent = get_hatena_article(
        hatena_id=HATENA_USER_ID,
        blog_id=HATENA_BLOG_NAME,
        api_key=HATENA_API_KEY_VAL,
        entry_id=non_existent_id
    )
    if article_data_non_existent is None:
        print(f"Correctly failed to retrieve non-existent article ID {non_existent_id} (or an error occurred).")
    else:
        print(f"Unexpectedly retrieved data for non-existent ID {non_existent_id}: {article_data_non_existent.get('title')}")

    print("\nNote: To run Test Case 1, you need a pre-existing article on your Hatena blog")
    print("and its numeric ID set in the HATENA_EXISTING_ARTICLE_ID_FOR_TEST environment variable.")
