"""
Entrypoint for Lambda execution.
"""

import src.ingestor as ingestor

handler = ingestor.handler
