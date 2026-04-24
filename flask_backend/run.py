"""Flask application entry point."""
import os
from app import create_app

# Get Flask environment
env = os.getenv('FLASK_ENV', 'development')

# Create app
app = create_app()

if __name__ == '__main__':
    app.run(
        debug=(env == 'development'),
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )

