import requests
import sys

def fetch_post_engagement_metrics(post_id, access_token):
    """
    Fetches reactions, comments, and shares from the post object.
    """
    url = f"https://graph.facebook.com/v19.0/{post_id}"
    params = {
        'fields': 'reactions.summary(true),comments.summary(true),shares',
        'access_token': access_token
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        return {
            'likes': data.get('reactions', {}).get('summary', {}).get('total_count', 0),
            'comments': data.get('comments', {}).get('summary', {}).get('total_count', 0),
            'shares': data.get('shares', {}).get('count', 0),
        }

    except Exception as e:
        print(f"[ERROR] GUI engagement fetch failed for post {post_id}: {e}")
        return {'likes': 0, 'comments': 0, 'shares': 0}

def fetch_post_insight_metrics(post_id, access_token):
    """
    Fetches post reach (impressions) from the /insights endpoint.
    """
    url = f"https://graph.facebook.com/v19.0/{post_id}/insights"
    params = {
        'metric': 'post_impressions_unique',
        'period': 'lifetime',
        'access_token': access_token
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        for item in data.get('data', []):
            if item['name'] == 'post_impressions_unique':
                return {'reach': item['values'][0]['value']}
        return {'reach': 0}

    except Exception as e:
        print(f"[ERROR] GUI insights fetch failed for post {post_id}: {e}")
        return {'reach': 0}

def fetch_combined_post_metrics(post_id, access_token):
    """
    Fetches and combines engagement + insights for use in the GUI.
    """
    engagement = fetch_post_engagement_metrics(post_id, access_token)
    insight = fetch_post_insight_metrics(post_id, access_token)

    combined = {
        **engagement,
        **insight,
        'clicks': 0  # Optional: add if you use click tracking
    }

    if combined['reach'] > 0:
        combined['engagement_score'] = (
            combined['likes'] + combined['comments'] + combined['shares']
        ) / combined['reach']
    else:
        combined['engagement_score'] = 0.0

    return combined
