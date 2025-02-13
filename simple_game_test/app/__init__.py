from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

from flask_socketio import SocketIO
from multiprocessing import Manager, Pool, Lock
import logging, os
from werkzeug.middleware.proxy_fix import ProxyFix




app = Flask(__name__)
app.config.from_object(Config)
# app.config['APPLICATION_ROOT'] = '/flask_closed_loop_teaching/'  # Comment this line when running on local host to avoid CSRF token error
# # app.config['SESSION_COOKIE_PATH'] = '/flask_closed_loop_teaching'
# # app.config['SESSION_COOKIE_SECURE'] = True
# app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1) # Apply ProxyFix middleware for subroutes in externalnginx server
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=2)


# app.config['WTF_CSRF_ENABLED'] = False  # Ensure CSRF protection is explicitly enabled


print('app config session cookie secure:', app.config.get('SESSION_COOKIE_SECURE'))
print('app config session cookie path:', app.config.get('SESSION_COOKIE_PATH'))
print('app config application root:', app.config.get('APPLICATION_ROOT'))
print('app config secret key:', app.config.get('SECRET_KEY'))
print('app config wtf csrf enabled:', app.config.get('WTF_CSRF_ENABLED'))


db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = "login"

socketio = SocketIO(app)
# socketio.init_app(app)

# if __name__ == '__main__':
# 	socketio.run(app)

from app import routes, models

# comment lines below when creating the database. uncomment lines below when running the app
from app.params import ONLINE_CONDITIONS, IN_PERSON_CONDITIONS

# Initialize the multiprocessing tools
manager = Manager()
lock = manager.Lock()
pool_size = min(os.cpu_count(), 64)
print(f"Using {pool_size} processes")
pool = Pool(processes=pool_size)  # Adjust the number of processes as needed

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
