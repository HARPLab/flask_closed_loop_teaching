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
from .group_teaching.codes.user_study.user_study_utils import generate_demos_test_interaction_round, initialize_teaching, obtain_constraint
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


    
@app.route("/", methods=["GET", "POST"])
# @app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    online_condition_id = current_user.online_condition_id
    current_condition = db.session.query(OnlineCondition).get(online_condition_id)

    completed = True if current_user.study_completed == 1 else False

    current_user.loop_condition = "debug"
    db.session.add(current_user)
    db.session.commit()

    return render_template("index.html",
                           title="Home Page",
                           completed=completed,
                           code=current_user.code)

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


# @socketio.on("disconnect")
# def handle_disconnect():
#     print(request.sid + " disconnected?")
#     leave_group()


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
        preamble = ''' <h3>Feel free to play around in the game below and get used to the controls. </h3> <h4>You can click the continue button whenever you feel ready to move on.</h4><br>
        <h4>If you accidentally take a wrong action, you may reset the simulation and start over.</h4><h4>A subset of the following keys will be available to control Chip in each game:</h4><br>
        '''
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
        "<h3>As previously mentioned, the task in this practice game is the following: </h3> <br>" +
        "<table class=\"center\"><tr><th>Task</th><th>Sample sequence</th></tr><tr><td>Dropping off the green pentagon at the purple star</td><td><img src = 'static/img/sandbox_dropoff1.png' width=\"75\" height=auto /><img src = 'static/img/arrow.png' width=\"30\" height=auto /><img src = 'static/img/sandbox_dropoff2.png' width=\"75\" height=auto /></td></tr></table> <br>" +
        "<h3>Each game will consist of <b>actions that change your energy level</b> differently. In this game, the following actions affect your energy:</h3> <br>" +
        "<table class=\"center\"><tr><th>Action</th><th>Sample sequence</th><th>Energy change</th></tr>" +
        "<tr><td>Moving through the orange diamond</td><td><img src = 'static/img/sandbox_diamond1.png' width=\"225\" height=auto /><img src = 'static/img/arrow.png' width=\"30\" height=auto /><img src = 'static/img/sandbox_diamond2.png' width=\"225\" height=auto /> <img src='static/img/arrow.png' width=\"30\" height=auto /><img src ='static/img/sandbox_diamond3.png' width=\"225\" height=auto/> <td>+10%</td></tr>" +
        "<tr><td>Any action that you take (e.g. moving right)</td><td><img src = 'static/img/right1.png' width=\"150\" height=auto /><img src = 'static/img/arrow.png' width=\"30\" height=auto /><img src = 'static/img/right2.png' width=\"150\" height=auto /><td>-5%</td></tr></table> <br>" +
        "<h3><b>Pick up the green pentagon</b> and <b>drop it off at the purple star</b> with the <b>maximum possible energy remaining</b>. </h3> " +
        "<h4>You should end with 40% energy left (you won't be able to move if energy falls to 0%). <u>You will have 3 chances to get it right to continue on with the study!</u></h4>" +
        "<h4>Note: Since this is practice, we have revealed each actions's effect on Chip's energy and also provide a running counter of Chip's current energy level below.</h4> <br>")
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

    preamble = ("<h3>Good job on completing the practice game! Let's now head over to the three main games and <b>begin the real study</b>.</h3><br>" +
            "<h3>In these games, you will <b>not</b> be told how each action changes Chip's energy level.</h3><br>" +
            "For example, note the '???' in the Energy Change column below. <table class=\"center\"><tr><th>Action</th><th>Sample sequence</th><th>Energy change</th></tr><tr><td>Any action that you take (e.g. moving right)</td><td><img src = 'static/img/right1.png' width=\"150\" height=auto /><img src = 'static/img/arrow.png' width=\"30\" height=auto /><img src = 'static/img/right2.png' width=\"150\" height=auto /><td>???</td></tr></table> <br>" +
            "<h3>Instead, you will have to <u>figure that out</u> and subsequently the best strategy for completing the task while minimizing Chip's energy loss <u>by observing Chip's demonstrations!</u></h3><br>")
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
    old_group = db.session.query(Group).order_by(Group.id.desc()).first()
    num_active_members = old_group.num_active_members
    
    params = get_mdp_parameters("")
    print('Join group function. Current user group: ', current_user.group, 'num_active_members:', num_active_members)
    print('Old group:', 'Group id:', old_group.id, 'Group members:', old_group.members, 'Group mem ids:', old_group.member_user_ids, 'Group status:', old_group.members_statuses, 'Group experimental condition:', old_group.experimental_condition)
    
    if not current_user.group: # if no group yet, join one
        
        if num_active_members == 0 or num_active_members == params['team_size']: # if group is full or empty, create a new group
            print('No group yet.. Creating one...')
            current_user.group = 1 if old_group.id is None else old_group.id + 1
            new_group_entry = Group(
                # experimental_condition=cond_list[current_user.group % 4],
                experimental_condition=cond_list[0],
                status = "Experiment_started",
                member_user_ids = [None for i in range(params['team_size'])],
                members = [None for i in range(params['team_size'])],
                members_statuses = ["not joined" for i in range(params['team_size'])],
                num_active_members = 0,
                num_members = params['team_size'],
                members_EOR = [False for i in range(params['team_size'])],
                members_last_test = [False for i in range(params['team_size'])],
                )
                        
            # new_group = db.session.query(Group).order_by(Group.id.desc()).first()

            _, current_user.group_code, current_user.domain_1, current_user.domain_2 = new_group_entry.groups_push(current_user.username, current_user.id)
            print('New group:', 'Group id:', new_group_entry.id, 'Group members:', new_group_entry.members, 'Active members:', new_group_entry.num_active_members, 'Group mem ids:', new_group_entry.member_user_ids, 'Group status:', new_group_entry.members_statuses, 'Group experimental condition:', new_group_entry.experimental_condition)
            update_database(new_group_entry, 'Member to new group')
            num_active_members = 1
        else:
            print('Adding to existing group')
            _, current_user.group_code, current_user.domain_1, current_user.domain_2 = old_group.groups_push(current_user.username, current_user.id)
            current_user.group = old_group.id
            num_active_members += 1
            print('Old group:', 'Group id:', old_group.id, 'Group members:', old_group.members, 'Group mem ids:', old_group.member_user_ids, 'Group status:', old_group.members_statuses, 'Group experimental condition:', old_group.experimental_condition)

            update_database(old_group, 'Member to existing group')
    
    # TODO: Rejoining not implemented properly
    # else: # if rejoining, get added to the same room
    #     print('Rejoining group')
    #     rejoined_group = db.session.query(Group).filter_by(id=current_user.group).first()
    #     # TODO: Handling the rejoining case
    #     num_active_members = rejoined_group.num_active_members + 1
    #     # db.session.add(rejoined_group)
    #     db.session.commit()

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

@socketio.on("join group v2")
def join_group_v2():
    join_room('room_'+ str(current_user.group))
    socketio.emit("member joined again", {"user code": current_user.group_code}, to='room_'+ str(current_user.group))
    return

@socketio.on("leave group temp")
def leave_group_temp():
    socketio.emit("member left temp", {"member code": current_user.group_code}, to='room_'+ str(current_user.group))
    return

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
    curr_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()
    _ = curr_group.groups_remove(current_user.username)

    update_database(curr_group, 'Member left group')
    

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
    elif current_user.curr_progress == "domain 1":
        current_user.set_curr_progress("domain 2")
        socketio.emit("next domain is", {"domain": current_user.domain_2}, to=request.sid)
    elif current_user.curr_progress == "domain 2":
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

    # update database with iteration data
    if current_user.interaction_type == "survey":
        add_survey_data(domain, data)
        # end study
    else:
        
        response = {}
        curr_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()
        curr_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()

        print('Current user group: ', current_user.group, 'Domain: ', curr_group.curr_progress, 'Round_num:', current_user.round, 'Curr_round:', curr_round, current_user.iteration, current_user.interaction_type)

        if curr_round is not None:
            curr_mdp_params = curr_round.round_info[current_user.iteration - 1]
            current_user.interaction_type = curr_mdp_params["interaction type"]
        
        if data["movement"] == "next":
            print('User: ', current_user.id, 'Next movement............................................')

            ### add/update trial data to database  
            print('data: ', data)
            print('Checking if previous trial exists...')
            print('Domain: ', domain, 'Current user round:', current_user.round, 'Current user iteration:', current_user.iteration, 'current interaction type:', current_user.interaction_type)
            
            # check if current iteration has been already completed and add/update trial data
            curr_already_completed = False
            curr_trial = db.session.query(Trial).filter_by(user_id=current_user.id,
                                                                domain=domain,
                                                                round=current_user.round,
                                                                iteration=current_user.iteration).order_by(Trial.id.desc()).first()                          
                                                        

            print('Current trial in next movement:', curr_trial)

            if 'test' in current_user.interaction_type:
                # for completed tests
                if len(data["user input"]) != 0:
                    data["user input"]["mdp_parameters"]["human_actions"] = data["user input"]["moves"]
                    # update_pf = True # redundant as pf is updated based on tests only after all group memebers EOR
        
            ### Add trial data to database when a trial is completed and re-visited after completion
            if (curr_trial is None and current_user.round !=0 and int(data["interaction_survey"]) != -1) or (curr_trial is not None and int(data["interaction_survey"]) != -1):
                add_trial_data(domain, data)
            elif curr_trial is not None:
                curr_already_completed = True
                curr_trial.num_visits += 1
                flag_modified(curr_trial, "num_visits")
                update_database(curr_trial, 'Current trial num visits: ' + str(curr_trial.num_visits))
            
            db.session.commit()

            #########################
            print('Next movement. Current trial already completed:', curr_already_completed, '. Current user last iter in round:', current_user.last_iter_in_round)
            ### generate new round if all group members are at the end of current round (end of tests); if not step through the remaining iterations in the round
            if not curr_already_completed and current_user.last_test_in_round:
                
                ### check for end of domain
                print('Current user round: ', current_user.round, 'Current user iteration:', current_user.iteration, 'Current user last iter in round:', current_user.last_iter_in_round, 'current interaction type:', current_user.interaction_type)
                print('Checking for new domain............')
                # for final tests, last test and last iteration should be the same
                if (current_user.round > 0) and curr_mdp_params["interaction type"] == "final test"  and current_user.last_iter_in_round:
                    print("Current group status: ", curr_group.status, 'Group id:', curr_group.id, 'Group members:', curr_group.members, 'Group mem ids:', curr_group.member_user_ids, 'Group status:', curr_group.members_statuses, 'Group experimental condition:', curr_group.experimental_condition, 'curr_progress:', curr_group.curr_progress)            
                   
                    curr_group.curr_progress, curr_group.status, domain, mdp_class = update_domain(curr_group.curr_progress, curr_group.domain_2)
                    flag_modified(curr_group, "curr_progress")
                    flag_modified(curr_group, "status")
                    update_database(curr_group, 'Current group status: ' + curr_group.status)

                    params = get_mdp_parameters(mdp_class)  # update params for new domain

                    print("All groups reached end of current domain, so I'm trying to construct the first round of next domain.")

                #############################

                print("Current group status: ", curr_group.status, 'Current user round:', current_user.round, 'current_user group:', current_user.group, 'current_user curr_progress:', current_user.curr_progress)
                

                ### Generate first round for the group
                if (current_user.round == 0):
                    first_round_flag = True
                    if (db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=1).count() == 0 and 
                        curr_group.status != "gen_demos"):

                        print('Generating first round...')
                        retrieve_next_round(params)
                        
                        curr_group.ind_member_models, curr_group.group_union_model, curr_group.group_intersection_model = update_learner_models_from_demos(params)
                        curr_group.status = "upd_demos"

                        flag_modified(curr_group, "status")
                        flag_modified(curr_group, "ind_member_models")
                        flag_modified(curr_group, "group_union_model")
                        flag_modified(curr_group, "group_intersection_model")
                        update_database(curr_group, 'Current group status: upd_demos')
                        
                        next_round_id = current_user.round+1
                        next_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()


                    else:
                        round_status = ""
                        print('Waiting for first round to be generated...')
                        next_round_id = current_user.round+1
                        next_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()

                        if next_round is None:
                            while (round_status != "demo_tests_generated") and (round_status != "final_tests_generated"):
                                next_round_id = current_user.round+1
                                next_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()
                                if next_round is not None:
                                    round_status = next_round.status  

                else:
                    
                    ## update EOR status for current user
                    member_idx = curr_group.members.index(current_user.username)
                    curr_group.members_last_test[member_idx] = True
                    flag_modified(curr_group, "members_last_test")
                    print('Member' + str(member_idx) + ' reached last test')
                    update_database(curr_group, 'Member ' + str(member_idx) + ' reached last test')

                    # curr_group.members_EOR[member_idx] = True
                    # flag_modified(curr_group, "members_EOR")
                    # print('Member' + str(member_idx) + ' reached EOR')
                    # update_database(curr_group, 'Member ' + str(member_idx) + ' reached EOR')

                    
                    print('Group members EOR status: ', curr_group.members_EOR, 'all EOR:', curr_group.groups_all_EOR(), 'all last test:', curr_group.group_last_test(), 'mdp_params["interaction type"]: ', curr_mdp_params["interaction type"])
                    if (curr_group.group_last_test()):
                        print("All groups reached last test, so i'm trying to construct the next round now")
                        print("Current group status: ", curr_group.status)
                        
                        if curr_group.status == "upd_demos":
                            curr_group.status = "upd_tests"
                            
                            flag_modified(curr_group, "status")
                            update_database(curr_group, 'Current group status: upd_tests')
                            
                            curr_group.ind_member_models, curr_group.group_union_model, curr_group.group_intersection_model = update_learner_models_from_tests(params)  # only for diagnostic tests and not for final tests
                            curr_group.status = "gen_demos"
                            
                            flag_modified(curr_group, "status")
                            flag_modified(curr_group, "ind_member_models")
                            flag_modified(curr_group, "group_union_model")
                            flag_modified(curr_group, "group_intersection_model")
                            update_database(curr_group, 'Current group status: upd_tests')
                            
                        
                            print("Generating next round...")
                            retrieve_next_round(params)
                            next_round_id = current_user.round+1
                            next_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()
                            
                            print('Updating learner models from demos...')
                            curr_group.ind_member_models, curr_group.group_union_model, curr_group.group_intersection_model = update_learner_models_from_demos(params)
                            curr_group.status = "upd_demos"
                            flag_modified(curr_group, "status")
                            flag_modified(curr_group, "ind_member_models")
                            flag_modified(curr_group, "group_union_model")
                            flag_modified(curr_group, "group_intersection_model")
                            update_database(curr_group, 'Current group status: upd_demos')
                        else:
                            print('Curr group status: ', curr_group.status)
                            print("Group status not updated to upd_demos")
                        
                        print('Socket emitting all reached EOR')
                        print('Rooms for current user:', rooms())  # This will show the rooms the user is part of
                        socketio.emit("all reached EOR", to='room_'+ str(current_user.group))  # triggers next page button to go to next round for clients

                    print('Interaction type: ', curr_mdp_params["interaction type"], 'current user iteration:', current_user.iteration, 'len of round info:', len(curr_round.round_info))
    
                current_user.iteration += 1   # iteration for answers to diagnostic tests


            else:
                print('Moving for with next iteration in current round...', 'Iteration:', current_user.iteration)
                current_user.iteration += 1
            ###########################


            ### update member status for last iteration in round
            if current_user.last_iter_in_round and current_user.round != 0:
                print('User: ', current_user.username, 'reached last iteration in round')
                member_idx = curr_group.members.index(current_user.username)
                curr_group.members_EOR[member_idx] = True
                flag_modified(curr_group, "members_EOR")
                print('Member' + str(member_idx) + ' reached EOR')


        elif data["movement"] == "prev":
            print('User: ', current_user.id, 'Prev movement............................................')
            if current_user.iteration > 1:
                current_user.iteration -= 1 #update iteration for current round
            else:
                current_user.round -= 1
                print('User round after prev:', current_user.round)
                curr_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()
                current_user.iteration = len(curr_round.round_info)
                
        ################################################################################


        # update user's round and iteration
        # print('curr_group.groups_all_EOR:', curr_group.groups_all_EOR(), 'first_round_flag:', first_round_flag)
        ## check if a new round was generated
        if current_user.last_iter_in_round: 

            print('Checking if new round is already generated...')
            ## check if new round is already generated (this is a safety check as the user should be able to press 'Next' only if next round is available)
            next_round_id = current_user.round+1
            next_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()

            if next_round is not None:
                new_round_flag = True
                
                print('Next round generated...')
                current_user.round += 1
                current_user.iteration = 1  # reset iteration to 1 for new round
                current_user.last_iter_in_round = False
                current_user.last_test_in_round = False

                # reset EOR flags
                curr_group.members_EOR = [False for x in curr_group.members_EOR]
                curr_group.members_last_test = [False for x in curr_group.members_last_test]

                flag_modified(curr_group, "members_EOR")
                flag_modified(curr_group, "members_last_test")

                update_database(curr_group, 'Reset EOR flags')

        ########################

        # check if next trial to be shown has already been completed
        next_already_completed = False

        print('group_id:', current_user.group, 'Current user round:', current_user.round, 'Curr_group progress:', curr_group.curr_progress, 'Current user iteration:', current_user.iteration)
        
        next_trial = db.session.query(Trial).filter_by(user_id=current_user.id, domain=domain, round=current_user.round, iteration=current_user.iteration).order_by(Trial.id.desc()).first()
        updated_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()

        print('Next trial: ', next_trial, '. Updated round:', updated_round)




        ## update variables

        if next_trial is not None and next_trial.likert != -1:
            
            next_already_completed = True

            current_user.interaction_type = next_trial.interaction_type

            response["params"] = next_trial.mdp_parameters
            response["moves"] = next_trial.moves

            if 'test' in current_user.interaction_type:
                # if you've already been to this test page, you should simply show the optimal trajectory
                response["params"]["tag"] = -1

        else:

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

            next_mdp_params = updated_round.round_info[current_user.iteration - 1]

            response["params"] = next_mdp_params["params"]
            current_user.interaction_type = next_mdp_params["interaction type"]
            

        

        print('user id:', current_user.id, 'data movement: ', data["movement"], 'current user iteration:', current_user.iteration, 'current user round:', current_user.round, 'current user interaction type:', current_user.interaction_type, 'next already completed:', next_already_completed)


        flag_modified(current_user, "last_iter_in_round")
        flag_modified(current_user, "last_test_in_round")
        flag_modified(current_user, "iteration")
        flag_modified(current_user, "round")
        flag_modified(current_user, "interaction_type")

        update_database(current_user, str(current_user.username) + ". User progress in settings")

          
        # check if the next page should be able to go back
        go_prev = True
        print('current_user.round:', current_user.round, 'current_user.iteration:', current_user.iteration, 'current_user.interaction_type:', current_user.interaction_type, 'next already_completed:', next_already_completed)
        # if (current_user.round == 1 and current_user.iteration==1 and current_user.interaction_type == "demo") or ("test" in current_user.interaction_type and not already_completed) or (current_user.interaction_type == "survey"):
        if (current_user.round == 1 and current_user.iteration==1 and current_user.interaction_type == "demo") or (current_user.interaction_type == "survey"):
            go_prev = False

        print('Go prev for this iteration:', go_prev)

        # debug_string = f"domain={domain}, interaction type={current_user.interaction_type}, iteration={current_user.iteration}, round={current_user.round}"
        debug_string = ""
        print('Updated round:', updated_round, 'Next round:', next_round, 'Current round:', curr_round)

        if current_user.interaction_type == "demo":
            debug_string = f"Seeing a demonstration. Current learning session ={current_user.round}. Iteration={current_user.iteration}/{len(updated_round.round_info)}."
        elif current_user.interaction_type == "diagnostic test":
            debug_string = f"A diagnostic test. Iteration={current_user.iteration}/{len(updated_round.round_info)}. Current learning session ={current_user.round}"
        elif current_user.interaction_type == "answer":
            debug_string = f"Here is the answer to the diagnostic test. Iteration={current_user.iteration}/{len(updated_round.round_info)}. Current learning session ={current_user.round}"
        elif current_user.interaction_type == "final test":
            debug_string = f"Final tests for this game. Iteration={current_user.iteration}/{len(updated_round.round_info)}."



        response["debug string"] = debug_string
        response["last answer"] = current_user.last_iter_in_round
        response["interaction type"] = current_user.interaction_type
        response["already completed"] = next_already_completed
        response["go prev"] = go_prev
        if curr_group.status == "Teaching completed" and current_user.last_iter_in_round:
            response["domain_completed"] = True
        else:
            response["domain_completed"] = False

        print('Settings response:', response)
    
    # Ensure that user is in the correct room
    print('Ensuring user is in room:', room_name)
    join_room(room_name)

    socketio.emit("settings configured", response, to=request.sid)


    #########################




@app.route("/sign_consent", methods=["GET", "POST"])
@login_required
def sign_consent():
    current_user.consent = 1
    flag_modified(current_user, "consent")
    update_database(current_user, str(current_user.username) + ". User consent")
    # need to return json since this function is called on button press
    # which replaces the current url with new url
    # sorry trying to work within existing infra
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
    #         code = user.set_code()
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
    if current_user.is_authenticated:
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
            # code = user.set_code()

            db.session.add(user)

            # cond.users.append(user)
            # cond.count += 1

            db.session.commit()

        login_user(user)
        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(next_page)

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

        print(form.ethnicity.data)

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


def update_learner_models_from_tests(params) -> tuple:
    
    print('Updating learner models based on tests...')

    # user_ids = db.session.query(Group).filter_by(id=current_user.group).first().user_ids
    curr_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()
    curr_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=current_user.round).order_by(Round.id.desc()).first()

    domain_id = curr_group.curr_progress
    if domain_id == "domain_1":
        domain = curr_group.domain_1
    elif domain_id == "domain_2":
        domain = curr_group.domain_2
    else:
        print('Domain id:', domain_id)
        raise ValueError('Domain not found')
    curr_domain = db.session.query(DomainParams).filter_by(domain_name=domain).first()
    print('All domains:',  db.session.query(DomainParams).all())

    
    teaching_uf = params['teacher_learning_factor']
    model_type = params['teacher_update_model_type']
    
    # current models
    ind_member_models = copy.deepcopy(curr_group.ind_member_models)
    group_union_model = copy.deepcopy(curr_group.group_union_model)
    group_intersection_model = copy.deepcopy(curr_group.group_intersection_model)
    num_members = curr_group.num_members

    group_knowledge = curr_round.group_knowledge[0]
    kc_id = curr_round.kc_id

    group_usernames = retrieve_group_usernames()
    group_test_constraints = []
    joint_constraints = []
    knowledge_to_update = []
    for username in group_usernames:
        group_code = db.session.query(User).filter_by(username=username).first().group_code
        print('Username:', username, 'Group:', current_user.group, 'Group code:', group_code, 'round:', current_user.round, 'member statuses:', curr_group.members_statuses)
        tests = db.session.query(Trial).filter_by(group=current_user.group, group_code=group_code, round=current_user.round, interaction_type="diagnostic test").all()
        
        update_model_flag = False
        if curr_group.members_statuses[group_code] == 'joined':
            update_model_flag = True
        
        if update_model_flag:
            test_constraints = []
            for test in tests:
                cur_test_constraints = get_test_constraints(domain, test, curr_domain.traj_record, curr_domain.traj_features_record)
                test_constraints.extend(cur_test_constraints)
                print('Test constraints:', test_constraints)    
            group_test_constraints.append(test_constraints)
            print('Group test constraints so far:', group_test_constraints)

            min_test_constraints = remove_redundant_constraints(test_constraints, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the unit's demonstrations
            print('Min test constraints:', min_test_constraints)
            
            # update learner models
            ind_member_models[group_code].update(min_test_constraints, teaching_uf, model_type, params)

            joint_constraints.append(min_test_constraints)

    group_test_constraints_expanded = [item for sublist in group_test_constraints for item in sublist]
    print('Group test constraints expanded:', group_test_constraints_expanded)
    print('Joint constraints:', joint_constraints)

    # update group_union_model and group_intersection_model
    # TODO: Keep track of proper common and joint constraints with majority rules.
    group_min_constraints = remove_redundant_constraints(group_test_constraints_expanded, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the group's demonstrations
    
    print('Group min constraints:', group_min_constraints)

    group_intersection_model.update(group_min_constraints, teaching_uf, model_type, params) # common belief model
    
    group_union_model.update_jk(joint_constraints, teaching_uf, model_type, params)  # joint belief model

    
    # update team knowledge
    print('Update team knowledge for num members:', num_members)
    updated_group_knowledge = update_team_knowledge(group_knowledge, kc_id, True, group_test_constraints, num_members, params['mdp_parameters']['weights'], params['step_cost_flag'], knowledge_to_update = 'all')


    print('Updated group knowledge:', updated_group_knowledge)

    ind_member_models_pos_current = [ind_member_models[i].positions for i in range(num_members)]
    ind_member_models_weights_current = [ind_member_models[i].weights for i in range(num_members)]

    # add the updated round information to the database
    curr_round_tests_updated = Round(group_id=curr_round.group_id, 
                                    round_num=curr_round.round_num,
                                    domain = curr_group.curr_progress,
                                    members_statuses=curr_group.members_statuses,
                                    kc_id = kc_id,
                                    min_KC_constraints = curr_round.min_KC_constraints,
                                    round_info=curr_round.round_info,
                                    status="tests_updated",
                                    variable_filter=curr_round.variable_filter,
                                    nonzero_counter=curr_round.nonzero_counter,
                                    min_BEC_constraints_running=curr_round.min_BEC_constraints_running,
                                    prior_min_BEC_constraints_running=curr_round.prior_min_BEC_constraints_running,
                                    visited_env_traj_idxs=curr_round.visited_env_traj_idxs,
                                    ind_member_models_pos = curr_round.ind_member_models_pos.append(ind_member_models_pos_current),
                                    ind_member_models_weights = curr_round.ind_member_models_weights.append(ind_member_models_weights_current),
                                    group_union_model_pos = curr_round.group_union_model_pos.append(group_union_model.positions),
                                    group_union_model_weights = curr_round.group_union_model_weights.append(group_union_model.weights),
                                    group_intersection_model_pos = curr_round.group_intersection_model_pos.append(group_intersection_model.positions),
                                    group_intersection_model_weights = curr_round.group_intersection_model_weights.append(group_intersection_model.weights),
                                    group_knowledge = [updated_group_knowledge]
                                    )

    update_database(curr_round_tests_updated, 'Update learner models from tests')


    return ind_member_models, group_union_model, group_intersection_model



def retrieve_next_round(params) -> dict:
    """
    retrieves necessary environment variables for displaying the next round to
    the client based on database entries. gets called on the condition that 
    player group_code == A, since we don't want to do computation more than once

    data in: none (retrieves test moves from database)
    data out: environment variables for next round
    side effects: none  
    """ 
    from app import pool, lock


    group = current_user.group
    round = current_user.round 
    curr_group = db.session.query(Group).filter_by(id=group).order_by(Group.id.desc()).first()
    domain_id = curr_group.curr_progress
    if domain_id == "domain_1":
        domain = curr_group.domain_1
    elif domain_id == "domain_2":
        domain = curr_group.domain_2
    else:
        print('Domain id:', domain_id)
        raise ValueError('Domain not found')
    
    print('round:', round, 'Group status:', curr_group.status, 'Group experimental condition:', curr_group.experimental_condition, 'Group members:', curr_group.members)

    curr_group.status = "gen_demos"
    flag_modified(curr_group, "status")
    update_database(curr_group, 'Group status: gen_demos; in retrieve next round')

    print('Member statuses retrive next round:', curr_group.members_statuses)
    
    print('Group experimental condition:', curr_group.experimental_condition, 'Group status:', curr_group.status, 'Group id:', curr_group.id, 'Group members:', curr_group.members)
    experimental_condition = curr_group.experimental_condition
    members_statuses = curr_group.members_statuses
    
    vars_filename = date.today().strftime("%Y-%m-%d") + '_group_' + str(group)
    new_round_for_var_filter = False

    # load previous round data
    if round > 0:
        print('current_user.curr_progress:', current_user.curr_progress, 'curr_group prgress:', curr_group.curr_progress, 'round:', round, 'group:', group)
        prev_models = db.session.query(Round).filter_by(group_id=group, domain=curr_group.curr_progress, round_num=round).order_by(Round.id.desc()).first()
        print('Previous round:', prev_models.id, prev_models.round_num, prev_models.status, prev_models.group_id, prev_models.group_knowledge, prev_models.kc_id, prev_models.min_KC_constraints)
        
        all_prev_rounds = db.session.query(Round).filter_by(group_id=group, domain=curr_group.curr_progress).all()
        print('All previous rounds...')
        for prev_round in all_prev_rounds:
            print('Previous round:', prev_round.id, prev_round.round_num, prev_round.status, prev_round.group_id, prev_round.group_knowledge, prev_round.kc_id, prev_round.min_KC_constraints)
        
        group_union_model = curr_group.group_union_model
        group_intersection_model = curr_group.group_intersection_model
        ind_member_models = curr_group.ind_member_models

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
        # hardcode variable filter for testing
        # variable_filter = np.zeros((1,3))
        # nonzero_counter = np.ones(3)*np.inf
        # variable_filter[0,2] = 1
        # nonzero_counter[2] = 100
        # min_KC_constraints = np.zeros(3)
        
        print('nonzero counter:', nonzero_counter, 'round:', 0, 'variable filter:', variable_filter)

        ind_member_models = []
        for key in particles_team_teacher.keys():
            if 'common' not in key and 'joint' not in key:
                ind_member_models.append(particles_team_teacher[key])

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
        print('Round:', round, 'Group knowledge:', group_knowledge, 'min_KC_constraints:', min_KC_constraints, 'kc_id:', kc_id)
        unit_learning_goal_reached_flag = check_unit_learning_goal_reached(params, group_knowledge, min_KC_constraints, kc_id)
    else:
        unit_learning_goal_reached_flag = False
    

    if (curr_group.status != "Teaching completed"):

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
        if not np.any(variable_filter):
            teaching_complete_flag = True
            curr_group.status = "Teaching completed"
            
            flag_modified(curr_group, "status")
            update_database(curr_group, 'Group status: Teaching completed. In retrieve next round')

        print('Teaching complete flag before generating demos:', teaching_complete_flag)


        # get demonstrations and tests for this round
        if not teaching_complete_flag:

            args = domain, vars_filename, group_union_model, group_intersection_model, ind_member_models, members_statuses, experimental_condition, variable_filter, nonzero_counter, new_round_for_var_filter, min_BEC_constraints_running, visited_env_traj_idxs, pool, lock    
            min_KC_constraints, demo_mdps, test_mdps, experimental_condition, variable_filter, nonzero_counter, min_BEC_constraints_running, visited_env_traj_idxs, teaching_complete_flag = generate_demos_test_interaction_round(args)
            round_status = "demo_tests_generated"
            games = list()
            for i in range(len(demo_mdps)):
                games.append({"interaction type": "demo", "params": demo_mdps[i]})

            for i in range(len(test_mdps)):
                games.append({"interaction type": "diagnostic test", "params": test_mdps[i]})
        else:
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


        print('Teaching complete flag:', teaching_complete_flag)


        # to_add = []
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



        # add models
        print('Adding particle filter models to group')
        curr_group.ind_member_models = ind_member_models
        curr_group.group_union_model = group_union_model
        curr_group.group_intersection_model = group_intersection_model

        flag_modified(curr_group, "ind_member_models")
        flag_modified(curr_group, "group_union_model")
        flag_modified(curr_group, "group_intersection_model")


        update_database(curr_group, 'Reset EOR flags')

        ind_member_models_pos = [ind_member_models[i].positions for i in range(len(ind_member_models))]
        ind_member_models_weights = [ind_member_models[i].weights for i in range(len(ind_member_models))]

        print('Group curr progress:', curr_group.curr_progress)
        new_round = Round(group_id=group, 
                        domain = curr_group.curr_progress,
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
                        
        db.session.add(new_round)
        db.session.commit()

        return games_extended

    else:
        return list()



def update_learner_models_from_demos(params) -> tuple:

    print('Updating learner models based on demos...')

    teacher_uf = params['teacher_learning_factor']
    model_type = params['teacher_update_model_type']

    curr_group = db.session.query(Group).filter_by(id=current_user.group).order_by(Group.id.desc()).first()

    print('Current user group:', current_user.group, 'Domain:', curr_group.curr_progress, 'Round:',  current_user.round)
    next_round_id = current_user.round+1
    updated_curr_round = db.session.query(Round).filter_by(group_id=current_user.group, domain=curr_group.curr_progress, round_num=next_round_id).order_by(Round.id.desc()).first()
    print('Next round: ', updated_curr_round)
    
    ind_member_models = copy.deepcopy(curr_group.ind_member_models)
    group_union_model = copy.deepcopy(curr_group.group_union_model)
    group_intersection_model = copy.deepcopy(curr_group.group_intersection_model)

    # update the models based on the demos
    demo_mdps = [game["params"] for game in updated_curr_round.round_info if game["interaction type"] == "demo"]
    
    constraints = []
    for demo_mdp in demo_mdps:
        constraints.extend(demo_mdp['constraints'])

    min_KC_constraints = remove_redundant_constraints(constraints, params['mdp_parameters']['weights'], params['step_cost_flag']) # minimum constraints conveyed by the unit's demonstrations
            
    
    print('Constraints from demos: ', constraints, 'min_demo_constraints:', min_KC_constraints)
    
    # update the models
    joint_constraints = []
    ind_member_models_pos_current = []
    ind_member_models_weights_current  = []
    for i in range(len(ind_member_models)):
        if curr_group.members_statuses[i] == 'joined':
            print('Updating model for member:', i)
            ind_member_models[i].update(min_KC_constraints, teacher_uf, model_type, params)
            joint_constraints.append(min_KC_constraints)

            ind_member_models_pos_current.append(ind_member_models[i].positions)
            ind_member_models_weights_current.append(ind_member_models[i].weights)

    # update the team models
    print('Updating group models...')
    group_intersection_model.update(min_KC_constraints, teacher_uf, model_type, params)  # common belief model
    print('Updated common belief model')
    group_union_model.update_jk(joint_constraints, teacher_uf, model_type, params) # joint belief model

    print('Updated all models based on demos')

    # add the updated round information to the database
    curr_round_demo_updated = Round(group_id=updated_curr_round.group_id, 
                                    domain = curr_group.curr_progress,
                                    round_num=updated_curr_round.round_num,
                                    kc_id = updated_curr_round.kc_id,
                                    min_KC_constraints = min_KC_constraints,
                                    members_statuses=curr_group.members_statuses,
                                    round_info=updated_curr_round.round_info,
                                    status="demos_updated",
                                    variable_filter=updated_curr_round.variable_filter,
                                    nonzero_counter=updated_curr_round.nonzero_counter,
                                    min_BEC_constraints_running=updated_curr_round.min_BEC_constraints_running,
                                    prior_min_BEC_constraints_running=updated_curr_round.prior_min_BEC_constraints_running,
                                    visited_env_traj_idxs=updated_curr_round.visited_env_traj_idxs,
                                    ind_member_models_pos = updated_curr_round.ind_member_models_pos.append(ind_member_models_pos_current),
                                    ind_member_models_weights = updated_curr_round.ind_member_models_weights.append(ind_member_models_weights_current),
                                    group_union_model_pos = updated_curr_round.group_union_model_pos.append(group_union_model.positions),
                                    group_union_model_weights = updated_curr_round.group_union_model_weights.append(group_union_model.weights),
                                    group_intersection_model_pos = updated_curr_round.group_intersection_model_pos.append(group_intersection_model.positions),
                                    group_intersection_model_weights = updated_curr_round.group_intersection_model_weights.append(group_intersection_model.weights),
                                    group_knowledge = updated_curr_round.group_knowledge
                                    )
    
    db.session.add(curr_round_demo_updated)
    print('Updated round info')
    db.session.flush()
    print('Flushed session')
    db.session.commit()         
    print('Updated learner models based on demos...')    

    return ind_member_models, group_union_model, group_intersection_model



def retrieve_group_usernames() -> list[str]:
    """
    retrieves group usernames given current user

    data in: none 
    data out: list[str] of 3 groupmates (including current user)
    side effects: none
    """

    curr_group_num = current_user.group

    # run query on Groups database
    curr_group = db.session.query(Group).filter_by(id=curr_group_num).order_by(Group.id.desc()).first()

    group_usernames = []
    for loop_id in range(len(curr_group.members)):
        if curr_group.members_statuses[loop_id] == 'joined':
            group_usernames.append(curr_group.members[loop_id])

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
        print("Commit successful. ", update_type )
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
        likert = int(data["interaction_survey"]),
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


def update_domain(group_curr_progress, next_domain):

     # update group variables
    if group_curr_progress == "domain_1":
        group_curr_progress = "domain_2"
        group_status = "gen_demos"
        domain = next_domain

    elif curr_group.curr_progress == "domain_2":
        group_curr_progress = "study_end"
        group_status = "study_end"
        domain = next_domain

    else:
        RuntimeError("Domain not found")

    # update user variables
    current_user.curr_progress = curr_group.curr_progress
    current_user.round = 0
    current_user.iteration = 1
    current_user.interaction_type = "demo"

    flag_modified(current_user, "curr_progress")
    flag_modified(current_user, "round")
    flag_modified(current_user, "iteration")
    flag_modified(current_user, "interaction_type")
    update_database(current_user, 'Current user progress: ' + current_user.curr_progress)

    if domain == 'at':
        mdp_class = 'augmented_taxi2'
    elif domain == 'sb':
        mdp_class = 'skateboard2'
    else:
        print('Domain:', domain)
        raise ValueError('Domain not found')


    return group_curr_progress, group_status, domain, mdp_class