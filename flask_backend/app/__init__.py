"""Flask app initialization and configuration."""
from flask import Flask
from flask_cors import CORS
from config import get_config
from app.models import db


def create_app(config_name=None):
    """
    Application factory function.
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
        
    Returns:
        Flask app instance
    """
    config = get_config()
    
    app = Flask(__name__)
    app.config.from_object(config)
    
    # Initialize database
    db.init_app(app)
    
    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": config.CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })
    
    # Register blueprints
    from app.routes import pdf_bp, parser_bp, gemini_bp, comparison_bp, pdf_edit_bp, health_bp
    
    app.register_blueprint(pdf_bp.bp)
    app.register_blueprint(parser_bp.bp)
    app.register_blueprint(gemini_bp.bp)
    app.register_blueprint(comparison_bp.bp)
    app.register_blueprint(pdf_edit_bp.bp)
    app.register_blueprint(health_bp.bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        from app.utils import APIResponse
        return APIResponse.error(
            'NOT_FOUND',
            'Endpoint not found',
            status_code=404
        )
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        from app.utils import APIResponse
        return APIResponse.error(
            'METHOD_NOT_ALLOWED',
            'HTTP method not allowed',
            status_code=405
        )
    
    @app.errorhandler(500)
    def internal_error(error):
        from app.utils import APIResponse
        print(f"Internal server error: {str(error)}")
        return APIResponse.error(
            'INTERNAL_ERROR',
            'Internal server error',
            status_code=500
        )
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)

