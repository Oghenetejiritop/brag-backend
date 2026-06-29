import logging


def get_logger(name: str = "brag") -> logging.Logger:
    """
    Creates and returns a configured logger for BRAG.

    This ensures consistent logging across all services.
    """

    logger = logging.getLogger(name)

    # Prevent duplicate handlers (important in FastAPI later)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        fmt="[BRAG] %(levelname)s - %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

