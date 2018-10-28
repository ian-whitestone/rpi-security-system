from app import application
from app import config

config.init_logging()

if __name__ == '__main__':
    application.run(debug=True, host='0.0.0.0', port=52961, threaded=True)

