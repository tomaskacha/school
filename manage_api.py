#!/usr/bin/python3

import logging
from flask import Flask, request, jsonify, json
from werkzeug.exceptions import HTTPException
import wl_dns


# -------------------- Logging configuration ------------- #
LOGGER_FILE = '/opt/log/python_api.log'
LOGGER_LEVEL = logging.DEBUG
# Nuber of rotated log files
LOGGER_COUNT = 12
# Create logger and set it's name
logger = logging.getLogger(name='manage_api')
logger_format = logging.Formatter(fmt='%(asctime)s - %(name)s.%(funcName)s\
    - %(levelname)s - %(message)s')
logger_handler = logging.handlers.TimedRotatingFileHandler(
    filename=LOGGER_FILE,
    when='midnight',
    backupCount=LOGGER_COUNT)
logger_handler.setFormatter(logger_format)
logger.addHandler(logger_handler)
logger.setLevel(LOGGER_LEVEL)
logger.debug('Logger configuration finished.')

app = Flask(__name__)

@app.route('/dns_set', methods=['POST'])
def dns_set() -> str:
    if request.headers['Content-Type'] != 'application/json':
        logger.debug(request.headers['Content-Type'])
        return jsonify(msg=('Header Error'))
    
    data = request.get_json()
    return wl_dns.run(data)

@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


if __name__ == '__main__':
    app.run(debug=False, host='127.0.0.1', port=8080)
