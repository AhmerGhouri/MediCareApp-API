import logging
from logging.handlers import RotatingFileHandler
import os

# Create a 'logs' directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Initialize the logger
logger = logging.getLogger("hospital_api")
logger.setLevel(logging.INFO) # Captures INFO, WARNING, ERROR, and CRITICAL

# Setup Rotating File Handler
# This keeps the log file at a max of 5MB. Once full, it renames it to api_audit.log.1 
# and starts a fresh one. It keeps up to 5 backup files.
log_file = os.path.join(LOG_DIR, "api_audit.log")
handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)

# Define the exact format of the log message
# Example: 2026-07-20 11:16:11,123 - ERROR - [auth.py:42] - Failed to send OTP
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)