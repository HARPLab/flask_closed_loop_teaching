# # First, import multiprocessing to ensure it's initialized before patching
# import multiprocessing

# # Set the start method to 'fork' which works better with gevent
# # (Only use on Linux - on Windows or Mac use 'spawn')
# multiprocessing.set_start_method('fork')

# # Now apply gevent monkey patching
# from gevent import monkey
# monkey.patch_all(thread=False)  # Don't patch threading to avoid conflicts

# # Now import your application
# from app import app, socketio

# if __name__ == "__main__":
#     socketio.run(
#         app, 
#         host="0.0.0.0",
#         port=5000,
#         debug=False
#     )

###############################

from app import app as flask_app
from middleware import WebSocketBlocker

# Apply the WebSocketBlocker middleware specifically for login routes
app = WebSocketBlocker(flask_app)

if __name__ == "__main__":
    flask_app.run()