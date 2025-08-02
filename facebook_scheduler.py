# D:\Facebook_Posts_generation\facebook_scheduler.py

import sys
import os
import requests
import json
import time
import re
from datetime import datetime

import database_manager # Import your database manager
import facebook_metrics_gui_helpers # For Facebook API calls

# --- Debugging setup ---
DEBUG_SCHEDULER_MODE = True

def debug_scheduler_print(message):
    if DEBUG_SCHEDULER_MODE:
        print(f"[DEBUG - Scheduler]: {message}")

def post_to_facebook(post_data, base_output_dir): # Renamed output_dir to base_output_dir for clarity
    """
    Posts content to Facebook using the Graph API.
    post_data is expected to be a dictionary with all post details.
    """
    db_id = post_data.get('id')
    page_name = post_data.get('page_name')
    content_en = post_data.get('content_en')
    content_ar = post_data.get('content_ar')
    generated_image_filename = post_data.get('generated_image_filename')
    facebook_page_id = post_data.get('facebook_page_id')
    access_token = post_data.get('facebook_access_token')

    debug_scheduler_print(f"Attempting to post DB ID {db_id} to page '{page_name}'.")

    if not facebook_page_id or not access_token:
        print(f"ERROR: Failed to schedule Post ID {db_id}: Missing Facebook Page ID or Access Token for page '{page_name}'.")
        return False, None

    # Determine which content to post based on language
    message_to_post = ""
    if post_data.get('language') == "English" and content_en:
        message_to_post = content_en
    elif post_data.get('language') == "Arabic" and content_ar:
        message_to_post = content_ar
    elif post_data.get('language') == "Both":
        if content_en and content_ar:
            message_to_post = f"{content_en}\n\n{content_ar}" # Combine both languages
        elif content_en:
            message_to_post = content_en
        elif content_ar:
            message_to_post = content_ar
    
    if not message_to_post:
        print(f"ERROR: Failed to schedule Post ID {db_id}: No content generated for selected language(s).")
        return False, None


    post_url = f"https://graph.facebook.com/v19.0/{facebook_page_id}/feed"
    payload = {
        'message': message_to_post,
        'access_token': access_token
    }
    
    attached_image_id = None

    if generated_image_filename and not generated_image_filename.startswith("ERROR_"):
        # --- CRITICAL FIX: Form the correct image path with the 'generated_images' subfolder ---
        image_path = os.path.join(base_output_dir, "generated_images", generated_image_filename)
        # --- END CRITICAL FIX ---
        if os.path.exists(image_path):
            debug_scheduler_print(f"Attaching image: {image_path}")
            # First, upload the photo
            photo_upload_url = f"https://graph.facebook.com/v19.0/{facebook_page_id}/photos"
            try:
                with open(image_path, 'rb') as img_file:
                    # Using published='false' means it uploads as unpublished, then we attach it to a new feed post.
                    # This is standard when combining text and images.
                    photo_response = requests.post(photo_upload_url, data={'access_token': access_token, 'published': 'false'}, files={'source': img_file})
                photo_response.raise_for_status()
                photo_data = photo_response.json()
                attached_image_id = photo_data.get('id')
                debug_scheduler_print(f"Image uploaded successfully, ID: {attached_image_id}")

                # Then, attach the photo to the post
                payload['attached_media'] = json.dumps([{'media_fbid': attached_image_id}])
                debug_scheduler_print("Attached image to post payload.")

            except requests.exceptions.HTTPError as e:
                error_details = e.response.json() if e.response and e.response.text else str(e)
                print(f"ERROR: Failed to upload image for Post ID {db_id} (HTTP Error): {e.response.status_code} - {error_details}")
            except Exception as e:
                print(f"ERROR: Failed to upload image for Post ID {db_id} (General Error): {e}")
        else:
            print(f"WARNING: Image file not found for Post ID {db_id}: {image_path}. Posting without image.")

    try:
        response = requests.post(post_url, data=payload, timeout=30)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        post_response_data = response.json()
        facebook_post_id = post_response_data.get('id')

        # Update database with actual Facebook post ID
        database_manager.update_post_facebook_id(db_id, facebook_post_id, facebook_page_id, access_token)
        print(f"Successfully scheduled Post ID {db_id} (FB ID: {facebook_post_id}) to page '{page_name}'.")
        return True, facebook_post_id

    except requests.exceptions.HTTPError as e:
        error_details = e.response.json() if e.response and e.response.text else str(e)
        print(f"ERROR: Failed to schedule Post ID {db_id} (HTTP Error): {e.response.status_code} - {error_details}")
        database_manager.update_post_facebook_id(db_id, None, facebook_page_id, access_token) # Mark as attempted even on HTTP error
        return False, None
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to schedule Post ID {db_id} (Network/Connection Error): {e}")
        database_manager.update_post_facebook_id(db_id, None, facebook_page_id, access_token)
        return False, None
    except Exception as e:
        print(f"ERROR: Failed to schedule Post ID {db_id} (Unexpected Error): {e}")
        database_manager.update_post_facebook_id(db_id, None, facebook_page_id, access_token)
        return False, None

def main(db_ids_arg, output_dir_arg):
    debug_scheduler_print(f"Scheduler started for DB IDs: {db_ids_arg}, Output Dir: {output_dir_arg}")
    
    db_ids = [int(id_str) for id_str in db_ids_arg.split(',')]
    
    for db_id in db_ids:
        post_details_dict = database_manager.get_post_details_by_db_id(db_id)

        if post_details_dict:
            debug_scheduler_print(f"Processing post DB ID {db_id}: {post_details_dict.get('page_name')}")
            # Ensure post_to_facebook is passed the correct base output directory
            success, fb_post_id = post_to_facebook(post_details_dict, output_dir_arg)
            if not success:
                print(f"Failed to schedule post with DB ID {db_id}.")
            time.sleep(1) # Small delay between posts
        else:
            print(f"WARNING: Post details not found in DB for ID {db_id}. Skipping.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python facebook_scheduler.py <comma_separated_db_ids> <output_directory>")
        sys.exit(1)
    
    db_ids_arg = sys.argv[1]
    output_dir_arg = sys.argv[2]
    main(db_ids_arg, output_dir_arg)