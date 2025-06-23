import logging
import os

def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """
    Setup a logger with the specified name and log file.
    
    Parameters:
        name (str): Name of the logger.
        log_file (str): Path to the log file.
        level (int): Logging level.
    
    Returns:
        logging.Logger: Configured logger instance.
    """
    # Ensure the log directory exists
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if not logger.handlers:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger