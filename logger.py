import logging
import os

LOG_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "jobboard.log")

app_logger = logging.getLogger("jobboard")
app_logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
app_logger.addHandler(fh)
