import logging

LOG_LEVEL = logging.INFO

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(name)s:%(levelname)s:%(message)s"))
logging.basicConfig(level=LOG_LEVEL)
