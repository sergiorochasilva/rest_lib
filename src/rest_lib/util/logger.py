import logging
import os

APP_NAME = os.getenv("APP_NAME", "rest_lib")


def get_logger():
    return logging.getLogger(APP_NAME)
