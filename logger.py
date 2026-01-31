import logging
import sys

def setup_logging(level=logging.INFO):
    """
    Sets up the logging configuration.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_logger(name):
    """
    Returns a logger with the given name.
    """
    return logging.getLogger(name)
