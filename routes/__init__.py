# routes/__init__.py
import os
from datetime import datetime
from flask import Flask, Blueprint, session, redirect, url_for, flash, current_app
from flask_moment import Moment
import database_manager

# Import the ConfigLoader from the same package
from .config_loader import ConfigLoader, FACEBOOK_PAGES

# Define a default configuration class
class DefaultConfig:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'a_very_secret_key_for_session_management')
    DATABASE_FILE = 'facebook_posts_data.db'
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'Generated_Posts_Output')
    
    DEFAULT_TEXT_GEN_PROVIDER = os.getenv('DEFAULT_TEXT_GEN_PROVIDER', "Gemini")
    DEFAULT_GEMINI_MODEL = os.getenv('DEFAULT_GEMINI_MODEL', "gemini-1.5-flash")
    DEFAULT_OPENAI_TEXT_MODEL = os.getenv('DEFAULT_OPENAI_TEXT_MODEL', "gpt-3.5-turbo")
    DEFAULT_OPENAI_IMAGE_MODEL = os.getenv('DEFAULT_OPENAI_IMAGE_MODEL', "dall-e-3")
    DEFAULT_IMAGE_GEN_PROVIDER = os.getenv('DEFAULT_IMAGE_GEN_PROVIDER', "OpenAI (DALL-E)")
    DEFAULT_NUM_POSTS = int(os.getenv('DEFAULT_NUM_POSTS', 84))
    DEFAULT_GEMINI_TEMPERATURE = float(os.getenv('DEFAULT_GEMINI_TEMPERATURE', 0.7))
    DEFAULT_START_DATE = os.getenv('DEFAULT_START_DATE', datetime.now().strftime("%Y-%m-%d"))

# Flag to ensure one-time initialization tasks are only run once per app instance
_app_initialized = False

def create_app(project_root=None):
    global _app_initialized
    
    if project_root is None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

    templates_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')

    app = Flask(__name__, 
                root_path=project_root, 
                template_folder=templates_dir, 
                static_url_path='/static', # Explicitly set URL path
                static_folder=static_dir) # Explicitly set static folder
    
    app.config.from_object(DefaultConfig)
    app.secret_key = app.config['SECRET_KEY']

    Moment(app)

    os.makedirs(app.config.get('OUTPUT_DIR', 'Generated_Posts_Output'), exist_ok=True)
    os.makedirs(os.path.join(app.config.get('OUTPUT_DIR', 'Generated_Posts_Output'), "generated_images"), exist_ok=True)

    # Register blueprints (these need to be imported first)
    from .main_routes import main_routes
    from .topic_routes import topic_routes
    from .post_routes import post_routes
    from .feedback_routes import feedback_routes
    from .tracking_routes import tracking_routes
    from .ml_routes import ml_routes
    from .page_routes import page_routes

    app.register_blueprint(main_routes)
    app.register_blueprint(topic_routes)
    app.register_blueprint(post_routes)
    app.register_blueprint(feedback_routes)
    app.register_blueprint(tracking_routes)
    app.register_blueprint(ml_routes)
    app.register_blueprint(page_routes)


    if not _app_initialized:
        print(f"[DEBUG - Path Check in __init__.py create_app]: app.root_path is: {app.root_path}")
        print(f"[DEBUG - Path Check in __init__.py create_app]: app.static_folder is: {app.static_folder}")
        ConfigLoader.load_app_config(app)
        print(f"[DEBUG - __init__.py]: After ConfigLoader.load_app_config, FACEBOOK_PAGES has {len(FACEBOOK_PAGES)} entries.")
        if FACEBOOK_PAGES:
            print(f"[DEBUG - __init__.py]: First page name: {FACEBOOK_PAGES[0].get('page_name')}")
        database_manager.create_tables()
        _app_initialized = True

    app.jinja_env.globals.update(
        get_page_names=get_page_names,
        get_page_by_name=get_page_by_name,
        get_api_key_status=get_api_key_status,
        get_post_details_for_template=get_post_details_for_template,
        FACEBOOK_PAGES=FACEBOOK_PAGES
    )

    @app.before_request
    def check_facebook_pages_loaded_before_request():
        if not session.get('pages_checked') and not FACEBOOK_PAGES:
            flash("No Facebook pages configured. Please add pages via the 'Page Details' tab.", "warning")
            session['pages_checked'] = True

    return app

def get_page_names():
    return [page["page_name"] for page in FACEBOOK_PAGES]

def get_page_by_name(page_name):
    return next((p for p in FACEBOOK_PAGES if p["page_name"] == page_name), None)

def save_app_config():
    if current_app:
        ConfigLoader.save_app_config(current_app)
    else:
        print("[ERROR - save_app_config]: current_app not available. Cannot save config.")

def get_api_key_status():
    status = {}
    status['GEMINI_API_KEY'] = "Found" if os.getenv('GEMINI_API_KEY') else "Not Found"
    status['OPENAI_API_KEY'] = "Found" if os.getenv('OPENAI_API_KEY') else "Not Found"
    
    gcp_project_id = os.getenv('GCP_PROJECT_ID')
    gcp_region = os.getenv('GCP_REGION')
    status['IMAGEN_STATUS'] = f"Set (Project: {gcp_project_id}, Region: {gcp_region})" if gcp_project_id and gcp_region else "Not Set (Required for Imagen)"
    
    return status

def get_post_details_for_template(db_post_id):
    post_details = database_manager.get_post_details_by_db_id(db_post_id)
    if post_details and 'post_hour' in post_details:
        post_details['post_hour'] = f"{post_details['post_hour']:02d}:00"
    return post_details