import sqlite3
import os
from datetime import datetime # You might not need all imports for a simple migration
import pandas as pd # You might not need all imports for a simple migration

# Assuming database_manager.py is in the same directory or accessible
import database_manager

def migrate_old_post_ids():
    conn = database_manager.connect_db()
    cursor = conn.cursor()

    print("Starting migration of old Facebook Post IDs...")

    # Select posts that are 'Yes' and have an actual_post_id that doesn't contain an underscore
    # and has a non-null facebook_page_id
    cursor.execute('''
        SELECT id, actual_post_id, facebook_page_id
        FROM posts
        WHERE posted = 'Yes'
          AND actual_post_id IS NOT NULL
          AND facebook_page_id IS NOT NULL
          AND instr(actual_post_id, '_') = 0;
    ''')
    posts_to_migrate = cursor.fetchall()

    if not posts_to_migrate:
        print("No old post IDs found requiring migration. Database is clean.")
        conn.close()
        return

    migrated_count = 0
    for post_id, old_actual_post_id, fb_page_id in posts_to_migrate:
        if not fb_page_id:
            print(f"Skipping post ID {post_id}: Missing facebook_page_id. Cannot form correct actual_post_id.")
            continue

        corrected_actual_post_id = f"{fb_page_id}_{old_actual_post_id}"

        try:
            cursor.execute('''
                UPDATE posts
                SET actual_post_id = ?
                WHERE id = ?
            ''', (corrected_actual_post_id, post_id))
            print(f"Migrated Post DB ID {post_id}: {old_actual_post_id} -> {corrected_actual_post_id}")
            migrated_count += 1
        except sqlite3.Error as e:
            print(f"Error migrating Post DB ID {post_id} ({old_actual_post_id}): {e}")
            conn.rollback() # Rollback if an error occurs for this specific update
            continue # Continue to the next post

    conn.commit()
    conn.close()
    print(f"Migration complete. Successfully updated {migrated_count} old post IDs.")

if __name__ == '__main__':
    migrate_old_post_ids()