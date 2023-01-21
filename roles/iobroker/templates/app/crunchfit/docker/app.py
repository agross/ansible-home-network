from logging.config import dictConfig
from flask import Flask, jsonify
import datetime
import os
import populartimes

dictConfig({
  'version': 1,
  'formatters': {
    'default': {
      'format': '[%(asctime)s] %(levelname)s: %(message)s',
    }
  },
  'handlers': {
    'wsgi': {
      'class': 'logging.StreamHandler',
      'stream': 'ext://flask.logging.wsgi_errors_stream',
      'formatter': 'default'
    }
  },
  'root': {
    'level': 'INFO',
    'handlers': ['wsgi']
  }
})

app = Flask(__name__)

API_KEY = os.environ['API_KEY']
PLACE_ID = os.environ['PLACE_ID']

@app.route('/')
def index():
  data = populartimes.get_id(API_KEY, PLACE_ID)
  app.logger.info(data)

  return jsonify(data)

if __name__ == '__main__':
  app.run(debug=True)
