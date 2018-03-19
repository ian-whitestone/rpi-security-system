from app import main_app
from app import socketio

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=52961, threaded=True)
    socketio.run(debug=True, host='0.0.0.0', port=52962)

