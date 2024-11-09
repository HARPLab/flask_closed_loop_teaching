from flask import render_template, flash, redirect, url_for, request, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, TrialForm, DemoForm, ConsentForm, AttentionCheckForm, FinalForm, TrainingForm, FeedbackSurveyForm, NoFeedbackSurveyForm, InformativenessForm
from app.models import User, Trial, Demo, Survey, Domain, Group, Round, DomainParams, OnlineCondition, InPersonCondition
from app.params import *
import copy
# import numpy as np
# import random as rand
import json
# from datetime import datetime

import sys, os
# sys.path.append(os.path.join(os.path.dirname(__file__), 'augmented_taxi'))
# from .augmented_taxi.policy_summarization.flask_user_study_utils import normalize_trajectories, obtain_constraint
# from .augmented_taxi.policy_summarization.BEC import obtain_remedial_demonstrations
# from .augmented_taxi import params
# from .augmented_taxi.policy_summarization import BEC_helpers
# from .augmented_taxi.policy_summarization import particle_filter as pf

sys.path.append(os.path.join(os.path.dirname(__file__), 'group_teaching'))
from .group_teaching.codes.user_study.user_study_utils import generate_demos_test_interaction_round, initialize_teaching, obtain_constraint, normalize_trajectories
# from .group_teaching.codes import params_team as params
from .group_teaching.codes.policy_summarization.BEC_helpers import remove_redundant_constraints, update_variable_filter
from .group_teaching.codes.teams.teams_helpers import update_team_knowledge, check_unit_learning_goal_reached
from .group_teaching.codes.params_utils import get_mdp_parameters
from app.backend_test import send_signal
from app import socketio
from flask_socketio import join_room, leave_room, rooms
import asyncio
from concurrent.futures import ProcessPoolExecutor
from sqlalchemy.orm.attributes import flag_modified

# from transitions import Machine, State


import pickle
import numpy as np
from datetime import date
import matplotlib.pyplot as plt

executor = ProcessPoolExecutor()


with open(os.path.join(os.path.dirname(__file__), 'user_study_dict.json'), 'r') as f:
    jsons = json.load(f)

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


@app.route("/logout")
def logout():
    # Clear this variable -- for some reason was not clearing on its own.
    session.pop("attention_check_rules", None)
    logout_user()
    return {"url":url_for("index")}

    
@app.route("/", methods=["GET", "POST"])
# @app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    # online_condition_id = current_user.online_condition_id
    # current_condition = db.session.query(OnlineCondition).get(online_condition_id)

    print("Index url in index function:", request.url)
    print("User is authenticated?", current_user.is_authenticated)

    completed = True if current_user.study_completed == 1 else False

    current_user.loop_condition = "debug"
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
    print(request.sid)
    print("I am getting called with version: " + str(version))
    # print('received message: ' + data['version'])
    # session_id = request.sid
    # print('session_id is: ' + session_id)
    # print(request.sid)
    if version == 1:
        current_user.set_curr_progress("sandbox_1")
    elif version == 2:
        current_user.set_curr_progress("sandbox_2")

    flag_modified(current_user, "curr_progress")
    update_database(current_user, str(current_user.username) + ". User progress sandbox")

    print("current user progress is: " + current_user.curr_progress)
    print(request.sid)
    socketio.emit('made sandbox', to=request.sid)
    # current_user.set_test_column(812)
    # db.session.commit()
    # curr_room = ""
    # if len(current_user.username) % 2 == 0:
    #     curr_room = "room1"
    # else:
    #     curr_room = "room2"
    # join_room(curr_room)
    # socketio.emit('join event', {"test":current_user.username + "just joined!"}, to=curr_room)

@socketio.on("connect")
def handle_connect():
    print(request.sid + " connected?")
    rejoin_group()


@socketio.on("disconnect")
def handle_disconnect():
    print(request.sid + " disconnected?")
    leave_group()


@socketio.on("sandbox settings")
def sandbox_settings(data):
    print(request.sid)
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
    print(version)
    if version == "sandbox_1":
        preamble = ("<h1>Free play</h1> <hr/> " + "<h4>A subset of the keys in the table below will be available to control Chip in each game.<br>All game instances that you decide how Chip behaves in will be marked with a <font color='blue'>blue border</font>, like below.</h4><br>" +
        "<h4>Feel free to play around in the game below and get used to the controls.</h4>" +
        "<h4>If you accidentally take a wrong action, you may reset the simulation and start over by pressing 'r'.</h4><br>" +
        "<h4>You can click the continue button whenever you feel ready to move on.</h4><br>" +
        "<h5> As a reminder this game consists of a <b>location</b> (e.g. <img src = 'static/img/star.png' width=\"20\" height=auto />), <b>an object that you can grab and drop</b> (e.g. <img src = 'static/img/pentagon.png' width=\"20\" height=auto />), <b>an object that you can absorb by moving through</b> (e.g. <img src = 'static/img/diamond.png' width=\"20\" height=auto />), and <b>walls </b>that you can't move through (<img src = 'static/img/wall.png' width=\"20\" height=auto />).</h5>")
      
        # params = {
        #     'agent': {'x': 4, 'y': 3, 'has_passenger': 0},
        #     'walls': [{'x': 2, 'y': 3}, {'x': 2, 'y': 2}, {'x': 3, 'y': 2}, {'x': 4, 'y': 2}],
        #     'passengers': [{'x': 4, 'y': 1, 'dest_x': 1, 'dest_y': 4, 'in_taxi': 0}],
        #     'hotswap_station': [{'x': 1, 'y': 2}],
        #     'width': 4,
        #     'height': 4,
        # }
        legend = ""
        # continue_condition = "free_play"
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
        # params = {
        #     'agent': {'x': 4, 'y': 1, 'has_passenger': 0},
        #     'walls': [{'x': 1, 'y': 3}, {'x': 2, 'y': 3}, {'x': 3, 'y': 3}],
        #     'passengers': [{'x': 1, 'y': 2, 'dest_x': 1, 'dest_y': 4, 'in_taxi': 0}],
        #     'hotswap_station': [{'x': 2, 'y': 1}],
        #     'width': 4,
        #     'height': 4,
        # }
        legend = "<br><br><br><table class=\"center\"><tr><th>Key</th><th>Action</th></tr><tr><td>up/down/left/right arrow keys</td><td>corresponding movement</td></tr><tr><td>p</td><td>pick up</td></tr><tr><td>d</td><td>drop</td></tr><tr><td>r</td><td>reset simulation</td></tr></table><br>"
        # continue_condition = "optimal_traj_1"
    # stimulus = '<iframe id = "ifrm" style="border:none;" src="' + source + '" height="550" width="950" title="Iframe Example"></iframe>    '
    res = render_template("mike/sandbox.html", preamble=preamble, legend=legend)
    # print(res)
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
    print("I'm in post practice")
    current_user.set_curr_progress("post practice")
    current_user.last_iter_in_round = True

    flag_modified(current_user, "curr_progress")
    flag_modified(current_user, "last_iter_in_round")

    update_database(current_user, str(current_user.username) + ". User progress post practice")

    preamble = ("<br><br><h3>Good job on completing the practice game! <b>Read these instructions carefully!</b> Let's now head over to the <b>two main games</b> and <b>begin the real study</b>.</h3><br>" +
            "<h4>In these games, you will <b>not</b> be told how each action changes Chip's energy level.</h4><br>" +
            "For example, note the '???' in the Energy Change column below. <table class=\"center\"><tr><th>Action</th><th>Sample sequence</th><th>Energy change</th></tr><tr><td>Any action that you take (e.g. moving right)</td><td><img src = 'static/img/right1.png' width=\"150\" height=auto /><img src = 'static/img/arrow.png' width=\"30\" height=auto /><img src = 'static/img/right2.png' width=\"150\" height=auto /><td>???</td></tr></table> <br>" +
            "<h4>Instead, you will have to <u>figure that out</u> and subsequently the best strategy for completing the task while minimizing Chip's energy loss <u>by observing Chip's demonstrations, given as different lessons!</u></h3><br>" +
            "<h4>In between demonstrations/lessons, Chip may test your understanding by asking you to predict the best strategy and giving you corrective feedback to help you learn!</h4><br>" +
            "<h4>Finally, <u>you may navigate back to previous interactions</u> (e.g. demonstrations) to refresh your memory <u>when you're not being tested!</u></h4>" + 
            "<h4> <b> Remember, you are part of a group and will be learning the same lessons as the group members. This means you may have to wait for all your members to complete a lesson before moving onto the next lesson. </b> </h4><br>" +
            "<h4> <b> If anyone in your group has not learned the lesson, your entire group will repeat the lesson. </b> </h4><br>" +
            "<h4> You will need to successfully complete both games to finish the study</u> and receive your compensation!</h4><br>" +
            "<h4>Click the Next button when you're ready to start the study!</h4>"
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

    ret = {}
    cond_list = ["individual_belief_low", "individual_belief_high", "common_belief", "joint_belief"]
    
    # get last entry in groups table
    # the initial entry is an empty list as initialized in app/__init__.py
    open_group = db.session.query(Group).filter_by(status="study_not_start").order_by(Group.id.desc()).first()

    num_active_members = 0
    params = get_mdp_parameters("")

    if not current_user.group: # if no group yet, join one

        print('Join group function. Current user group: ', current_user.group)
        
        if open_group is not None:
            num_active_members = open_group.num_active_members
            print('Old group:', 'Group id:', open_group.id, 'num_active_members:', num_active_members, 'Group members:', open_group.members, 'Group mem ids:', open_group.member_user_ids, 'Group status:', open_group.members_statuses, 'Group experimental condition:', open_group.experimental_condition)


        if num_active_members == 0 or num_active_members == params['team_size']: # if group is full or empty, create a new group
            print('No group yet.. Creating one...')
            new_group_entry = Group(
                # experimental_condition=cond_list[current_user.group % 4],
                experimental_condition=cond_list[0],
                status = "study_not_start",
                member_user_ids = [None for i in range(params['team_size'])],
                members = [None for i in range(params['team_size'])],
                members_statuses = ["not joined" for i in range(params['team_size'])],
                num_active_members = 0,
                num_members = params['team_size'],
                members_EOR = [False for i in range(params['team_size'])],
                members_last_test = [False for i in range(params['team_size'])],
                )

            db.session.add(new_group_entry)
            db.session.commit()
                        
            new_group = db.session.query(Group).order_by(Group.id.desc()).first()
            current_user.group = new_group.id

            _, current_user.group_code, current_user.domain_1, current_user.domain_2 = new_group.groups_push(current_user.username, current_user.id)
            print('New group:', 'Group id:', new_group.id, 'Group members:', new_group.members, 'Active members:', new_group.num_active_members, 'Group mem ids:', new_group.member_user_ids, 'Group status:', new_group.members_statuses, 'Group experimental condition:', new_group.experimental_condition)
            print('Current user:', current_user.username, 'Current user group:', current_user.group, 'Current user group code:', current_user.group_code, 'Current user domain 1:', current_user.domain_1, 'Current user domain 2:', current_user.domain_2)
            num_active_members = 1

            update_database(new_group, 'Member to new group')
            
        else:
            print('Adding to existing group')
            _, current_user.group_code, current_user.domain_1, current_user.domain_2 = open_group.groups_push(current_user.username, current_user.id)
            current_user.group = open_group.id
            num_active_members += 1
            print('Old group:', 'Group id:', open_group.id, 'Group members:', open_group.members, 'Group mem ids:', open_group.member_user_ids, 'Group status:', open_group.members_statuses, 'Group experimental condition:', open_group.experimental_condition)
            print('Current user:', current_user.username, 'Current user group:', current_user.group, 'Current user group code:', current_user.group_code, 'Current user domain 1:', current_user.domain_1, 'Current user domain 2:', current_user.domain_2)

            update_database(open_group, 'Member to existing group')
    

    print('Current user: ' + str(current_user.username) + 'Current user group: ' + str(current_user.group))
    

    # make sure that when people leave and rejoin they check the time elapsed and 
    # if it's not too long, then put them back in a group
    # they shouldn't be able to go back once they're in the waiting room

    # test 
    all_groups = db.session.query(Group).all()
    print([[g.id, g.members] for g in all_groups])

    print('Room:', 'room_'+ str(current_user.group))
    join_room('room_'+ str(current_user.group))

    # if room is None then it gets sent to everyone
    print('Rooms for current user:', rooms())  # This will show the rooms the user is part of
    socketio.emit("group joined", {"num_members":num_active_members, "max_num_members": params['team_size'], "room_name": 'room_'+ str(current_user.group)}, to='room_'+ str(current_user.group))
    return


def rejoin_group():

    print('Rejoining group....')
    # check if current user has a group

    print('Current user:', current_user.username, 'Current user group:', current_user.group)

    if current_user.group is not None:
        # get the group
        group_to_rejoin = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()

        print('Group to rejoin:', 'Group id:', group_to_rejoin.id, 'Group members:', group_to_rejoin.members, 'Group mem ids:', group_to_rejoin.member_user_ids, 'Group status:', group_to_rejoin.members_statuses, 'Group experimental condition:', group_to_rejoin.experimental_condition)
        
        user_status = group_to_rejoin.members_statuses[current_user.group_code]

        # check if current user is in the group
        if user_status != 'joined':
            
            # add the user to the group
            _, current_user.group_code, current_user.domain_1, current_user.domain_2 = group_to_rejoin.groups_push_again(current_user.username, current_user.id)
            # update the database
            update_database(group_to_rejoin, 'Member rejoined group')
            # join the room
            join_room('room_'+ str(current_user.group))
            # emit the group joined signal
            socketio.emit("group joined", {"num_members":group_to_rejoin.num_active_members, "max_num_members": group_to_rejoin.num_members, "room_name": 'room_'+ str(current_user.group)}, to='room_'+ str(current_user.group))
        
    return True




# @socketio.on("join group v2")
# def join_group_v2():
#     join_room('room_'+ str(current_user.group))
#     socketio.emit("member joined again", {"user code": current_user.group_code}, to='room_'+ str(current_user.group))
#     return

# @socketio.on("leave group temp")
# def leave_group_temp():
#     socketio.emit("member left temp", {"member code": current_user.group_code}, to='room_'+ str(current_user.group))
#     return

@socketio.on("leave group")
def leave_group():
    """
    handles leaving groups. executed upon client-side call to "leave 
    group" in mike/augmented_taxi2_introduction.html or mike/augmented_taxi2.html.
    emits the code for the group member which dropped, back to the other two 
    group members, at endpoint "member left".

    data in: none
    data emitted: member_code
    side effects: TBD   
    """ 

    print('Leaving group....')

    current_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()

    print('Before leaving group:', 'Group id:', current_group.id, 'Group members:', current_group.members, 'Group mem ids:', current_group.member_user_ids, 'Group status:', current_group.members_statuses, 'Group experimental condition:', current_group.experimental_condition)

    _ = current_group.groups_remove(current_user.username)

    update_database(current_group, 'Member left group')

    print('After leaving group:', 'Group id:', current_group.id, 'Group members:', current_group.members, 'Group mem ids:', current_group.member_user_ids, 'Group status:', current_group.members_statuses, 'Group experimental condition:', current_group.experimental_condition)
    
    socketio.emit("member left", {"member code": current_user.group_code}, to='room_'+ str(current_user.group))
    return


# @socketio.on('join room')
# def handle_message():
#     # print('received message: ' + data['data'])
#     # session_id = request.sid
#     # print('session_id is: ' + session_id)
    
#     # print(request.sid)
#     # if current_user.username[0] == "a":
#     #     current_user.group = "room1"
#     # else:
#     #     current_user.group = "room2"

#     join_room("waiting_room")
#     # socketio.emit('join event', {"test":current_user.username + "just joined!"}, to=curr_room)

@socketio.on("next domain")
def next_domain(data):
    
    # save remaining data from final test
    if len(data["user input"]) !=0:
        domain, _ = get_domain()
        trial = Trial(
            user_id = current_user.id,
            group_code = current_user.group_code,
            group = current_user.group,
            domain = domain,
            round = current_user.round,
            interaction_type = current_user.interaction_type,
            iteration = current_user.iteration,
            subiteration = current_user.subiteration,
            likert = int(data["interaction survey"]),
            moves = data["user input"]["moves"],
            coordinates = data["user input"]["agent_history_nonoffset"],
            is_opt_response = data["user input"]["opt_response"],
            mdp_parameters = data["user input"]["mdp_parameters"],
            duration_ms = data["user input"]["simulation_rt"],
            human_model = None #TODO: later?
        )
        db.session.add(trial)
        db.session.commit()
    
    
    
    print("next domain yassss")
    current_user.interaction_type = "demo"
    current_user.iteration = 0
    print('curr_progress in next domain:', current_user.curr_progress)

    if current_user.curr_progress == "post practice":
        print("slayyy")
        current_user.set_curr_progress("domain 1")
        print('current_user domains:', current_user.domain_1, current_user.domain_2)
        socketio.emit("next domain is", {"domain": current_user.domain_1}, to=request.sid)
    # elif current_user.curr_progress == "domain 1":
    #     current_user.set_curr_progress("domain 2")
    #     socketio.emit("next domain is", {"domain": current_user.domain_2}, to=request.sid)
    # elif current_user.curr_progress == "domain 2":
    #     current_user.set_curr_progress("final survey")
    #     socketio.emit("next domain is", {"domain": "final survey"}, to=request.sid)
    elif current_user.curr_progress == "domain 1":
        current_user.interaction_type = "survey"
        current_user.set_curr_progress("final survey")
        socketio.emit("next domain is", {"domain": "final survey"}, to=request.sid)

    flag_modified(current_user, "curr_progress")
    flag_modified(current_user, "interaction_type")
    flag_modified(current_user, "iteration")

    update_database(current_user, str(current_user.username) + ". User progress next domain")


# @socketio.on("retrieve_first_round")
# def retrieve_first_round() -> dict:

async def retrieve_first_round():

    loop = asyncio.get_event_loop()
    games = await loop.run_in_executor(executor, retrieve_first_round_helper)
    return games

    

# ## WIP functions, not completely working at the moment - 08/21/24
# def retrieve_first_round_helper(params) -> dict:

#     # TODO: find non-zero counter variable and add to Round database

#     from app import pool, lock

#     # initialize the particles for the group
#     particles_team_teacher, _, _, _, _, domain_params = initialize_teaching((domain, pool, lock))

#     ind_member_models = []
#     for key in particles_team_teacher.keys():
#         if 'common' not in key and 'joint' not in key:
#             ind_member_models.append(particles_team_teacher[key])

#     group_intersection_model = copy.deepcopy(particles_team_teacher['common_knowledge'])
#     group_union_model = copy.deepcopy(particles_team_teacher['joint_knowledge'])

#     group = current_user.group

#     #load the first round demos and tests (games)
#     with open(os.path.join(os.path.dirname(__file__), '../augmentedtaxi_first_demo_test_mdps.pickle'), 'rb') as f:
#         demo_mdps, test_mdps, variable_filter, min_BEC_constraints_running, visited_env_traj_idxs  = pickle.load(f)
    
#     print('Initial variable filter: ', variable_filter)



#     games = list()
#     for i in range(len(demo_mdps)):
#         games.append({"interaction type": "demo", "params": demo_mdps[i]})

#     for i in range(len(test_mdps)):
#         games.append({"interaction type": "diagnostic test", "params": test_mdps[i]})

#     print('Initializing teacher model of learner for group: ', group)
#     new_round = Round(group_id=group, round_num=0, 
#                       ind_member_models=ind_member_models,
#                       group_union_model=group_union_model,
#                       group_intersection_model=group_intersection_model,
#                       status ="demo_tests_generated",
#                       variable_filter=variable_filter,
#                       min_BEC_constraints_running=min_BEC_constraints_running,
#                       visited_env_traj_idxs=visited_env_traj_idxs,)
#     db.session.add(new_round)
#     db.session.commit()

#     return games


@app.route("/at_intro", methods=["GET", "POST"])
@login_required
def at_intro():
    return render_template("mike/augmented_taxi2_introduction.html")

@app.route("/at", methods=["GET", "POST"])
@login_required
def at():
    # form = InformativenessForm()
    # if form.validate_on_submit():
    #     # do something, this might not be the best way to structure this lol
    #     db.session.commit()
    return render_template("mike/augmented_taxi2.html")

@app.route("/sb_intro", methods=["GET", "POST"])
@login_required
def sb_intro():
    return render_template("mike/skateboard2_introduction.html")

@app.route("/sb", methods=["GET", "POST"])
@login_required
def sb():
    return render_template("mike/skateboard2.html")




# takes in state, including user input etc
# and returns params for next state
@socketio.on("settings")
def settings(data):

    room_name = data["room_name"]
    domain, mdp_class = get_domain()
    params = get_mdp_parameters(mdp_class)

    print('Current user:', current_user.id, 'Group:', current_user.group, 'Curr_progress:', current_user.curr_progress, 'Curr interaction:', current_user.interaction_type)
    print('Room name:', room_name)
    print('domain:', domain, 'mdp class:', mdp_class)
    
    next_round = None
    new_round_flag = False
    first_round_flag = False
    update_pf = False
    skip_response = False
    opt_response_flag = False
    next_kc_id = -1
    current_kc_id = -2

    # check if response needs to be skipped
    if current_user.last_test_in_round and current_user.round != 0 and data["movement"] == "next":
        recent_trial = db.session.query(Trial).filter_by(user_id=current_user.id).order_by(Trial.id.desc()).first()
        if recent_trial.interaction_type == "diagnostic test":
            skip_response = True
            print('Skipping response for diagnostic test')


    # update database with iteration data
    if not skip_response:
        if current_user.interaction_type == "survey":
            add_survey_data(domain, data)
            # end study
        else:
            
            response = {}
            current_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()
            current_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()

            print('Current user group: ', current_user.group, 'Domain: ', current_group.curr_progress, 'Round_num:', current_user.round, 'current_round:', current_round, current_user.iteration, current_user.interaction_type)

            if current_round is not None:
                current_mdp_params = current_round.round_info[current_user.iteration - 1]
                current_user.interaction_type = current_mdp_params["interaction type"]
                current_kc_id = current_round.kc_id
            
            if data["movement"] == "next":
                print('User: ', current_user.id, 'Next movement............................................')

                ### add/update trial data to database  
                print('data: ', data)
                print('Domain: ', domain, 'Current user round:', current_user.round, 'Current user iteration:', current_user.iteration, 'current interaction type:', current_user.interaction_type)
                
                # check if current iteration has been already completed and add/update trial data
                curr_already_completed = False
                current_trial = db.session.query(Trial).filter_by(user_id=current_user.id,
                                                                    domain=domain,
                                                                    round=current_user.round,
                                                                    iteration=current_user.iteration).order_by(Trial.id.desc()).first()                          
                                                            
                print('Checking if previous trial exists...')
                print('Current trial in next movement:', current_trial)


                ### Add trial data to database when a trial is completed and re-visited after completion
                if (current_trial is None and current_user.round !=0 and data["interaction type"] is not None and int(data["interaction survey"]) != -1) or (current_trial is not None and int(data["interaction survey"]) != -1):
                    
                    print('Adding trial data to database...')
                    if 'test' in current_user.interaction_type:
                        # for completed tests
                        if len(data["user input"]) != 0:
                            data["user input"]["mdp_parameters"]["human_actions"] = data["user input"]["moves"]
                            opt_response_flag = data["user input"]["opt_response"]
                    
                    add_trial_data(domain, data)

                elif current_trial is not None:
                    print('Updating visited count to trial data...')
                    curr_already_completed = True
                    current_trial.num_visits += 1
                    flag_modified(current_trial, "num_visits")
                    update_database(current_trial, 'Current trial num visits: ' + str(current_trial.num_visits))
                
                db.session.commit()

                #########################
                print('Next movement. Current trial already completed:', curr_already_completed, '. Current user last iter in round:', current_user.last_iter_in_round)
                ### generate new round if all group members are at the end of current round (end of tests); if not step through the remaining iterations in the round
                # if not curr_already_completed and current_user.last_test_in_round:
                if not curr_already_completed and current_user.last_iter_in_round:
                    
                    ### check for end of domain
                    print('Current user round: ', current_user.round, 'Current user iteration:', current_user.iteration, 'Current user last iter in round:', current_user.last_iter_in_round, 'current interaction type:', current_user.interaction_type)
                    print('Checking for new domain............')
                    # for final tests, last test and last iteration should be the same
                    if (current_user.round > 0) and current_mdp_params["interaction type"] == "final test"  and current_user.last_iter_in_round:
                        print("Current group status: ", current_group.status, 'Group id:', current_group.id, 'Group members:', current_group.members, 'Group mem ids:', current_group.member_user_ids, 'Group status:', current_group.members_statuses, 'Group experimental condition:', current_group.experimental_condition, 'curr_progress:', current_group.curr_progress)            
                        domain, mdp_class = update_domain(current_group)
                        update_database(current_group, 'Current group status: ' + current_group.status)
                        params = get_mdp_parameters(mdp_class)  # update params for new domain
                        print("All groups reached end of current domain, so I'm trying to construct the first round of next domain.")

                    #############################

                    print("Current group status: ", current_group.status, 'Current user round:', current_user.round, 'current_user group:', current_user.group, 'current_user curr_progress:', current_user.curr_progress)
                    

                    ### Generate first round for the group
                    if (current_user.round == 0):
                        first_round_flag = True
                        if (db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=1).count() == 0 and 
                            current_group.status != "gen_demos"):

                            print('Generating first round...')
                            retrieve_next_round(params, current_group)
                            
                            # current_group.ind_member_models, current_group.group_union_model, current_group.group_intersection_model = update_learner_models_from_demos(params)
                            next_round_id = current_user.round+1
                            next_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()
                            db.session.refresh(current_group)
                            

                            if current_group.status != "Domain teaching completed":
                                update_learner_models_from_demos(params, current_group, next_round)
                            db.session.refresh(current_group)
                            current_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()

                            print('After updating learner models from demos...')
                            find_prob_particles(current_group.ind_member_models, current_group.members_statuses, next_round.min_BEC_constraints_running)

                        else:
                            round_status = ""
                            print('Waiting for first round to be generated...')
                            next_round_id = current_user.round+1
                            next_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()

                            if next_round is None:
                                while (round_status != "demo_tests_generated") and (round_status != "final_tests_generated"):
                                    next_round_id = current_user.round+1
                                    next_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()
                                    if next_round is not None:
                                        round_status = next_round.status  
                        
                        # vars for next round
                        next_kc_id = next_round.kc_id
                        print('Next round:', next_round, 'Next round status:', next_round.status, 'Next round kc_id:', next_kc_id)

                    else:
                        
                        # ## update last test status for current user
                        # member_idx = current_group.members.index(current_user.username)
                        # current_group.members_last_test[member_idx] = True
                        # flag_modified(current_group, "members_last_test")
                        # print('Member' + str(member_idx) + ' reached last test')
                        # update_database(current_group, 'Member ' + str(member_idx) + ' reached last test')

                        ## Update EOR status for current user
                        print('User: ', current_user.username, 'reached last iteration in round')
                        member_idx = current_group.members.index(current_user.username)
                        current_group.members_EOR[member_idx] = True
                        flag_modified(current_group, "members_EOR")
                        print('Member' + str(member_idx) + ' reached EOR')
                        update_database(current_group, 'Member ' + str(member_idx) + ' reached EOR')

                        
                        print('Group members EOR status: ', current_group.members_EOR, 'all EOR:', current_group.groups_all_EOR(), 'all last test:', current_group.group_last_test(), 'mdp_params["interaction type"]: ', current_mdp_params["interaction type"])
                        # if (current_group.group_last_test()):
                        #     print("All groups reached last test, so i'm trying to construct the next round now")
                        #     print("Current group status: ", current_group.status)

                        if (current_group.groups_all_EOR()):
                            print("All groups reached last test, so i'm trying to construct the next round now")
                            print("Current group status: ", current_group.status)
                            
                            if current_group.status == "upd_demos":
                                
                                # update models from test responses
                                update_learner_models_from_tests(params, current_group, current_round)  # only for diagnostic tests and not for final tests
                                db.session.refresh(current_group)
                                current_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()
                                

                                pf_round_id = current_user.round
                                pf_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=pf_round_id).order_by(Round.id.desc()).first()
                                
                                print('After updating learner models from tests...')
                                find_prob_particles(current_group.ind_member_models, current_group.members_statuses, pf_round.min_BEC_constraints_running)
                                
                                # flag_modified(current_group, "status")
                                # flag_modified(current_group, "ind_member_models")
                                # flag_modified(current_group, "group_union_model")
                                # flag_modified(current_group, "group_intersection_model")
                                # update_database(current_group, 'Current group status: upd_tests')
                                
                            
                                print("Generating next round...")
                                retrieve_next_round(params, current_group)
                                db.session.refresh(current_group)
                                next_round_id = current_user.round+1
                                next_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()
                                
                                next_kc_id = next_round.kc_id

                                print('Updating learner models from demos...')
                                # current_group.ind_member_models, current_group.group_union_model, current_group.group_intersection_model = update_learner_models_from_demos(params)
                                if current_group.status != "Domain teaching completed":
                                    update_learner_models_from_demos(params, current_group, next_round)
                                db.session.refresh(current_group)
                                current_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()                            

                                print('After updating learner models from demos...')
                                find_prob_particles(current_group.ind_member_models, current_group.members_statuses, next_round.min_BEC_constraints_running)

                                # flag_modified(current_group, "status")
                                # flag_modified(current_group, "ind_member_models")
                                # flag_modified(current_group, "group_union_model")
                                # flag_modified(current_group, "group_intersection_model")
                                # update_database(current_group, 'Current group status: upd_demos')
                            else:
                                print('Curr group status: ', current_group.status)
                                print("Group status not updated to upd_demos")
                            
                            print('Socket emitting all reached EOR')
                            print('Rooms for current user:', rooms())  # This will show the rooms the user is part of
                            socketio.emit("all reached EOR", to='room_'+ str(current_user.group))  # triggers next page button to go to next round for clients

                        print('Interaction type: ', current_mdp_params["interaction type"], 'current user iteration:', current_user.iteration, 'len of round info:', len(current_round.round_info))

                    if not opt_response_flag:
                        current_user.iteration += 1   # iteration for answers to diagnostic tests
                    # else:
                    #     current_user.last_iter_in_round = True
                    else:
                        current_user.iteration += 1 


                else:
                    print('Moving for with next iteration in current round...', 'Iteration:', current_user.iteration)
                    if data["interaction type"] != "diagnostic test": 
                        current_user.iteration += 1
                    elif data["interaction type"] == "diagnostic test" and not opt_response_flag:
                        current_user.iteration += 1
                    elif data["interaction type"] == "diagnostic test" and opt_response_flag:
                        current_user.iteration += 1
                        # current_user.iteration += 2  # skip the optimal response and go to the next test
                ###########################


                # ### update member status for last iteration in round (when new round is generated based on last test)
                # if current_user.last_iter_in_round and current_user.round != 0:
                #     print('User: ', current_user.username, 'reached last iteration in round')
                #     member_idx = current_group.members.index(current_user.username)
                #     current_group.members_EOR[member_idx] = True
                #     flag_modified(current_group, "members_EOR")
                #     print('Member' + str(member_idx) + ' reached EOR')
                #################

                ## check if a new round was generated
                print('next_round:', next_round, 'current_user.last_iter_in_round', current_user.last_iter_in_round)
                if current_user.last_iter_in_round: 

                    print('Checking if new round is already generated...')
                    
                    # check if new round is already generated (this is a safety check as the user should be able to press 'Next' only if next round is available)
                    next_round_id = current_user.round+1
                    next_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()

                    if next_round is not None:
                        new_round_flag = True
                        
                        print('Next round generated...')
                        current_user.round += 1
                        current_user.iteration = 1  # reset iteration to 1 for new round
                        current_user.last_iter_in_round = False
                        current_user.last_test_in_round = False

                        # reset EOR flags
                        current_group.members_EOR = [False for x in current_group.members_EOR]
                        current_group.members_last_test = [False for x in current_group.members_last_test]

                        flag_modified(current_group, "members_EOR")
                        flag_modified(current_group, "members_last_test")

                        update_database(current_group, 'Reset EOR flags')
                ################################

            elif data["movement"] == "prev":
                print('User: ', current_user.id, 'Prev movement............................................')
                if current_user.iteration > 1:
                    current_user.iteration -= 1 #update iteration for current round
                else:
                    current_user.round -= 1
                    print('User round after prev:', current_user.round)
                    prev_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()
                    current_user.iteration = len(prev_round.round_info)
                    
            ################################################################################


            # update user's round and iteration
            # print('current_group.groups_all_EOR:', current_group.groups_all_EOR(), 'first_round_flag:', first_round_flag)


            ########################

            # check if next trial to be shown has already been completed
            next_already_completed = False

            print('group_id:', current_user.group, 'Current user round:', current_user.round, 'current_group progress:', current_group.curr_progress, 'Current user iteration:', current_user.iteration)
            
            next_trial = db.session.query(Trial).filter_by(user_id=current_user.id, domain=domain, round=current_user.round, iteration=current_user.iteration).order_by(Trial.id.desc()).first()
            updated_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()

            print('Next trial: ', next_trial, '. Updated round:', updated_round)
            ######################


            # check if this is the last test in the round
            interaction_list = [x["interaction type"] for x in updated_round.round_info]
            last_test_iteration_idx = next((i for i in reversed(range(len(interaction_list))) if 'test' in interaction_list[i]), None)
            print('current_user.iteration:', current_user.iteration, 'Last test iteration:', last_test_iteration_idx + 1)

            if current_user.iteration == last_test_iteration_idx + 1:
                current_user.last_test_in_round = True
                print("Next test is last in round for user")
            else:
                current_user.last_test_in_round = False
            
            # check if this is the last iteration in the round
            if current_user.iteration == len(updated_round.round_info):
                current_user.last_iter_in_round = True
                print("Next iteration is last in round for user")
            else:
                current_user.last_iter_in_round = False
            ###################


            ## update variables
            if next_trial is not None and next_trial.likert != -1:
                print('Response params of previously completed trial...')
                next_already_completed = True
                skip_response = False  # do not skip if the trial has already been completed
                current_user.interaction_type = next_trial.interaction_type

                response["params"] = next_trial.mdp_parameters
                response["moves"] = next_trial.moves

                if 'test' in current_user.interaction_type:
                    # # if you've already been to this test page, you should simply show the optimal trajectory
                    response["params"]["tag"] = -1
                    if not opt_response_flag:
                        response["params"]["opt_actions"] = next_trial.moves
                    

            else:
                print('Response params from MDP params for new trial...')
                next_mdp_params = updated_round.round_info[current_user.iteration - 1]
                response["params"] = next_mdp_params["params"]
                current_user.interaction_type = next_mdp_params["interaction type"]
            #######################
            
            ## check if next trial is "answer"
            if 'answer' in current_user.interaction_type:
                # Show correct response for the previous test with normalize the actions of the optimal and (incorrect) human trajectory such that they're the same length
                # (by causing the longer trajectory to wait at overlapping states)
                # update human actions and locations for visuzalization

                last_test_trial = db.session.query(Trial).filter_by(user_id=current_user.id, domain=domain, round=current_user.round, iteration=current_user.iteration - 1).order_by(Trial.id.desc()).first()
                print('Last test trial interaction type:', last_test_trial.interaction_type)

                normalized_opt_actions, normalized_human_actions = get_normalized_trajectories(last_test_trial, domain)
                # print('normalized_opt_actions:', normalized_opt_actions)
                # print('normalized_human_actions:', normalized_human_actions)

                # update the relevant mdp_parameter with the normalized versions of the trajectories
                if not opt_response_flag:
                    response["params"]["normalized_opt_actions"] = normalized_opt_actions
                else:
                    response["params"]["normalized_opt_actions"] = normalized_human_actions
                    response["params"]["opt_actions"] = last_test_trial.moves
                
                response["params"]["normalized_human_actions"] = normalized_human_actions
                response["params"]["human_actions"] = last_test_trial.moves
                response["params"]["tag"] = -2


            print('user id:', current_user.id, 'data movement: ', data["movement"], 'current user iteration:', current_user.iteration, 'current user round:', current_user.round, 'current user interaction type:', current_user.interaction_type, 'next already completed:', next_already_completed)

            flag_modified(current_user, "last_iter_in_round")
            flag_modified(current_user, "last_test_in_round")
            flag_modified(current_user, "iteration")
            flag_modified(current_user, "round")
            flag_modified(current_user, "interaction_type")

            update_database(current_user, str(current_user.username) + ". User progress in settings")
            ########################

            
            # check if the next page should be able to go back
            go_prev = True
            print('current_user.round:', current_user.round, 'current_user.iteration:', current_user.iteration, 'current_user.interaction_type:', current_user.interaction_type, 'next already_completed:', next_already_completed)
            # if (current_user.round == 1 and current_user.iteration==1 and current_user.interaction_type == "demo") or ("test" in current_user.interaction_type and not already_completed) or (current_user.interaction_type == "survey"):
            if (current_user.round == 1 and current_user.iteration==1 and current_user.interaction_type == "demo") or (current_user.interaction_type == "survey") or (current_user.interaction_type == "answer"):
                go_prev = False
            if ('test' in current_user.interaction_type):
                go_prev = False

            print('Go prev for this iteration:', go_prev)

            debug_string = ""
            print('Updated round:', updated_round, 'Next round:', next_round, 'Current round:', current_round)

            N_demos = len([x for x in updated_round.round_info if x["interaction type"] == "demo"])
            N_diagnostic_tests = len([x for x in updated_round.round_info if x["interaction type"] == "diagnostic test"])
            
            if current_kc_id != next_kc_id:
                first_demo_string = f"Moving onto a new game lesson."
            else:
                first_demo_string = f"Not everyone in your group learned the previous game lesson. Repeating it again."
            
            print('current_kc_id:', current_kc_id, 'next_kc_id:', next_kc_id, 'first_demo_string:', first_demo_string)
            print('current_user.interaction_type: ', current_user.interaction_type, 'current_user.iteration: ', current_user.iteration)

            lesson_string = ''
            iteration_id = ''
            N_iterations = ''
            debug_string = ''
            lesson_id = current_kc_id + 1
            if current_user.interaction_type == "demo" and current_user.iteration == 1:
                # debug_string = first_demo_string
                lesson_string = first_demo_string
                iteration_id = 1
                N_iterations = N_demos
                lesson_id = next_kc_id + 1
            elif current_user.interaction_type == "demo" and current_user.iteration > 1:
                # debug_string = f"Lesson ={current_kc_id}. Demo no. {current_user.iteration}/{N_demos}. <br>"
                iteration_id = current_user.iteration
                N_iterations = N_demos
                lesson_id = current_kc_id + 1
            elif current_user.interaction_type == "diagnostic test":
                iteration_id = int((current_user.iteration - N_demos)/2) + 1
                N_iterations = N_diagnostic_tests
                lesson_id = current_kc_id + 1
                # debug_string = f"Lesson ={current_kc_id}. Test no. {iteration_id}/{N_diagnostic_tests}. <br>"
            elif current_user.interaction_type == "answer":
                # debug_string = f"Here is the answer to the previous diagnostic test. <br> Current learning session ={current_user.round}. <br> Game instance in current round = {current_user.iteration}/{len(updated_round.round_info)}"
                debug_string = ''    
                lesson_id = current_kc_id + 1            
            elif current_user.interaction_type == "final test":
                iteration_id = current_user.iteration
                N_iterations = len(updated_round.round_info)
                # debug_string = f"Final tests for this game. <br> Test no. {current_user.iteration}/{len(updated_round.round_info)}."

            response["debug string"] = ''
            response["last iteration"] = current_user.last_iter_in_round
            response["last test"] = current_user.last_test_in_round
            response["interaction type"] = current_user.interaction_type
            response["already completed"] = next_already_completed
            response["go prev"] = go_prev
            response["iteration"] = iteration_id
            response["total iterations"] = N_iterations
            response["lesson id"] = lesson_id
            response["lesson string"] = lesson_string
            if current_group.status == "Domain teaching completed" and current_user.interaction_type=="final test" and current_user.last_iter_in_round:
                response["domain completed"] = True
            else:
                response["domain completed"] = False

            print('Settings response:', response)
        
        # Ensure that user is in the correct room
        print('Ensuring user is in room:', room_name)
        join_room(room_name)

        socketio.emit("settings configured", response, to=request.sid)


    #########################




@app.route("/sign_consent", methods=["GET", "POST"])
@login_required
def sign_consent():
    print('Entering sign consent')
    current_user.consent = 1
    flag_modified(current_user, "consent")
    update_database(current_user, str(current_user.username) + ". User consent")
    # need to return json since this function is called on button press
    # which replaces the current url with new url
    # sorry trying to work within existing infra
    print('Url for introduction:', url_for("introduction"))
    return {"url":url_for("introduction")}

@app.route("/pass_trajectories", methods=["GET", "POST"])
@login_required
def pass_trajectories():
    final_data = request.get_json()
    print(final_data)
    return json.dumps(send_signal(final_data["opt_response"]))



@socketio.on("group comm")
def group_comm(data):
    data["user"] = current_user.username
    socketio.emit("incoming group data", data, to='room_'+ str(current_user.group), include_self=False)

@app.route("/intro", methods=["GET", "POST"])
@login_required
def intro():
    print(send_signal(True))
    # form = LoginForm()
    # if form.validate_on_submit():
    #     user = User.query.filter_by(username=form.username.data).first()
    #
    #     if user is None:
    #         user = User(username=form.username.data)
    #         user.set_num_trials_completed(0)
    #         user.set_completion(0)
    #         user.set_attention_check(-1)
    #
    #         # Change depending on the study type.
    #         cond = user.set_condition("in_person" if IS_IN_PERSON else "online")
    #         code = user.()
    #
    #         db.session.add(user)
    #
    #         cond.users.append(user)
    #         cond.count += 1
    #
    #         db.session.commit()
    #
    #     login_user(user)
    #     next_page = request.args.get("next")
    #     if not next_page or url_parse(next_page).netloc != "":
    #         next_page = url_for("index")
    #     return redirect(next_page)
    #
    # render_template("login.html", title="Sign In", form=form)

    # just testing out my code
    # return render_template("intro.html")
    return render_template("augmented_taxi2.html")


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
        procedure = "This study may take up to 30 minutes."
    return render_template("consent.html", title="Consent", form=form, procedure=procedure)

@app.route("/login", methods=["GET", "POST"])
def login():
    print('Index url: ', url_for("index", _external=True))
    print('User is authenticated?', current_user.is_authenticated)
    
    if current_user.is_authenticated:
        # next_page = request.args.get("next")

        # if next_page == "/":
        #     # Redirect to /flask_closed_loop_teaching/ instead of root
        #     next_page = "/flask_closed_loop_teaching/"

        # return redirect(next_page or url_for("index"))
        return redirect(url_for("index"))
    
    
    form = LoginForm()
    
    print('form validate:', form.validate_on_submit())
    print('Form errors:', form.errors)


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
            db.session.add(user)

            # cond.users.append(user)
            # cond.count += 1

            db.session.commit()

        print('Logging in user:', user)
        login_user(user)
        print(f"User is authenticated after login? {current_user.is_authenticated}")
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        
        print('Next page url:', next_page)
        
        # if next_page == '/':
        #     print('Next page is / so redirecting to index')
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
    print(form.errors)

    if form.is_submitted():
        print("submitted")
    

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
    
    print(form.errors)
    return render_template(template,
                            methods=["GET", "POST"],
                            form=form,
                            round=round)



####################  Functions   ####################


def update_learner_models_from_tests(params, current_group, current_round) -> tuple:
    
    print('Updating learner models based on tests...')

    # current_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()
    # current_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()

    domain_id = current_group.curr_progress
    if domain_id == "domain_1":
        domain = current_group.domain_1
    elif domain_id == "domain_2":
        domain = current_group.domain_2
    else:
        print('Domain id:', domain_id)
        raise ValueError('Domain not found')
    
    current_domain = db.session.query(DomainParams).filter_by(domain_name=domain).first()
    print('All domains:',  db.session.query(DomainParams).all())

    
    teaching_uf = params['teacher_learning_factor']
    model_type = params['teacher_update_model_type']
    
    # current models
    ind_member_models = copy.deepcopy(current_group.ind_member_models)
    group_union_model = copy.deepcopy(current_group.group_union_model)
    group_intersection_model = copy.deepcopy(current_group.group_intersection_model)
    num_members = copy.deepcopy(current_group.num_members)
    num_active_members = copy.deepcopy(current_group.num_active_members)
    active_member_ids = [idx for idx, status in enumerate(current_group.members_statuses) if status == 'joined']


    print('Before updating learner models from tests for constraints...', current_round.min_BEC_constraints_running)
    find_prob_particles(ind_member_models, current_group.members_statuses, current_round.min_BEC_constraints_running)

    group_knowledge = current_round.group_knowledge[0]
    kc_id = current_round.kc_id

    group_usernames = retrieve_group_usernames(current_group)
    group_test_constraints = []
    joint_constraints = []
    knowledge_to_update = []
    
    for username in group_usernames:
        group_code = db.session.query(User).filter_by(username=username).first().group_code
        print('Username:', username, 'Group:', current_user.group, 'Group code:', group_code, 'round:', current_user.round, 'member statuses:', current_group.members_statuses)
        tests = db.session.query(Trial).filter_by(group=current_user.group, group_code=group_code, round=current_user.round, interaction_type="diagnostic test").all()
        
        update_model_flag = False
        if current_group.members_statuses[group_code] == 'joined':
            update_model_flag = True
        
        if update_model_flag:
            test_constraints = []
            for test in tests:
                cur_test_constraints = get_test_constraints(domain, test, current_domain.traj_record, current_domain.traj_features_record)
                test_constraints.extend(cur_test_constraints)
                print('Test constraints:', test_constraints)    
            group_test_constraints.append(test_constraints)
            print('Group test constraints so far:', group_test_constraints)

            min_test_constraints = remove_redundant_constraints(test_constraints, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the unit's demonstrations
            print('Min test constraints:', min_test_constraints)
            
            # update learner models
            print('Updating learner models for member:', group_code, 'with constraints:', min_test_constraints)
            ind_member_models[group_code].update(min_test_constraints, teaching_uf, model_type, params)

            joint_constraints.append(min_test_constraints)

    group_test_constraints_expanded = [item for sublist in group_test_constraints for item in sublist]
    print('Group test constraints expanded:', group_test_constraints_expanded)
    print('Joint constraints:', joint_constraints)

    # update group_union_model and group_intersection_model
    group_min_constraints = remove_redundant_constraints(group_test_constraints_expanded, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the group's demonstrations
    
    print('Updating common model with constraints:', group_min_constraints)
    group_intersection_model.update(group_min_constraints, teaching_uf, model_type, params) # common belief model
    
    print('Updating joint model with constraints:', joint_constraints)
    group_union_model.update_jk(joint_constraints, teaching_uf, model_type, params)  # joint belief model

    
    # update team knowledge
    print('Update team knowledge for num members:', num_members)
    updated_group_knowledge = update_team_knowledge(group_knowledge, kc_id, True, group_test_constraints, num_active_members, active_member_ids, params['mdp_parameters']['weights'], params['step_cost_flag'], knowledge_to_update = 'all')


    print('Updated group knowledge:', updated_group_knowledge)

    ind_member_models_pos_current = [ind_member_models[i].positions for i in range(num_members)]
    ind_member_models_weights_current = [ind_member_models[i].weights for i in range(num_members)]

    # add the updated round information to the database
    current_round_tests_updated = Round(group_id=current_round.group_id, 
                                    round_num=current_round.round_num,
                                    domain = current_group.curr_progress,
                                    members_statuses=current_group.members_statuses,
                                    kc_id = kc_id,
                                    min_KC_constraints = current_round.min_KC_constraints,
                                    round_info=current_round.round_info,
                                    status="tests_updated",
                                    variable_filter=current_round.variable_filter,
                                    nonzero_counter=current_round.nonzero_counter,
                                    min_BEC_constraints_running=current_round.min_BEC_constraints_running,
                                    prior_min_BEC_constraints_running=current_round.prior_min_BEC_constraints_running,
                                    visited_env_traj_idxs=current_round.visited_env_traj_idxs,
                                    ind_member_models_pos = current_round.ind_member_models_pos.append(ind_member_models_pos_current),
                                    ind_member_models_weights = current_round.ind_member_models_weights.append(ind_member_models_weights_current),
                                    group_union_model_pos = current_round.group_union_model_pos.append(group_union_model.positions),
                                    group_union_model_weights = current_round.group_union_model_weights.append(group_union_model.weights),
                                    group_intersection_model_pos = current_round.group_intersection_model_pos.append(group_intersection_model.positions),
                                    group_intersection_model_weights = current_round.group_intersection_model_weights.append(group_intersection_model.weights),
                                    group_knowledge = [updated_group_knowledge]
                                    )

    update_database(current_round_tests_updated, 'Update round data from tests')



    print('After updating learner models from tests for constraints...', current_round_tests_updated.min_BEC_constraints_running)
    find_prob_particles(ind_member_models, current_group.members_statuses, current_round_tests_updated.min_BEC_constraints_running)


    print('Adding particle filter models to group')
    current_group.ind_member_models = copy.deepcopy(ind_member_models)
    current_group.group_union_model = copy.deepcopy(group_union_model)
    current_group.group_intersection_model = copy.deepcopy(group_intersection_model)
    current_group.status = "upd_tests"  #reset status to generate demos

    flag_modified(current_group, "ind_member_models")
    flag_modified(current_group, "group_union_model")
    flag_modified(current_group, "group_intersection_model")   
    flag_modified(current_group, "status")

    update_database(current_group, 'Update group learner models from tests')


    # return ind_member_models, group_union_model, group_intersection_model



def retrieve_next_round(params, current_group) -> dict:
    """
    retrieves necessary environment variables for displaying the next round to
    the client based on database entries. gets called on the condition that 
    player group_code == A, since we don't want to do computation more than once

    data in: none (retrieves test moves from database)
    data out: environment variables for next round
    side effects: none  
    """ 
    from app import pool, lock

    # group = current_user.group
    # current_group = db.session.query(Group).filter_by(id=group).order_by(Group.id.desc()).first()

    
    round = current_user.round 

    domain_id = current_group.curr_progress
    if domain_id == "domain_1":
        domain = current_group.domain_1
    elif domain_id == "domain_2":
        domain = current_group.domain_2
    else:
        print('Domain id:', domain_id)
        raise ValueError('Domain not found')
    
    print('round:', round, 'Group status:', current_group.status, 'Group experimental condition:', current_group.experimental_condition, 'Group members:', current_group.members)

    current_group.status = "gen_demos"
    flag_modified(current_group, "status")
    update_database(current_group, 'Group status: gen_demos; in retrieve next round')

    print('Member statuses retrive next round:', current_group.members_statuses)
    
    print('Group experimental condition:', current_group.experimental_condition, 'Group status:', current_group.status, 'Group id:', current_group.id, 'Group members:', current_group.members)
    experimental_condition = current_group.experimental_condition
    members_statuses = current_group.members_statuses
    active_member_ids = [idx for idx, status in enumerate(members_statuses) if status == 'joined']
    
    vars_filename = date.today().strftime("%Y-%m-%d") + '_group_' + str(current_user.group)
    new_round_for_var_filter = False

    # load previous round data
    if round > 0:
        print('current_user.curr_progress:', current_user.curr_progress, 'current_group prgress:', current_group.curr_progress, 'round:', round, 'group:', current_user.group)
        prev_models = db.session.query(Round).filter_by(group_id=current_group.id, domain=current_group.curr_progress, round_num=round).order_by(Round.id.desc()).first()
        print('Previous round:', prev_models.id, prev_models.round_num, prev_models.status, prev_models.group_id, prev_models.group_knowledge, prev_models.kc_id, prev_models.min_KC_constraints)
        
        all_prev_rounds = db.session.query(Round).filter_by(group_id=current_group.id, domain=current_group.curr_progress).all()
        print('All previous rounds...')
        for prev_round in all_prev_rounds:
            print('Previous round:', prev_round.id, prev_round.round_num, prev_round.status, prev_round.group_id, prev_round.group_knowledge, prev_round.kc_id, prev_round.min_KC_constraints)
        
        group_union_model = copy.deepcopy(current_group.group_union_model)
        group_intersection_model =  copy.deepcopy(current_group.group_intersection_model)
        ind_member_models =  copy.deepcopy(current_group.ind_member_models)

        variable_filter = prev_models.variable_filter
        nonzero_counter = prev_models.nonzero_counter
        print('Nonzero counter:', nonzero_counter, 'round:', round)
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
        
        print('nonzero counter:', nonzero_counter, 'round:', 0, 'variable filter:', variable_filter)

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

            db.session.add(curr_domain_params)
            db.session.commit()


        # create a directory for the group
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(current_dir, 'group_teaching', 'results', params['data_loc']['BEC']))
        
        full_path_filename = base_dir + '/ind_sim_trials/' + vars_filename

        if not os.path.exists(full_path_filename):
            print('Creating folder for this run: ', full_path_filename)
            os.makedirs(full_path_filename, exist_ok=True)
    


    #check if unit knowledge is reached and update variable filter
    if round > 0:
        print('Round:', round, 'Group knowledge:', group_knowledge, 'min_KC_constraints:', min_KC_constraints, 'kc_id:', kc_id, 'active_member_ids:', active_member_ids)
        unit_learning_goal_reached_flag = check_unit_learning_goal_reached(params, group_knowledge, active_member_ids, min_KC_constraints, kc_id)
    else:
        unit_learning_goal_reached_flag = False
    
    print('Current group sttaus:', current_group.status)
    if (current_group.status != "Domain teaching completed"):

        print('Current variable filter: ', variable_filter, ' with nonzero counter: ', nonzero_counter)
        if unit_learning_goal_reached_flag:
            variable_filter, nonzero_counter = update_variable_filter(nonzero_counter)
            print('Updated variable filter: ', variable_filter, ' with nonzero counter: ', nonzero_counter)
            kc_id += 1
            new_round_for_var_filter = True

            # update prior min BEC constraints
            prior_min_BEC_constraints_running = copy.deepcopy(min_BEC_constraints_running)
        else:
            new_round_for_var_filter = False

            # update BEC constraints
            min_BEC_constraints_running = copy.deepcopy(prior_min_BEC_constraints_running)
        
        print('min BEC constraints:', min_BEC_constraints_running, 'prior min BEC constraints:', prior_min_BEC_constraints_running)
        
        # check if teaching is complete
        teaching_complete_flag = False
        if not np.any(variable_filter) and unit_learning_goal_reached_flag:
            teaching_complete_flag = True

        # # Debug for having only one round
        # if round > 0:
        #     teaching_complete_flag = True


        print('Teaching complete flag before generating demos:', teaching_complete_flag)


        # get demonstrations and tests for this round
        if not teaching_complete_flag:
            ind_member_models_demo_gen = copy.deepcopy(ind_member_models)
            group_union_model_demo_gen = copy.deepcopy(group_union_model)
            group_intersection_model_demo_gen = copy.deepcopy(group_intersection_model)

            args = domain, vars_filename, group_union_model_demo_gen, group_intersection_model_demo_gen, ind_member_models_demo_gen, members_statuses, experimental_condition, variable_filter, nonzero_counter, new_round_for_var_filter, min_BEC_constraints_running, visited_env_traj_idxs, pool, lock    
            min_KC_constraints, demo_mdps, test_mdps, experimental_condition, variable_filter, nonzero_counter, min_BEC_constraints_running, visited_env_traj_idxs, teaching_complete_flag = generate_demos_test_interaction_round(args)
            round_status = "demo_tests_generated"
            games = list()
            for i in range(len(demo_mdps)):
                games.append({"interaction type": "demo", "params": demo_mdps[i]})

            for i in range(len(test_mdps)):
                games.append({"interaction type": "diagnostic test", "params": test_mdps[i]})
        else:
            print('Adding final tests for this round...')
            round_status = "final_tests_generated"
            test_difficulty = ['low', 'medium', 'high']
            games = list()

            if domain == 'at':
                mdp_class = 'augmented_taxi2'
            elif domain == 'sb':
                mdp_class = 'skateboard2'
            
            final_test_id = 1
            final_tests_to_add = [8, 12] # indices of final tests to add (one for each difficulty level)
            
            for td in test_difficulty:
                for mdp_list in jsons[mdp_class]["final test"][td]:
                    for mdp_dict in mdp_list:
                        if final_test_id in final_tests_to_add:
                            games.append({"interaction type": "final test", "params": mdp_dict})
                        final_test_id += 1

            # add a survey at the end
            # games.append({"interaction type": "survey", "params": {}})

            print('Added ', len(games), ' final tests for this round...')
            


        games_extended = []
        for game in games:
            games_extended.append(game)
            if game["interaction type"] == "diagnostic test":
                new_game = copy.deepcopy(game)
                new_game["interaction type"] = "answer"
                new_game["params"]["tag"] = -1  
                games_extended.append(new_game)
        
        for game in games_extended:
            print('Extended list. Interaction type: ', game["interaction type"])



        # add models to group database
        print('Adding particle filter models to group')
        current_group.ind_member_models = copy.deepcopy(ind_member_models)
        current_group.group_union_model = copy.deepcopy(group_union_model)
        current_group.group_intersection_model = copy.deepcopy(group_intersection_model)

        flag_modified(current_group, "ind_member_models")
        flag_modified(current_group, "group_union_model")
        flag_modified(current_group, "group_intersection_model")

        if teaching_complete_flag:
            current_group.status = "Domain teaching completed"
            flag_modified(current_group, "status")

        update_database(current_group, 'PF models, teaching status updated')


        # add new round to round database
        ind_member_models_pos = [ind_member_models[i].positions for i in range(len(ind_member_models))]
        ind_member_models_weights = [ind_member_models[i].weights for i in range(len(ind_member_models))]

        print('Group curr progress:', current_group.curr_progress)
        new_round = Round(group_id=current_group.id, 
                        domain = current_group.curr_progress,
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
                        group_knowledge = [group_knowledge])
                        
        update_database(new_round, 'New round data generated')

        return games_extended

    else:
        return list()



def update_learner_models_from_demos(params, current_group, next_round) -> tuple:

    print('Updating learner models based on demos...')

    teacher_uf = params['teacher_learning_factor']
    model_type = params['teacher_update_model_type']

    # current_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()

    # print('Current user group:', current_user.group, 'Domain:', current_group.curr_progress, 'Round:',  current_user.round)
    # next_round_id = current_user.round+1
    # updated_current_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=current_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()
    # print('Next round: ', next_round)

    print('Current user group:', current_user.group, 'Domain:', current_group.curr_progress, 'Round:',  current_user.round, 'Next round:', next_round)
    
    print('Before updating demos for constraints...', next_round.min_BEC_constraints_running)
    find_prob_particles(current_group.ind_member_models, current_group.members_statuses, next_round.min_BEC_constraints_running)

    # current models
    ind_member_models = copy.deepcopy(current_group.ind_member_models)
    group_union_model = copy.deepcopy(current_group.group_union_model)
    group_intersection_model = copy.deepcopy(current_group.group_intersection_model)

    # # DEBUG
    # for ind_member_model in ind_member_models:
    #     # fig, ax = plt.figure()
    #     ind_member_model.plot()
    #     # plt.show()
    # group_union_model.plot()
    # # plt.show()
    # group_intersection_model.plot()
    # # plt.show()

    # update the models based on the demos
    demo_mdps = [game["params"] for game in next_round.round_info if game["interaction type"] == "demo"]

    print("Len Demo MDPS:", len(demo_mdps))
    
    constraints = []
    for demo_mdp in demo_mdps:
        constraints.extend(demo_mdp['constraints'])

    print('Constraints from demos: ', constraints)

    min_KC_constraints = remove_redundant_constraints(constraints, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the unit's demonstrations
            
    
    print('Constraints from demos: ', constraints, 'min_demo_constraints:', min_KC_constraints)
    
    # update the models
    joint_constraints = []
    ind_member_models_pos_current = []
    ind_member_models_weights_current  = []
    for i in range(len(ind_member_models)):
        if current_group.members_statuses[i] == 'joined':
            print('Updating model for member:', i, 'with constraints:', min_KC_constraints)
            ind_member_models[i].update(min_KC_constraints, teacher_uf, model_type, params)
            joint_constraints.append(min_KC_constraints)

            ind_member_models_pos_current.append(ind_member_models[i].positions)
            ind_member_models_weights_current.append(ind_member_models[i].weights)

    # update the team models
    print('Updating common models... with constraints:', min_KC_constraints)
    group_intersection_model.update(min_KC_constraints, teacher_uf, model_type, params)  # common belief model
    print('Updated group belief model with constraints:', joint_constraints)
    group_union_model.update_jk(joint_constraints, teacher_uf, model_type, params) # joint belief model

    print('After updating demos for constraints...', next_round.min_BEC_constraints_running)
    find_prob_particles(ind_member_models, current_group.members_statuses, next_round.min_BEC_constraints_running)
    
    # # DEBUG
    # for ind_member_model in ind_member_models:
    #         ind_member_model.plot()
    #         # plt.show()
    # group_union_model.plot()
    # # plt.show()
    # group_intersection_model.plot()
    # # plt.show()


    # add the updated round information to the database
    current_round_demo_updated = Round(group_id=next_round.group_id, 
                                    domain = current_group.curr_progress,
                                    round_num=next_round.round_num,
                                    kc_id = next_round.kc_id,
                                    min_KC_constraints = min_KC_constraints,
                                    members_statuses=current_group.members_statuses,
                                    round_info=next_round.round_info,
                                    status="demos_updated",
                                    variable_filter=next_round.variable_filter,
                                    nonzero_counter=next_round.nonzero_counter,
                                    min_BEC_constraints_running=next_round.min_BEC_constraints_running,
                                    prior_min_BEC_constraints_running=next_round.prior_min_BEC_constraints_running,
                                    visited_env_traj_idxs=next_round.visited_env_traj_idxs,
                                    ind_member_models_pos = next_round.ind_member_models_pos.append(ind_member_models_pos_current),
                                    ind_member_models_weights = next_round.ind_member_models_weights.append(ind_member_models_weights_current),
                                    group_union_model_pos = next_round.group_union_model_pos.append(group_union_model.positions),
                                    group_union_model_weights = next_round.group_union_model_weights.append(group_union_model.weights),
                                    group_intersection_model_pos = next_round.group_intersection_model_pos.append(group_intersection_model.positions),
                                    group_intersection_model_weights = next_round.group_intersection_model_weights.append(group_intersection_model.weights),
                                    group_knowledge = next_round.group_knowledge
                                    )
    
    update_database(current_round_demo_updated, 'Update learner models from demos')
       

    print('Updating models to group')
    current_group.ind_member_models = copy.deepcopy(ind_member_models)
    current_group.group_union_model = copy.deepcopy(group_union_model)
    current_group.group_intersection_model = copy.deepcopy(group_intersection_model)
    current_group.status = "upd_demos"

    flag_modified(current_group, "ind_member_models")
    flag_modified(current_group, "group_union_model")
    flag_modified(current_group, "group_intersection_model")   
    flag_modified(current_group, "status")

    update_database(current_group, 'Update learner models from demos')


    # return ind_member_models, group_union_model, group_intersection_model



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
    print('Test MDP params:', prev_mdp_parameters)
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


def update_database(updated_data, update_type):

    try:
        db.session.add(updated_data)
        db.session.flush()
        db.session.commit()
        print("Flush and Commit successful. Remember to commit at the end.", update_type )
    except Exception as e:
        print(f"Error during commit: {e}.", update_type)
        db.session.rollback()

    if update_type == 'Update learner models from tests':
        # Verify if the round is present after the commit
        all_rounds = db.session.query(Round).filter_by(group_id=updated_data.group_id, round_num=updated_data.round_num).order_by(Round.id.desc()).all()
        for rnd in all_rounds:
            print('Round info: ', rnd.id, rnd.group_id, rnd.round_num, rnd.status, rnd.group_knowledge, rnd.kc_id, rnd.min_KC_constraints)


def get_domain():
    # get game domain
    curr_domain = current_user.curr_progress[-1]  # just get last string

    if curr_domain == "1":
        domain = current_user.domain_1
    elif curr_domain == "2":
        domain = current_user.domain_2
    else:
        domain = ""

    if domain == 'at':
        mdp_class = 'augmented_taxi2'
    elif domain == 'sb':
        mdp_class = 'skateboard2'

    return domain, mdp_class


def add_survey_data(domain, data):
    # add survey data to database
    dom = Domain(
            user_id = current_user.id,
            domain_name = domain,
            attn1 = int(data["attn1"]),
            attn2 = int(data["attn2"]),
            attn3 = int(data["attn3"]),
            use1 = int(data["use1"]),
            use2 = int(data["use2"]),
            use3 = int(data["use3"]),
            short_answer = data["short answer"]
        )
    db.session.add(dom)
    db.session.commit()


def add_trial_data(domain, data):

    # if len(data["user input"]) !=0:
    print('Adding trial data to database...', ' user id: ', current_user.id, 'round:', current_user.round, 'iteration:', current_user.iteration)

    trial = Trial(
        user_id = current_user.id,
        group_code = current_user.group_code,
        group = current_user.group,
        domain = domain,
        round = current_user.round,
        interaction_type = current_user.interaction_type,
        iteration = current_user.iteration,
        subiteration = current_user.subiteration,
        likert = int(data["interaction survey"]),
        moves = data["user input"]["moves"],
        coordinates = data["user input"]["agent_history_nonoffset"],
        is_opt_response = data["user input"]["opt_response"],
        mdp_parameters = data["user input"]["mdp_parameters"],
        duration_ms = data["user input"]["simulation_rt"],
        human_model = None, #TODO: later?,
        num_visits = 1,
    )
    db.session.add(trial)

    db.session.commit()


def update_domain(current_group):

    # update group variables
    if current_group.curr_progress == "domain_1":
        current_group.curr_progress = "domain_2"
        current_group.status = "next_domain"
        domain = current_group.domain_2

    elif current_group.curr_progress == "domain_2":
        current_group.curr_progress = "study_end"
        current_group.status = "study_end"
        domain = current_group.domain_2

    else:
        RuntimeError("Domain not found")

    print('Updated domain:', domain)

    flag_modified(current_group, "curr_progress")
    flag_modified(current_group, "status")
    update_database(current_group, 'New domain group db: ' + current_group.curr_progress)

    # update user variables
    current_user.curr_progress = current_group.curr_progress
    current_user.round = 0
    current_user.iteration = 1
    current_user.interaction_type = "demo"

    flag_modified(current_user, "curr_progress")
    flag_modified(current_user, "round")
    flag_modified(current_user, "iteration")
    flag_modified(current_user, "interaction_type")
    update_database(current_user, 'New domain user db: ' + current_user.curr_progress)

    if domain == 'at':
        mdp_class = 'augmented_taxi2'
    elif domain == 'sb':
        mdp_class = 'skateboard2'
    else:
        print('Domain:', domain)
        raise ValueError('Domain not found')


    return domain, mdp_class


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
    print('Prob of learning, models: ', prob_models_array, 'Model ids: ', model_ids)


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


    normalized_opt_actions, normalized_human_actions = normalize_trajectories(opt_locations_tuple, opt_actions, human_locations_tuple, human_actions)

    return normalized_opt_actions, normalized_human_actions

