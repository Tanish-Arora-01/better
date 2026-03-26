"""Application configuration."""

import os


class Config:
    """Base configuration."""

    BASE_DIR: str = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'sip_billing.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    TESTING: bool = False


class TestingConfig(Config):
    """Configuration overrides for tests."""

    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    TESTING: bool = True
