"""
Configuration management with environment variables
Extensive logging for debugging configuration issues
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from .logger import DebugLogger

logger = DebugLogger("config")


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Babylon Chain Configuration
    babylon_rpc_url: str = Field(
        default="https://rpc.testnet-5.babylonlabs.io",
        description="Babylon RPC endpoint URL"
    )
    babylon_rest_url: str = Field(
        default="https://lcd.testnet-5.babylonlabs.io",
        description="Babylon REST API endpoint URL"
    )
    babylon_ws_url: str = Field(
        default="wss://rpc.testnet-5.babylonlabs.io/websocket",
        description="Babylon WebSocket endpoint URL"
    )
    start_height: int = Field(
        default=1,
        description="Block height to start indexing from"
    )
    chain_id: str = Field(
        default="bbn-test-5",
        description="Babylon chain ID"
    )

    # Database Configuration
    database_url: str = Field(
        default="postgresql://dev:dev_password@localhost:5432/babylon_analytics",
        description="PostgreSQL database URL"
    )
    database_pool_size: int = Field(
        default=20,
        description="Database connection pool size"
    )
    database_echo: bool = Field(
        default=False,
        description="Echo SQL queries (for debugging)"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis URL for caching and pub/sub"
    )
    redis_db: int = Field(
        default=0,
        description="Redis database number"
    )

    # API Configuration
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    api_port: int = Field(
        default=8000,
        description="API server port"
    )
    api_workers: int = Field(
        default=1,
        description="Number of API worker processes"
    )
    api_reload: bool = Field(
        default=True,
        description="Enable auto-reload for development"
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )

    # Logging Configuration
    log_level: str = Field(
        default="DEBUG",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    log_to_file: bool = Field(
        default=False,
        description="Enable file logging"
    )
    log_file: str = Field(
        default="babylon_analytics.log",
        description="Log file path"
    )

    # Indexer Configuration
    indexer_batch_size: int = Field(
        default=100,
        description="Number of blocks to process in batch"
    )
    indexer_checkpoint_interval: int = Field(
        default=100,
        description="Save checkpoint every N blocks"
    )
    indexer_retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed requests"
    )
    indexer_retry_delay: int = Field(
        default=5,
        description="Delay between retry attempts (seconds)"
    )
    indexer_block_time: float = Field(
        default=6.0,
        description="Average block time in seconds"
    )

    # Performance Configuration
    max_workers: int = Field(
        default=4,
        description="Maximum number of worker threads"
    )
    request_timeout: int = Field(
        default=30,
        description="HTTP request timeout (seconds)"
    )

    # Security Configuration
    api_key_enabled: bool = Field(
        default=False,
        description="Enable API key authentication"
    )
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting"
    )
    rate_limit_per_minute: int = Field(
        default=60,
        description="Requests per minute per IP"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper

    def log_config(self):
        """Log configuration (with sensitive data masked)"""
        logger.log_startup("Configuration Loaded", {
            "babylon_rpc_url": self.babylon_rpc_url,
            "babylon_rest_url": self.babylon_rest_url,
            "chain_id": self.chain_id,
            "start_height": self.start_height,
            "database_url": self._mask_password(self.database_url),
            "redis_url": self._mask_password(self.redis_url),
            "api_port": self.api_port,
            "log_level": self.log_level,
            "indexer_batch_size": self.indexer_batch_size,
            "max_workers": self.max_workers,
        })

    @staticmethod
    def _mask_password(url: str) -> str:
        """Mask password in connection string"""
        if "@" in url and "://" in url:
            parts = url.split("://")
            if len(parts) == 2:
                protocol = parts[0]
                rest = parts[1]
                if "@" in rest:
                    creds, host = rest.split("@", 1)
                    if ":" in creds:
                        user, _ = creds.split(":", 1)
                        return f"{protocol}://{user}:****@{host}"
        return url


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton instance"""
    global _settings
    if _settings is None:
        print("=" * 80)
        print("🔧 Loading Babylon Analytics Configuration")
        print("=" * 80)

        _settings = Settings()
        _settings.log_config()

        print("=" * 80)
        print("✓ Configuration loaded successfully")
        print("=" * 80)

    return _settings


# Convenience function
def reload_settings() -> Settings:
    """Reload settings from environment"""
    global _settings
    _settings = None
    return get_settings()


if __name__ == "__main__":
    # Test configuration loading
    print("\n" + "=" * 80)
    print("Testing Configuration Loading")
    print("=" * 80 + "\n")

    settings = get_settings()

    print("\n" + "=" * 80)
    print("Configuration Test Complete")
    print("=" * 80)
    print(f"\n✓ Babylon RPC URL: {settings.babylon_rpc_url}")
    print(f"✓ Chain ID: {settings.chain_id}")
    print(f"✓ Start Height: {settings.start_height}")
    print(f"✓ Database URL: {settings._mask_password(settings.database_url)}")
    print(f"✓ Log Level: {settings.log_level}")
    print(f"✓ API Port: {settings.api_port}")
    print("=" * 80)
