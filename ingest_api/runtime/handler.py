"""
Entrypoint for Lambda execution.
"""

from mangum import Mangum
from src.main import app

handler = Mangum(app, lifespan="off")
