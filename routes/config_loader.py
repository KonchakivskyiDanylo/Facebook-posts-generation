# routes/config_loader.py
import os
import json
from datetime import datetime
import sys

# Global list to hold Facebook page data
FACEBOOK_PAGES = []

class ConfigLoader:
    """
    Manages loading and saving application configuration and Facebook page data
    from gui_config.json.
    """
    @staticmethod
    def load_app_config(app_instance):
        """
        Loads configuration and Facebook pages from gui_config.json into the Flask app's config
        and updates the global FACEBOOK_PAGES list.
        """
        # Calculate path relative to the project root
        # app_instance.root_path is the directory where the Flask app object (app.py) was created
        config_folder_path = os.path.join(app_instance.root_path, 'config')
        gui_config_path = os.path.join(config_folder_path, "gui_config.json")

        print(f"[DEBUG - ConfigLoader]: Attempting to load config from: {gui_config_path}")

        # Ensure the config directory exists
        os.makedirs(config_folder_path, exist_ok=True)

        if os.path.exists(gui_config_path):
            try:
                with open(gui_config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    print(f"[DEBUG - ConfigLoader]: Successfully read JSON from {gui_config_path}")

                    # Update Flask app.config with loaded values, providing defaults from app_instance.config
                    app_instance.config['OUTPUT_DIR'] = config_data.get("output_dir", app_instance.config.get('OUTPUT_DIR'))
                    app_instance.config['DEFAULT_TEXT_GEN_PROVIDER'] = config_data.get("selected_text_gen_provider", app_instance.config.get('DEFAULT_TEXT_GEN_PROVIDER'))
                    app_instance.config['DEFAULT_GEMINI_MODEL'] = config_data.get("selected_gemini_model", app_instance.config.get('DEFAULT_GEMINI_MODEL'))
                    app_instance.config['DEFAULT_OPENAI_TEXT_MODEL'] = config_data.get("selected_openai_text_model", app_instance.config.get('DEFAULT_OPENAI_TEXT_MODEL'))
                    app_instance.config['DEFAULT_OPENAI_IMAGE_MODEL'] = config_data.get("selected_openai_image_model", config_data.get("selected_openai_model", app_instance.config.get('DEFAULT_OPENAI_IMAGE_MODEL')))
                    app_instance.config['DEFAULT_IMAGE_GEN_PROVIDER'] = config_data.get("selected_image_gen_provider", app_instance.config.get('DEFAULT_IMAGE_GEN_PROVIDER'))
                    
                    app_instance.config['DEFAULT_GEMINI_TEMPERATURE'] = float(config_data.get("gemini_temperature", app_instance.config.get('DEFAULT_GEMINI_TEMPERATURE')))
                    app_instance.config['DEFAULT_NUM_POSTS'] = int(config_data.get("num_posts_default", app_instance.config.get('DEFAULT_NUM_POSTS')))
                    app_instance.config['DEFAULT_START_DATE'] = config_data.get("start_date", datetime.now().strftime("%Y-%m-%d"))

                    # Update the global FACEBOOK_PAGES list from this module
                    FACEBOOK_PAGES.clear()
                    FACEBOOK_PAGES.extend(config_data.get("facebook_pages", []))
                    print(f"[DEBUG - ConfigLoader]: Loaded {len(FACEBOOK_PAGES)} Facebook pages and configuration from {gui_config_path}")
                    if FACEBOOK_PAGES:
                        print(f"[DEBUG - ConfigLoader]: First page loaded: {FACEBOOK_PAGES[0].get('page_name')}")
                    else:
                        print("[DEBUG - ConfigLoader]: No Facebook pages found in gui_config.json 'facebook_pages' list.")

            except json.JSONDecodeError as e:
                print(f"[ERROR - ConfigLoader]: Error reading gui_config.json (JSON Decode Error): {e}. File might be corrupted or malformed. Initializing pages to empty list and using default config.")
                FACEBOOK_PAGES.clear()
            except Exception as e:
                print(f"[ERROR - ConfigLoader]: An unexpected error occurred loading gui_config.json: {e}. Initializing pages to empty list and using default config.")
                FACEBOOK_PAGES.clear()
        else:
            print(f"[INFO - ConfigLoader]: gui_config.json not found at {gui_config_path}. Starting with no configured Facebook pages and default config.")
            FACEBOOK_PAGES.clear() 

    @staticmethod
    def save_app_config(app_instance):
        config_folder_path = os.path.join(app_instance.root_path, 'config')
        gui_config_path = os.path.join(config_folder_path, "gui_config.json")
        os.makedirs(os.path.dirname(gui_config_path), exist_ok=True)

        config_data = {
            "output_dir": app_instance.config.get('OUTPUT_DIR', 'Generated_Posts_Output'),
            "selected_text_gen_provider": app_instance.config.get('DEFAULT_TEXT_GEN_PROVIDER', "Gemini"),
            "selected_gemini_model": app_instance.config.get('DEFAULT_GEMINI_MODEL', "gemini-1.5-flash"),
            "selected_openai_text_model": app_instance.config.get('DEFAULT_OPENAI_TEXT_MODEL', "gpt-3.5-turbo"),
            "selected_openai_image_model": app_instance.config.get('DEFAULT_OPENAI_IMAGE_MODEL', "dall-e-3"),
            "selected_image_gen_provider": app_instance.config.get('DEFAULT_IMAGE_GEN_PROVIDER', "OpenAI (DALL-E)"),
            "gemini_temperature": app_instance.config.get('DEFAULT_GEMINI_TEMPERATURE', 0.7),
            "num_posts_default": app_instance.config.get('DEFAULT_NUM_POSTS', 84),
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "facebook_pages": FACEBOOK_PAGES
        }
        try:
            with open(gui_config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            print(f"[DEBUG - ConfigLoader]: Configuration saved to: {gui_config_path}")
        except Exception as e:
            print(f"[ERROR - ConfigLoader]: Error saving config to {gui_config_path}: {e}")