# app_config_manager.py
import os
import json
from datetime import datetime

# Global list to hold Facebook page data
FACEBOOK_PAGES = []

class AppConfigManager:
    def __init__(self):
        pass

    @staticmethod
    def load_app_config(app_instance):
        """Loads configuration and Facebook pages from gui_config.json."""
        config_dir = 'config'
        # Path needs to be relative to the app's root (project_root), which is passed in app_instance.root_path
        gui_config_path = os.path.join(app_instance.root_path, config_dir, "gui_config.json")

        os.makedirs(os.path.dirname(gui_config_path), exist_ok=True)

        if os.path.exists(gui_config_path):
            try:
                with open(gui_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                    app_instance.config['OUTPUT_DIR'] = config_data.get("output_dir", app_instance.config['OUTPUT_DIR'])
                    app_instance.config['DEFAULT_TEXT_GEN_PROVIDER'] = config_data.get("selected_text_gen_provider", app_instance.config['DEFAULT_TEXT_GEN_PROVIDER'])
                    app_instance.config['DEFAULT_GEMINI_MODEL'] = config_data.get("selected_gemini_model", app_instance.config['DEFAULT_GEMINI_MODEL'])
                    app_instance.config['DEFAULT_OPENAI_TEXT_MODEL'] = config_data.get("selected_openai_text_model", app_instance.config['DEFAULT_OPENAI_TEXT_MODEL'])
                    app_instance.config['DEFAULT_OPENAI_IMAGE_MODEL'] = config_data.get("selected_openai_image_model", config_data.get("selected_openai_model", app_instance.config['DEFAULT_OPENAI_IMAGE_MODEL']))
                    app_instance.config['DEFAULT_IMAGE_GEN_PROVIDER'] = config_data.get("selected_image_gen_provider", app_instance.config['DEFAULT_IMAGE_GEN_PROVIDER'])
                    app_instance.config['DEFAULT_GEMINI_TEMPERATURE'] = float(config_data.get("gemini_temperature", app_instance.config['DEFAULT_GEMINI_TEMPERATURE']))
                    app_instance.config['DEFAULT_NUM_POSTS'] = int(config_data.get("num_posts_default", app_instance.config['DEFAULT_NUM_POSTS']))
                    app_instance.config['DEFAULT_START_DATE'] = config_data.get("start_date", app_instance.config['DEFAULT_START_DATE'])

                    # IMPORTANT: Clear and extend the global FACEBOOK_PAGES list in this module
                    FACEBOOK_PAGES.clear()
                    FACEBOOK_PAGES.extend(config_data.get("facebook_pages", []))
                    print(f"Loaded {len(FACEBOOK_PAGES)} Facebook pages from {gui_config_path}")
            except json.JSONDecodeError as e:
                print(f"Error reading gui_config.json: {e}. Initializing pages to empty list.")
                FACEBOOK_PAGES.clear()
            except Exception as e:
                print(f"An unexpected error occurred loading gui_config.json: {e}. Initializing pages to empty list.")
                FACEBOOK_PAGES.clear()
        else:
            print("gui_config.json not found. Starting with no configured Facebook pages.")

    @staticmethod
    def save_app_config(app_instance):
        """Saves current configuration and Facebook pages to gui_config.json."""
        config_dir = 'config'
        gui_config_path = os.path.join(app_instance.root_path, config_dir, "gui_config.json")
        os.makedirs(os.path.dirname(gui_config_path), exist_ok=True)

        config_data = {
            "output_dir": app_instance.config['OUTPUT_DIR'],
            "selected_text_gen_provider": app_instance.config['DEFAULT_TEXT_GEN_PROVIDER'],
            "selected_gemini_model": app_instance.config['DEFAULT_GEMINI_MODEL'],
            "selected_openai_text_model": app_instance.config['DEFAULT_OPENAI_TEXT_MODEL'],
            "selected_openai_image_model": app_instance.config['DEFAULT_OPENAI_IMAGE_MODEL'],
            "selected_image_gen_provider": app_instance.config['DEFAULT_IMAGE_GEN_PROVIDER'],
            "gemini_temperature": app_instance.config['DEFAULT_GEMINI_TEMPERATURE'],
            "num_posts_default": app_instance.config['DEFAULT_NUM_POSTS'],
            "start_date": app_instance.config['DEFAULT_START_DATE'],
            "facebook_pages": FACEBOOK_PAGES # Use the global list from this module
        }
        try:
            with open(gui_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            print(f"Configuration saved to: {gui_config_path}")
        except Exception as e:
            print(f"Error saving config: {e}")