"""
n8n Integration Hub Backend - Configuration

Environment-based configuration using pydantic-settings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "n8n Integration Hub"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"  # level for this module's own loggers; see app.logging_setup
    
    # API
    api_prefix: str = "/api/n8n-nkz"
    cors_origins: list[str] = ["*"]
    
    # Keycloak / JWT Authentication
    keycloak_url: str = "https://auth.robotika.cloud/auth"
    keycloak_internal_url: str = ""  # Internal K8s service URL (e.g. http://keycloak:8080/auth)
    keycloak_realm: str = "nekazari"
    jwt_audience: str = "account"
    jwt_issuer: str = ""  # Auto-derived from keycloak_url + realm if empty

    # Service-to-service authentication
    module_management_key: str = ""

    # ==========================================================================
    # Integration Service URLs
    # ==========================================================================

    n8n_encryption_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    n8n_addon_price_eur: float = 4.99
    n8n_addon_price_id: str = ""  # Stripe Price ID

    # Provisioning
    n8n_grace_period_days: int = 30
    n8n_instance_image: str = "n8nio/n8n:latest"
    frontend_url: str = "https://nekazari.robotika.cloud"

    # Intelligence Module
    intelligence_url: str = "http://intelligence-api-service:8000"
    intelligence_api_prefix: str = "/api/intelligence"
    
    # NDVI Worker
    ndvi_worker_url: str = "http://ndvi-worker-service:8000"
    
    # Notification Services
    email_service_url: str = "http://email-service:8000"
    
    # Odoo ERP
    odoo_url: str = ""
    odoo_db: str = ""
    odoo_username: str = ""
    odoo_password: str = ""
    
    # ROS2 Bridge
    ros2_bridge_url: str = "http://ros2-fiware-bridge-service:8000"
    
    # Orion-LD
    orion_url: str = "http://orion-ld-service:1026"
    context_url: str = "https://nekazari.robotika.cloud/ngsi-ld-context.json"
    
    # Redis (for caching)
    redis_host: str = "redis-service"
    redis_port: int = 6379
    redis_password: str = ""
    
    # Database (for webhook configs)
    database_url: str = ""
    
    @property
    def jwt_issuer_url(self) -> str:
        """Get the JWT issuer URL."""
        if self.jwt_issuer:
            return self.jwt_issuer
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"
    
    @property
    def jwks_url(self) -> str:
        """Get the JWKS URL for token verification."""
        return f"{self.jwt_issuer_url}/protocol/openid-connect/certs"
    
    @property
    def intelligence_base_url(self) -> str:
        """Get full intelligence service URL."""
        return f"{self.intelligence_url}{self.intelligence_api_prefix}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
