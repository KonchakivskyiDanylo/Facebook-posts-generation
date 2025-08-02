# D:\Facebook_Posts_generation\facebook_metrics_gui_helpers.py

import requests
import json

def fetch_post_engagement_metrics(post_id, access_token):
    """
    Fetches reactions, comments, and shares from the post object.
    Returns a dictionary of metrics, or None on API error.
    """
    url = f"https://graph.facebook.com/v19.0/{post_id}"
    params = {
        'fields': 'reactions.summary(true),comments.summary(true),shares',
        'access_token': access_token
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status() # This will raise an HTTPError for 4xx/5xx responses
        data = response.json()

        return {
            'likes': data.get('reactions', {}).get('summary', {}).get('total_count', 0),
            'comments': data.get('comments', {}).get('summary', {}).get('total_count', 0),
            'shares': data.get('shares', {}).get('count', 0),
        }

    except requests.exceptions.HTTPError as e:
        error_details = "N/A"
        if e.response is not None:
            try:
                error_details = e.response.json()
            except json.JSONDecodeError:
                error_details = e.response.text # Fallback to raw text if not JSON
        print(f"[ERROR] fetch_post_engagement_metrics HTTP Error for {post_id}: {e.response.status_code} - {error_details}")
        # Return None to explicitly indicate API call failure
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] fetch_post_engagement_metrics Request Error for {post_id}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] fetch_post_engagement_metrics JSON Decode Error for {post_id}: {e}. Response was: {response.text}")
        return None
    except Exception as e:
        print(f"[ERROR] fetch_post_engagement_metrics Unexpected Error for {post_id}: {e}")
        return None


def fetch_post_insight_metrics(post_id, access_token):
    """
    Fetches post reach (post_impressions_unique) from the /insights endpoint.
    Returns a dictionary of metrics, or None on API error.
    """
    url = f"https://graph.facebook.com/v19.0/{post_id}/insights"
    params = {
        'metric': 'post_impressions_unique',
        'period': 'lifetime',
        'access_token': access_token
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status() # This will raise an HTTPError for 4xx/5xx responses
        data = response.json()

        for item in data.get('data', []):
            if item['name'] == 'post_impressions_unique':
                return {'reach': item['values'][0]['value']}
        return {'reach': 0} # Return 0 if metric not found in response

    except requests.exceptions.HTTPError as e:
        error_details = "N/A"
        if e.response is not None:
            try:
                error_details = e.response.json()
            except json.JSONDecodeError:
                error_details = e.response.text # Fallback to raw text if not JSON
        print(f"[ERROR] fetch_post_insight_metrics HTTP Error for {post_id}: {e.response.status_code} - {error_details}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] fetch_post_insight_metrics Request Error for {post_id}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] fetch_post_insight_metrics JSON Decode Error for {post_id}: {e}. Response was: {response.text}")
        return None
    except Exception as e:
        print(f"[ERROR] fetch_post_insight_metrics Unexpected Error for {post_id}: {e}")
        return None

def fetch_combined_post_metrics(post_id, access_token):
    """
    Fetches and combines engagement + insights for use in the GUI.
    Returns a dictionary of metrics, or None if a critical error occurs.
    """
    engagement = fetch_post_engagement_metrics(post_id, access_token)
    insight = fetch_post_insight_metrics(post_id, access_token)

    # If either engagement or insight fetch failed (returned None), handle it.
    # If a sub-fetch returns None, it means an API error occurred.
    # We still try to combine if one succeeded, but the overall result might be incomplete.
    # The database manager expects a dict, so we ensure defaults if one part failed.
    combined = {
        'likes': engagement.get('likes', 0) if engagement is not None else 0,
        'comments': engagement.get('comments', 0) if engagement is not None else 0,
        'shares': engagement.get('shares', 0) if engagement is not None else 0,
        'reach': insight.get('reach', 0) if insight is not None else 0,
        'clicks': 0 # Clicks isn't being fetched from Facebook, so it remains 0
    }

    # If both failed, return None to signal a complete failure to the caller
    if engagement is None and insight is None:
        print(f"[ERROR] fetch_combined_post_metrics: Both engagement and insight fetches failed for {post_id}. Returning None.")
        return None

    if combined['reach'] > 0:
        combined['engagement_score'] = (
            combined['likes'] + combined['comments'] + combined['shares']
        ) / combined['reach']
    else:
        combined['engagement_score'] = 0.0

    return combined