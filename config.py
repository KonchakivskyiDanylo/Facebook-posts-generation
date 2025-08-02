# config.py
import os
from datetime import datetime

class DefaultConfig:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'a_very_secret_key_for_session_management')
    DATABASE_FILE = 'facebook_posts_data.db'
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'Generated_Posts_Output')
    
    # Default API settings (can be overridden by saved config.json)
    DEFAULT_TEXT_GEN_PROVIDER = os.getenv('DEFAULT_TEXT_GEN_PROVIDER', "Gemini")
    DEFAULT_GEMINI_MODEL = os.getenv('DEFAULT_GEMINI_MODEL', "gemini-1.5-flash")
    DEFAULT_OPENAI_TEXT_MODEL = os.getenv('DEFAULT_OPENAI_TEXT_MODEL', "gpt-3.5-turbo")
    DEFAULT_OPENAI_IMAGE_MODEL = os.getenv('DEFAULT_OPENAI_IMAGE_MODEL', "dall-e-3")
    DEFAULT_IMAGE_GEN_PROVIDER = os.getenv('DEFAULT_IMAGE_GEN_PROVIDER', "OpenAI (DALL-E)")
    DEFAULT_NUM_POSTS = int(os.getenv('DEFAULT_NUM_POSTS', 84))
    DEFAULT_GEMINI_TEMPERATURE = float(os.getenv('DEFAULT_GEMINI_TEMPERATURE', 0.7))
    DEFAULT_START_DATE = os.getenv('DEFAULT_START_DATE', datetime.now().strftime("%Y-%m-%d"))