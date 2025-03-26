# from gevent import monkey
# # Patch standard libraries for Gevent compatibility
# monkey.patch_all()

# print("Monkey patched?", monkey.is_module_patched("socket"))

# # Import Socket.IO and app
# from app import app, socketio


# if __name__ == "__main__":
#     # For direct execution (not via Gunicorn)
#     socketio.run(
#         app, 
#         host="0.0.0.0",
#         port=5000,
#         debug=False
#     )