from flask import Flask

app = Flask(__name__)

from app import config
from app import views

config.init_logging()