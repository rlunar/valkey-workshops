from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
  pass

db = SQLAlchemy(model_class=Base)

# Initialize the Flask application
app = Flask(__name__)

# REQUIRED: A secret key for the session and the debug toolbar
# In a real application, use a more secure, randomly generated key
app.config['SECRET_KEY'] = 'a_very_secret_key'

# Optional: Set to False to disable the toolbar intercepting redirects
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# Initialize the debug toolbar
toolbar = DebugToolbarExtension(app)

# Define a simple route
@app.route('/')
def index():
    """Renders a simple greeting."""
    return '<html><head><title>Flask</title></head><body><h1>Hello, World!</h1><p>Welcome to the Flask Debug Toolbar example.</p></body></html>'

if __name__ == '__main__':
    # Run the app in debug mode to see the toolbar
    app.run(debug=True)