"""AWS Lambda handler."""

import os
import logging

os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("SECRET_ACCESS_KEY")
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("ACCESS_KEY_ID")
os.environ["AWS_SESSION_TOKEN"] = os.getenv("SESSION_TOKEN")

from mangum import Mangum
from src.app import app

logging.getLogger("mangum.lifespan").setLevel(logging.ERROR)
logging.getLogger("mangum.http").setLevel(logging.ERROR)

handler = Mangum(app, lifespan="auto")
