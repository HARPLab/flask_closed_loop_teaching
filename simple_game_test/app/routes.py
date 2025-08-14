from flask import render_template, flash, redirect, url_for, request, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from flask_socketio import join_room, leave_room, rooms
import asyncio
from flask import redirect, url_for, jsonify, render_template
from flask_login import logout_user


print('Routes: Loaded flask apps...')

from app import app, db
from app.forms import LoginForm, RegistrationForm, TrialForm, DemoForm, ConsentForm, AttentionCheckForm, FinalForm, TrainingForm, FeedbackSurveyForm, NoFeedbackSurveyForm, InformativenessForm
from app.models import User, Trial, Demo, Survey, Domain, Group, Round, DomainParams, OnlineCondition, InPersonCondition
from app.params import *
from app.backend_test import send_signal
from app import socketio



print('Routes: Loaded "App"...')



# import numpy as np
# import random as rand
import copy
import json
import time
import threading
from threading import Timer

from datetime import datetime

from termcolor import colored
import random
# from flask import g
from datetime import date, timedelta
from itertools import cycle

import pickle
import numpy as np
from datetime import date
import matplotlib.pyplot as plt
from threading import RLock

from collections import defaultdict
from contextlib import contextmanager

# from concurrent.futures import ProcessPoolExecutor
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.exc import OperationalError

import logging, os, sys



print('Routes: Loaded python apps...')

sys.path.append(os.path.join(os.path.dirname(__file__), 'group_teaching'))
from .group_teaching.codes.user_study.user_study_utils import generate_demos_test_interaction_round, initialize_teaching, obtain_constraint, normalize_trajectories
from .group_teaching.codes.policy_summarization.BEC_helpers import remove_redundant_constraints, update_variable_filter
from .group_teaching.codes.teams.teams_helpers import update_team_knowledge, check_unit_learning_goal_reached
from .group_teaching.codes.params_utils import get_mdp_parameters

#################################
# Define log file
log_filename = os.path.join(os.path.dirname(__file__), "app_log.txt")

# Create the log file if it doesn't exist
if not os.path.exists(log_filename):

    with open(log_filename, 'w') as f:
        f.write("")  # create empty file

# Set up logging to file and console
logging.basicConfig(
    level=logging.DEBUG,  # Capture both INFO and ERROR logs
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, mode="a"),  # Append logs to file
        # logging.StreamHandler(sys.stdout)  # Also print logs to console
    ]
)


class LoggerWriter:
    """Redirects stdout and stderr to logging."""
    
    def __init__(self, level):
        self.level = level  # Log level (INFO for stdout, ERROR for stderr)

    def write(self, message):
        if message.strip():  # Ignore empty messages
            self.level(message.strip())  # Log the message

    def flush(self):
        pass  # Needed for compatibility with sys.stdout/sys.stderr


# Redirect stdout and stderr to logging
sys.stdout = LoggerWriter(logging.info)  # Redirect print() to logging (INFO)
sys.stderr = LoggerWriter(logging.error)  # Redirect errors to logging (ERROR)


# --- ANSI color support ---
ANSI_CODES = {'red':'31','green':'32','yellow':'33','blue':'34','magenta':'35','cyan':'36'}

def _ansi_enabled():
    # enable if real TTY and TERM not dumb, or FORCE_COLOR=1
    if os.environ.get("FORCE_COLOR") == "1":
        return True
    s = getattr(sys, "__stdout__", None)
    return bool(s and hasattr(s, "isatty") and s.isatty() and os.environ.get("TERM") not in ("", None, "dumb"))

def _colorize(text, color, bold=True):
    if not _ansi_enabled():
        return text
    code = ANSI_CODES.get(color, '37')
    return f"\033[{'1;' if bold else ''}{code}m{text}\033[0m"

# --- stable per-group colors ---
_GROUP_COLORS = ['cyan','green','yellow','magenta','blue','red','white']
_color_cycle = cycle(_GROUP_COLORS)
_group_to_color = {}  # group_id -> color
def _color_for(group_id):
    if group_id not in _group_to_color:
        _group_to_color[group_id] = next(_color_cycle)
    return _group_to_color[group_id]

def group_print(group_id, *args, level=logging.INFO):
    """Log plain text to file; print colored to console (sys.__stdout__)."""
    msg = " ".join(map(str, args))
    tag = f"[Group {group_id}] "
    # file log stays clean (no ANSI)
    logging.log(level, f"{tag}{msg}")
    # console pretty
    try:
        line = _colorize(f"{tag}{msg}", _color_for(group_id), bold=True)
        sys.__stdout__.write(line + "\n")
        sys.__stdout__.flush()
    except Exception:
        # never break app on console issues
        pass
##########################################


ideal_kc_constraints = {'at': {}, 'sb': {}}
ideal_kc_constraints['at'][0] = [np.array([[ 1,  0, -4]]), np.array([[-1,  0,  2]])]
ideal_kc_constraints['at'][1] = [np.array([[ 0, -1, -4]]), np.array([[0, 1, 2]])]
ideal_kc_constraints['at'][2] = [np.array([[ 1, 1, 0]])]

ideal_kc_constraints['sb'][0] = [np.array([[ 0, -2, -1]]), np.array([[0, 5, 2]])]
ideal_kc_constraints['sb'][1] = [np.array([[-6,  0, -5]]), np.array([[4, 0, 3]])]
ideal_kc_constraints['sb'][2] = [np.array([[-6,  4, -3]]), np.array([[5, 2, 5]]), np.array([[ 3, -3,  1]])]


#####################################


def log_print(*args):
    """Log messages and ensure they are printed to both file and console."""
    message = " ".join(map(str, args))
    logging.info(message)


def log_error(*args):
    """Log messages and ensure they are printed to both file and console."""
    message = " ".join(map(str, args))
    logging.error(message)


def status_print(*args):
    """Log important status messages to both file and console."""
    message = " ".join(map(str, args))
    # Log to file via the regular logger
    logging.info(message)
    # Also print to console directly (bypassing redirections)
    print(f"STATUS: {message}", file=sys.__stdout__)

def normalize_constraints(lst):
    return set(tuple(map(tuple, arr)) for arr in lst)

######################################


log_print('Routes: Loaded group teaching apps...')

# print("App url map:", app.url_map)

# db_lock = Lock()
disconnected_users_lock = RLock()
# executor = ProcessPoolExecutor()

# Dictionary to store locks per group - automatically creates locks as needed
group_locks = defaultdict(RLock)

# Keep the global lock only for operations that affect multiple groups
global_db_lock = RLock()

log_print('Global db lock: ', global_db_lock)


@contextmanager
def group_database_transaction(group_id, context, retries=5, base_delay=0.1):
    """
    Context manager for group-specific database operations
    Only locks operations for the specific group
    """
    group_db_lock = group_locks[group_id]
    with group_db_lock:
        attempt = 0
        while attempt < retries:
            try:
                yield db.session
                db.session.flush()
                db.session.commit()
                if current_user and current_user.is_authenticated:
                    log_print('Group:', group_id, '. Current user: ', current_user.id, 'Group db lock - process complete. ', context)
                return
            except OperationalError as e:
                if current_user and current_user.is_authenticated:
                    log_print('Group:', group_id,'. Current user: ', current_user.id, 'Group lock is still active... ', context, 'Error:', str(e))
                if "database is locked" in str(e):
                    delay = base_delay * (2 ** attempt)  # exponential backoff
                    time.sleep(delay)
                    attempt += 1
                    continue
                else:
                    db.session.rollback()
                    raise
        db.session.rollback()
        raise RuntimeError(f"Failed to complete transaction for group {group_id} after {retries} retries.")


with open(os.path.join(os.path.dirname(__file__), 'group_user_study_dict.json'), 'r') as f:
    default_rounds = json.load(f)

# with open(os.path.join(os.path.dirname(__file__), 'user_study_dict.json'), 'r') as f:
#     default_rounds = json.load(f)

# print(default_rounds)

# rule_str = None
# TODO need a proper solution instead of global variables, i.e. per-user environment
# https://stackoverflow.com/questions/27611216/how-to-pass-a-variable-between-flask-pages
    
# pallavi's study
'''
learners = {}
MODE = 'hard'
'''
IS_IN_PERSON = False
'''
CARD_ID_TO_FEATURES = [
    [color, fill, shape, number] for color in ['red', 'green', 'purple'] for fill in ['hollow', 'striped', 'solid'] for shape in ['diamond', 'ellipse', 'squiggle'] for number in ['one', 'two', 'three']
]
'''

QUICK_DEBUG_FLAG = False

# Timeout for reconnection (in seconds)
RECONNECT_TIMEOUT = 150  # Change this to the desired time
MAX_ITERATIONS = 500
GROUP_JOIN_THRESHOLD = 1800
ROUND_GENERATION_WAIT_TIME = 10  # seconds

# List to track disconnected users
disconnected_users = {}  # Stores user ID, disconnect times, and reconnect times
disconnect_timers = {}   # Stores active timers for users
last_disconnect_pages = {}



@app.route("/", methods=["GET", "POST"])
# @app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    # online_condition_id = current_user.online_condition_id
    # current_condition = db.session.query(OnlineCondition).get(online_condition_id)

    log_print("Index url in index function:", request.url)
    log_print("User is authenticated?", current_user.is_authenticated)

    completed = True if current_user.study_completed == 1 else False

    current_user.loop_condition = "debug"
    # with global_db_lock:
    db.session.add(current_user)
    db.session.commit()

    return render_template("index.html",
                           title="Home Page",
                           completed=completed,
                           code=current_user.code)

# For Debugging
@app.route('/headers')
def headers():
    headers = dict(request.headers)
    return f"Received Headers: {headers}"


@app.route("/introduction", methods=["GET", "POST"])
@login_required
def introduction():
    # socketio.emit("intro_load_first_round", to=request.sid)
    # retrieve_first_round()  # load first round info
    # asyncio.run(retrieve_first_round())

    return render_template("mike/intro.html")

@app.route("/overview", methods=["GET", "POST"])
@login_required
def overview():
    return render_template("mike/overview.html")

@app.route("/sandbox_introduction", methods=["GET", "POST"])
@login_required
def sandbox_introduction():
    return render_template("mike/sandbox_introduction.html")

@socketio.on('make sandbox')
def make_sandbox(data):
    version = data['version']
    
    if version == 1:
        current_user.set_curr_progress("sandbox_1")
    elif version == 2:
        current_user.set_curr_progress("sandbox_2")

    flag_modified(current_user, "curr_progress")
    update_database(current_user, str(current_user.username) + ". User progress sandbox")

    log_print("current user progress is: " + current_user.curr_progress)
    log_print(request.sid)
    socketio.emit('made sandbox', to=request.sid)


@socketio.on("connect")
def handle_connect(auth=None):
    """Handles user reconnection and removes them from disconnected_users if needed"""
    status_print('User: ', current_user.id, ' connected....')

    if current_user.is_authenticated:
        log_print(f"User {current_user.id} connected with SID {request.sid}")
        user_id = current_user.id

        # check and reroute to logout if they have already completed the study previously or left the study
        if current_user.study_completed:
            # return redirect(url_for('logout_confirmation', reason='complete'))
            return jsonify({'url': url_for('logout_confirmation'), 'reason': 'complete'})  # Send redirect URL to frontend

        
        elif current_user.curr_progress == "left_study_or_got_disconnected" or current_user.curr_progress == "removed_due_to_inactivity":
            # socketio.emit("force_logout", {"reason": 'inactivity'}, to=request.sid)
            # return redirect(url_for('logout_confirmation', reason='inactivity'))
            return jsonify({'url': url_for('logout_confirmation'), 'reason': 'inactivity'})  # Send redirect URL to frontend


        # reconnect user
        reconnect_time = datetime.now().strftime("%m-%d %H:%M:%S")
        # reconnect_page = request.referrer
        referrer = auth.get("referrer") if auth else "Unknown"
        reconnect_page = referrer
        reconnect_page = reconnect_page.replace("https://bridge.apt.ri.cmu.edu/flask_closed_loop_teaching/", "")

        with disconnected_users_lock:
            if user_id in disconnected_users:
                disconnected_users[user_id]["reconnect_times"].append(reconnect_time)
                disconnected_users[user_id]["reconnect_pages"].append(reconnect_page)
                status_print(f"User {user_id}: Reconnected at {reconnect_time} , from: {reconnect_page}")


                # Cancel the active timer if it exists
                if user_id in disconnect_timers:
                    disconnect_timers[user_id].cancel()
                    del disconnect_timers[user_id]  # Remove from dictionary
                    log_print(f"User {user_id}: Timer canceled due to reconnection.")

                # # Remove only if user has fully reconnected for every disconnect
                # if len(disconnected_users[user_id]["disconnect_times"]) == len(disconnected_users[user_id]["reconnect_times"]):
                #     disconnected_users.pop(user_id, None)
                #     log_print(f"User {user_id} fully reconnected and removed from tracking.")

        # Ensure they rejoin their correct room
        if current_user.group:
            print('User:', current_user.id, 'Joining room on connect:', 'room_'+ str(current_user.group))
            join_room(f"room_{current_user.group}")



@socketio.on("disconnect")
def handle_disconnect():
    """Handles user disconnection and starts a timer to check reconnection"""
    
    if current_user.is_authenticated:
        user_id = current_user.id
        user_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()

        if user_group is not None:
            user_status = user_group.members_statuses[current_user.group_code]
            
        if (user_group is None or user_status != "left"):
            status_print(f"User id: {current_user.id}, {request.sid} disconnected.")

            user_id = current_user.id
            disconnect_time = datetime.now().strftime("%m-%d %H:%M:%S")
            # disconnect_page = request.referrer  # for polling transport
            disconnect_page = last_disconnect_pages.pop(user_id, "Unknown")
            disconnect_page = disconnect_page.replace("https://bridge.apt.ri.cmu.edu/flask_closed_loop_teaching/", "")


            with disconnected_users_lock:

                # Initialize tracking if not exists
                if user_id not in disconnected_users:
                    disconnected_users[user_id] = {
                        "disconnect_times": [],
                        "reconnect_times": [],
                        "disconnect_pages": [],
                        "reconnect_pages": []
                    }

                # Track disconnect time
                disconnected_users[user_id]["disconnect_times"].append(disconnect_time)
                disconnected_users[user_id]["disconnect_pages"].append(disconnect_page)
                status_print(f"User {user_id}: Disconnected at {disconnect_time} , from: {disconnect_page}")

            # cancel the existing timer
            if user_id in disconnect_timers:
                disconnect_timers[user_id].cancel()
                del disconnect_timers[user_id]
                status_print(f"User {user_id}: Existing disconnect timer canceled before setting a new one.")


            # Start a new thread-based timer (non-blocking)
            timer = threading.Timer(RECONNECT_TIMEOUT, check_reconnection, [user_id])
            timer.start()
            disconnect_timers[user_id] = timer  # Save the timer reference
        else:
            status_print(f"User id: {current_user.id}, {request.sid} disconnected but has already left the study.")


@socketio.on('last_disconnect_page')
def store_disconnect_page(data):
    if current_user.is_authenticated:
        user_id = current_user.id
        last_disconnect_pages[user_id] = data.get("referrer", "Unknown")
        # print('Disconnect pages list:', last_disconnect_pages[user_id])


def check_current_user_in_group():
    if current_user.is_authenticated:
    
        user_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()

        if user_group is not None:
            user_status = user_group.members_statuses[current_user.group_code]

        if (user_status != "left"):
            return True
        
    return False
        

        


@socketio.on('heartbeat')
def handle_heartbeat(data):
    # Log if needed
    log_print(f"Current User: {current_user.id}, Received heartbeat from {request.sid}")
    # You can respond if you want
    socketio.emit('heartbeat_response', {'server_time': time.time()}, to=request.sid)


def check_reconnection(user_id):
    """Checks if user is still disconnected after timeout"""
    
    # ## Based on the number of disconnect-reconnect. Sometimes, the reconnect is not being recorded, but still reconnects.
    # # Ensure the user is still in disconnected_users after timeout
    # if user_id in disconnected_users:
    #     disconnect_count = len(disconnected_users[user_id]["disconnect_times"])
    #     reconnect_count = len(disconnected_users[user_id]["reconnect_times"])

    #     if disconnect_count > reconnect_count:  # Still missing reconnects
    #         status_print(f"User {user_id}: Did not fully reconnect within {RECONNECT_TIMEOUT} seconds. Removing...")

    #         removed_user = db.session.query(User).get(user_id)
    #         if removed_user and (removed_user.curr_progress != "left_study_or_got_disconnected" and removed_user.curr_progress != "removed_due_to_inactivity" and removed_user.study_completed != 1):
    #             with app.app_context():  # Ensure Flask context for DB operations
    #                 removed_user.set_curr_progress("left_study_or_got_disconnected")
    #                 flag_modified(removed_user, "curr_progress")
    #                 update_database(removed_user, f"User left study or got disconnected")
    #                 remove_from_study(user_id)
           
    #         status_print(f"User {user_id} permanently removed from tracking due to timeout.")
    # else:
    #     status_print(f"User {user_id}: Already reconnected or removed from tracking.")

    ## Based on disconnection and reconnection times
    with disconnected_users_lock:
        # status_print('Disconnected_users:', disconnected_users)

        if user_id in disconnected_users:
            disconnect_times = disconnected_users[user_id]["disconnect_times"]

            last_disconnect = datetime.strptime(f"{datetime.now().year}-{disconnect_times[-1]}", "%Y-%m-%d %H:%M:%S") if disconnect_times else None
            current_time = datetime.now()

            status_print('Last disconnect:', last_disconnect, 'current_time:', current_time)

            if last_disconnect:
                time_since_disconnect = (current_time - last_disconnect).total_seconds()
                status_print('User:', user_id, 'Time since disconnect:', time_since_disconnect)

                # Check if user failed to reconnect within RECONNECT_TIMEOUT
                if time_since_disconnect >= RECONNECT_TIMEOUT:
                    status_print(f"User {user_id}: Did not reconnect within timeout. Removing...")

                    with app.app_context():
                        removed_user = db.session.query(User).get(user_id)
                        if removed_user and (removed_user.curr_progress not in ["left_study_or_got_disconnected", "removed_due_to_inactivity"] and removed_user.study_completed != 1):
                            removed_user.set_curr_progress("left_study_or_got_disconnected")
                            flag_modified(removed_user, "curr_progress")
                            update_database(removed_user, "User left study or got disconnected")
                            remove_from_study(user_id)

                    status_print(f"User {user_id} removed from tracking.")
                else:
                    status_print(f"User {user_id}: Reconnected in time, no action taken.")
            else:
                status_print(f"User {user_id}: No disconnect times found.")
        else:
            status_print(f"User {user_id}: Already reconnected or removed.")



@socketio.on("force_remove_user")
def handle_remove_user(data):
    """Runs on the main thread to log out the user safely"""
    user_id = data["user_id"]

    if user_id in disconnected_users:
        
        # Logout the user properly
        user = db.session.query(User).get(user_id)
        
        if user:
            status_print(f"User {user_id} removed from study.")
            
            # session.clear()  # Clears all session variables
            logout_user()  # Logs out the user

        # Remove user tracking data
        disconnected_users.pop(user_id, None)

        


@socketio.on("disconnect_user")
def disconnect_user(data):
    status_print("User disconnecting due to inactivity....")
    group_print(current_user.group, 'User: ', current_user.id, 'disconnecting due to inactivity.')

    # If user is still connected and authenticated, log them out
    if current_user.is_authenticated:
        # if current_user.last_activity is not None:
            # last_activity_time_seconds = float(data["last_activity_time"])/1000
            # current_user.last_activity.append(data["last_activity"])
            # current_user.last_activity_time.append(datetime.fromtimestamp(last_activity_time_seconds))

        try:
            current_user.last_activity = data["activity_log"]
        except:
            current_user.last_activity = ""


        current_user.set_curr_progress("removed_due_to_inactivity")
        
        flag_modified(current_user, "last_activity")
        flag_modified(current_user, "last_activity_time")
        flag_modified(current_user, "curr_progress")
        update_database(current_user, str(current_user.username) + ". User logged out due to inactivity")
        user_id = current_user.id
        remove_from_study(user_id)


    # Notify the client to redirect
    socketio.emit("force_logout", {"reason": 'inactivity'}, to=request.sid)


@socketio.on("logout_request")
def logout_handler():
    """
    Logs out the user and redirects to the logout confirmation page with a reason.
    """

    reason = "complete"

    # Update progress
    current_user.set_curr_progress("study_completed")
    flag_modified(current_user, "curr_progress")
    update_database(current_user, f"{current_user.username}. User progress study completed")

    status_print(f'Logging out user {current_user.id} as they completed the study. Reason: {reason}')

    # Logout user
    logout_user()

    # Emit logout response to the client
    socketio.emit("logout_response", {'reason': 'complete'}, to=request.sid)



@app.route('/logout_confirmation')
def logout_confirmation():
    return render_template('logout_confirmation.html')  # Render confirmation page



@socketio.on("sandbox settings")
def sandbox_settings(data):
    version = data["version"]
    if version == 1:
        sb_params = {
            'agent': {'x': 4, 'y': 3, 'has_passenger': 0},
            'walls': [{'x': 2, 'y': 3}, {'x': 2, 'y': 2}, {'x': 3, 'y': 2}, {'x': 4, 'y': 2}],
            'passengers': [{'x': 4, 'y': 1, 'dest_x': 1, 'dest_y': 4, 'in_taxi': 0}],
            'hotswap_station': [{'x': 1, 'y': 2}],
            'width': 4,
            'height': 4,
        }
        continue_condition = "free_play"
    elif version == 2:
        sb_params = {
            'agent': {'x': 4, 'y': 1, 'has_passenger': 0},
            'walls': [{'x': 1, 'y': 3}, {'x': 2, 'y': 3}, {'x': 3, 'y': 3}],
            'passengers': [{'x': 1, 'y': 2, 'dest_x': 1, 'dest_y': 4, 'in_taxi': 0}],
            'hotswap_station': [{'x': 2, 'y': 1}],
            'width': 4,
            'height': 4,
        }
        continue_condition = "optimal_traj_1"
    socketio.emit("sandbox configured", {"params": sb_params, "continue_condition": continue_condition}, to=request.sid)


@app.route("/sandbox", methods=["GET", "POST"])
@login_required
def sandbox():
    version = current_user.curr_progress
    
    if version != "sandbox_1" and version != "sandbox_2":
        version = "sandbox_1"  # default to sandbox_2 if not set (in case they randomly land on this page)
    
    
    log_print("current user progress is: " + version)
    if version == "sandbox_1":
        preamble = ("<h1>Free play</h1> <hr/> " + "<h4>A subset of the keys in the table below will be available to control Chip in each game.<br>All game instances that you decide how Chip behaves in will be marked with a <font color='blue'>blue border</font>, like below.</h4><br>" +
        "<h4>Feel free to play around in the game below and get used to the controls.</h4>" +
        "<h4>If you accidentally take a wrong action, you may reset the simulation and start over by pressing 'r'.</h4><br>" +
        "<h4>You can click the continue button whenever you feel ready to move on.</h4><br>" +
        "<h5> As a reminder this game consists of a <b>location</b> (e.g. <img src = 'static/img/star.png' width=\"20\" height=auto />), <b>an object that you can grab and drop</b> (e.g. <img src = 'static/img/pentagon.png' width=\"20\" height=auto />), <b>an object that you can absorb by moving through</b> (e.g. <img src = 'static/img/diamond.png' width=\"20\" height=auto />), and <b>walls </b>that you can't move through (<img src = 'static/img/wall.png' width=\"20\" height=auto />).</h5>")
      
        legend = ""

    elif version == "sandbox_2":
        preamble = ("<h1>Practice game</h1> <hr/> " +
        "<h4>As previously mentioned, the task in this practice game is the following: </h4> <br>" +
        "<table class=\"center\"><tr><th>Task</th><th>Sample sequence</th></tr><tr><td>Dropping off the green pentagon at the purple star</td><td><img src = 'static/img/sandbox_dropoff1.png' width=\"75\" height=auto /><img src = 'static/img/arrow.png' width=\"30\" height=auto /><img src = 'static/img/sandbox_dropoff2.png' width=\"75\" height=auto /></td></tr></table> <br>" +
        "<h4>Each game will consist of <b>actions that change your energy level</b> differently. In this game, the following actions affect your energy:</h4> <br>" +
        "<table class=\"center\"><tr><th>Action</th><th>Sample sequence</th><th>Energy change</th></tr>" +
        "<tr><td>Moving through the orange diamond</td><td><img src = 'static/img/sandbox_diamond1.png' width=\"225\" height=auto /><img src = 'static/img/arrow.png' width=\"30\" height=auto /><img src = 'static/img/sandbox_diamond2.png' width=\"225\" height=auto /> <img src='static/img/arrow.png' width=\"30\" height=auto /><img src ='static/img/sandbox_diamond3.png' width=\"225\" height=auto/> <td><h3><b>+ 3%</b></h3></td></tr>" +
        "<tr><td>Any action that you take (e.g. moving right)</td><td><img src = 'static/img/right1.png' width=\"150\" height=auto /><img src = 'static/img/arrow.png' width=\"30\" height=auto /><img src = 'static/img/right2.png' width=\"150\" height=auto /><td><h3><b>- 1%</b></h3></td></tr></table> <br>" +
        "<h4><b>Grab the green pentagon</b> and <b>drop it off at the purple star</b> with the <b>maximum possible energy remaining</b>. </h4> " +
        "<h5>You should end with 89% energy left (you won't be able to move if energy falls to 0%, but you can reset by pressing 'r'). <u>You will need to successfully complete this practice game to continue on with the study!</u></h5>" +
        "<h5>Note: Since this is practice, we have revealed each actions's effect on Chip's energy and also provide a running counter of Chip's current energy level below.</h5> <br>")
        legend = "<br><br><br><table class=\"center\"><tr><th>Key</th><th>Action</th></tr><tr><td>up/down/left/right arrow keys</td><td>corresponding movement</td></tr><tr><td>p</td><td>pick up</td></tr><tr><td>d</td><td>drop</td></tr><tr><td>r</td><td>reset simulation</td></tr></table><br>"


    res = render_template("mike/sandbox.html", preamble=preamble, legend=legend)
    # log_print(res)
    return res

@socketio.on("attention check")
def attention_check(data):
    if data["passed"]:
        socketio.emit("attention checked", {"passed": True}, to=request.sid)
        current_user.set_attention_check(1)

        flag_modified(current_user, "attention_check")
        update_database(current_user, str(current_user.username) + ". User attention check")


@app.route("/post_practice", methods=["GET", "POST"])
@login_required
def post_practice():
    current_user.set_curr_progress("post practice")
    current_user.last_iter_in_round = True

    flag_modified(current_user, "curr_progress")
    flag_modified(current_user, "last_iter_in_round")

    update_database(current_user, str(current_user.username) + ". User progress post practice")

    preamble = ("<br><br><p>Good job on completing the practice game! <b>Read these instructions carefully!</b> Let's now head over to the <b>two main games</b> and <b>begin the real study</b>.</p><br>" +
            "<p>In these games, you will <b>not</b> be told how each action changes Chip's energy level.</p><br>" +
            "For example, note the '???' in the Energy Change column below. <table class=\"center\"><tr><th>Action</th><th>Sample sequence</th><th>Energy change</th></tr><tr><td>Any action that you take (e.g. moving right)</td><td><img src = 'static/img/right1.png' width=\"150\" height=auto /><img src = 'static/img/arrow.png' width=\"30\" height=auto /><img src = 'static/img/right2.png' width=\"150\" height=auto /><td>???</td></tr></table> <br>" +
            "<p>Instead, you will have to <u>figure that out</u> and subsequently the best strategy for completing the task while minimizing Chip's energy loss <u>by observing Chip's demonstrations, given as different lessons!</u></p><br>" +
            "<p>In between demonstrations/lessons, Chip may test your understanding by asking you to predict the best strategy and giving you corrective feedback to help you learn!</p><br>" +
            "<p>Finally, <u>you may navigate back to previous interactions</u> (e.g. demonstrations) to refresh your memory <u>when you're not being tested!</u></p>" + 
            "<p> <b> Remember, you are part of a group </b> and will be learning the same lessons as the group members. This means <b> you may have to wait for all your members to complete a lesson </b> before moving onto the next lesson. </p><br>" +
            "<p> If any member of your group has not learned the lesson, the entire group could repeat it. This will continue either until everyone in the group learns the lesson or until a set number of times the lesson is repeated, after which the group will move on to the next lesson. There are totally three lessons for each game. </p><br>" +
            "<p> You will need to successfully complete both games to finish the study</u> and receive your compensation!</p><br>" +
            "<p> You can track your teammate's proress during each game and even if any of your teammates have left the study, you should continue with the study until you have finished it to earn the full compensation. </p><br>" +
            "<p>Click the Next button when you're ready to start the study!</p>"
        )
    
    return render_template("mike/post_practice.html", preamble=preamble)

@app.route("/waiting_room", methods=["GET", "POST"])
@login_required
def waiting_room():
    preamble = ("<h3>Please wait while we find more group members for you!</h3")

    return render_template("mike/waiting_room.html", preamble=preamble)

@socketio.on("join group")
def join_group():
    """
    handles adding members to groups. executed upon client-side call to "join 
    group" in mike/augmented_taxi2_introduction.html. emits the status of the 
    group (1 member, 2 members, 3 members) back to all group members, received
    in the same at_intro file, endpoint named "group joined".

    data in: none
    data emitted: num_members
    side effects: alters Groups database with added member in appropriate row   
    """ 
    
    # cond_list = ["individual_belief_low", "common_belief", "individual_belief_high", "joint_belief"]
    # domain_list = [["at", "sb"], ["sb", "at"]]

    cond_list = ["common_belief"]
    domain_list = [["sb", "at"]]

    if QUICK_DEBUG_FLAG:
        domain_list = [["sb", "at"]]

    
    # cond_list = ["individual_belief_low"]
    # domain_list = [["at", "sb"]]

    
    # get last entry in groups table
    # the initial entry is an empty list as initialized in app/__init__.py
    open_group = db.session.query(Group).filter_by(status="study_not_start").order_by(Group.id.desc()).first()

    num_active_members = 0
    params = get_mdp_parameters("")
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Updated params:', params)
    

    # Counterbalance experimental conditions
    condition_index = db.session.query(Group).count() % len(cond_list)
    domain_index = db.session.query(Group).count() % len(domain_list)

    if not current_user.group: # if no group yet, join one

        log_print('Group:', current_user.group, 'User:', current_user.id, 'Join group function. Current user group: ', current_user.group)
        
        if open_group is not None:
            num_active_members = open_group.num_active_members
            status_print('Group:', current_user.group, 'User:', current_user.id, 'Old group Group id:', open_group.id, 'num_active_members:', num_active_members, 'Group members:', open_group.members, 'Group mem ids:', open_group.member_user_ids, 'Group status:', open_group.members_statuses, 'Joined timestamps:', open_group.join_timestamps, 'Group experimental condition:', open_group.experimental_condition)

            # Check if any existing members joined more than 30 minutes ago
            current_time = datetime.now()
            create_new_group = False

            log_print('New group flag initialized to false...')

            for timestamp_str in open_group.join_timestamps:
                log_print('Timestamp: ', timestamp_str)
                if timestamp_str is not None:
                    # Parse the timestamp string back to datetime
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%y-%m-%d-%H-%M-%S")
                        time_diff = current_time - timestamp
                        log_print('Timediff: ', time_diff)
                        if time_diff.total_seconds() > GROUP_JOIN_THRESHOLD:  # 30 minutes = 1800 seconds
                            create_new_group = True
                            break
                    except (ValueError, TypeError):
                        break
        else:
            create_new_group = True
                

        
        if create_new_group or num_active_members == 0 or num_active_members == params['team_size']: # if group is full or empty, create a new group
            status_print('Group:', current_user.group, 'User:', current_user.id, 'No group yet.. Creating one...')
            new_group_entry = Group(
                experimental_condition=cond_list[condition_index],
                domain_1=domain_list[domain_index][0],
                domain_2=domain_list[domain_index][1],
                status = "study_not_start",
                member_user_ids = [None for i in range(params['team_size'])],
                members = [None for i in range(params['team_size'])],
                members_statuses = ["not joined" for i in range(params['team_size'])],
                num_active_members = 0,
                num_members = params['team_size'],
                members_EOR = [False for i in range(params['team_size'])],
                members_last_test = [False for i in range(params['team_size'])],
                join_timestamps = [None for i in range(params['team_size'])],  # Add timestamps array
                )

            db.session.add(new_group_entry)
            db.session.commit()
                        
            new_group = db.session.query(Group).order_by(Group.id.desc()).first()
            current_user.group = new_group.id

            current_time = datetime.now()
            new_group.join_timestamps[0] = current_time.strftime("%y-%m-%d-%H-%M-%S")


            _, current_user.group_code, current_user.domain_1, current_user.domain_2 = new_group.groups_push(current_user.username, current_user.id)
            flag_modified(new_group, "members")
            flag_modified(new_group, "member_user_ids")
            flag_modified(new_group, "members_statuses")
            flag_modified(new_group, "num_active_members")
            flag_modified(new_group, "join_timestamps")
            group_print(current_user.group, 'User:', current_user.id, 'New group:', 'Group id:', new_group.id, 'Group members:', new_group.members, 'Active members:', new_group.num_active_members, 'Group mem ids:', new_group.member_user_ids, 'Group status:', new_group.members_statuses, 'Group experimental condition:', new_group.experimental_condition)
            group_print(current_user.group, 'User:', current_user.id, 'Current user:', current_user.username, 'Current user group:', current_user.group, 'Current user group code:', current_user.group_code, 'Current user domain 1:', current_user.domain_1, 'Current user domain 2:', current_user.domain_2)
            num_active_members = 1

            update_database(new_group, 'Member to new group')
            
        else:
            log_print('Group:', current_user.group, 'User:', current_user.id, 'Group timestamps:', open_group.join_timestamps, 'Adding to existing group')
            _, current_user.group_code, current_user.domain_1, current_user.domain_2 = open_group.groups_push(current_user.username, current_user.id)
            
            # log_print('Updated group data...')
            group_print(current_user.group, 'member_user_ids:', open_group.member_user_ids, 'timestamps:', open_group.join_timestamps, 'Adding to existing group')


            current_time = datetime.now()            
            open_group.join_timestamps[current_user.group_code] = current_time.strftime("%y-%m-%d-%H-%M-%S")

            # status_print('Timestamps added....')
            
            flag_modified(open_group, "members")
            flag_modified(open_group, "member_user_ids")
            flag_modified(open_group, "members_statuses")
            flag_modified(open_group, "num_active_members")
            flag_modified(open_group, "join_timestamps")

            current_user.group = open_group.id
            num_active_members += 1
            status_print('Group:', current_user.group, 'User:', current_user.id, 'Group id:', open_group.id, 'Group members:', open_group.members, 'Group mem ids:', open_group.member_user_ids, 'Group status:', open_group.members_statuses, 'Group experimental condition:', open_group.experimental_condition)
            status_print('Group:', current_user.group, 'User:', current_user.id, 'Current user:', current_user.username, 'Current user group:', current_user.group, 'Current user group code:', current_user.group_code, 'Current user domain 1:', current_user.domain_1, 'Current user domain 2:', current_user.domain_2)

            update_database(open_group, 'Member to existing group')
    

        log_print('Group:', current_user.group, 'User:', current_user.id, 'Current user: ' + str(current_user.username) + 'Current user group: ' + str(current_user.group))
        

        # make sure that when people leave and rejoin they check the time elapsed and 
        # if it's not too long, then put them back in a group
        # they shouldn't be able to go back once they're in the waiting room

        # test 
        all_groups = db.session.query(Group).all()
        log_print([[g.id, g.members] for g in all_groups])

        log_print('Group:', current_user.group, 'User:', current_user.id, 'Room:', 'room_'+ str(current_user.group))
        log_print('Rooms for current user:', rooms())  # This will show the rooms the user is part of
        join_room('room_'+ str(current_user.group))

        # if room is None then it gets sent to everyone
        log_print('Group:', current_user.group, 'User:', current_user.id, 'Rooms for current user:', rooms())  # This will show the rooms the user is part of
        socketio.emit("group joined", {"num_members":num_active_members, "max_num_members": params['team_size'], "room_name": 'room_'+ str(current_user.group)}, to='room_'+ str(current_user.group))
        




# def rejoin_group():

#     # check if current user has a group
#     log_print('Rejoining group.... User:', current_user.id, 'Current user:', current_user.username, 'Current user group:', current_user.group)

#     if current_user.group is not None:
#         # get the group
#         group_to_rejoin = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()

#         log_print('Group:', current_user.group, 'User:', current_user.id, 'Group to rejoin:', 'Group id:', group_to_rejoin.id, 'Group members:', group_to_rejoin.members, 'Group mem ids:', group_to_rejoin.member_user_ids, 'Group status:', group_to_rejoin.members_statuses, 'Group experimental condition:', group_to_rejoin.experimental_condition)
        
#         user_status = group_to_rejoin.members_statuses[current_user.group_code]

#         # check if current user is in the group
#         if user_status != 'joined':
            
#             # add the user to the group
#             _, current_user.group_code, current_user.domain_1, current_user.domain_2 = group_to_rejoin.groups_push_again(current_user.username, current_user.id)
#             flag_modified(group_to_rejoin, "members_statuses")
#             flag_modified(group_to_rejoin, "num_active_members")
#             # update the database
#             update_database(group_to_rejoin, 'Member rejoined group')
#             # join the room
#             join_room('room_'+ str(current_user.group))
#             log_print('Rooms for current user:', rooms())  # This will show the rooms the user is part of

#             # emit the group joined signal
#             socketio.emit("group joined", {"num_members":group_to_rejoin.num_active_members, "max_num_members": group_to_rejoin.num_members, "room_name": 'room_'+ str(current_user.group)}, to='room_'+ str(current_user.group))
        
#     return True



# @socketio.on("leave group")
def remove_from_study(user_id):
    
    """
    handles leaving groups. executed upon client-side call to "leave 
    group" in mike/augmented_taxi2_introduction.html or mike/augmented_taxi2.html.
    emits the code for the group member which dropped, back to the other two 
    group members, at endpoint "member left".

    data in: none
    data emitted: member_code  
    """ 

    user = db.session.query(User).get(user_id)

    if user.group is not None:
        
        db.session.refresh(user)
        
        # Use group-specific lock since we're only modifying this group's data
        with group_database_transaction(user.group, 'Removing user from group'):
                
            current_group = db.session.query(Group).filter_by(id=user.group).order_by(Group.id.desc()).first()
    
            # group_print(user.group, 'User:', user.id, 'Before leaving study:', 'Group id:', current_group.id, 'Group members:', current_group.members, 'Group mem ids:', current_group.member_user_ids, 'Group status:', current_group.members_statuses, 'Group experimental condition:', current_group.experimental_condition)
    
            _ = current_group.groups_remove(user.username)
            
            flag_modified(current_group, "members_statuses")
            flag_modified(current_group, "num_active_members")
            flag_modified(current_group, "members")
        
            # Don't call update_database() - let the context manager handle commit
            # update_database(current_group, 'Member left group and study')
        
        log_print('Group:', user.group, 'User:', user.id, 'Group db lock released...')
        
        group_print(user.group, 'User:', user.id, 'After leaving group:', 'Group id:', current_group.id, 'Group members:', current_group.members, 'Group mem ids:', current_group.member_user_ids, 'Group status:', current_group.members_statuses, 'Group experimental condition:', current_group.experimental_condition)
        log_print('Sending signal to members in group:', 'room_'+ str(user.group))
        
        db.session.refresh(current_group)
        group_EOR_status = current_group.groups_all_EOR()
        group_print(user.group, 'EOR status: ', group_EOR_status)

        socketio.emit("member left", {"member code": user.group_code}, to='room_'+ str(user.group))
        socketio.emit("force_remove_user", {"user_id": user_id})



def refresh_group_and_check_active_members(group_id):
    """
    Refresh group data and return updated group object and active member count
    """
    current_group = db.session.query(Group).filter_by(id=group_id).first()
    if current_group:
        # Force refresh from database to get latest status changes
        db.session.refresh(current_group)
        db.session.expunge(current_group)
        current_group = db.session.query(Group).filter_by(id=group_id).first()
        
        active_count = sum(1 for status in current_group.members_statuses if status == 'joined')
        return current_group, active_count
    return None, 0



@socketio.on("next domain")
def next_domain(data):

    ''' To handle domain transitions on the client side. '''
    
    # save remaining data from 
    if len(data["user input"]) !=0:
        domain, _, _ = get_domain()
        add_trial_data(domain, data)

    # add survey data
    if (current_user.curr_progress == "domain_1" or current_user.curr_progress == "domain_2") :
        domain, _, _ = get_domain()
        log_print(colored('Adding survey data...', 'red'))
        add_survey_data(domain, data)

    log_print("current_user.curr_progress", current_user.curr_progress)

    if current_user.curr_progress == "post practice":
        socketio.emit("next domain is", {"domain": current_user.domain_1}, to=request.sid)
    elif current_user.curr_progress == "domain_1":
        socketio.emit("next domain is", {"domain": current_user.domain_2}, to=request.sid)
    elif current_user.curr_progress == "domain_2":
        socketio.emit("next domain is", {"domain": "final survey"}, to=request.sid)



@app.route("/at_intro", methods=["GET", "POST"])
@login_required
def at_intro():
    return render_template("mike/augmented_taxi2_introduction.html")

@app.route("/at", methods=["GET", "POST"])
@login_required
def at():
    return render_template("mike/augmented_taxi2.html")

@app.route("/sb_intro", methods=["GET", "POST"])
@login_required
def sb_intro():
    return render_template("mike/skateboard2_introduction.html")

@app.route("/sb", methods=["GET", "POST"])
@login_required
def sb():
    return render_template("mike/skateboard2.html")


# Check member status
def check_member_and_group_status():
    '''Checks if all members in a group have completed a domain'''
    
    db.session.refresh(current_user)
    group_id = current_user.group
    
    with group_database_transaction(group_id, 'Checking member and group status'):
        current_group = db.session.query(Group).filter_by(id=group_id).order_by(Group.id.desc()).first()
        all_group_members = db.session.query(User).filter_by(group=group_id).all()
    
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Checking member and group status. Group id:', group_id, 'Group progress:', current_group.curr_progress, 'Current user progress:', current_user.curr_progress, 'Group members:', current_group.members)
    
    for member in all_group_members:
        log_print('Group:', current_user.group, 'User:', current_user.id, 'Member id:', member.id, 'Member group:', member.group, 'Member curr progress:', member.curr_progress, 'Group progress:', current_group.curr_progress)
        if 'domain' in member.curr_progress and member.curr_progress != current_group.curr_progress:
            return False

    return True



def is_user_active():
    """ 
    Check if the user is actively still part of the group and has not completed the study or left the study
    """
    
    if current_user.curr_progress == "left_study_or_got_disconnected" or current_user.curr_progress == "removed_due_to_inactivity":
        log_print('Group:', current_user.group, 'User:', current_user.id, '. User not active....')
        socketio.emit("force_logout", {"reason": 'inactivity'}, to=request.sid)
        return False

    elif current_user.curr_progress == "study_completed":
        log_print('Group:', current_user.group, 'User:', current_user.id, '. User completed study....')
        socketio.emit("force_logout", {"reason": 'study_completed'}, to=request.sid)
        return False
    
    elif current_user.study_type == 'in_loop':
        log_print('Group:', current_user.group, 'User:', current_user.id, '. User stuck in loop....')
        return False
    
    else:
        return True
        


def setup_user_context(data):
    
    current_kc_id = -2  # default value
    
    room_name = data["room_name"]        
    domain, domain_order, mdp_class = get_domain()
    params = get_mdp_parameters(mdp_class)

    log_print('Group:', current_user.group, 'User:', current_user.id, 'Group:', current_user.group, 'Room name:', room_name, 'domain:', domain, 'mdp class:', mdp_class, 'Updated params:', params)


    # get current group and round data
    with group_database_transaction(current_user.group, 'Setting up user context'):
        current_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()
        current_round = db.session.query(Round).filter_by(group_id=current_user.group, domain_progress=current_user.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()
    
    log_print('Group:', current_user.group, 'User:', current_user.id, 'current_user progress: ', current_user.curr_progress, 'current_group progress: ', current_group.curr_progress, 'Round_num:', current_user.round, 'current_round:', current_round, current_user.iteration, current_user.interaction_type)
    

    ## Get round details
    if current_round is not None:
        current_mdp_params = current_round.round_info[current_user.iteration - 1]
        current_user.interaction_type = current_mdp_params["interaction type"]
        current_kc_id = current_round.kc_id
    
    return room_name, domain, domain_order, mdp_class, params, current_group, current_round, current_kc_id
   
    

def process_activity_and_trial_data(data, domain):
    """
    Updates current_user's activity log and trial data if 'movement' is 'next'.
    Returns: (opt_response_flag: bool, curr_already_completed: bool)
    """
    # Save activity log
    try:
        current_user.last_activity = data.get("activity_log", "")
    except Exception:
        log_print('Group:', current_user.group, 'User:', current_user.id, 'No user activity available to log.')
        current_user.last_activity = ""

    flag_modified(current_user, "last_activity")
    update_database(current_user, "Current user last activity")
    db.session.refresh(current_user)

    opt_response_flag = False
    curr_already_completed = False

    
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Next movement. Checking if current trial was already completed..')

    # check if current iteration has been already completed and add/update trial data
    current_trial = db.session.query(Trial).filter_by(user_id=current_user.id,
                                                        domain=domain,
                                                        round=current_user.round,
                                                        iteration=current_user.iteration).order_by(Trial.id.desc()).first()  

    survey_valid = int(data.get("survey", -1)) != -1
    interaction_type = data.get("interaction type")

    log_print('Group:', current_user.group, 'User:', current_user.id, 'Current trial:', current_trial, 'Current user iteration:', current_user.iteration, 'Current user round:', current_user.round, 'Interaction type:', interaction_type, 'Survey valid:', survey_valid)

    # if (current_trial is None and data["movement"] == "prev"):
    #     # do nothing
    #     pass

    if current_user.interaction_type == "survey":
        log_print(colored("Adding survey data...", "red"))
        add_survey_data(domain, data)

    elif ((current_trial is None and current_user.round != 0 and interaction_type and survey_valid)
        or (current_trial is not None and survey_valid)):
        if 'test' in current_user.interaction_type and data.get("user input"):
            data["user input"]["mdp_parameters"]["human_actions"] = data["user input"]["moves"]
            opt_response_flag = data["user input"].get("opt_response", False)

        add_trial_data(domain, data)

    elif (current_trial is None and current_user.round != 0 and interaction_type == "final test"):
        if data.get("user input"):
            data["user input"]["mdp_parameters"]["human_actions"] = data["user input"]["moves"]
            opt_response_flag = data["user input"].get("opt_response", False)

        add_trial_data(domain, data)

    elif current_trial is not None:
        curr_already_completed = True
        
        # Update number of visits (if page is being reloaded it could count as revisits unfortunately)
        if data.get("movement") == "next":
            current_trial.num_visits += 1
            flag_modified(current_trial, "num_visits")
            update_database(current_trial, f"Updating current trial num visits: {current_trial.num_visits}")

    return opt_response_flag, curr_already_completed



def check_and_update_domain(data, current_group):
    """
    Check if the domain needs to be updated. If so, updates group and user domain progress,
    refreshes parameters, and returns updated (domain, domain_order, mdp_class, params, current_round).
    """
    log_print('New domain? :', data.get("new_domain"))

    if not data.get("new_domain", False):
        return None, None, None, None, None  # No update needed

    log_print('Updating domain in backend and database...')
    db.session.refresh(current_group)

    # Update domain for group
    if current_user.curr_progress == current_group.curr_progress:
        group_print(current_user.group, 'User:', current_user.id, 'Updating domain of group...')
        update_domain_group(current_group)
        db.session.refresh(current_group)

    # Update domain for user if their progress has not yet been synced
    if current_user.curr_progress != current_group.curr_progress:
        group_print(current_user.group, 'User:', current_user.id, 'Updating domain of user and reset vars...')
        update_domain_user(current_user, current_group)
        db.session.refresh(current_user)

        domain, domain_order, mdp_class = get_domain()
        log_print('Group:', current_user.group, 'User:', current_user.id,
                  'Updated Domain:', domain, 'Domain order:', domain_order, 'mdp class:', mdp_class)
    else:
        domain, domain_order, mdp_class = get_domain()

    # Get study parameters
    params = get_mdp_parameters(mdp_class) if mdp_class else None
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Updated params:', params)

    # Refresh current round
    current_round = get_current_round(current_user.group, current_user.curr_progress, current_user.round)

    return domain, domain_order, mdp_class, params, current_round



def advance_or_generate_round(
    data, domain, domain_order, current_group, current_round,
    params, opt_response_flag, curr_already_completed
    ):
    """
    Handles forward movement logic:
    - Steps to the next iteration
    - Generates the next round if all members finished the current one
    - Handles EOR and updates learner models
    Returns: updated current_group, current_round, next_round, next_kc_id
    """
    next_round = None
    next_kc_id = -1

    log_print('Group:', current_user.group, 'User:', current_user.id, 'Next movement. Current trial already completed?',
              curr_already_completed, '. Current user last iter in round?', current_user.last_iter_in_round, 'opt_response_flag:', opt_response_flag)

    debug_rand_loop = random.random()

    while True:
        
        log_print('Group:', current_user.group, 'User:', current_user.id, 'Advance or generate round...', 'Debug rand loop:', debug_rand_loop)

        current_user.study_type = 'in_loop'
        
        with group_database_transaction(current_user.group, 'Refreshing group and checking active members in advance_or_generate_round'):
            current_group, _ = refresh_group_and_check_active_members(current_user.group)

        # # presence of next roundis not checked
        # should_generate_new_round = (
        #     not curr_already_completed and 
        #         (current_user.last_iter_in_round or (current_user.last_test_in_round and opt_response_flag and current_user.interaction_type != "final test")) and 
        #         (check_member_and_group_status() or (domain_order == '1' and current_user.round == 0))
        # )
        
        next_round = get_current_round(current_user.group, current_user.curr_progress, current_user.round + 1)
        
        # should_generate_new_round = (
        #     not (next_round and curr_already_completed) and
        #         (current_user.last_iter_in_round or (current_user.last_test_in_round and opt_response_flag and current_user.interaction_type != "final test")) and 
        #         (check_member_and_group_status() or (domain_order == '1' and current_user.round == 0))
        # )

        should_generate_new_round = (
            not (next_round) and
                (current_user.last_iter_in_round or (current_user.last_test_in_round and opt_response_flag and current_user.interaction_type != "final test")) and 
                (check_member_and_group_status() or (domain_order == '1' and current_user.round == 0))
        )


        log_print('Group:', current_user.group, 'User:', current_user.id, 'Should generate new round:', should_generate_new_round)

        if next_round is not None:
            next_kc_id = next_round.kc_id
            # socketio.emit("new lesson available", to='room_'+ str(current_user.group)) 
            socketio.emit("new lesson available", to=request.sid)
            break

        elif should_generate_new_round:
            time.sleep(random.random()*ROUND_GENERATION_WAIT_TIME/2)  # desync simultaneous generation (0-5s delay)
            print('Group:', current_user.group, 'User:', current_user.id, 'Round number:', current_user.round)
            
            if current_user.round == 0:
                next_round = _generate_first_round(current_group, params)
            else:
                next_round = _generate_subsequent_round(current_group, current_round, params)

            if next_round is not None:
                next_kc_id = next_round.kc_id
                # socketio.emit("new lesson available", to='room_'+ str(current_user.group)) 
                socketio.emit("new lesson available", to=request.sid)

            if current_user.last_test_in_round and opt_response_flag:
                current_user.last_iter_in_round = True

            break

        # Else: Step to next trial in current round if available
        elif current_round and current_user.iteration < len(current_round.round_info):
            _step_forward_in_round(data, domain, current_round, curr_already_completed, opt_response_flag)
            next_kc_id = current_round.kc_id
            break

        time.sleep(0.2*ROUND_GENERATION_WAIT_TIME + random.random()*0.2*ROUND_GENERATION_WAIT_TIME)  # Random (2-4 s) Wait before checking again
        if not check_current_user_in_group():
            break
        
    current_user.study_type = 'not_in_loop'
    
    # Safety check: If last_iter_in_round is set, update round if needed
    if current_user.last_iter_in_round:
        next_round = get_current_round(current_user.group, current_user.curr_progress, current_user.round + 1)
        if next_round:
            next_kc_id = next_round.kc_id
            current_user.round += 1
            current_user.iteration = 1
            current_user.last_iter_in_round = False
            current_user.last_test_in_round = False
            _reset_eor_flags(current_group)

    return current_group, next_kc_id


def get_current_round(group_id, curr_progress, round_num):
    return (
        db.session.query(Round)
        .filter_by(group_id=group_id, domain_progress=curr_progress, round_num=round_num)
        .order_by(Round.id.desc())
        .first()
    )

def _generate_first_round(current_group, params):
    
    debug_rand_loop = random.random()

    while True:
        start_round_generation = False
        current_user.study_type = 'in_loop'

        log_print('Group:', current_user.group, 'User:', current_user.id, 'Waiting to generate first round...', 'Debug rand loop:', debug_rand_loop)
        next_round = get_current_round(current_user.group, current_user.curr_progress, 1)
        
        if next_round is not None:
            current_user.study_type = 'not_in_loop'
            return next_round


        with group_database_transaction(current_user.group, 'Updating group status for first round generation'):
            current_group, _ = refresh_group_and_check_active_members(current_user.group)
            if (
                db.session.query(Round).filter_by(group_id=current_user.group, domain_progress=current_user.curr_progress, round_num=1).count() == 0 and
                current_group.status != "gen_demos"
            ):
                current_group.status = "gen_demos"
                flag_modified(current_group, "status")
                # update_database(current_group, 'Generating first round...')  update automatically occurs when the group lock is released
                # db.session.refresh(current_group)
                start_round_generation = True
        
        db.session.refresh(current_group)


        ## Start round generation
        if start_round_generation:

            log_print('Group:', current_user.group, 'User:', current_user.id, 'Generating first round...', 'Debug rand loop:', debug_rand_loop)

            retrieve_next_round(params, current_group)
            db.session.refresh(current_group)

            next_round = get_current_round(current_user.group, current_user.curr_progress, 1)
            if next_round and current_group.status != "Domain teaching completed":
                update_learner_models_from_demos(params, current_group, next_round)
            db.session.refresh(current_group)
            current_user.study_type = 'not_in_loop'
            return next_round

        time.sleep(0.2*ROUND_GENERATION_WAIT_TIME + random.random()*0.2*ROUND_GENERATION_WAIT_TIME)  # Random (2-4 s) Wait before checking again

        if not check_current_user_in_group():
            current_user.study_type = 'not_in_loop'
            break


def _generate_subsequent_round(current_group, current_round, params):
    
    
    with group_database_transaction(current_user.group, 'Refreshing group and checking active members in initial generate_subsequent_round'):
        current_group, _ = refresh_group_and_check_active_members(current_user.group)
        member_idx = current_group.members.index(current_user.username)
        current_group.members_EOR[member_idx] = True
        flag_modified(current_group, "members_EOR")
    
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Group db member EOR lock released...')

    db.session.refresh(current_group)

    debug_rand_loop = random.random()


    while True:
        log_print('Group:', current_user.group, 'User:', current_user.id,'Waiting to generate next round...', 'Debug rand loop:', debug_rand_loop)
        
        current_user.study_type = 'in_loop'
        start_round_generation = False
            
        with group_database_transaction(current_user.group, 'Refreshing group and checking active members in generate_subsequent_round'):
            current_group, _ = refresh_group_and_check_active_members(current_user.group)

        log_print('Group:', current_user.group, 'User:', current_user.id, 'Current group EOR statuses:', current_group.members_EOR, 
                  'groups_all_EOR():', current_group.groups_all_EOR(), 'member and group status match:', check_member_and_group_status())
        
        if current_group.groups_all_EOR() and check_member_and_group_status():
            log_print('Group:', current_user.group, 'User:', current_user.id, 'All members EOR and member and group domains match. Generating next round...')
            member_idx = current_user.group_code
            
            # Reset EOR for current user
            with group_database_transaction(current_user.group, 'Resetting EOR for current user in generate_subsequent_round'):
                current_group.members_EOR[member_idx] = False
                current_group.status = "gen_demos"
                flag_modified(current_group, "members_EOR")
                flag_modified(current_group, "status")
                # update_database(current_group, f'Resetting EOR for user {current_user.id}')
            db.session.refresh(current_group)

            # Update PF learner models from tests
            update_learner_models_from_tests(params, current_group, current_round)
            db.session.refresh(current_group)



            next_round = get_current_round(current_user.group, current_user.curr_progress, current_user.round + 1)

            # Generate new round if not already generated (for example when going to previous lesson and coming back to current lesson)
            if next_round is None:
                retrieve_next_round(params, current_group)
                db.session.refresh(current_group)

            if next_round and current_group.status != "Domain teaching completed":
                update_learner_models_from_demos(params, current_group, next_round)

            current_user.study_type = 'not_in_loop'
            return next_round
        else:
            next_round = get_current_round(current_user.group, current_user.curr_progress, current_user.round + 1)
            if next_round is not None:
                current_user.study_type = 'not_in_loop'
                return next_round

        time.sleep(0.2*ROUND_GENERATION_WAIT_TIME + random.random()*0.2*ROUND_GENERATION_WAIT_TIME)  # Random (2-4 s) Wait before checking again

        # if user left group
        if not check_current_user_in_group():
            current_user.study_type = 'not_in_loop'
            break



def _step_forward_in_round(data, domain, current_round, curr_already_completed, opt_response_flag):
    """
    Steps the user forward within the current round.
    Handles regular, diagnostic, and repeated test logic.
    Updates `current_user.iteration` and `last_iter_in_round`.
    """


    interaction_type = data.get("interaction type")

    log_print('Group:', current_user.group, 'User:', current_user.id,
            'Moving forward in current round. Iteration:', current_user.iteration, 'interaction_type:', interaction_type)

    if interaction_type != "diagnostic test":
        current_user.iteration += 1

    elif not curr_already_completed:
        if not opt_response_flag:
            current_user.iteration += 1
        else:
            current_user.iteration += 2  # Skip over feedback to next test
    else:
        current_trial = ( db.session.query(Trial).filter_by(user_id=current_user.id, domain=domain, round=current_user.round, iteration=current_user.iteration)
            .order_by(Trial.id.desc()).first()  )
        
        if current_trial and current_trial.is_opt_response:
            current_user.iteration += 2
        else:
            current_user.iteration += 1

    # Check if we’re past the last iteration
    if current_user.iteration > len(current_round.round_info):
        current_user.last_iter_in_round = True
        log_print("User reached last iteration of the round.")

    update_database(current_user, f"Set next iteration")





def move_to_previous_trial(domain):
    """
    Handles the user pressing the 'Prev' button.
    Moves back one iteration or to the last iteration of the previous round.
    """
    log_print('Group:', current_user.group, 'User:', current_user.id, 'round:', current_user.round, 'iteration:', current_user.iteration, 'User pressed Prev')

    if current_user.iteration > 1:
        current_user.iteration -= 1
        cur_round = get_current_round(current_user.group, current_user.curr_progress, current_user.round)
        next_kc_id = cur_round.kc_id
    else:
        # Move to previous round
        current_user.round -= 1
        log_print('User moved to previous round:', current_user.round)

        prev_round = get_current_round(current_user.group, current_user.curr_progress, current_user.round)
        if prev_round is not None:
            current_user.iteration = len(prev_round.round_info)
        else:
            current_user.iteration = 1

        next_kc_id = prev_round.kc_id

    
    prev_trial = (
        db.session.query(Trial)
        .filter_by(user_id=current_user.id, domain=domain, round=current_user.round, iteration=current_user.iteration)
        .order_by(Trial.id.desc())
        .first()
    )

    # If no trial found for that iteration (likely because it was a feedback for a correct response in diagnostic test), skip back by one more iteration
    if prev_trial is None and current_user.iteration > 1:
        current_user.iteration -= 1

    return next_kc_id



def prepare_next_trial_data(data, domain, current_group, updated_round, next_kc_id, current_kc_id, opt_response_flag):
    """
    Prepares the response dictionary for the next trial.
    Updates flags, interaction type, and teammate statuses.
    """
    response = {}
    next_trial = (
        db.session.query(Trial)
        .filter_by(user_id=current_user.id, domain=domain, round=current_user.round, iteration=current_user.iteration)
        .order_by(Trial.id.desc())
        .first()
    )

    next_already_completed = False
    interaction_list = [x["interaction type"] for x in updated_round.round_info]

    # Set last_test and last_iter flags
    last_test_idx = next((i for i in reversed(range(len(interaction_list))) if 'test' in interaction_list[i]), -1)
    current_user.last_test_in_round = (current_user.iteration == last_test_idx + 1)
    current_user.last_iter_in_round = (current_user.iteration == len(updated_round.round_info))

    # Get trial params
    if next_trial and next_trial.likert != -1:
        next_already_completed = True
        current_user.interaction_type = next_trial.interaction_type
        response["params"] = next_trial.mdp_parameters
        response["moves"] = next_trial.moves

        if 'test' in current_user.interaction_type:
            response["params"]["tag"] = -1
            if not opt_response_flag:
                response["params"]["opt_actions"] = next_trial.moves
    else:
        next_mdp_params = updated_round.round_info[current_user.iteration - 1]
        response["params"] = next_mdp_params["params"]
        current_user.interaction_type = next_mdp_params["interaction type"]

    # Add feedback if applicable
    if 'feedback' in current_user.interaction_type:
        last_test_trial = (
            db.session.query(Trial)
            .filter_by(user_id=current_user.id, domain=domain, round=current_user.round, iteration=current_user.iteration - 1)
            .order_by(Trial.id.desc())
            .first()
        )

        if last_test_trial:
            if not opt_response_flag:
                norm_opt, norm_human = get_normalized_trajectories(last_test_trial, domain)
            else:
                norm_opt = norm_human = last_test_trial.moves

            response["params"].update({
                "normalized_opt_actions": norm_opt,
                "opt_actions": last_test_trial.moves,
                "normalized_human_actions": norm_human,
                "human_actions": last_test_trial.moves,
                "tag": -2,
            })

    # Update DB-tracked user state
    for field in ["last_iter_in_round", "last_test_in_round", "iteration", "round", "interaction_type"]:
        flag_modified(current_user, field)
    update_database(current_user, f"{current_user.username}. User progress in settings")

    # Should "Prev" be allowed?
    response["go prev"] = not (
        (current_user.round == 1 and current_user.iteration == 1 and current_user.interaction_type == "demo")
        or (current_user.interaction_type == "survey")
    )

    # Add lesson context
    N_demos = sum(1 for x in updated_round.round_info if x["interaction type"] == "demo")
    N_tests = sum(1 for x in updated_round.round_info if x["interaction type"] == "diagnostic test")
    lesson_id = next_kc_id + 1 if next_kc_id != -1 else 0
    interaction = current_user.interaction_type

    if interaction == "demo":
        iteration_id = current_user.iteration
        total = N_demos
        if current_kc_id is not None:
            lesson_string = (
                "Starting with the first game lesson." if next_kc_id == 0 else
                "Moving onto a new game lesson." if current_kc_id != next_kc_id else
                "Repeating the previous game lesson."
            )
        else:
            lesson_string = "Another game lesson."
    elif interaction == "diagnostic test":
        iteration_id = int((current_user.iteration - N_demos) / 2) + 1
        total = N_tests
        lesson_string = ""
    elif interaction == "final test":
        iteration_id = current_user.iteration
        total = len(updated_round.round_info)
        lesson_string = ""
    else:
        iteration_id = ""
        total = ""
        lesson_string = ""

    # Teammate progress strings
    round_type = "Strategy assessment" if interaction == "final test" else "Current lesson"
    group_user_ids = current_group.member_user_ids

    teammate_statuses = {}
    teammate_id = 1
    for i, uid in enumerate(group_user_ids):
        if uid == current_user.id:
            continue
        key = f"teammate_{teammate_id}_progress"
        if current_group.members_statuses[i] == "joined":
            if current_group.members_EOR[i]:
                teammate_statuses[key] = f"{round_type} completed. Waiting for teammate(s)."
            else:
                teammate_statuses[key] = f"{round_type} in progress"
        elif current_group.members_statuses[i] == "left":
            teammate_statuses[key] = "Left the study"
        teammate_id += 1

    # Final response dict
    response.update({
        "domain": domain,
        "last iteration": current_user.last_iter_in_round,
        "last test": current_user.last_test_in_round,
        "interaction type": interaction,
        "already completed": next_already_completed,
        "iteration": current_user.iteration,
        "iteration_in_category": iteration_id,
        "total iterations": total,
        "lesson id": lesson_id,
        "lesson string": lesson_string,
        "debug string": "",
        "domain completed": interaction == "survey",
        **teammate_statuses,
    })

    log_print("Prepared response:", response)
    return response



def handle_trial_navigation(data, domain, domain_order, current_group, current_round,
    params, opt_response_flag, curr_already_completed, current_kc_id):
    """
    Handles trial navigation including forward/backward movement,
    new round generation, and preparing trial response.
    """
    response = {}
    next_kc_id = -1

    # Skip if user already completed study or is doing a survey
    if current_group.curr_progress == "study_completed" or current_user.interaction_type == "survey":
        return current_group, response, next_kc_id

    movement = data.get("movement")

    if movement == "next":
        log_print('Group:', current_user.group, 'User:', current_user.id, 'User pressed Next...')
        current_group, next_kc_id = advance_or_generate_round(data, domain, domain_order, current_group, current_round,
                                                                                         params, opt_response_flag, curr_already_completed)

    elif movement == "prev":
        log_print('Group:', current_user.group, 'User:', current_user.id, 'User pressed Prev...')
        next_kc_id = move_to_previous_trial(domain)

    # Re-fetch current round (in case it changed)
    updated_round = get_current_round(current_user.group, current_user.curr_progress, current_user.round)
    
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Updated round after navigation:', updated_round, 'next_kc_id:', next_kc_id)
    
    if updated_round:
        response = prepare_next_trial_data(data, domain, current_group, updated_round, next_kc_id, current_kc_id, opt_response_flag)
    else:
        log_error('No updated round found after trial navigation')
        raise RuntimeError("No updated round found for user")

    return current_group, response, next_kc_id



def _reset_eor_flags(current_group):
    """
    Resets the current user's EOR and last test flags in the group
    after moving to a new round. Operates under group-level lock.
    """
    with group_database_transaction(current_user.group, 'Resetting EOR and last test flags'):
        current_group = db.session.query(Group).filter_by(id=current_user.group).first()

        member_idx = current_user.group_code
        current_group.members_EOR[member_idx] = False
        current_group.members_last_test[member_idx] = False

        flag_modified(current_group, "members_EOR")
        flag_modified(current_group, "members_last_test")
        # Commit handled by context manager while exiting context

    log_print('Group:', current_user.group, 'User:', current_user.id, 'Group db lock released...')
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Reset EOR and last test flags:', current_group.members_EOR)
    
    db.session.refresh(current_group)


# takes in state, including user input etc
# and returns params for next state
@socketio.on("settings")
def settings(data):
    log_print('Data received:', data)

    if data["domain"] is None or current_user.iteration == data["iteration"]: 
        repeating_data = False
    else:
        repeating_data = True
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Repeating data:', repeating_data, 'Current user iteration:', current_user.iteration, 'Data iteration:', data["iteration"])


    if is_user_active():

        log_print('Group:', current_user.group, 'User:', current_user.id, '. User active.')

        # INITIALIZE ROUND GENERATION VARIABLES
        next_round = None
        opt_response_flag = False
        next_kc_id = -1
        curr_already_completed = False
        response = {}
        

        
        ## Check if current user iteration matches the received data (sometimes when reloaded when next round was generated, the data may not match in which case we skip adding trial data)
        
        if not repeating_data:    
            log_print('Group:', current_user.group, 'User:', current_user.id, 'User iteration matches received data. Adding trial data.')

            # GET USER CONTEXT
            room_name, domain, domain_order, mdp_class, params, current_group, current_round, current_kc_id = setup_user_context(data)
            
            log_print('Group:', current_user.group, 'User:', current_user.id, 'Room name:', room_name, 'Domain:', domain, 'Domain order:', domain_order, 'MDP class:', mdp_class, 'Params:', params, 'Current round:', current_round, 'Current KC id:', current_kc_id)


            ## SAVE USER ACTIVITY DATA
            if data.get("movement") == "next":
                opt_response_flag, curr_already_completed = process_activity_and_trial_data(data, domain)
                

            print('Group:', current_user.group, 'User:', current_user.id, 'Processed trial data...', 'Opt response flag:', opt_response_flag, 'Current already completed:', curr_already_completed)

            ## CHECK AND UPDATE DOMAIN
            with group_database_transaction(current_user.group, 'Updating group before trial navigation'):
                current_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()
            
            update_result = check_and_update_domain(data, current_group)
            if update_result[0] is not None:
                domain, domain_order, mdp_class, params, current_round = update_result
                log_print('Group:', current_user.group, 'User:', current_user.id, 'Updated Domain:', domain, 'Domain order:', domain_order, 'MDP class:', mdp_class, 'Params:', params)
            
            
            # Trial navigation + round generation + response
            current_group, response, next_kc_id = handle_trial_navigation( data, domain, domain_order, current_group, current_round,
                                                                                                        params, opt_response_flag, curr_already_completed, current_kc_id)
            
            log_print('Group:', current_user.group, 'User:', current_user.id, 'Next trial response:', response)
        
        else:
            log_print('Group:', current_user.group, 'User:', current_user.id, 'User iteration does not match received data. Skipping trial data addition.')
            
            domain, domain_order, mdp_class = get_domain()
            opt_response_flag = data["user input"].get("opt_response", False)
            current_iteration = data["iteration"]
            
            
            # Fetch recent available round
            with group_database_transaction(current_user.group, 'Retrieving next round and updated group for next trial'):
                current_round = db.session.query(Round).filter_by(group_id=current_user.group, domain_progress=current_user.curr_progress).order_by(Round.id.desc()).first()
                current_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()
            
            next_kc_id = current_round.kc_id if current_round else -1

            log_print('Group:', current_user.group, 'User:', current_user.id, 'Current round:', current_round, 'Next KC id:', next_kc_id)

            if current_round:
                response = prepare_next_trial_data(data, domain, current_group, current_round, next_kc_id, None, opt_response_flag)
                log_print('Group:', current_user.group, 'User:', current_user.id, 'Next trial response:', response)
            else:
                log_error('No updated round found after trial navigation')
                raise RuntimeError("No updated round found for user")
        
        # Step 5: Emit final settings response to user
        socketio.emit("settings configured", response, to=request.sid)
        
#######################################################################################        
         
        

@app.route("/sign_consent", methods=["GET", "POST"])
@login_required
def sign_consent():
    status_print('Group:', current_user.group, 'User:', current_user.id, 'Entering sign consent')
    current_user.consent = 1
    flag_modified(current_user, "consent")
    update_database(current_user, str(current_user.username) + ". User consent")
    # need to return json since this function is called on button press
    # which replaces the current url with new url
    # sorry trying to work within existing infra
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Url for introduction:', url_for("introduction"))
    return {"url":url_for("introduction")}

@app.route("/pass_trajectories", methods=["GET", "POST"])
@login_required
def pass_trajectories():
    final_data = request.get_json()
    log_print(final_data)
    return json.dumps(send_signal(final_data["opt_response"]))



@socketio.on("group comm")
def group_comm(data):
    data["user"] = current_user.username
    log_print('Rooms for current user:', rooms())  # This will show the rooms the user is part of
    socketio.emit("incoming group data", data, to='room_'+ str(current_user.group), include_self=False)



@app.route("/consent", methods=["GET", "POST"])
@login_required
def consent():
    form = ConsentForm()
    # if current_user.consent:
    #     # flash("Consent completed!")
    #     online_condition_id = current_user.online_condition_id
    #     current_condition = db.session.query(OnlineCondition).get(online_condition_id)

    #     if current_user.num_trials_completed < (len(current_condition.trials)):
    #         return redirect(url_for("intro")) # verifying url_for and displaying training/testing simulations
    #         # return redirect(url_for("test"))
    #     return redirect(url_for("survey"))

    # else:
    if IS_IN_PERSON:
        procedure = "This study may take up to 90 minutes, and audio/screen recordings will be collected."
    else:
        procedure = "This study may take up to 70 minutes."
    return render_template("consent.html", title="Consent", form=form, procedure=procedure)


@app.route("/login", methods=["GET", "POST"])
def login():
    
    if current_user.is_authenticated:
        # next_page = request.args.get("next")

        # if next_page == "/":
        #     # Redirect to /flask_closed_loop_teaching/ instead of root
        #     next_page = "/flask_closed_loop_teaching/"

        # return redirect(next_page or url_for("index"))
        return redirect(url_for("index"))
    
    form = LoginForm()
    

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user is None:
            user = User(username=form.username.data)
            user.control_stack = []
            user.set_num_trials_completed(0)
            user.set_completion(0)
            user.set_attention_check(-1)

            # Change depending on the study type.
            # cond = user.set_condition("in_person" if IS_IN_PERSON else "online")
            
            code = user.set_code()

            with global_db_lock:
                db.session.add(user)
                db.session.commit()

        log_print('Logging in user:', user)
        login_user(user)
        log_print(f"User is authenticated after login? {current_user.is_authenticated}")
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        
        log_print('Next page url:', next_page)
        log_print(f"Redirecting to: {url_for('index', _external=True)}")

        
        # if next_page == '/':
        #     log_print('Group:', current_user.group, 'User:', current_user.id, 'Next page is / so redirecting to index')
        #     next_page = '/flask_closed_loop_teaching/'
        
        return redirect(next_page or url_for("index"))
        # return redirect(next_page)

    return render_template("login.html", title="Sign In", form=form)


@app.route("/final_survey", methods=["GET", "POST"])
@login_required
def final_survey():
    # online_condition_id = current_user.online_condition_id
    # current_condition = db.session.query(OnlineCondition).get(online_condition_id)

    (form, template) = (FinalForm(), "final_survey.html")
    log_print(form.errors)

    if form.is_submitted():
        log_print("submitted")
    

    # todo: maybe support being able to pick up where you left off, in case people frequently end up timing out of the study
    #  fwiw, people shouldn't be timing out around this portion of the study though
    if form.validate_on_submit():
        current_user.age = form.age.data
        current_user.gender = form.gender.data
        current_user.ethnicity = form.ethnicity.data
        current_user.education = form.education.data
        current_user.final_feedback = form.opt_text.data
        current_user.set_completion(1)

        flag_modified(current_user, "age")
        flag_modified(current_user, "gender")
        flag_modified(current_user, "ethnicity")
        flag_modified(current_user, "education")
        flag_modified(current_user, "final_feedback")
        flag_modified(current_user, "study_completed")

        update_database(current_user, str(current_user.username) + ". User final survey")


        # They are complete and can receive their payment code
        return redirect(url_for("index"))
    
    log_print(form.errors)
    return render_template(template,
                            methods=["GET", "POST"],
                            form=form,
                            round=round)





####################  Functions   ###################

def _get_domain_from_group(cur_group):
    
    domain_id = cur_group.curr_progress
    if domain_id == "domain_1":
        domain = cur_group.domain_1
    elif domain_id == "domain_2":
        domain = cur_group.domain_2
    else:
        log_print('Group:', current_user.group, 'User:', current_user.id, 'Domain id:', domain_id)
        raise ValueError('Domain not found')
    
    return domain


def update_learner_models_from_tests(params, cur_group, cur_round) -> tuple:
    
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating learner models based on tests...')
    
    domain = _get_domain_from_group(cur_group)

    current_domain = db.session.query(DomainParams).filter_by(domain_name=domain).first()
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Current domain:', current_domain.domain_name)

    teaching_uf = params['teacher_learning_factor']
    model_type = params['teacher_update_model_type']
    
    # current models
    ind_member_models = copy.deepcopy(cur_group.ind_member_models)
    group_union_model = copy.deepcopy(cur_group.group_union_model)
    group_intersection_model = copy.deepcopy(cur_group.group_intersection_model)
    num_members = copy.deepcopy(cur_group.num_members)
    num_active_members = copy.deepcopy(cur_group.num_active_members)
    active_member_ids = [idx for idx, status in enumerate(cur_group.members_statuses) if status == 'joined']


    log_print('Group:', current_user.group, 'User:', current_user.id, 'Before updating learner models from tests for constraints...', cur_round.min_BEC_constraints_running)
    find_prob_particles(ind_member_models, cur_group.members_statuses, cur_round.min_BEC_constraints_running)

    group_knowledge = cur_round.group_knowledge[0]
    kc_id = cur_round.kc_id

    group_usernames = retrieve_group_usernames(cur_group)
    group_test_constraints = []
    joint_constraints = []
    knowledge_to_update = []
    
    for username in group_usernames:
        group_code = db.session.query(User).filter_by(username=username).first().group_code
        log_print('Group:', current_user.group, 'User:', current_user.id, 'Username:', username, 'Group:', current_user.group, 'Group code:', group_code, 'round:', current_user.round, 'member statuses:', cur_group.members_statuses)
        tests = db.session.query(Trial).filter_by(domain=domain, group=current_user.group, group_code=group_code, round=current_user.round, interaction_type="diagnostic test").all()
        
        update_model_flag = False
        if cur_group.members_statuses[group_code] == 'joined':
            update_model_flag = True
        
        if update_model_flag and len(tests) > 0:
            test_constraints = []
            for test in tests:
                cur_test_constraints = get_test_constraints(domain, test, current_domain.traj_record, current_domain.traj_features_record)
                test_constraints.extend(cur_test_constraints)
                log_print('Group:', current_user.group, 'User:', current_user.id, 'Test constraints:', test_constraints)    
            group_test_constraints.append(test_constraints)
            log_print('Group:', current_user.group, 'User:', current_user.id, 'Group test constraints so far:', group_test_constraints)

            min_test_constraints = remove_redundant_constraints(test_constraints, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the unit's demonstrations
            log_print('Group:', current_user.group, 'User:', current_user.id, 'Min test constraints:', min_test_constraints)
            
            # update learner models
            log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating learner models for member:', group_code, 'with constraints:', min_test_constraints)
            ind_member_models[group_code].update(min_test_constraints, teaching_uf, model_type, params)

            joint_constraints.append(min_test_constraints)

    group_test_constraints_expanded = [item for sublist in group_test_constraints for item in sublist]
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Group test constraints expanded:', group_test_constraints_expanded)
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Joint constraints:', joint_constraints)

    # update group_union_model and group_intersection_model
    group_min_constraints = remove_redundant_constraints(group_test_constraints_expanded, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the group's demonstrations
    
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating common model with constraints:', group_min_constraints)
    group_intersection_model.update(group_min_constraints, teaching_uf, model_type, params) # common belief model
    
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating joint model with constraints:', joint_constraints)
    group_union_model.update_jk(joint_constraints, teaching_uf, model_type, params)  # joint belief model

    
    # update team knowledge
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Update team knowledge for num members:', num_members)
    updated_group_knowledge = update_team_knowledge(group_knowledge, kc_id, True, group_test_constraints, num_active_members, active_member_ids, params['mdp_parameters']['weights'], params['step_cost_flag'], knowledge_to_update = 'all')


    log_print('Group:', current_user.group, 'User:', current_user.id, 'Updated group knowledge:', updated_group_knowledge)

    ind_member_models_pos_current = [ind_member_models[i].positions for i in range(num_members)]
    ind_member_models_weights_current = [ind_member_models[i].weights for i in range(num_members)]

    current_round_tests_updated = Round(group_id=cur_round.group_id, 
                                round_num=cur_round.round_num,
                                domain_progress = cur_group.curr_progress,
                                domain = domain,
                                members_statuses=cur_group.members_statuses,
                                kc_id = kc_id,
                                min_KC_constraints = cur_round.min_KC_constraints,
                                round_info=cur_round.round_info,
                                status="tests_updated",
                                variable_filter=cur_round.variable_filter,
                                nonzero_counter=cur_round.nonzero_counter,
                                min_BEC_constraints_running=cur_round.min_BEC_constraints_running,
                                prior_min_BEC_constraints_running=cur_round.prior_min_BEC_constraints_running,
                                visited_env_traj_idxs=cur_round.visited_env_traj_idxs,
                                ind_member_models_pos = [ind_member_models_pos_current],
                                ind_member_models_weights = [ind_member_models_weights_current],
                                group_union_model_pos = [group_union_model.positions],
                                group_union_model_weights = [group_union_model.weights],
                                group_intersection_model_pos = [group_intersection_model.positions],
                                group_intersection_model_weights = [group_intersection_model.weights],
                                group_knowledge = [updated_group_knowledge]
                                )

    update_database(current_round_tests_updated, 'Update round data from tests')



    log_print('Group:', current_user.group, 'User:', current_user.id, 'After updating learner models from tests for constraints...', current_round_tests_updated.min_BEC_constraints_running)
    find_prob_particles(ind_member_models, cur_group.members_statuses, current_round_tests_updated.min_BEC_constraints_running)

    log_print('Group:', current_user.group, 'User:', current_user.id, 'Adding particle filter models to group')
    cur_group.ind_member_models = copy.deepcopy(ind_member_models)
    cur_group.group_union_model = copy.deepcopy(group_union_model)
    cur_group.group_intersection_model = copy.deepcopy(group_intersection_model)
    cur_group.status = "upd_tests"  # update status

    flag_modified(cur_group, "ind_member_models")
    flag_modified(cur_group, "group_union_model")
    flag_modified(cur_group, "group_intersection_model")   
    flag_modified(cur_group, "status")

    update_database(cur_group, 'Update group learner models from tests')


    # return ind_member_models, group_union_model, group_intersection_model



def retrieve_next_round(params, cur_group) -> dict:
    """
    retrieves necessary environment variables for displaying the next round to
    the client based on database entries. gets called on the condition that 
    player group_code == A, since we don't want to do computation more than once

    data in: none (retrieves test moves from database)
    data out: environment variables for next round
    side effects: none  
    """ 
    
    from app import pool, lock

    group_id = cur_group.id
    
    # with group_database_transaction(group_id):
        
    # Refresh group data to get latest state
    db.session.refresh(cur_group)   
    
    
    round = current_user.round 

    domain_id = cur_group.curr_progress
    if domain_id == "domain_1":
        domain = cur_group.domain_1
    elif domain_id == "domain_2":
        domain = cur_group.domain_2
    else:
        log_print('Group:', current_user.group, 'User:', current_user.id, 'Domain id:', domain_id)
        raise ValueError('Domain not found')
    
    log_print('Group:', current_user.group, 'User:', current_user.id, 'round:', round, 'Group status:', cur_group.status, 'Group experimental condition:', cur_group.experimental_condition, 'Group members:', cur_group.members)

    experimental_condition = cur_group.experimental_condition
    members_statuses = cur_group.members_statuses
    active_member_ids = [idx for idx, status in enumerate(members_statuses) if status == 'joined']
    
    vars_filename = date.today().strftime("%Y-%m-%d") + '_group_' + str(current_user.group)
    new_round_for_var_filter = False


    # load previous round data
    if round > 0:
        log_print('Group:', current_user.group, 'User:', current_user.id, 'current_user.curr_progress:', current_user.curr_progress, 'current_group prgress:', cur_group.curr_progress, 'round:', round, 'group:', current_user.group)
        prev_models = db.session.query(Round).filter_by(group_id=cur_group.id, domain_progress=current_user.curr_progress, round_num=round).order_by(Round.id.desc()).first()
        log_print('Group:', current_user.group, 'User:', current_user.id, 'Previous round:', prev_models.id, prev_models.round_num, prev_models.status, prev_models.group_id, prev_models.domain, prev_models.group_knowledge, prev_models.kc_id, prev_models.min_KC_constraints)
        
        # all_prev_rounds = db.session.query(Round).filter_by(group_id=cur_group.id, domain_progress=current_user.curr_progress).all()
        # log_print('Group:', current_user.group, 'User:', current_user.id, 'All previous rounds...')
        # for prev_round in all_prev_rounds:
        #     log_print('Group:', current_user.group, 'User:', current_user.id, 'Previous round:', prev_round.id, prev_round.round_num, prev_round.status, prev_round.group_id, prev_round.domain, prev_round.group_knowledge, prev_round.kc_id, prev_round.min_KC_constraints)
        
        group_union_model = copy.deepcopy(cur_group.group_union_model)
        group_intersection_model =  copy.deepcopy(cur_group.group_intersection_model)
        ind_member_models =  copy.deepcopy(cur_group.ind_member_models)

        variable_filter = prev_models.variable_filter
        nonzero_counter = prev_models.nonzero_counter
        log_print('Group:', current_user.group, 'User:', current_user.id, 'Nonzero counter:', nonzero_counter, 'round:', round)
        min_BEC_constraints_running = prev_models.min_BEC_constraints_running
        prior_min_BEC_constraints_running = prev_models.prior_min_BEC_constraints_running
        visited_env_traj_idxs = prev_models.visited_env_traj_idxs
        group_knowledge = prev_models.group_knowledge[0]
        kc_id = prev_models.kc_id
        min_KC_constraints = prev_models.min_KC_constraints


    else:
        # initialize models for first round/learning session
        group_knowledge, particles_team_teacher, variable_filter, nonzero_counter, min_BEC_constraints_running, visited_env_traj_idxs, domain_params = initialize_teaching((domain, pool, lock))
        prior_min_BEC_constraints_running = copy.deepcopy(min_BEC_constraints_running)
        
        log_print('Group:', current_user.group, 'User:', current_user.id, 'nonzero counter:', nonzero_counter, 'round:', 0, 'variable filter:', variable_filter)

        ind_member_models = []
        for key in particles_team_teacher.keys():
            if 'common' not in key and 'joint' not in key:
                ind_member_models.append(copy.deepcopy(particles_team_teacher[key]))

        group_intersection_model = copy.deepcopy(particles_team_teacher['common_knowledge'])
        group_union_model = copy.deepcopy(particles_team_teacher['joint_knowledge'])
        kc_id = 0
            
            
        # # # save domain params to database (run only once for each domain)
        existing_domain_params = db.session.query(DomainParams).filter_by(domain_name=domain).first()
        if existing_domain_params is None:
            curr_domain_params = DomainParams(
                domain_name = domain_params["domain_name"],
                min_subset_constraints_record = domain_params["min_subset_constraints_record"],
                env_record = domain_params["env_record"],
                traj_record = domain_params["traj_record"],
                traj_features_record = domain_params["traj_features_record"],
                mdp_features_record = domain_params["mdp_features_record"],
                consistent_state_count = domain_params["consistent_state_count"],
                min_BEC_constraints = domain_params["min_BEC_constraints"]
            )
            
            # with group_database_transaction(group_id):
            db.session.add(curr_domain_params)
            db.session.commit()


        # create a directory for the group
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(current_dir, 'group_teaching', 'results', params['data_loc']['BEC']))
        
        full_path_filename = base_dir + '/ind_sim_trials/' + vars_filename

        if not os.path.exists(full_path_filename):
            # sometimes when date chanages at midnight
            alternate_path_filename =  base_dir + '/ind_sim_trials/' + (date.today() - timedelta(days=1)).strftime("%Y-%m-%d") + '_group_' + str(current_user.group)
            if os.path.exists(alternate_path_filename):
                full_path_filename = alternate_path_filename
            
            status_print('Group:', current_user.group, 'User:', current_user.id, 'Creating folder for this run: ', full_path_filename)
            os.makedirs(full_path_filename, exist_ok=True)
    


    #check if unit knowledge is reached and update variable filter
    if round > 0:
        log_print('Group:', current_user.group, 'User:', current_user.id, 'Round:', round, 'Group knowledge:', group_knowledge, 'min_KC_constraints:', min_KC_constraints, 'kc_id:', kc_id, 'active_member_ids:', active_member_ids)
        unit_learning_goal_reached_flag = check_unit_learning_goal_reached(params, group_knowledge, active_member_ids, min_KC_constraints, kc_id)
    else:
        unit_learning_goal_reached_flag = False
        new_round_for_var_filter = True

    # check if max KC loops are reached
    if not unit_learning_goal_reached_flag:
        all_kc_rounds = db.session.query(Round).filter_by(group_id=cur_group.id, domain_progress=current_user.curr_progress, kc_id=kc_id, status="demo_tests_generated").all()
        
        unique_keys = set((r.group_id, r.kc_id, r.round_num) for r in all_kc_rounds)  # replace with actual deduplication keys
        num_unique_rounds = len(unique_keys)
        log_print('N KC rounds:', num_unique_rounds, 'Params max KC loops:', params['max_KC_loops'])
        
        if num_unique_rounds >= params['max_KC_loops']:
            unit_learning_goal_reached_flag = True
    

    log_print('Group:', current_user.group, 'User:', current_user.id, 'Current group status:', cur_group.status)
    
    if (cur_group.status != "Domain teaching completed"):

        log_print('Group:', current_user.group, 'User:', current_user.id, 'Current variable filter: ', variable_filter, ' with nonzero counter: ', nonzero_counter)
        if unit_learning_goal_reached_flag:
            variable_filter, nonzero_counter = update_variable_filter(nonzero_counter)
            log_print('Group:', current_user.group, 'User:', current_user.id, 'Updated variable filter: ', variable_filter, ' with nonzero counter: ', nonzero_counter)
            kc_id += 1
            new_round_for_var_filter = True

            # update prior min BEC constraints
            prior_min_BEC_constraints_running = copy.deepcopy(min_BEC_constraints_running)
        else:
            # update BEC constraints
            min_BEC_constraints_running = copy.deepcopy(prior_min_BEC_constraints_running)

        
        log_print('Group:', current_user.group, 'User:', current_user.id, 'min BEC constraints:', min_BEC_constraints_running, 'prior min BEC constraints:', prior_min_BEC_constraints_running)
        
        # check if teaching is complete
        teaching_complete_flag = False
        if not np.any(variable_filter) and unit_learning_goal_reached_flag:
            teaching_complete_flag = True

        # NOTE: Only for Quick Debugging. Having only one knowledge component/round
        if QUICK_DEBUG_FLAG:
            if round > 1:
                teaching_complete_flag = True


        group_print(current_user.group, 'User:', current_user.id, 'Teaching complete flag before generating demos:', teaching_complete_flag)


        # get demonstrations and tests for this round
        if not teaching_complete_flag:
            ind_member_models_demo_gen = copy.deepcopy(ind_member_models)
            group_union_model_demo_gen = copy.deepcopy(group_union_model)
            group_intersection_model_demo_gen = copy.deepcopy(group_intersection_model)

            args = domain, vars_filename, group_union_model_demo_gen, group_intersection_model_demo_gen, ind_member_models_demo_gen, members_statuses, experimental_condition, variable_filter, nonzero_counter, new_round_for_var_filter, min_BEC_constraints_running, visited_env_traj_idxs, pool, lock    
            min_KC_constraints, demo_mdps, test_mdps, experimental_condition, variable_filter, nonzero_counter, min_BEC_constraints_running, visited_env_traj_idxs, teaching_complete_flag, _ = generate_demos_test_interaction_round(args)
            
            
            round_status = "demo_tests_generated"
            games_extended = []

            group_print(current_user.group, 'User:', current_user.id, 'N Demo mdps:', len(demo_mdps))


            # Check if demo_mpds provide full information intended for this lesson
            demo_constraints = []
            reduced_demo_information_flag = False
            ideal_lesson_constraints = ideal_kc_constraints[domain][kc_id] if domain in ideal_kc_constraints and kc_id < len(ideal_kc_constraints[domain]) else None
            
            if len(demo_mdps) > 0:
                for d_mdp in demo_mdps:
                    demo_constraints.extend(d_mdp.get('constraints'))
                
                min_demo_constraints = remove_redundant_constraints(demo_constraints, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the unit's demonstrations
            
                if normalize_constraints(min_demo_constraints) != normalize_constraints(ideal_lesson_constraints):
                    reduced_demo_information_flag = True
                else:
                    reduced_demo_information_flag = False
                

            
            # lesson
            log_print('Group:', current_user.group, 'User:', current_user.id, 'Reduced demo information flag:', reduced_demo_information_flag, 'min demo constraints:', min_demo_constraints, 'ideal_lesson_constraints:', ideal_lesson_constraints)
            
            # new round data
            if len(demo_mdps) > 0 and not reduced_demo_information_flag:
                
                games = list()
                for i in range(len(demo_mdps)):
                    games.append({"interaction type": "demo", "params": demo_mdps[i]})

                for i in range(len(test_mdps)):
                    games.append({"interaction type": "diagnostic test", "params": test_mdps[i]})
                
            
            elif new_round_for_var_filter:
                log_print(colored('No new demos generated for the new variable filter. Using default demos...', 'red'))
                group_print(current_user.group, 'User:', current_user.id, 'No new demos generated for the new variable filter. Using default demos...')
                
                games = list()
                if domain == 'at':
                    mdp_class = 'augmented_taxi2'
                elif domain == 'sb':
                    mdp_class = 'skateboard2'

                interaction_types = ['demo', 'diagnostic test']

                for it in interaction_types:
                    for interaction_id in default_rounds[mdp_class][it].keys():
                        mdp_dict = default_rounds[mdp_class][it][interaction_id]
                        # # check if variable filter matches
                        if (np.array(mdp_dict['variable_filter']) == variable_filter).all():
                            games.append({"interaction type": it, "params": mdp_dict}) 

                # status_print('Games:', games)

            else:
                group_print(current_user.group, 'User:', current_user.id, 'No new demos generated. Repeating previous round...')
                # repeat the same round if no demos are generated
                prev_round_data = db.session.query(Round).filter_by(group_id=cur_group.id, domain_progress=current_user.curr_progress, round_num=round).order_by(Round.id.desc()).first()
                games_extended = prev_round_data.round_info
                min_KC_constraints = prev_round_data.min_KC_constraints

            ## Add feedback for diagnostic tests
            if len(games_extended)==0:  
                for game in games:
                    games_extended.append(game)
                    if game["interaction type"] == "diagnostic test":
                        new_game = copy.deepcopy(game)
                        new_game["interaction type"] = "diagnostic feedback"
                        new_game["params"]["tag"] = -1  
                        games_extended.append(new_game)
        
        
        
        else:
            log_print(current_user.group, 'User:', current_user.id, 'Adding final tests for this round...')
            round_status = "final_tests_generated"
            round_generation_process = ''
            test_difficulty = ['low', 'medium', 'high']
            games = list()

            if domain == 'at':
                mdp_class = 'augmented_taxi2'
            elif domain == 'sb':
                mdp_class = 'skateboard2'
            
            final_test_id = 1
            # final_tests_to_add = [3, 5, 8, 12, 15, 17] # indices of final tests to add (one for each difficulty level)
            final_tests_to_add = [1, 2, 3, 4, 5, 6] # indices of final tests to add (one for each difficulty level)

            # final_tests_to_add = [1, 2, 4, 8, 10, 12] # balances KCs from among the available tests
            
            # if domain == 'at':
            #     final_tests_to_add = [6, 7, 8, 11, 14, 15]
            # elif domain == 'sb':
            #     final_tests_to_add = [4, 7, 10, 12, 14, 16]
            # else:
            #     RuntimeError('Unknown domain')
                
                
            if QUICK_DEBUG_FLAG:
                final_tests_to_add = [1, 3]
            
            for td in test_difficulty:
                for mdp_list in default_rounds[mdp_class]["final test"][td]:
                    for mdp_dict in mdp_list:
                        if final_test_id in final_tests_to_add:
                            log_print('Adding final test:', final_test_id, 'Difficulty:', td)
                            games.append({"interaction type": "final test", "params": mdp_dict})
                        final_test_id += 1

            # add a survey at the end
            games.append({"interaction type": "survey", "params": {}})

            log_print('Group:', current_user.group, 'User:', current_user.id, 'Added ', len(games), ' final tests for this round...')

            games_extended = []
            for game in games:
                games_extended.append(game)
                if game["interaction type"] == "diagnostic test":
                    new_game = copy.deepcopy(game)
                    new_game["interaction type"] = "diagnostic feedback"
                    new_game["params"]["tag"] = -1  
                    games_extended.append(new_game)
            
            for game in games_extended:
                log_print('Group:', current_user.group, 'User:', current_user.id, 'Extended list. Interaction type: ', game["interaction type"])
            

        # add models to group database
        log_print('Group:', current_user.group, 'User:', current_user.id, 'Adding particle filter models to group for new round...')
        cur_group.ind_member_models = copy.deepcopy(ind_member_models)
        cur_group.group_union_model = copy.deepcopy(group_union_model)
        cur_group.group_intersection_model = copy.deepcopy(group_intersection_model)

        flag_modified(cur_group, "ind_member_models")
        flag_modified(cur_group, "group_union_model")
        flag_modified(cur_group, "group_intersection_model")

        if teaching_complete_flag:
            cur_group.status = "Domain teaching completed"
            flag_modified(cur_group, "status")
        
        update_database(cur_group, 'PF models, teaching status updated')


        # add new round to round database
        ind_member_models_pos = [ind_member_models[i].positions for i in range(len(ind_member_models))]
        ind_member_models_weights = [ind_member_models[i].weights for i in range(len(ind_member_models))]

        log_print('Group:', current_user.group, 'User:', current_user.id, 'Group curr progress:', cur_group.curr_progress, 'domain:', domain, 'round:', round )
        log_print('kc_id: ', kc_id, 'min_KC_constraints:', min_KC_constraints, 'round_status: ', round_status)
        new_round = Round(group_id=cur_group.id, 
                        domain_progress = cur_group.curr_progress,
                        domain = domain,
                        round_num=round+1, 
                        members_statuses = members_statuses,
                        kc_id = kc_id,
                        min_KC_constraints = min_KC_constraints,
                        round_info=games_extended,
                        status = round_status,
                        variable_filter=variable_filter,
                        nonzero_counter=nonzero_counter,
                        min_BEC_constraints_running=min_BEC_constraints_running,
                        prior_min_BEC_constraints_running=prior_min_BEC_constraints_running,
                        visited_env_traj_idxs=visited_env_traj_idxs,
                        ind_member_models_pos = [ind_member_models_pos],
                        ind_member_models_weights = [ind_member_models_weights],
                        group_union_model_pos = [group_union_model.positions],
                        group_union_model_weights = [group_union_model.weights],
                        group_intersection_model_pos = [group_intersection_model.positions],
                        group_intersection_model_weights = [group_intersection_model.weights],
                        group_knowledge = [group_knowledge]
                )         
        log_print('New round info:', new_round)                     
        update_database(new_round, 'New round data generated')

        return games_extended

    else:
        return list()



def update_learner_models_from_demos(params, cur_group, next_round) -> tuple:

    log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating learner models based on demos...')

    teacher_uf = params['teacher_learning_factor']
    model_type = params['teacher_update_model_type']

    
    # log_print('Group:', current_user.group, 'User:', current_user.id, 'Before updating demos for constraints...', next_round.min_BEC_constraints_running)
    find_prob_particles(cur_group.ind_member_models, cur_group.members_statuses, next_round.min_BEC_constraints_running)

    # current models
    ind_member_models = copy.deepcopy(cur_group.ind_member_models)
    group_union_model = copy.deepcopy(cur_group.group_union_model)
    group_intersection_model = copy.deepcopy(cur_group.group_intersection_model)

    # update the models based on the demos
    demo_mdps = [game["params"] for game in next_round.round_info if game["interaction type"] == "demo"]
    
    constraints = []
    for demo_mdp in demo_mdps:
        constraints.extend(demo_mdp['constraints'])

    min_KC_constraints = remove_redundant_constraints(constraints, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the unit's demonstrations
            
    
    # update the models
    joint_constraints = []
    ind_member_models_pos_current = []
    ind_member_models_weights_current  = []
    for i in range(len(ind_member_models)):
        if cur_group.members_statuses[i] == 'joined':
            # log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating model for member:', i, 'with constraints:', min_KC_constraints)
            ind_member_models[i].update(min_KC_constraints, teacher_uf, model_type, params)
            joint_constraints.append(min_KC_constraints)

            ind_member_models_pos_current.append(ind_member_models[i].positions)
            ind_member_models_weights_current.append(ind_member_models[i].weights)

            # log_print('Group:', current_user.group, 'User:', current_user.id, 'Member:', i, 'N positions:', len(ind_member_models[i].positions), 'N weights:', len(ind_member_models[i].weights))

    # update the team models
    # log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating common models... with constraints:', min_KC_constraints)
    group_intersection_model.update(min_KC_constraints, teacher_uf, model_type, params)  # common belief model
    # log_print('Group:', current_user.group, 'User:', current_user.id, 'Updated group belief model with constraints:', joint_constraints)
    group_union_model.update_jk(joint_constraints, teacher_uf, model_type, params) # joint belief model

    # log_print('Group:', current_user.group, 'User:', current_user.id, 'After updating demos for constraints...', next_round.min_BEC_constraints_running)
    find_prob_particles(ind_member_models, cur_group.members_statuses, next_round.min_BEC_constraints_running)
    

    current_round_demo_updated = Round(group_id=next_round.group_id, 
                                    domain_progress = cur_group.curr_progress,
                                    domain = next_round.domain,
                                    round_num=next_round.round_num,
                                    kc_id = next_round.kc_id,
                                    min_KC_constraints = min_KC_constraints,
                                    members_statuses=cur_group.members_statuses,
                                    round_info=next_round.round_info,
                                    status="demos_updated",
                                    variable_filter=next_round.variable_filter,
                                    nonzero_counter=next_round.nonzero_counter,
                                    min_BEC_constraints_running=next_round.min_BEC_constraints_running,
                                    prior_min_BEC_constraints_running=next_round.prior_min_BEC_constraints_running,
                                    visited_env_traj_idxs=next_round.visited_env_traj_idxs,
                                    ind_member_models_pos = [ind_member_models_pos_current],
                                    ind_member_models_weights = [ind_member_models_weights_current],
                                    group_union_model_pos = [group_union_model.positions],
                                    group_union_model_weights = [group_union_model.weights],
                                    group_intersection_model_pos = [group_intersection_model.positions],
                                    group_intersection_model_weights = [group_intersection_model.weights],
                                    group_knowledge = next_round.group_knowledge
                                    )
    
    update_database(current_round_demo_updated, 'Round db -Update learner models from demos')
       
    # log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating models to group')
    cur_group.ind_member_models = copy.deepcopy(ind_member_models)
    cur_group.group_union_model = copy.deepcopy(group_union_model)
    cur_group.group_intersection_model = copy.deepcopy(group_intersection_model)
    cur_group.status = "upd_demos"

    flag_modified(cur_group, "ind_member_models")
    flag_modified(cur_group, "group_union_model")
    flag_modified(cur_group, "group_intersection_model")   
    flag_modified(cur_group, "status")

    update_database(cur_group, 'Group db - Update learner models from demos')


    # return ind_member_models, group_union_model, group_intersection_model



def update_learner_models_from_feedback(params, cur_group, next_round) -> tuple:

    log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating learner models based on feedback...')

    teacher_uf = params['teacher_learning_factor']
    model_type = params['teacher_update_model_type']

    
    # log_print('Group:', current_user.group, 'User:', current_user.id, 'Before updating demos for constraints...', next_round.min_BEC_constraints_running)
    find_prob_particles(cur_group.ind_member_models, cur_group.members_statuses, next_round.min_BEC_constraints_running)

    # current models
    ind_member_models = copy.deepcopy(cur_group.ind_member_models)
    group_union_model = copy.deepcopy(cur_group.group_union_model)
    group_intersection_model = copy.deepcopy(cur_group.group_intersection_model)

    # update the models based on the demos
    test_mdps = [game["params"] for game in next_round.round_info if game["interaction type"] == "diagnostic test"]
    
    constraints = []
    for test_mdp in test_mdps:
        constraints.extend(test_mdp['constraints'])

    min_KC_constraints = remove_redundant_constraints(constraints, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the unit's demonstrations
            
    
    # update the models
    joint_constraints = []
    ind_member_models_pos_current = []
    ind_member_models_weights_current  = []
    for i in range(len(ind_member_models)):
        if cur_group.members_statuses[i] == 'joined':
            # log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating model for member:', i, 'with constraints:', min_KC_constraints)
            ind_member_models[i].update(min_KC_constraints, teacher_uf, model_type, params)
            joint_constraints.append(min_KC_constraints)

            ind_member_models_pos_current.append(ind_member_models[i].positions)
            ind_member_models_weights_current.append(ind_member_models[i].weights)

            # log_print('Group:', current_user.group, 'User:', current_user.id, 'Member:', i, 'N positions:', len(ind_member_models[i].positions), 'N weights:', len(ind_member_models[i].weights))

    # update the team models
    # log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating common models... with constraints:', min_KC_constraints)
    group_intersection_model.update(min_KC_constraints, teacher_uf, model_type, params)  # common belief model
    # log_print('Group:', current_user.group, 'User:', current_user.id, 'Updated group belief model with constraints:', joint_constraints)
    group_union_model.update_jk(joint_constraints, teacher_uf, model_type, params) # joint belief model

    # log_print('Group:', current_user.group, 'User:', current_user.id, 'After updating demos for constraints...', next_round.min_BEC_constraints_running)
    find_prob_particles(ind_member_models, cur_group.members_statuses, next_round.min_BEC_constraints_running)
    

    current_round_feedback_updated = Round(group_id=next_round.group_id, 
                                    domain_progress = cur_group.curr_progress,
                                    domain = next_round.domain,
                                    round_num=next_round.round_num,
                                    kc_id = next_round.kc_id,
                                    min_KC_constraints = min_KC_constraints,
                                    members_statuses=cur_group.members_statuses,
                                    round_info=next_round.round_info,
                                    status="feedback_updated",
                                    variable_filter=next_round.variable_filter,
                                    nonzero_counter=next_round.nonzero_counter,
                                    min_BEC_constraints_running=next_round.min_BEC_constraints_running,
                                    prior_min_BEC_constraints_running=next_round.prior_min_BEC_constraints_running,
                                    visited_env_traj_idxs=next_round.visited_env_traj_idxs,
                                    ind_member_models_pos = [ind_member_models_pos_current],
                                    ind_member_models_weights = [ind_member_models_weights_current],
                                    group_union_model_pos = [group_union_model.positions],
                                    group_union_model_weights = [group_union_model.weights],
                                    group_intersection_model_pos = [group_intersection_model.positions],
                                    group_intersection_model_weights = [group_intersection_model.weights],
                                    group_knowledge = next_round.group_knowledge
                                    )
    
    update_database(current_round_feedback_updated, 'Update round data from feedback')
       
    # log_print('Group:', current_user.group, 'User:', current_user.id, 'Updating models to group')
    cur_group.ind_member_models = copy.deepcopy(ind_member_models)
    cur_group.group_union_model = copy.deepcopy(group_union_model)
    cur_group.group_intersection_model = copy.deepcopy(group_intersection_model)
    cur_group.status = "upd_feedback"

    flag_modified(cur_group, "ind_member_models")
    flag_modified(cur_group, "group_union_model")
    flag_modified(cur_group, "group_intersection_model")   
    flag_modified(cur_group, "status")

    update_database(cur_group, 'Update group learner models from feedback')






def retrieve_group_usernames(current_group) -> list[str]:
    """
    retrieves group usernames given current user

    data in: none 
    data out: list[str] of 3 groupmates (including current user)
    side effects: none
    """

    # run query on Groups database
    # current_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()

    group_usernames = []
    for loop_id in range(len(current_group.members)):
        if current_group.members_statuses[loop_id] == 'joined':
            group_usernames.append(current_group.members[loop_id])

    return group_usernames




def get_test_constraints(domain, trial, traj_record, traj_features_record) -> np.ndarray:
    prev_mdp_parameters = trial.mdp_parameters
    log_print('Group:', current_user.group, 'User:', current_user.id, 'Test MDP params:', prev_mdp_parameters)
    best_env_idx, best_traj_idx = prev_mdp_parameters['env_traj_idxs']
    opt_traj = traj_record[best_env_idx][best_traj_idx]
    opt_traj_features = traj_features_record[best_env_idx][best_traj_idx]

    if domain == 'at':
        mdp_class = 'augmented_taxi2'
    elif domain == 'sb':
        mdp_class = 'skateboard2'

    # obtain the constraint that the participant failed to demonstrate
    constraint = obtain_constraint(mdp_class, prev_mdp_parameters, opt_traj, opt_traj_features)

    return constraint


    
def update_database(updated_data, update_type, max_retries=5):
    """
    Simplified database update with retry logic for SQLite locks
    """
    for attempt in range(max_retries):
        try:     
            db.session.add(updated_data)
            db.session.flush()
            db.session.commit()
            db.session.refresh(updated_data)
            if "User left study" not in update_type:
                log_print(f"Current Group: {current_user.group}, User: {current_user.id}, Database operation successful: {update_type}")
            
            return True
            
        except OperationalError as e:
            
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                db.session.rollback() # first rollback the session in case of lock errors before accessing any tables from the db (user, group, etc.)
                if "User left study" not in update_type:
                    log_error(f"Current Group: {current_user.group}, User: {current_user.id}, Database locked, retrying in {wait_time:.2f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                db.session.rollback()
                if "User left study" not in update_type:
                    log_error(f"Current Group: {current_user.group}, User: {current_user.id}, Database operation failed: {update_type}, Error: {str(e).lower()}")
                raise
        except Exception as e:
            db.session.rollback()
            if "User left study" not in update_type:
                log_error(f"Current Group: {current_user.group}, User: {current_user.id}, Unexpected error during {update_type}: {e}")
            raise



def get_domain():
    # get game domain
    curr_domain = current_user.curr_progress[-1]  # just get last string


    if curr_domain == "1":
        domain = current_user.domain_1
    elif curr_domain == "2":
        domain = current_user.domain_2
    else:
        # default
        curr_domain = "1"
        domain = current_user.domain_1

    if domain == 'at':
        mdp_class = 'augmented_taxi2'
    elif domain == 'sb':
        mdp_class = 'skateboard2'
    else:
        mdp_class = ""

    log_print('Group:', current_user.group, 'User:', current_user.id, 'curr_progress:', current_user.curr_progress, 'curr_domain:', curr_domain)


    return domain, curr_domain, mdp_class


def add_survey_data(domain, data):
    group_print(current_user.group, 'User:', current_user.id, 'Survey data:', data)
    # add survey data to database
    dom = Domain(
            group_id = current_user.group,
            user_id = current_user.id,
            domain_name = domain,
            attn1 = int(data["attn1"]),
            attn2 = int(data["attn2"]),
            attn3 = int(data["attn3"]),
            use1 = int(data["use1"]),
            use2 = int(data["use2"]),
            use3 = int(data["use3"]),
            understanding = data["understanding"],
            engagement_short_answer = data["engagement_input"],
            reward_ft_weights = data["reward_ft_weights"]
        )
    
    # with global_db_lock:
        # db.session.add(dom)
        # db.session.commit()
        
    update_database(dom, 'Adding survey data to database...')


def add_trial_data(domain, data):

    # if len(data["user input"]) !=0:
    group_print(current_user.group, 'User:', current_user.id, 'Adding trial data to database...', ' user id: ', current_user.id, 'round:', current_user.round, 'iteration:', current_user.iteration)

    trial = Trial(
        user_id = current_user.id,
        group_code = current_user.group_code,
        group = current_user.group,
        domain = domain,
        round = current_user.round,
        interaction_type = current_user.interaction_type,
        iteration = current_user.iteration,
        subiteration = current_user.subiteration,
        likert = int(data["survey"]),
        moves = data["user input"]["moves"],
        coordinates = data["user input"]["agent_history_nonoffset"],
        is_opt_response = data["user input"]["opt_response"],
        mdp_parameters = data["user input"]["mdp_parameters"],
        duration_ms = data["user input"]["simulation_rt"],
        human_model = None, #TODO: later?,
        num_visits = 1,
        engagement_short_answer = data["engagement_input"],
        improvement_short_answer = data["improvement_input"],

        final_score = int(data["final_score"]),
        all_scores = data["final_score_string"]
    )

    # with global_db_lock:
    #     db.session.add(trial)
    #     db.session.commit()
    
    update_database(trial, 'Adding trial data to database...')


def update_domain_group(cur_group):

    # update group variables
    if cur_group.curr_progress == "domain_1":
        cur_group.curr_progress = "domain_2"
        cur_group.status = "next_domain"
        # domain = current_group.domain_2

    elif cur_group.curr_progress == "domain_2":
        cur_group.curr_progress = "study_completed"
        cur_group.status = "study_completed"
        # domain = current_group.domain_2

    else:
        RuntimeError("Domain not found")

    flag_modified(cur_group, "curr_progress")
    flag_modified(cur_group, "status")
    update_database(cur_group, 'New domain group db: ' + cur_group.curr_progress)



def update_domain_user(current_user, current_group):

    # update user variables
    current_user.round = 0
    current_user.iteration = 0
    current_user.interaction_type = ""
    current_user.last_iter_in_round = True

    current_user.curr_progress = current_group.curr_progress

    flag_modified(current_user, "curr_progress")
    flag_modified(current_user, "round")
    flag_modified(current_user, "iteration")
    flag_modified(current_user, "interaction_type")
    flag_modified(current_user, "last_iter_in_round")
    update_database(current_user, 'New domain for user db: ' + current_user.curr_progress)



def find_prob_particles(individual_models, members_statuses, min_BEC_constraints_running):

    # calculate the knowledge level of the individual models
    prob_models = []
    model_ids = []
    for loop_id in range(len(individual_models)):
        # only consider the models that are still part of the group
        if members_statuses[loop_id] == 'joined':
            individual_models[loop_id].calc_particles_probability(min_BEC_constraints_running)
            prob_models.append(individual_models[loop_id].particles_prob_correct)
            model_ids.append(loop_id)

    prob_models_array = np.array(prob_models)
    log_print(colored('Prob of learning for constraints:','blue'))
    log_print( min_BEC_constraints_running, 'models: ', prob_models_array, 'Model ids: ', model_ids)


def get_normalized_trajectories(last_test_trial, domain):


    opt_actions = last_test_trial.mdp_parameters['opt_actions']
    opt_locations = last_test_trial.mdp_parameters['opt_locations']
    opt_locations_tuple = [tuple(opt_location) for opt_location in opt_locations]

    human_actions = last_test_trial.moves
    human_locations = last_test_trial.coordinates
    
    if domain == 'at':
        human_locations_tuple = [(human_location[0], human_location[1], int(human_location[2])) for
                                    human_location in human_locations]
    else:
        human_locations_tuple = [(human_location[0], human_location[1]) for
                                    human_location in human_locations]

    log_print('Group:', current_user.group, 'User:', current_user.id, 'Opt locations:', opt_locations_tuple, 'Human locations:', human_locations_tuple, 'Opt actions:', opt_actions, 'Human actions:', human_actions) 
    
    try:
        normalized_opt_actions, normalized_human_actions = normalize_trajectories(opt_locations_tuple, opt_actions, human_locations_tuple, human_actions)
    except:
        # give original trajectories if normalization fails
        normalized_opt_actions, normalized_human_actions = opt_actions, human_actions

    return normalized_opt_actions, normalized_human_actions



