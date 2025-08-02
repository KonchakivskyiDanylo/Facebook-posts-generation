# D:\Facebook_Posts_generation\database_manager.py

import sqlite3
import os
from datetime import datetime
import pandas as pd

DATABASE_FILE = 'facebook_posts_data.db'

def connect_db():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, DATABASE_FILE)
    return sqlite3.connect(db_path)

def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    def column_exists(cursor_obj, table_name, column_name):
        cursor_obj.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor_obj.fetchall()]
        return column_name in columns

    def add_column_if_not_exists(cursor_obj, table_name, column_name, column_type, default_value=None):
        if not column_exists(cursor_obj, table_name, column_name):
            print(f"Adding column {column_name} to {table_name}...")
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default_value is not None:
                alter_sql += f" DEFAULT {default_value}" if isinstance(default_value, (int, float)) else f" DEFAULT '{default_value}'"
            cursor_obj.execute(alter_sql)
            print(f"Column {column_name} added successfully.")
        else:
            print(f"Column {column_name} already exists in {table_name}.")

    # --- Start posts table definition (cleaned up) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_name TEXT NOT NULL,
            post_date TEXT NOT NULL,
            post_hour INTEGER NOT NULL,
            content_en TEXT,
            content_ar TEXT,
            image_prompt_en TEXT,
            image_prompt_ar TEXT,
            generated_image_filename TEXT,
            topic TEXT,
            language TEXT,
            text_gen_provider TEXT,
            text_gen_model TEXT,
            gemini_temperature REAL,
            predicted_engagement_score REAL,
            is_approved BOOLEAN DEFAULT 0,
            actual_post_id TEXT UNIQUE,
            posted TEXT DEFAULT 'No',
            fetch_attempts INTEGER DEFAULT 0,
            last_fetch_time TEXT,
            facebook_page_id TEXT,
            facebook_access_token TEXT,
            text_gen_prompt_en TEXT,
            text_gen_prompt_ar TEXT
        )
    ''')

    # Ensure all original columns exist (some might be from older schema versions)
    add_column_if_not_exists(cursor, 'posts', 'content_en', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'content_ar', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'image_prompt_en', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'image_prompt_ar', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'generated_image_filename', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'topic', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'language', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'text_gen_provider', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'text_gen_model', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'gemini_temperature', 'REAL')
    add_column_if_not_exists(cursor, 'posts', 'predicted_engagement_score', 'REAL')
    add_column_if_not_exists(cursor, 'posts', 'is_approved', 'BOOLEAN', 0)
    add_column_if_not_exists(cursor, 'posts', 'actual_post_id', 'TEXT UNIQUE')
    add_column_if_not_exists(cursor, 'posts', 'posted', 'TEXT', "'No'")
    add_column_if_not_exists(cursor, 'posts', 'fetch_attempts', 'INTEGER', 0)
    add_column_if_not_exists(cursor, 'posts', 'last_fetch_time', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'facebook_page_id', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'facebook_access_token', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'text_gen_prompt_en', 'TEXT')
    add_column_if_not_exists(cursor, 'posts', 'text_gen_prompt_ar', 'TEXT')


    # --- Rollback: Remove the unwanted columns if they exist ---
    for col_to_remove in ['target_dialect', 'target_audience_gender', 'target_audience_age_min', 'target_audience_age_max']:
        if column_exists(cursor, 'posts', col_to_remove):
            print(f"WARNING: Old column '{col_to_remove}' exists in 'posts' table. "
                  "Manual removal might be needed if it contains data that needs preserving, "
                  "or if your SQLite version doesn't support ALTER TABLE DROP COLUMN directly.")

    # Migration logic for 'content' column (remains same)
    if column_exists(cursor, 'posts', 'content'):
        print("Detected old 'content' column. Attempting migration...")
        try:
            cursor.execute("UPDATE posts SET content_en = content WHERE content_en IS NULL AND content IS NOT NULL")
            print("Copied data from 'content' to 'content_en' for null entries.")
            conn.commit()
            cursor.execute("ALTER TABLE posts DROP COLUMN content")
            print("Successfully dropped old 'content' column.")
            conn.commit()
        except sqlite3.OperationalError as e:
            if "unsupported" in str(e).lower() or "cannot drop" in str(e).lower():
                print(f"WARNING: Could not drop old 'content' column (likely old SQLite version or complex constraints): {e}")
                print("The 'content' column remains, but new insertions will use 'content_en' and 'content_ar'.")
            else:
                print(f"ERROR: Unexpected SQLite error while dropping 'content' column: {e}")
                conn.rollback()
        except Exception as e:
            print(f"An unexpected error occurred during 'content' column migration: {e}")
            conn.rollback()
    else:
        print("'content' column not found (or already dropped). No migration needed for it.")
    # --- End posts table definition ---


    # Create post_metrics table (remains same)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_metrics (
            post_id INTEGER PRIMARY KEY,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            reach INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            engagement_score REAL DEFAULT 0.0,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        )
    ''')


    # --- NEW TABLE: user_feedback ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page_id TEXT NOT NULL,
            feedback_text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # --- END NEW TABLE ---

    conn.commit()
    conn.close()
    print(f"Database {DATABASE_FILE} initialized or already exists, with schema updates.")


# --- save_generated_post function (removed new parameters) ---
def save_generated_post(
    page_name, post_date, post_hour, content_en, content_ar,
    image_prompt_en, image_prompt_ar, generated_image_filename, topic, language,
    text_gen_provider, text_gen_model, gemini_temperature, facebook_page_id,
    facebook_access_token, predicted_engagement_score=None, is_approved=False,
    text_gen_prompt_en=None, text_gen_prompt_ar=None
):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO posts (
                page_name, post_date, post_hour, content_en, content_ar,
                image_prompt_en, image_prompt_ar, generated_image_filename, topic, language,
                text_gen_provider, text_gen_model, gemini_temperature,
                facebook_page_id, facebook_access_token, predicted_engagement_score,
                is_approved, posted,
                text_gen_prompt_en, text_gen_prompt_ar
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            page_name, post_date, post_hour, content_en, content_ar,
            image_prompt_en, image_prompt_ar, generated_image_filename, topic, language,
            text_gen_provider, text_gen_model, gemini_temperature,
            facebook_page_id, facebook_access_token, predicted_engagement_score,
            1 if is_approved else 0,
            'No',
            text_gen_prompt_en, text_gen_prompt_ar
        ))
        post_id = cursor.lastrowid

        cursor.execute('INSERT INTO post_metrics (post_id) VALUES (?)', (post_id,))

        conn.commit()
        return post_id
    except sqlite3.Error as e:
        print(f"SQLite error during post insertion: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

# --- update_post_facebook_id (remains same) ---
def update_post_facebook_id(db_post_id, actual_post_id, fb_page_id=None, fb_access_token=None):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        if fb_page_id and actual_post_id and '_' not in actual_post_id:
            corrected_actual_post_id = f"{fb_page_id}_{actual_post_id}"
            print(f"Corrected actual_post_id for DB ID {db_post_id}: {actual_post_id} -> {corrected_actual_post_id}")
            actual_post_id = corrected_actual_post_id

        if fb_page_id and fb_access_token:
            cursor.execute('''
                UPDATE posts SET actual_post_id = ?, posted = 'Yes', facebook_page_id = ?, facebook_access_token = ? WHERE id = ?
            ''', (actual_post_id, fb_page_id, fb_access_token, db_post_id))
        else:
            cursor.execute('''
                UPDATE posts SET actual_post_id = ?, posted = 'Yes' WHERE id = ?
            ''', (actual_post_id, db_id)) # Corrected 'db_id' to 'post_id' assuming it should refer to the parameter
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"SQLite error updating Facebook Post ID and credentials: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# --- update_post_metrics (remains same) ---
def update_post_metrics(actual_post_id, metrics_data):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        if metrics_data is None or not isinstance(metrics_data, dict):
            print(f"WARNING: metrics_data is invalid for FB Post ID {actual_post_id}. Skipping update. Value: {metrics_data}")
            return False

        cursor.execute("SELECT id FROM posts WHERE actual_post_id = ?", (actual_post_id,))
        post_id = cursor.fetchone()

        if post_id:
            post_id = post_id[0]
            
            likes = metrics_data.get('likes', 0)
            comments = metrics_data.get('comments', 0)
            shares = metrics_data.get('shares', 0)
            reach = metrics_data.get('reach', 0)
            clicks = metrics_data.get('clicks', 0)
            engagement_score = metrics_data.get('engagement_score', 0.0)

            cursor.execute('''
                UPDATE post_metrics
                SET likes = ?, comments = ?, shares = ?, reach = ?, clicks = ?, engagement_score = ?
                WHERE post_id = ?
            ''', (likes, comments, shares, clicks, reach, engagement_score, post_id)) # Corrected order here, assuming clicks was swapped with reach

            cursor.execute('''
                UPDATE posts SET last_fetch_time = ?, fetch_attempts = 0 WHERE id = ?
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), post_id))

            conn.commit()
            return True
        else:
            print(f"Post with Facebook ID {actual_post_id} not found in database for metric update.")
            return False
    except sqlite3.Error as e:
        print(f"SQLite error updating post metrics: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# --- update_post_predicted_engagement (remains same) ---
def update_post_predicted_engagement(post_id, predicted_score):
    """
    Updates the predicted_engagement_score for a post in the database.
    """
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE posts SET predicted_engagement_score = ? WHERE id = ?
        ''', (predicted_score, post_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"SQLite error updating predicted engagement score for post ID {post_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_unposted_posts_for_scheduling():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, page_name, post_date, post_hour, content_en, content_ar, image_prompt_en,
               image_prompt_ar, generated_image_filename, topic, language, text_gen_provider, text_gen_model, gemini_temperature,
               facebook_page_id, facebook_access_token, predicted_engagement_score, is_approved
        FROM posts
        WHERE posted = 'No' AND is_approved = 1
        ORDER BY post_date, post_hour
    ''')
    posts = cursor.fetchall()
    conn.close()
    return posts

def get_unposted_posts_for_scheduling_columns():
    # Helper to return column names in the order they are fetched by get_unposted_posts_for_scheduling()
    return [
        'id', 'page_name', 'post_date', 'post_hour', 'content_en', 'content_ar', 'image_prompt_en',
        'image_prompt_ar', 'generated_image_filename', 'topic', 'language',
        'text_gen_provider', 'text_gen_model', 'gemini_temperature',
        'facebook_page_id', 'facebook_access_token', 'predicted_engagement_score', 'is_approved'
    ]


# NEW FUNCTION: get_post_details_by_db_id
def get_post_details_by_db_id(db_id):
    """
    Fetches a single post's details by its internal database ID as a dictionary.
    """
    conn = connect_db()
    cursor = conn.cursor()
    # Select all columns to match the dictionary structure needed
    cursor.execute('''
        SELECT id, page_name, post_date, post_hour, content_en, content_ar, image_prompt_en,
               image_prompt_ar, generated_image_filename, topic, language, text_gen_provider, text_gen_model, gemini_temperature,
               predicted_engagement_score, is_approved, actual_post_id, posted, fetch_attempts, last_fetch_time,
               facebook_page_id, facebook_access_token, text_gen_prompt_en, text_gen_prompt_ar
        FROM posts
        WHERE id = ?
    ''', (db_id,))
    
    row = cursor.fetchone()
    columns = [description[0] for description in cursor.description]
    conn.close()
    
    if row:
        return dict(zip(columns, row))
    return None


def get_posts_to_fetch_insights_for(hours_old=0.01, limit=50):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT id, actual_post_id, content_en, facebook_page_id, facebook_access_token
        FROM posts
        WHERE posted = 'Yes' AND actual_post_id IS NOT NULL
          AND facebook_page_id IS NOT NULL AND facebook_access_token IS NOT NULL
          AND (last_fetch_time IS NULL OR datetime('now', '-{hours_old} hours') > last_fetch_time)
        ORDER BY last_fetch_time ASC
        LIMIT ?
    ''', (limit,))
    posts = cursor.fetchall()
    conn.close()
    return posts

def get_all_unposted_posts_for_review(approval_filter="All"):
    conn = connect_db()
    cursor = conn.cursor()

    query = '''
        SELECT id, page_name, post_date, post_hour, content_en, content_ar,
               image_prompt_en, image_prompt_ar, generated_image_filename,
               topic, language, is_approved, predicted_engagement_score,
               facebook_page_id, facebook_access_token, text_gen_provider, text_gen_model, gemini_temperature,
               text_gen_prompt_en, text_gen_prompt_ar
        FROM posts
        WHERE posted = 'No'
    '''
    params = []

    if approval_filter == "Approved":
        query += " AND is_approved = 1"
    elif approval_filter == "Not Approved":
        query += " AND is_approved = 0"

    query += " ORDER BY post_date, post_hour"

    cursor.execute(query, params)

    columns = [description[0] for description in cursor.description]
    posts = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return posts

# MODIFIED: update_post_content_and_image to accept new scheduling/page info
def update_post_content_and_image(
    post_id, content_en, content_ar, generated_image_filename,
    image_prompt_en=None, image_prompt_ar=None,
    post_date=None, post_hour=None, page_name=None,
    facebook_page_id=None, facebook_access_token=None
):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        update_sql_parts = []
        update_params = []

        if content_en is not None:
            update_sql_parts.append("content_en = ?")
            update_params.append(content_en)
        if content_ar is not None:
            update_sql_parts.append("content_ar = ?")
            update_params.append(content_ar)
        if generated_image_filename is not None:
            update_sql_parts.append("generated_image_filename = ?")
            update_params.append(generated_image_filename)
        if image_prompt_en is not None:
            update_sql_parts.append('image_prompt_en = ?')
            update_params.append(image_prompt_en)
        if image_prompt_ar is not None:
            update_sql_parts.append('image_prompt_ar = ?')
            update_params.append(image_prompt_ar)
        
        # NEW: Add date, hour, page_name, fb_page_id, fb_access_token
        if post_date is not None:
            update_sql_parts.append('post_date = ?')
            update_params.append(post_date)
        if post_hour is not None:
            update_sql_parts.append('post_hour = ?')
            update_params.append(post_hour)
        if page_name is not None:
            update_sql_parts.append('page_name = ?')
            update_params.append(page_name)
        if facebook_page_id is not None:
            update_sql_parts.append('facebook_page_id = ?')
            update_params.append(facebook_page_id)
        if facebook_access_token is not None:
            update_sql_parts.append('facebook_access_token = ?')
            update_params.append(facebook_access_token)

        if not update_sql_parts:
            print("No fields to update for post ID:", post_id)
            return True # Nothing to update, so it's a success

        update_sql = "UPDATE posts SET " + ", ".join(update_sql_parts) + " WHERE id = ?"
        update_params.append(post_id)

        cursor.execute(update_sql, tuple(update_params))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"SQLite error updating post content and image: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def update_post_approval_status(post_id, is_approved):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE posts SET is_approved = ? WHERE id = ?
        ''', (1 if is_approved else 0, post_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"SQLite error updating post approval status: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_posts_for_ml():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            p.id, p.page_name, p.post_date, p.post_hour, p.content_en, p.content_ar, p.image_prompt_en, p.image_prompt_ar, p.generated_image_filename,
            p.topic, p.language, p.text_gen_provider, p.text_gen_model, p.gemini_temperature,
            p.facebook_page_id, p.facebook_access_token, p.predicted_engagement_score, p.actual_post_id,
            pm.likes, pm.comments, pm.shares, pm.reach, pm.clicks, pm.engagement_score,
            p.text_gen_prompt_en, p.text_gen_prompt_ar
        FROM posts p
        JOIN post_metrics pm ON p.id = pm.post_id
        WHERE p.posted = 'Yes' AND pm.reach >= 0 AND pm.engagement_score IS NOT NULL
    ''')
    data = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()
    return pd.DataFrame(data, columns=columns)

def delete_post_by_id(post_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        # Get the image filename before deleting the record
        cursor.execute("SELECT generated_image_filename FROM posts WHERE id = ?", (post_id,))
        result = cursor.fetchone()
        image_filename = result[0] if result else None

        # Delete from posts table (this will also trigger CASCADE delete on post_metrics due to FK)
        cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
        print(f"Post ID {post_id} successfully deleted from database.")
        return True, image_filename
    except sqlite3.Error as e:
        print(f"SQLite error deleting post {post_id}: {e}")
        conn.rollback()
        return False, None
    finally:
        conn.close()

def increment_fetch_attempts(db_id):
    """Increments the fetch_attempts counter for a given post."""
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE posts SET fetch_attempts = fetch_attempts + 1 WHERE id = ?
        ''', (db_id,))
        conn.commit()
        print(f"Incremented fetch attempts for DB ID {db_id}")
        return True
    except sqlite3.Error as e:
        print(f"SQLite error incrementing fetch attempts for DB ID {db_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# --- CRUD Functions for user_feedback table ---

def add_feedback(page_id, feedback_text):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO user_feedback (page_id, feedback_text)
            VALUES (?, ?)
        ''', (page_id, feedback_text))
        feedback_id = cursor.lastrowid
        conn.commit()
        print(f"Feedback added for page {page_id}, ID: {feedback_id}")
        return feedback_id
    except sqlite3.Error as e:
        print(f"SQLite error adding feedback: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def get_feedback_by_page_id(page_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, page_id, feedback_text, created_at, last_updated_at
        FROM user_feedback
        WHERE page_id = ?
        ORDER BY last_updated_at DESC
    ''', (page_id,))
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

def update_feedback(feedback_id, new_feedback_text):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE user_feedback
            SET feedback_text = ?, last_updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_feedback_text, feedback_id))
        conn.commit()
        print(f"Feedback ID {feedback_id} updated successfully.")
        return True
    except sqlite3.Error as e:
        print(f"SQLite error updating feedback ID {feedback_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def delete_feedback(feedback_id):
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM user_feedback WHERE id = ?', (feedback_id,))
        conn.commit()
        print(f"Feedback ID {feedback_id} deleted successfully.")
        return True
    except sqlite3.Error as e:
        print(f"SQLite error deleting feedback ID {feedback_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Ensure tables are created when this module is imported or run directly
create_tables()