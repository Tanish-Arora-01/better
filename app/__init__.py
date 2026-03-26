"""Flask application factory and extensions."""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from marshmallow import ValidationError

db = SQLAlchemy()


def create_app(config_name: str = "config.Config") -> Flask:
    """Create and configure the Flask application.

    Args:
        config_name: Dotted path to the configuration class.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_name)

    db.init_app(app)
    CORS(app)

    # ── Global error handlers ────────────────────────────────────────
    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):  # type: ignore[type-arg]
        """Return a standardised 400 response for any Marshmallow
        validation failure, as required by Interface Safety rules."""
        return jsonify({"error": "Invalid payload", "details": exc.messages}), 400

    with app.app_context():
        # Import models so SQLAlchemy registers them before table creation.
        from app import models  # noqa: F401

        db.create_all()

    # ── Register blueprints ──────────────────────────────────────────
    from app.routes import api as api_bp  # noqa: E402

    app.register_blueprint(api_bp)

    return app
