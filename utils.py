import os
import sys
import sqlite3
from datetime import datetime
import importlib.util

# Step 1: Add project root (one level up from this file) to sys.path
current_dir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(current_dir)  # same as utils.py
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Step 2: Try importing app_config_manager using importlib as fallback
FACEBOOK_PAGES = []
try:
    import app_config_manager
    FACEBOOK_PAGES = app_config_manager.FACEBOOK_PAGES
except ImportError as e:
    print(f"[utils.py] ERROR: Failed to import app_config_manager: {e}")
    # Absolute fallback if import still fails
    config_path = os.path.join(project_root, 'app_config_manager.py')
    if os.path.exists(config_path):
        spec = importlib.util.spec_from_file_location("app_config_manager", config_path)
        app_config_manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_config_manager)
        FACEBOOK_PAGES = app_config_manager.FACEBOOK_PAGES


def get_all_page_names():
    return FACEBOOK_PAGES


def get_database_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_table_row_count(db_path, table_name):
    try:
        conn = get_database_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        print(f"[utils.py] Error counting rows in {table_name}: {e}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()


def get_last_updated_timestamp(file_path):
    if os.path.exists(file_path):
        ts = os.path.getmtime(file_path)
        return datetime.fromtimestamp(ts)
    return None
