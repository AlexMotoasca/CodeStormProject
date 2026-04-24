"""WSGI entry point for production deployment."""
import os
from app import create_app

# Get Flask environment
env = os.getenv('FLASK_ENV', 'production')

# Create app
app = create_app()

if __name__ == '__main__':
    # This is only for local testing; use gunicorn for production
    app.run()

