# app.py
import os
from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env file (uses python-dotenv)

# Import the create_app factory function from your routes package
from routes import create_app

# --- Main Application Entry Point ---
if __name__ == '__main__':
    # Calculate the absolute path to the project root (where app.py is located)
    explicit_project_root = os.path.abspath(os.path.dirname(__file__))

    # Create the Flask application instance, passing the explicit project root
    app = create_app(project_root=explicit_project_root)
    
    app.run(debug=True, port=5000, host='0.0.0.0')