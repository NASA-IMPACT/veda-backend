"""AWS Lambda handler."""

import logging
import os

try:
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ["SECRET_ACCESS_KEY"]
    os.environ["AWS_ACCESS_KEY_ID"] = os.environ["ACCESS_KEY_ID"]
    os.environ["AWS_SESSION_TOKEN"] = os.environ["SESSION_TOKEN"]
except KeyError:
    print("Earthdata session token not found")

from mangum import Mangum
from src.app import app

logging.getLogger("mangum.lifespan").setLevel(logging.ERROR)
logging.getLogger("mangum.http").setLevel(logging.ERROR)

handler = Mangum(app, lifespan="auto")
