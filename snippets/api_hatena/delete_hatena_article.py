import logging
import requests
import hashlib
import random
import base64
from datetime import datetime
from typing import Dict, Optional # Added Optional

logger = logging.getLogger(__name__)

# --- Helper function (copied for self-containment) ---
def _create_hatena_wsse_header_for_delete(hatena_id: str, api_key: str) -> str:
    """Creates a WSSE authentication header."""
    nonce = hashlib.sha1(str(random.random()).encode('utf-8')).digest()
    now_utc = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    password_digest = hashlib.sha1(nonce + now_utc.encode('utf-8') + api_key.encode('utf-8')).digest()
    return (f'UsernameToken Username="{hatena_id}", PasswordDigest="{base64.b64encode(password_digest).decode("utf-8")}", Nonce="{base64.b64encode(nonce).decode("utf-8")}", Created="{now_utc}"')
# --- End of Helper Function ---

def delete_hatena_article(
    hatena_id: str,
    blog_id: str,
    api_key: str,
    entry_id: str, # The numeric ID of the article to delete
    request_timeout: int = 30
) -> bool:
    """
    Deletes a specific article from Hatena Blog using the AtomPub API.

    Args:
        hatena_id (str): Your Hatena ID.
        blog_id (str): Your Hatena Blog ID (e.g., yourblog.hatenablog.com).
        api_key (str): Your Hatena Blog API key.
        entry_id (str): The numeric ID of the Hatena blog entry to delete.
        request_timeout (int, optional): Timeout for the HTTP request in seconds.

    Returns:
        bool: True if the article was deleted successfully, False otherwise.
    """
    base_api_url = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_id}/atom"

    numeric_entry_id = entry_id
    if entry_id.startswith('tag:blog.hatena.ne.jp'):
        try:
            numeric_entry_id = entry_id.split('-')[-1]
            if not numeric_entry_id.isdigit(): raise ValueError("Extracted part not numeric.")
        except (IndexError, ValueError) as e:
            logger.error(f"Invalid Hatena entry_id format for delete: {entry_id}. Error: {e}")
            return False
    elif not entry_id.isdigit():
        logger.error(f"Invalid Hatena entry_id for delete: {entry_id}. Expected numeric ID or full tag URI.")
        return False

    delete_url = f"{base_api_url}/entry/{numeric_entry_id}"

    headers = {
        'X-WSSE': _create_hatena_wsse_header_for_delete(hatena_id, api_key)
    }

    try:
        logger.info(f"Attempting to delete article ID {numeric_entry_id} from Hatena Blog...")
        response = requests.delete(delete_url, headers=headers, timeout=request_timeout)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

        if response.status_code == 204 or response.status_code == 200: # 204 No Content is common for DELETE, 200 OK also possible
            logger.info(f"Article ID {numeric_entry_id} deleted successfully from Hatena Blog.")
            return True
        else:
            # Should be caught by raise_for_status
            logger.error(f"Hatena API unexpected success status for DELETE: {response.status_code} - {response.text[:200]}")
            return False

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Article ID {numeric_entry_id} not found for deletion (404). Assuming already deleted or incorrect ID.")
            return True # Or False, depending on desired idempotency behavior. True if "is not there" is success.
        else:
            logger.error(f"Hatena API HTTP Error on DELETE: {e.response.status_code} - {e.response.text[:200]}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Hatena API Request Exception on DELETE: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during Hatena article deletion: {e}", exc_info=True)
        return False

# Example Usage
if __name__ == "__main__":
    import os
    # For testing deletion, it's good to first publish an article and then delete it.
    # We'll reuse the publish_hatena_article snippet for this.
    # This requires 'publish_hatena_article.py' to be in the same directory or accessible in PYTHONPATH.
    try:
        # Assuming publish_hatena_article.py is in the same directory for testing
        from publish_hatena_article import publish_hatena_article
        can_test_publish = True
    except ImportError:
        print("Skipping full delete test: `publish_hatena_article` snippet not found.")
        print("You can manually create an article and set HATENA_ARTICLE_ID_TO_DELETE to test deletion.")
        can_test_publish = False
        # publish_hatena_article = None # Ensure it's None

    logging.basicConfig(level=logging.INFO)

    try:
        HATENA_USER_ID = os.environ["HATENA_USER_ID"]
        HATENA_BLOG_NAME = os.environ["HATENA_BLOG_NAME"]
        HATENA_API_KEY_VAL = os.environ["HATENA_API_KEY"]
        # Optional: Set this env var to an ID you want to delete manually for testing
        MANUAL_ARTICLE_ID_TO_DELETE = os.environ.get("HATENA_ARTICLE_ID_TO_DELETE")
    except KeyError:
        print("Please set HATENA_USER_ID, HATENA_BLOG_NAME, and HATENA_API_KEY environment variables.")
        exit(1)

    article_to_delete_id = None

    if can_test_publish:
        print("--- Test Case 1: Publish an article to be deleted ---")
        temp_title = f"Article for Deletion Test - {datetime.now().strftime('%Y%m%d%H%M%S')}"
        temp_content = "<p>This article will be deleted by the test script.</p>"

        # Use the imported publish function
        # Ensure it's callable, otherwise skip this part
        if callable(publish_hatena_article):
            publish_result = publish_hatena_article(
                hatena_id=HATENA_USER_ID,
                blog_id=HATENA_BLOG_NAME,
                api_key=HATENA_API_KEY_VAL,
                title=temp_title,
                content_body=temp_content,
                tags=["delete-test"],
                draft=True, # Post as draft
                content_type="text/html"
            )

            if publish_result and publish_result.get('id'):
                article_to_delete_id = publish_result.get('id') # This will be the full tag URI
                # Extract numeric part for deletion if needed, or let delete_hatena_article handle it
                if article_to_delete_id.startswith('tag:'):
                     numeric_id_part = article_to_delete_id.split('-')[-1]
                     if numeric_id_part.isdigit():
                         article_to_delete_id = numeric_id_part # Use numeric ID for deletion

                print(f"Temporary article published for deletion test. Numeric ID: {article_to_delete_id}")
            else:
                print("Failed to publish temporary article for deletion test. Skipping deletion of temp article.")
        else:
            print("publish_hatena_article is not callable. Skipping publish step for delete test.")


    if not article_to_delete_id and MANUAL_ARTICLE_ID_TO_DELETE:
        print(f"--- Using manually specified article ID for deletion: {MANUAL_ARTICLE_ID_TO_DELETE} ---")
        article_to_delete_id = MANUAL_ARTICLE_ID_TO_DELETE

    if article_to_delete_id:
        print(f"\n--- Attempting to delete article ID: {article_to_delete_id} ---")
        # User confirmation before actual deletion in a test script is good practice
        # For automated tests, you might skip this.
        # confirm = input(f"Really delete article ID {article_to_delete_id}? (yes/no): ")
        # if confirm.lower() == 'yes':
        delete_success = delete_hatena_article(
            hatena_id=HATENA_USER_ID,
            blog_id=HATENA_BLOG_NAME,
            api_key=HATENA_API_KEY_VAL,
            entry_id=article_to_delete_id # Pass the numeric ID
        )
        if delete_success:
            print(f"Article ID {article_to_delete_id} was successfully deleted (or was already not found).")
        else:
            print(f"Failed to delete article ID {article_to_delete_id}.")
        # else:
        #     print("Deletion cancelled by user.")
    else:
        print("\nNo article ID available for deletion test (either temp publish failed or manual ID not set).")

    print("\n--- Test Case 2: Try to delete a non-existent article ---")
    non_existent_id_del = "0000000000000000001" # Highly unlikely to exist
    delete_non_existent_success = delete_hatena_article(
        hatena_id=HATENA_USER_ID,
        blog_id=HATENA_BLOG_NAME,
        api_key=HATENA_API_KEY_VAL,
        entry_id=non_existent_id_del
    )
    if delete_non_existent_success: # If 404 is treated as success (not there)
        print(f"Attempt to delete non-existent article ID {non_existent_id_del} handled as 'not found' (success).")
    else:
        # This might happen if there was an auth error or other non-404 HTTP error
        print(f"Attempt to delete non-existent article ID {non_existent_id_del} failed unexpectedly or did not return True on 404.")

    print("\nNote: Deletion is a permanent action. Test with care, preferably on a test blog or with drafts.")
