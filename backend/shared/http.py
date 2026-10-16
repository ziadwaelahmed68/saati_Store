import logging
import sys
from flask import jsonify

def configure_logging(service_name: str):
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        f'{{"time":"%(asctime)s","service":"{service_name}","level":"%(levelname)s","msg":"%(message)s"}}'
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def err(msg: str, code: int = 400):
    return jsonify(error=msg, message=msg), code