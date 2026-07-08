import logging
import sys

def setup_logging():
    # Setup basic logging to stdout with a clear format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True # Force override of default root handlers
    )
    
    # Optional: silence noisy third-party libraries if needed
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("hnswlib").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

    logger = logging.getLogger("app")
    logger.info("Logging configured successfully.")
