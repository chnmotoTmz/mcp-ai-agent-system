import logging
import requests
import hashlib
import random
import base64
from datetime import datetime
from xml.etree import ElementTree as ET
from typing import Dict, Optional, List, Any, Tuple # Added Tuple

logger = logging.getLogger(__name__)

# --- Helper functions (copied for self-containment) ---
def _create_hatena_wsse_header_for_list(hatena_id: str, api_key: str) -> str:
    """Creates a WSSE authentication header."""
    nonce = hashlib.sha1(str(random.random()).encode('utf-8')).digest()
    now_utc = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    password_digest = hashlib.sha1(nonce + now_utc.encode('utf-8') + api_key.encode('utf-8')).digest()
    return (f'UsernameToken Username="{hatena_id}", PasswordDigest="{base64.b64encode(password_digest).decode("utf-8")}", Nonce="{base64.b64encode(nonce).decode("utf-8")}", Created="{now_utc}"')

def _parse_hatena_atom_feed(feed_xml_text: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Parses a Hatena AtomPub feed XML string into a list of article dictionaries
    and extracts the 'next' page URL if available.

    Each article dictionary contains common fields like id, title, author_name,
    updated, published, alternate_url, edit_url, and categories (tags).
    """
    articles: List[Dict[str, Any]] = []
    next_page_url: Optional[str] = None
    try:
        root = ET.fromstring(feed_xml_text)
        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'app': 'http://www.w3.org/2007/app',
            'hatena': 'http://www.hatena.ne.jp/info/xmlns#'
        }

        # Find 'next' link for pagination
        next_link_el = root.find('atom:link[@rel="next"]', ns)
        if next_link_el is not None:
            next_page_url = next_link_el.get('href')

        for entry_el in root.findall('atom:entry', ns):
            article_dict: Dict[str, Any] = {}

            def find_text(element, path): return (el.text.strip() if el is not None and el.text else "" for el in [element.find(path, ns)]).__next__()
            def find_attr(element, path, attr_name): return (el.get(attr_name) if el is not None else "" for el in [element.find(path, ns)]).__next__()

            article_dict['id_uri'] = find_text(entry_el, 'atom:id') # Full ID URI
            # Extract numeric ID from the full ID URI if possible
            try:
                article_dict['numeric_id'] = article_dict['id_uri'].split('/')[-1].split('-')[-1] if article_dict['id_uri'] else ""
            except IndexError:
                article_dict['numeric_id'] = "" # Fallback if parsing fails

            article_dict['title'] = find_text(entry_el, 'atom:title')
            article_dict['author_name'] = find_text(entry_el, 'atom:author/atom:name')
            article_dict['updated'] = find_text(entry_el, 'atom:updated')
            article_dict['published'] = find_text(entry_el, 'atom:published')

            article_links = []
            for link_el in entry_el.findall('atom:link', ns):
                article_links.append({'rel': link_el.get('rel'), 'href': link_el.get('href'), 'type': link_el.get('type')})
            article_dict['links'] = article_links
            article_dict['alternate_url'] = next((l['href'] for l in article_links if l['rel'] == 'alternate'), "")
            article_dict['edit_url'] = next((l['href'] for l in article_links if l['rel'] == 'edit'), "")

            article_dict['tags'] = [cat.get('term', '') for cat in entry_el.findall('atom:category', ns) if cat.get('term')]

            summary_el = entry_el.find('atom:summary', ns) # Summary is optional
            if summary_el is not None and summary_el.text:
                article_dict['summary'] = summary_el.text.strip()
                article_dict['summary_type'] = summary_el.get('type', 'text')
            else: # Try content if summary is not present
                content_el = entry_el.find('atom:content', ns)
                if content_el is not None and content_el.text:
                    summary_text = content_el.text.strip()
                    article_dict['summary'] = summary_text[:200] + "..." if len(summary_text) > 200 else summary_text
                    article_dict['summary_type'] = "truncated_content"


            draft_elem = entry_el.find('app:control/app:draft', ns)
            article_dict['is_draft'] = draft_elem is not None and draft_elem.text.lower() == 'yes'

            articles.append(article_dict)

        logger.info(f"Parsed {len(articles)} articles from feed. Next page: {next_page_url or 'None'}")
        return articles, next_page_url

    except ET.ParseError as e:
        logger.error(f"XML Parse Error for Hatena feed: {e}")
        return [], None # Return empty list and no next page on parse error
    except Exception as e:
        logger.error(f"Unexpected error parsing Hatena feed XML: {e}", exc_info=True)
        return [], None
# --- End of Helper Functions ---

def get_hatena_articles_list(
    hatena_id: str,
    blog_id: str,
    api_key: str,
    page_url: Optional[str] = None, # For fetching subsequent pages
    request_timeout: int = 30
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Retrieves a list of articles from Hatena Blog using the AtomPub API.
    Supports pagination via the `page_url` argument.

    Args:
        hatena_id (str): Your Hatena ID.
        blog_id (str): Your Hatena Blog ID.
        api_key (str): Your Hatena Blog API key.
        page_url (Optional[str]): The URL for the specific page of results to fetch.
                                  If None, fetches the first page.
        request_timeout (int): Timeout for the HTTP request.

    Returns:
        Tuple[List[Dict[str, Any]], Optional[str]]:
            A tuple containing:
            - A list of dictionaries, where each dictionary represents an article's metadata.
            - An optional string URL for the 'next' page of results, if available.
              Returns ([], None) on failure.
    """
    if page_url:
        # If a specific page_url is provided, use it directly.
        # Ensure it's for the correct blog, but typically it comes from a previous response.
        target_url = page_url
    else:
        # Construct the URL for the first page of the collection feed.
        base_api_url = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_id}/atom"
        target_url = f"{base_api_url}/entry"

    headers = {
        'X-WSSE': _create_hatena_wsse_header_for_list(hatena_id, api_key)
    }

    try:
        logger.info(f"Fetching articles list from Hatena Blog: {target_url}")
        response = requests.get(target_url, headers=headers, timeout=request_timeout)
        response.raise_for_status()

        if response.status_code == 200:
            logger.info(f"Successfully fetched article feed from {target_url}.")
            return _parse_hatena_atom_feed(response.text)
        else:
            logger.error(f"Hatena API unexpected status for feed: {response.status_code} - {response.text[:200]}")
            return [], None

    except requests.exceptions.HTTPError as e:
        logger.error(f"Hatena API HTTP Error for feed: {e.response.status_code} - {e.response.text[:200]}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Hatena API Request Exception for feed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during Hatena articles list retrieval: {e}", exc_info=True)

    return [], None # Default return for any failure

# Example Usage
if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO)

    try:
        HATENA_USER_ID = os.environ["HATENA_USER_ID"]
        HATENA_BLOG_NAME = os.environ["HATENA_BLOG_NAME"]
        HATENA_API_KEY_VAL = os.environ["HATENA_API_KEY"]
    except KeyError:
        print("Please set HATENA_USER_ID, HATENA_BLOG_NAME, and HATENA_API_KEY environment variables to run example.")
        exit(1)

    print(f"--- Test Case: Get first page of articles ---")
    articles_page1, next_page1_url = get_hatena_articles_list(
        hatena_id=HATENA_USER_ID,
        blog_id=HATENA_BLOG_NAME,
        api_key=HATENA_API_KEY_VAL
    )

    if articles_page1:
        print(f"Retrieved {len(articles_page1)} articles from the first page:")
        for i, article in enumerate(articles_page1[:3]): # Print details of first 3
            print(f"  Article {i+1}:")
            print(f"    Title: {article.get('title')}")
            print(f"    Numeric ID: {article.get('numeric_id')}")
            print(f"    URL: {article.get('alternate_url')}")
            print(f"    Updated: {article.get('updated')}")
            print(f"    Tags: {article.get('tags')}")
            print(f"    Is Draft: {article.get('is_draft')}")
            print(f"    Summary (first 50): {article.get('summary', '')[:50]}...")

        if next_page1_url:
            print(f"\nNext page URL found: {next_page1_url}")
            print(f"--- Test Case: Get second page of articles (if available) ---")
            articles_page2, next_page2_url = get_hatena_articles_list(
                hatena_id=HATENA_USER_ID,
                blog_id=HATENA_BLOG_NAME,
                api_key=HATENA_API_KEY_VAL,
                page_url=next_page1_url # Use the 'next' URL from previous call
            )
            if articles_page2:
                print(f"Retrieved {len(articles_page2)} articles from the second page.")
                # You can print details similarly if needed
            elif next_page1_url: # next_page1_url was present but fetching failed
                 print(f"Failed to retrieve second page using URL: {next_page1_url}")

        else:
            print("\nNo next page URL found (or only one page of articles).")
    else:
        print("Failed to retrieve any articles from the first page.")

    print("\nNote: This example fetches a list of articles. The number of articles per page is determined by Hatena.")
