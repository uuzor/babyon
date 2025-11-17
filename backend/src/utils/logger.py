"""
Advanced logging utility with extensive debug capabilities
Provides colorful, structured logging for smooth debugging
"""
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import json


class ColorFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
        'BOLD': '\033[1m',        # Bold
    }

    def format(self, record: logging.LogRecord) -> str:
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{self.COLORS['BOLD']}"
                f"{levelname:8}{self.COLORS['RESET']}"
            )

        # Add timestamp with color
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        record.timestamp = f"{self.COLORS['DEBUG']}{timestamp}{self.COLORS['RESET']}"

        # Add module name with color
        record.module_name = f"{self.COLORS['DEBUG']}[{record.name}]{self.COLORS['RESET']}"

        return super().format(record)


def get_logger(
    name: str,
    level: str = "DEBUG",
    log_to_file: bool = False,
    log_file: str = "babylon_analytics.log"
) -> logging.Logger:
    """
    Get a configured logger instance with extensive debug output

    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to also log to a file
        log_file: Log file path if log_to_file is True

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only add handlers if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, level.upper()))

        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        # Format: timestamp [module] LEVEL message
        console_format = "%(timestamp)s %(module_name)s %(levelname)s %(message)s"
        console_handler.setFormatter(ColorFormatter(console_format))
        logger.addHandler(console_handler)

        # File handler (optional, without colors)
        if log_to_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
            file_handler.setFormatter(logging.Formatter(file_format))
            logger.addHandler(file_handler)

        print(f"✓ Logger '{name}' initialized at {level} level")

    return logger


class DebugLogger:
    """Enhanced logger with structured debug methods"""

    def __init__(self, name: str, level: str = "DEBUG"):
        self.logger = get_logger(name, level)
        self.name = name

    def debug(self, msg: str, **kwargs):
        """Debug message with optional context"""
        if kwargs:
            self.logger.debug(f"{msg} | Context: {self._format_context(kwargs)}")
        else:
            self.logger.debug(msg)

    def info(self, msg: str, **kwargs):
        """Info message with optional context"""
        if kwargs:
            self.logger.info(f"{msg} | {self._format_context(kwargs)}")
        else:
            self.logger.info(msg)

    def warning(self, msg: str, **kwargs):
        """Warning message with optional context"""
        if kwargs:
            self.logger.warning(f"{msg} | {self._format_context(kwargs)}")
        else:
            self.logger.warning(msg)

    def error(self, msg: str, exc: Optional[Exception] = None, **kwargs):
        """Error message with optional exception and context"""
        error_msg = msg
        if exc:
            error_msg += f" | Exception: {type(exc).__name__}: {str(exc)}"
        if kwargs:
            error_msg += f" | {self._format_context(kwargs)}"
        self.logger.error(error_msg)

    def critical(self, msg: str, exc: Optional[Exception] = None, **kwargs):
        """Critical message with optional exception and context"""
        error_msg = msg
        if exc:
            error_msg += f" | Exception: {type(exc).__name__}: {str(exc)}"
        if kwargs:
            error_msg += f" | {self._format_context(kwargs)}"
        self.logger.critical(error_msg)

    def log_function_call(self, func_name: str, args: tuple = (), kwargs: dict = None):
        """Log function call with arguments"""
        kwargs = kwargs or {}
        self.debug(
            f"🔧 Calling {func_name}",
            args=str(args)[:100],  # Truncate long args
            kwargs=str(kwargs)[:100]
        )

    def log_api_request(self, method: str, url: str, params: dict = None, body: dict = None):
        """Log API request details"""
        self.info(
            f"🌐 API Request: {method} {url}",
            params=params,
            body_size=len(str(body)) if body else 0
        )

    def log_api_response(self, status_code: int, url: str, response_size: int = 0, duration_ms: float = 0):
        """Log API response details"""
        emoji = "✅" if status_code < 400 else "❌"
        self.info(
            f"{emoji} API Response: {status_code}",
            url=url[:80],
            size=response_size,
            duration_ms=round(duration_ms, 2)
        )

    def log_database_query(self, query: str, params: dict = None, duration_ms: float = 0):
        """Log database query"""
        self.debug(
            f"🗄️  DB Query",
            query=query[:200],  # Truncate long queries
            params=params,
            duration_ms=round(duration_ms, 2) if duration_ms else None
        )

    def log_block_processed(self, height: int, tx_count: int, duration_ms: float):
        """Log block processing"""
        self.info(
            f"⛓️  Block #{height} processed",
            transactions=tx_count,
            duration_ms=round(duration_ms, 2)
        )

    def log_indexer_progress(self, current: int, target: int, blocks_per_sec: float):
        """Log indexer sync progress"""
        progress = (current / target * 100) if target > 0 else 0
        behind = target - current
        self.info(
            f"📊 Indexer Progress: {current}/{target}",
            progress_pct=round(progress, 2),
            behind=behind,
            blocks_per_sec=round(blocks_per_sec, 2)
        )

    def log_performance(self, operation: str, duration_ms: float, items_processed: int = 0):
        """Log performance metrics"""
        rate = items_processed / (duration_ms / 1000) if duration_ms > 0 and items_processed > 0 else 0
        self.debug(
            f"⚡ Performance: {operation}",
            duration_ms=round(duration_ms, 2),
            items=items_processed,
            items_per_sec=round(rate, 2) if rate else None
        )

    def log_cache_operation(self, operation: str, key: str, hit: bool = None):
        """Log cache operations"""
        emoji = "💚" if hit else "💔" if hit is False else "💾"
        self.debug(
            f"{emoji} Cache {operation}",
            key=key[:100],
            hit=hit
        )

    def log_ml_prediction(self, model: str, input_size: int, prediction: Any, confidence: float = None):
        """Log ML model predictions"""
        self.debug(
            f"🤖 ML Prediction: {model}",
            input_size=input_size,
            prediction=str(prediction)[:50],
            confidence=round(confidence, 4) if confidence else None
        )

    def log_startup(self, component: str, config: dict = None):
        """Log component startup"""
        self.info(
            f"🚀 Starting {component}",
            config={k: str(v)[:50] for k, v in config.items()} if config else None
        )

    def log_shutdown(self, component: str, reason: str = None):
        """Log component shutdown"""
        self.info(
            f"🛑 Shutting down {component}",
            reason=reason
        )

    def log_metric(self, metric_name: str, value: float, unit: str = None, tags: dict = None):
        """Log a metric value"""
        self.debug(
            f"📈 Metric: {metric_name}",
            value=value,
            unit=unit,
            tags=tags
        )

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary for logging"""
        try:
            # Try to format as JSON for readability
            formatted = json.dumps(context, default=str, separators=(',', ':'))
            return formatted if len(formatted) < 200 else formatted[:200] + "..."
        except:
            return str(context)[:200]


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("Testing Babylon Analytics Logger")
    print("=" * 80)

    # Basic logger
    logger = get_logger("test.module", level="DEBUG")
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")

    print("\n" + "=" * 80)
    print("Testing Enhanced Debug Logger")
    print("=" * 80)

    # Enhanced logger
    debug_logger = DebugLogger("test.enhanced")

    debug_logger.log_startup("Babylon Indexer", {"rpc_url": "https://rpc.testnet.babylon", "start_height": 1000})
    debug_logger.log_api_request("GET", "https://rpc.babylon/block", params={"height": 12345})
    debug_logger.log_api_response(200, "https://rpc.babylon/block", response_size=1024, duration_ms=45.67)
    debug_logger.log_block_processed(12345, 42, 123.45)
    debug_logger.log_indexer_progress(12345, 15000, 25.5)
    debug_logger.log_database_query("SELECT * FROM blocks WHERE height > $1", {"height": 1000}, 15.3)
    debug_logger.log_cache_operation("GET", "block:12345", hit=True)
    debug_logger.log_ml_prediction("address_classifier", 30, "exchange", 0.8754)
    debug_logger.log_performance("block_parsing", 45.2, 100)
    debug_logger.log_metric("blocks_indexed", 12345, "blocks", {"chain": "babylon"})

    print("\n" + "=" * 80)
    print("✓ Logger testing complete!")
    print("=" * 80)
