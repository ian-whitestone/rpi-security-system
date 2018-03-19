from flask import Flask

app = Flask(__name__)

from app import views
from app import utils

utils.init_logging()
