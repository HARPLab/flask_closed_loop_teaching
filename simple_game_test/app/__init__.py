from gevent import monkey
# Patch standard libraries for Gevent compatibility
monkey.patch_all()

print("Monkey patched?", monkey.is_module_patched("socket"))


from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

import logging, os
from werkzeug.middleware.proxy_fix import ProxyFix





app = Flask(__name__)
app.config.from_object(Config)

# app.config['SESSION_COOKIE_PATH'] = '/flask_closed_loop_teaching' # default is APPLICATION_ROOT
# app.static_url_path = '/flask_closed_loop_teaching/static'  # default is APPLICATION_ROOT/static
# app.config['WTF_CSRF_ENABLED'] = False  # Ensure CSRF protection is explicitly enabled



db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = "login"

# socketio = SocketIO(app,  ping_timeout=60, ping_interval=25)  # for running on local host
# socketio.init_app(app)

# app.config['APPLICATION_ROOT'] = '/flask_closed_loop_teaching'
# socketio = SocketIO(app, path="/flask_closed_loop_teaching/socket.io", cors_allowed_origins="*")  # Allow cross-origin for local testing

socketio = SocketIO(app, path="/socket.io", cors_allowed_origins="*")  # Allow cross-origin for local testing


# Initialize SocketIO with gevent
# socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# if os.environ.get("FLASK_ENV") == "development":
#     socketio = SocketIO(app)  # for running on local host
#     # socketio = SocketIO(app, path='/socket.io/', async_mode="gevent", cors_allowed_origins="*")
#     print("App url map in development mode:", app.url_map)
# else:
#     app.config['APPLICATION_ROOT'] = '/flask_closed_loop_teaching'
#     app.config['FORCE_SCRIPT_NAME'] = '/flask_closed_loop_teaching'
# 	# app.config['SESSION_COOKIE_SECURE'] = True  # Needed if running on HTTPS, 
# 	# app.config['PREFERRED_URL_SCHEME'] = 'https'
#     socketio = SocketIO(app, async_mode='gevent', path='/flask_closed_loop_teaching/socket.io', cors_allowed_origins="*")
#     # socketio = SocketIO(app, path='/flask_closed_loop_teaching/socket.io', cors_allowed_origins="*")
#     print("App url map in production mode:", app.url_map)

socketio.init_app(app)  # explicitly initialize the socketio object


app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1) # Apply ProxyFix middleware for subroutes in externalnginx server

# if __name__ == '__main__':
# 	socketio.run(app)

from app import routes, models

print("Final App url map after socketio initialization.", app.url_map)


# comment lines below when creating the database. uncomment lines below when running the app
from app.params import ONLINE_CONDITIONS, IN_PERSON_CONDITIONS


pool_size = min(os.cpu_count(), 64)
print(f"Using {pool_size} processes")

# ## Initialize the multiprocessing tools
# from multiprocessing import Manager, Pool, Lock  # Multiprocessing tools do not work well with gevent server
# manager = Manager()
# lock = manager.Lock()
# pool = Pool(processes=pool_size)  # Adjust the number of processes as needed  (python multiprocessing)


# Lock with threading
from threading import Lock
lock = Lock()

# from multiprocessing import Pool
# pool = Pool(processes=pool_size)  # Adjust the number of processes as needed  (python multiprocessing)

from gevent.pool import Pool
pool = Pool(size=pool_size)  # Adjust the number of processes as needed  (gevent pool)



logging.basicConfig(level=logging.DEBUG)

rows = (db.session.query(models.OnlineCondition).count() + db.session.query(models.InPersonCondition).count())
if rows == 0:
	for condition in ONLINE_CONDITIONS:
		no_feedback_trial = condition.index("no_feedback")
		feedback_trial = 1 - no_feedback_trial
		feedback_type = condition[feedback_trial]
		trials = condition
		db.session.add(models.OnlineCondition(trials=trials, no_feedback_trial=no_feedback_trial, feedback_trial=feedback_trial, feedback_type=feedback_type, count=0))
	for condition in IN_PERSON_CONDITIONS:
		trials = condition
		db.session.add(models.InPersonCondition(trials=trials, trial_1=condition[0], trial_2=condition[1], trial_3=condition[2], trial_4=condition[3], trial_5=condition[4], count=0))

# # remove the 3 lines below when starting the second round of trials
# db.session.query(models.Round).delete()
# db.session.query(models.Group).delete()

old_group = db.session.query(models.Group).first()
if old_group is None:
	group = models.Group(user_ids=[])
	db.session.add(group)

db.session.commit()

# if __name__ == "__main__" and os.environ.get("FLASK_ENV") == "development":
#     socketio.run(app, debug=True, host="127.0.0.1", port=5000, use_reloader=False)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
