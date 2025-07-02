import logging
import os
import requests # For making HTTP requests
import json # For handling JSON data
from typing import Dict, Optional, Any, List # Added List

# Google OAuth related imports
# These are needed if the snippet itself handles token loading/refreshing.
# For a simpler snippet, we might assume credentials object is passed in.
try:
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2.credentials import Credentials as GoogleCredentials
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GoogleAuthRequest = None # type: ignore
    GoogleCredentials = None # type: ignore
    GOOGLE_AUTH_AVAILABLE = False
    logging.warning("Google Auth libraries not found. Snippet will rely on fully configured credentials object if used.")

logger = logging.getLogger(__name__)

# Google Photos API Scopes required for uploading and basic access
# (appendonly is usually sufficient for just uploading)
DEFAULT_PHOTOS_SCOPES = ['https://www.googleapis.com/auth/photoslibrary.appendonly']


def _refresh_google_credentials(credentials: Any) -> Optional[Any]:
    """
    Refreshes Google OAuth2 credentials if they are expired and refreshable.
    Args:
        credentials: A google.oauth2.credentials.Credentials object.
    Returns:
        The refreshed credentials object, or None if refresh fails or not possible.
    """
    if not GOOGLE_AUTH_AVAILABLE or not credentials:
        return None
    if credentials.expired and credentials.refresh_token:
        try:
            logger.info("Google Photos API credentials expired, attempting refresh...")
            credentials.refresh(GoogleAuthRequest())
            logger.info("Credentials refreshed successfully.")
            return credentials
        except Exception as e:
            logger.error(f"Failed to refresh Google Photos API credentials: {e}", exc_info=True)
            return None
    elif not credentials.valid:
        logger.warning("Google Photos API credentials are not valid and cannot be refreshed (no refresh token or other issue).")
        return None
    return credentials # Credentials are valid or not refreshable but also not expired.

def _upload_bytes_to_google_photos(
    credentials: Any, # google.oauth2.credentials.Credentials
    image_path: str,
    album_id: Optional[str] = None # Optional: to add to a specific album directly
) -> Optional[str]:
    """
    Uploads image bytes to Google Photos and returns an upload token.
    This is the first step in adding an image to the library.
    """
    if not credentials or not credentials.token:
        logger.error("Cannot upload bytes: Missing Google API credentials or token.")
        return None

    try:
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
    except FileNotFoundError:
        logger.error(f"Image file not found at: {image_path}")
        return None
    except Exception as e:
        logger.error(f"Error reading image file {image_path}: {e}", exc_info=True)
        return None

    upload_url = 'https://photoslibrary.googleapis.com/v1/uploads'
    headers = {
        'Authorization': f'Bearer {credentials.token}',
        'Content-type': 'application/octet-stream',
        'X-Goog-Upload-Protocol': 'raw',
        'X-Goog-Upload-File-Name': os.path.basename(image_path)
        # Consider adding 'X-Goog-Upload-Content-Type': 'image/jpeg' or other mime type
    }

    try:
        logger.info(f"Uploading image bytes from {image_path} to Google Photos...")
        response = requests.post(upload_url, data=image_data, headers=headers, timeout=60) # Increased timeout
        response.raise_for_status() # Check for HTTP errors

        upload_token = response.text # This is the raw upload token
        logger.info(f"Image bytes uploaded successfully. Upload token: {upload_token[:20]}...")
        return upload_token
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error uploading bytes to Google Photos: {e.response.status_code} - {e.response.text[:200]}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception uploading bytes: {e}")
    except Exception as e:
        logger.error(f"Unexpected error uploading bytes: {e}", exc_info=True)
    return None

def _create_media_item_google_photos(
    credentials: Any, # google.oauth2.credentials.Credentials
    upload_token: str,
    description: str = "",
    album_id: Optional[str] = None,
    file_name: Optional[str] = None # Optional: for the media item
) -> Optional[Dict[str, Any]]:
    """
    Creates a media item in Google Photos library using an upload token.
    This is the second step after uploading bytes.
    """
    if not credentials or not credentials.token:
        logger.error("Cannot create media item: Missing Google API credentials or token.")
        return None

    media_creation_url = 'https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate'
    headers = {
        'Authorization': f'Bearer {credentials.token}',
        'Content-type': 'application/json',
    }

    new_media_item: Dict[str, Any] = {
        'description': description,
        'simpleMediaItem': {'uploadToken': upload_token}
    }
    if file_name: # Add filename if provided
        new_media_item['simpleMediaItem']['fileName'] = file_name

    payload: Dict[str, Any] = {'newMediaItems': [new_media_item]}
    if album_id: # If album_id is provided, add to that album
        payload['albumId'] = album_id
        # payload['albumPosition'] = {'position': 'LAST_IN_ALBUM'} # Example position

    try:
        logger.info(f"Creating media item in Google Photos with token {upload_token[:20]}...")
        response = requests.post(media_creation_url, data=json.dumps(payload), headers=headers, timeout=30)
        response.raise_for_status()

        response_json = response.json()
        # batchCreate returns a list of newMediaItemResults
        if response_json.get('newMediaItemResults') and len(response_json['newMediaItemResults']) > 0:
            item_result = response_json['newMediaItemResults'][0]
            if item_result.get('status', {}).get('message', '').lower() == 'success' or \
               item_result.get('status', {}).get('code', -1) == 0: # Check for gRPC OK status
                media_item_data = item_result.get('mediaItem', {})
                logger.info(f"Media item created successfully. ID: {media_item_data.get('id')}")
                return media_item_data # This dict contains id, productUrl, baseUrl, etc.
            else:
                error_detail = item_result.get('status', {})
                logger.error(f"Failed to create media item, status: {error_detail.get('message', 'Unknown error')}, code: {error_detail.get('code')}")
                return {"error": "Media item creation failed", "details": error_detail}
        else:
            logger.error(f"Unexpected response format from mediaItems:batchCreate: {response_json}")
            return {"error": "Unexpected response from media item creation"}

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error creating media item: {e.response.status_code} - {e.response.text[:200]}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception creating media item: {e}")
    except Exception as e:
        logger.error(f"Unexpected error creating media item: {e}", exc_info=True)
    return None


def upload_image_to_google_photos(
    credentials_path_or_obj: Union[str, Any], # Path to token.json or Credentials object
    image_path: str,
    description: str = "",
    album_id: Optional[str] = None, # Optional: ID of an album to add the image to
    scopes: List[str] = None # Optional: if creating Credentials from file
) -> Optional[Dict[str, Any]]:
    """
    Uploads an image to Google Photos library.
    Handles loading/refreshing credentials, uploading bytes, and creating media item.

    Args:
        credentials_path_or_obj (Union[str, Any]): Path to the Google OAuth token file (e.g., "token.json")
                                                   OR an already instantiated `google.oauth2.credentials.Credentials` object.
        image_path (str): Path to the image file to upload.
        description (str, optional): Description for the image in Google Photos.
        album_id (Optional[str], optional): If provided, adds the uploaded image to this album.
        scopes (List[str], optional): Scopes to use if loading credentials from a file.
                                      Defaults to DEFAULT_PHOTOS_SCOPES.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing details of the uploaded media item
                                  (id, productUrl, baseUrl, etc.) if successful,
                                  or a dictionary with an "error" key on failure, or None.
    """
    if scopes is None:
        scopes = DEFAULT_PHOTOS_SCOPES

    creds: Optional[Any] = None # google.oauth2.credentials.Credentials
    if isinstance(credentials_path_or_obj, str):
        if not GOOGLE_AUTH_AVAILABLE:
            logger.error("Google Auth libraries not available to load credentials from path.")
            return {"error": "Google Auth library not found."}
        if os.path.exists(credentials_path_or_obj):
            try:
                creds = GoogleCredentials.from_authorized_user_file(credentials_path_or_obj, scopes)
            except Exception as e:
                logger.error(f"Failed to load Google credentials from {credentials_path_or_obj}: {e}", exc_info=True)
                return {"error": f"Failed to load credentials: {e}"}
        else:
            logger.error(f"Google credentials file not found at: {credentials_path_or_obj}")
            return {"error": "Credentials file not found."}
    elif GOOGLE_AUTH_AVAILABLE and isinstance(credentials_path_or_obj, GoogleCredentials):
        creds = credentials_path_or_obj
    elif hasattr(credentials_path_or_obj, 'token') and hasattr(credentials_path_or_obj, 'valid'): # Duck typing
        creds = credentials_path_or_obj
    else:
        logger.error("Invalid credentials_path_or_obj provided. Must be path string or Credentials object.")
        return {"error": "Invalid credentials format."}

    if not creds: # If still no creds after trying to load/assign
        return {"error": "Credentials could not be established."}

    # Refresh credentials if necessary
    refreshed_creds = _refresh_google_credentials(creds)
    if not refreshed_creds or not refreshed_creds.valid:
        logger.error("Google Photos API authentication failed or credentials invalid after refresh attempt.")
        return {"error": "Authentication failed or credentials invalid."}

    # 1. Upload image bytes
    base_filename = os.path.basename(image_path)
    upload_token = _upload_bytes_to_google_photos(refreshed_creds, image_path, album_id)
    if not upload_token:
        return {"error": "Failed to get upload token from Google Photos."}

    # 2. Create media item
    media_item_details = _create_media_item_google_photos(
        credentials=refreshed_creds,
        upload_token=upload_token,
        description=description,
        album_id=album_id,
        file_name=base_filename
    )

    if media_item_details and not media_item_details.get("error"):
        logger.info(f"Image '{base_filename}' uploaded successfully to Google Photos. ID: {media_item_details.get('id')}")
        return {
            "success": True,
            "media_item": media_item_details # Contains id, productUrl, baseUrl, mimeType, mediaMetadata, filename
        }
    else:
        err_msg = "Failed to create media item in Google Photos."
        if media_item_details and media_item_details.get("details"):
            err_msg += f" Details: {media_item_details['details']}"
        return {"success": False, "error": err_msg, "upload_token": upload_token}


# Example Usage (requires a token.json or valid credentials object, and a test image)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Prerequisites for testing ---
    # 1. Ensure Google Auth libraries are installed: pip install google-auth google-auth-oauthlib google-auth-httplib2 requests
    # 2. Authenticate and get a `token.json`:
    #    You'd typically run a script like the `setup_google_photos.py` (from original repo)
    #    or a similar OAuth flow to generate `token.json` with the photoslibrary.appendonly scope.
    #    Place `token.json` in the same directory as this script, or provide its path.
    # 3. Create a dummy image file for testing.

    TEST_TOKEN_FILE = "google_photos_token.json" # Assumed to be created by an auth script
    TEST_IMAGE_FILE = "test_google_photos_upload.jpg"

    if not GOOGLE_AUTH_AVAILABLE:
        print("Google Auth libraries are not installed. Skipping Google Photos upload test.")
    elif not os.path.exists(TEST_TOKEN_FILE):
        print(f"{TEST_TOKEN_FILE} not found. Please authenticate first to run this example.")
        print("You might need to run an authentication script like the one from the original project,")
        print("or adapt the `setup_authentication` method from the original GooglePhotosService.")
    else:
        # Create a dummy image if it doesn't exist
        if not os.path.exists(TEST_IMAGE_FILE):
            try:
                from PIL import Image as PILImage # Local import for test setup
                img = PILImage.new('RGB', (100, 100), color = 'red')
                img.save(TEST_IMAGE_FILE)
                print(f"Created dummy test image: {TEST_IMAGE_FILE}")
            except ImportError:
                print("Pillow not installed. Cannot create dummy image. Please create one manually.")
                # exit(1) # Or skip test if image can't be created
            except Exception as e:
                print(f"Error creating dummy image: {e}")
                # exit(1)


        if os.path.exists(TEST_IMAGE_FILE):
            print(f"\n--- Test Case 1: Upload image '{TEST_IMAGE_FILE}' to Google Photos library ---")
            upload_result = upload_image_to_google_photos(
                credentials_path_or_obj=TEST_TOKEN_FILE,
                image_path=TEST_IMAGE_FILE,
                description="Test upload from snippet " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # album_id="YOUR_ALBUM_ID_HERE" # Optional: test adding to an album
            )

            if upload_result and upload_result.get("success"):
                print("Image uploaded successfully to Google Photos!")
                print("Media Item Details:")
                print(json.dumps(upload_result.get("media_item"), indent=2))
                # You can check the productUrl in your browser
            else:
                print("Failed to upload image to Google Photos.")
                print(f"Error details: {upload_result.get('error') if upload_result else 'Unknown error'}")
        else:
            print(f"Test image {TEST_IMAGE_FILE} not found. Skipping upload test.")

        # Clean up dummy image
        # if os.path.exists(TEST_IMAGE_FILE) and "dummy" in TEST_IMAGE_FILE: # Be careful with auto-delete
        #     os.remove(TEST_IMAGE_FILE)
        #     print(f"Removed dummy test image: {TEST_IMAGE_FILE}")

    print("\nNote: This test requires valid Google Photos API credentials (token.json).")
    print("Ensure the 'photoslibrary.appendonly' (or broader) scope was granted during auth.")
