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
from .group_teaching.codes import params_team as params
from .group_teaching.codes.policy_summarization.BEC_helpers import remove_redundant_constraints
from app.backend_test import send_signal
from app import socketio
from flask_socketio import join_room, leave_room
import asyncio
from concurrent.futures import ProcessPoolExecutor

import pickle
import numpy as np

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


# todo: Mike uncomment for remedial demos and tests
# # background variables needed for remedial demonstrations and tests
# domain_background_vars = {}
# def load_background_vars(data_loc):
#     with open('models/' + data_loc + '/base_constraints.pickle', 'rb') as f:
#         policy_constraints, min_subset_constraints_record, env_record, traj_record, traj_features_record, reward_record, mdp_features_record, consistent_state_count = pickle.load(
#             f)
#     background_vars = (
#     policy_constraints, min_subset_constraints_record, env_record, traj_record, traj_features_record, reward_record,
#     mdp_features_record, consistent_state_count)
#
#     return background_vars
#
# # todo: double check if this code is run for each new person
# args = ['augmented_taxi2', 'colored_tiles', 'skateboard2']
#
# for domain in args:
#     domain_background_vars[domain] = load_background_vars(domain)
#
# pool = Pool(os.cpu_count())

# 
# 
# 
# HOW TO PREVENT RULE / STATE CHANGE ON RELOAD???

# shenai: I think I wrote this function
def jsonStrToList(str):
    if len(str) > 2:
        return [int(val) for val in str[1:-1].split(',')]
    else:
        return []
    
@app.route("/", methods=["GET", "POST"])
# @app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    # condition_id = current_user.condition_id
    # print(condition_id)
    # current_condition = db.session.query(OnlineCondition).get(condition_id)
    # num_rounds = len(current_condition.difficulty)

    # completed = []
    # for round in range(num_rounds):
    #     completed.append([])
    #     rule_name = current_condition.difficulty[round]

    #     demo_cards = RULE_PROPS[rule_name]['demo_cards']
    #     num_completed_demos = db.session.query(Demo).filter_by(user_id=current_user.id, round_num=round).count()
    #     if num_completed_demos < len(demo_cards):
    #         completed[round].append(False)
    #     else:
    #         completed[round].append(True)

    #     cards = RULE_PROPS[rule_name]['cards']
    #     num_completed_trials = db.session.query(Trial).filter_by(user_id=current_user.id, round_num=round).count()
    #     if num_completed_trials < len(cards):
    #         completed[round].append(False)
    #     else:
    #         completed[round].append(True)

    #     num_completed_surveys = db.session.query(Survey).filter_by(user_id=current_user.id, round_num=round).count()
    #     if num_completed_surveys < 1:
    #         completed[round].append(False)
    #     else:
    #         completed[round].append(True)
    online_condition_id = current_user.online_condition_id
    current_condition = db.session.query(OnlineCondition).get(online_condition_id)

    completed = True if current_user.study_completed == 1 else False

    current_user.loop_condition = "debug"
    domains = ["at", "ct", "sb"]
    # domains = ["ct", "sb", "at"]
    # domains = ["sb", "at", "ct"]
    # rand.shuffle(domains)
    current_user.domain_1 = domains[0]
    current_user.domain_2 = domains[1]
    current_user.domain_3 = domains[2]
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
    db.session.commit()
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


@socketio.on("sandbox settings")
def sandbox_settings(data):
    print(request.sid)
    version = data["version"]
    if version == 1:
        params = {
            'agent': {'x': 4, 'y': 3, 'has_passenger': 0},
            'walls': [{'x': 2, 'y': 3}, {'x': 2, 'y': 2}, {'x': 3, 'y': 2}, {'x': 4, 'y': 2}],
            'passengers': [{'x': 4, 'y': 1, 'dest_x': 1, 'dest_y': 4, 'in_taxi': 0}],
            'hotswap_station': [{'x': 1, 'y': 2}],
            'width': 4,
            'height': 4,
        }
        continue_condition = "free_play"
    elif version == 2:
        params = {
            'agent': {'x': 4, 'y': 1, 'has_passenger': 0},
            'walls': [{'x': 1, 'y': 3}, {'x': 2, 'y': 3}, {'x': 3, 'y': 3}],
            'passengers': [{'x': 1, 'y': 2, 'dest_x': 1, 'dest_y': 4, 'in_taxi': 0}],
            'hotswap_station': [{'x': 2, 'y': 1}],
            'width': 4,
            'height': 4,
        }
        continue_condition = "optimal_traj_1"
    socketio.emit("sandbox configured", {"params": params, "continue_condition": continue_condition}, to=request.sid)


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

        db.session.commit()

@app.route("/post_practice", methods=["GET", "POST"])
@login_required
def post_practice():
    print("I'm in post practice")
    current_user.set_curr_progress("post practice")
    current_user.last_iter_in_round = True
    print(current_user.curr_progress)
    db.session.commit()
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
    # get last entry in groups table
    # the initial entry is an empty list as initialized in app/__init__.py
    old_group = db.session.query(Group).order_by(Group.id.desc()).first()
    print('Old group:', 'Group id:', old_group.id, 'Group members:', old_group.member_A, old_group.member_B, old_group.member_C, 'Group status:', old_group.status, 'Group experimental condition:', old_group.experimental_condition)
    num_members = old_group.num_members
    print('Num members:', num_members)
    cond_list = ["individual_belief_low", "individual_belief_high", "common_belief", "joint_belief"]
    if not current_user.group: # if no group yet, join one
        
        if num_members == 0 or num_members == 3:
            print('No group yet.. Creating one...')
            current_user.group = 1 if old_group.id is None else old_group.id + 1

            new_group_entry = Group(
                experimental_condition=cond_list[current_user.group % 4],
                status = "Experiment_started",
                user_ids = []
                )
            db.session.add(new_group_entry)
            db.session.commit()
            
            new_group = db.session.query(Group).order_by(Group.id.desc()).first()

            print('New group:', 'Group id:', new_group.id, 'Group members:', new_group.member_A, new_group.member_B, new_group.member_C, 'Group status:', new_group.status, 'Group experimental condition:', new_group.experimental_condition, 'num_members: ', new_group.num_members)
            current_user.group_code = new_group.groups_push(current_user.username)
        else:
            print('Adding to existing group')
            current_user.group_code = old_group.groups_push(current_user.username)
            current_user.group = old_group.id
            num_members += 1
    else: # if rejoining, get added to the same room
        print('Rejoining group')
        rejoined_group = db.session.query(Group).filter_by(id=current_user.group).first()
        num_members = rejoined_group.num_members

    print('Current user: .' + str(current_user.username) + 'Current user group: ' + str(current_user.group))
    
    db.session.commit() # after pushing to group, commit changes

    # make sure that when people leave and rejoin they check the time elapsed and 
    # if it's not too long, then put them back in a group
    # they shouldn't be able to go back once they're in the waiting room

    # test 
    new_groups = db.session.query(Group).all()
    print([[g.id, g.member_A, g.member_B, g.member_C] for g in new_groups])

    room = (current_user.group) 
    print('Room:', room)
    join_room(room)

    # if room is None then it gets sent to everyone 
    socketio.emit("group joined", {"num members":num_members}, to=room)
    return

@socketio.on("join group v2")
def join_group_v2():
    join_room(current_user.group)
    socketio.emit("member joined again", {"user code": current_user.group_code}, to=current_user.group)
    return

@socketio.on("leave group temp")
def leave_group_temp():
    socketio.emit("member left temp", {"member code": current_user.group_code}, to=current_user.group)
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
    if (current_user.group_code == "A"):

        db.session.query(Group).filter_by(id=current_user.group).first().groups_remove(current_user.username)
    db.session.commit()

    socketio.emit("member left", {"member code": current_user.group_code}, to=current_user.group)
    return


@socketio.on('join room')
def handle_message():
    # print('received message: ' + data['data'])
    # session_id = request.sid
    # print('session_id is: ' + session_id)
    print(request.sid)
    if current_user.username[0] == "a":
        current_user.group = "room1"
    else:
        current_user.group = "room2"
    # socketio.emit('ping event', {'test': 'sending to client'}, to=request.sid)
    # current_user.set_test_column(812)

    # curr_room = ""
    # if len(current_user.username) % 2 == 0:
    #     curr_room = "room1"
    # else:
    #     curr_room = "room2"
    join_room(current_user.group)
    db.session.commit()
    # socketio.emit('join event', {"test":current_user.username + "just joined!"}, to=curr_room)

@socketio.on("next domain")
def next_domain():
    print("yassss")
    current_user.interaction_type = "demo"
    current_user.iteration = 0
    current_user.subiteration = 0 # don't care about this
    current_user.control_stack = [] # or this
    print('curr_progress:', current_user.curr_progress)

    if current_user.curr_progress == "post practice":
        print("slayyy")
        current_user.set_curr_progress("domain 1")
        socketio.emit("next domain is", {"domain": current_user.domain_1}, to=request.sid)
    elif current_user.curr_progress == "domain 1":
        current_user.set_curr_progress("domain 2")
        socketio.emit("next domain is", {"domain": current_user.domain_2}, to=request.sid)
    elif current_user.curr_progress == "domain 2":
        current_user.set_curr_progress("domain 3")
        socketio.emit("next domain is", {"domain": current_user.domain_3}, to=request.sid)
    elif current_user.curr_progress == "domain 3":
        current_user.set_curr_progress("final survey")
        socketio.emit("next domain is", {"domain": "final survey"}, to=request.sid)

    db.session.commit()

# @socketio.on("retrieve_first_round")
# def retrieve_first_round() -> dict:

async def retrieve_first_round():

    loop = asyncio.get_event_loop()
    games = await loop.run_in_executor(executor, retrieve_first_round_helper)
    return games

    

## WIP functions, not completely working at the moment - 08/21/24
def retrieve_first_round_helper() -> dict:

    from app import pool, lock

    # initialize the particles for the group
    particles_team_teacher, _, _, _, _, domain_params = initialize_teaching((params.teacher_learning_factor, pool, lock))
    model_A = copy.deepcopy(particles_team_teacher['p1'])
    model_B = copy.deepcopy(particles_team_teacher['p2'])
    model_C = copy.deepcopy(particles_team_teacher['p3'])

    group_intersection = copy.deepcopy(particles_team_teacher['common_knowledge'])
    group_union = copy.deepcopy(particles_team_teacher['joint_knowledge'])

    group = current_user.group

    #load the first round demos and tests (games)
    with open(os.path.join(os.path.dirname(__file__), '../augmentedtaxi_first_demo_test_mdps.pickle'), 'rb') as f:
        demo_mdps, test_mdps, variable_filter, min_BEC_constraints_running, visited_env_traj_idxs  = pickle.load(f)
    
    games = list()
    for i in range(len(demo_mdps)):
        games.append({"interaction type": "demo", "params": demo_mdps[i]})

    for i in range(len(test_mdps)):
        games.append({"interaction type": "diagnostic test", "params": test_mdps[i]})

    print('Initializing teacher model of learner for group: ', group)
    new_round = Round(group_id=group, round_num=0, 
                      group_union=group_union,
                      group_intersection=group_intersection,
                      member_A_model=model_A,
                      member_B_model=model_B,
                      member_C_model=model_C,
                      round_info=games,
                      status ="demo_tests_generated",
                      variable_filter=variable_filter,
                      min_BEC_constraints_running=min_BEC_constraints_running,
                      visited_env_traj_idxs=visited_env_traj_idxs,)
    db.session.add(new_round)
    db.session.commit()

    return games


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

@app.route("/ct_intro", methods=["GET", "POST"])
@login_required
def ct_intro():
    return render_template("mike/colored_tiles_introduction.html")

@app.route("/ct", methods=["GET", "POST"])
@login_required
def ct():
    return render_template("mike/colored_tiles.html")

@app.route("/sb_intro", methods=["GET", "POST"])
@login_required
def sb_intro():
    return render_template("mike/skateboard2_introduction.html")

@app.route("/sb", methods=["GET", "POST"])
@login_required
def sb():
    return render_template("mike/skateboard2.html")

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

    return [curr_group.member_A, curr_group.member_B, curr_group.member_C]



def get_test_constraints(trial, traj_record, traj_features_record) -> np.ndarray:
    prev_mdp_parameters = trial.mdp_parameters
    best_env_idx, best_traj_idx = prev_mdp_parameters['env_traj_idxs']
    opt_traj = traj_record[best_env_idx][best_traj_idx]
    opt_traj_features = traj_features_record[best_env_idx][best_traj_idx]

    domain_key = 'augmented_taxi2' #fixed for now;  # TODO: make it an argument later

    # obtain the constraint that the participant failed to demonstrate
    constraint = obtain_constraint(domain_key, prev_mdp_parameters, opt_traj, opt_traj_features)

    return constraint


def update_learner_models_from_demos() -> tuple:

    print('Updating learner models based on demos...')

    teacher_uf = 0.8
    model_type = 'low_noise'
    
    updated_curr_round = db.session.query(Round).filter_by(group_id=current_user.group, round_num=current_user.round).order_by(Round.id.desc()).first()
    model_A = updated_curr_round.member_A_model
    model_B = updated_curr_round.member_B_model
    model_C = updated_curr_round.member_C_model
    group_union = updated_curr_round.group_union
    group_intersection = updated_curr_round.group_intersection

    # update the models based on the demos
    demo_mdps = [game["params"] for game in updated_curr_round.round_info if game["interaction type"] == "demo"]
    
    constraints = []
    for demo_mdp in demo_mdps:
        constraints.extend(demo_mdp['constraints'])

    min_KC_constraints = remove_redundant_constraints(constraints, params.weights['val'], params.step_cost_flag) # minimum constraints conveyed by the unit's demonstrations
            
    
    print('Constraints from demos: ', constraints, 'min_demo_constraints:', min_KC_constraints)
    # update the models
    model_A.update(min_KC_constraints, teacher_uf, model_type)
    model_B.update(min_KC_constraints, teacher_uf, model_type)
    model_C.update(min_KC_constraints, teacher_uf, model_type)

    # update the team models
    group_intersection.update(min_KC_constraints, teacher_uf, model_type)  # common belief model
    
    joint_constraints = [min_KC_constraints, min_KC_constraints, min_KC_constraints]
    group_union.update_jk(joint_constraints, teacher_uf, model_type) # joint belief model

    # add the updated round information to the database
    curr_round_demo_updated = Round(group_id=updated_curr_round.group_id, 
                                    round_num=updated_curr_round.round_num,
                                    group_union=group_union,
                                    group_intersection=group_intersection,
                                    member_A_model=model_A,
                                    member_B_model=model_B,
                                    member_C_model=model_C,
                                    round_info=updated_curr_round.round_info,
                                    status="demos_updated",
                                    variable_filter=updated_curr_round.variable_filter,
                                    min_BEC_constraints_running=updated_curr_round.min_BEC_constraints_running,
                                    visited_env_traj_idxs=updated_curr_round.visited_env_traj_idxs)
    
    db.session.add(curr_round_demo_updated)
    db.session.commit()         
    print('Updated learner models based on demos...')    

    return model_A, model_B, model_C, group_union, group_intersection



def update_learner_models_from_tests() -> tuple:
    
    print('Updating learner models based on tests...')

    user_ids = db.session.query(Group).filter_by(id=current_user.group).first().user_ids
    curr_round = db.session.query(Round).filter_by(group_id=current_user.group, round_num=current_user.round).order_by(Round.id.desc()).first()
    
    teaching_uf = 0.8
    model_type = 'low_noise'
    
    # current models
    model_A = curr_round.member_A_model
    model_B = curr_round.member_B_model
    model_C = curr_round.member_C_model
    group_union = curr_round.group_union
    group_intersection = curr_round.group_intersection

    for user_id in user_ids:
        tests = db.session.query(Trial).filter_by(group=current_user.group, user_id=user_id, round=current_user.round, interaction_type="diagnostic test").all()
        group_code = db.session.query(User).filter_by(id=user_id).first().group_code
        
        test_constraints = []
        for test in tests:    
            test_constraints.append(get_test_constraints(test, curr_round.traj_record, curr_round.traj_features_record))
        
        min_test_constraints = remove_redundant_constraints(test_constraints, params.weights['val'], params.step_cost_flag) # minimum constraints conveyed by the unit's demonstrations
     
        # update learner models
        if "A" in group_code:
            model_A.update(min_test_constraints, teaching_uf, model_type)
        elif "B" in group_code:
            model_B.update(min_test_constraints, teaching_uf, model_type)
        elif "C" in group_code:
            model_C.update(min_test_constraints, teaching_uf, model_type)

        # update group_union and group_intersection
        group_union.update(min_test_constraints, teaching_uf, model_type) # common belief model
        
        joint_constraints = [min_test_constraints, min_test_constraints, min_test_constraints] # TODO: make this adaptive to the number of group members for when members leave mid experiment
        group_intersection.update_jk(joint_constraints, teaching_uf, model_type)  # joint belief model


    # add the updated round information to the database
    curr_round_tests_updated = Round(group_id=curr_round.group_id, 
                                    round_num=curr_round.round_num,
                                    group_union=group_union,
                                    group_intersection=group_intersection,
                                    member_A_model=model_A,
                                    member_B_model=model_B,
                                    member_C_model=model_C,
                                    round_info=curr_round.round_info,
                                    status="tests_updated",
                                    variable_filter=curr_round.variable_filter,
                                    min_BEC_constraints_running=curr_round.min_BEC_constraints_running,
                                    visited_env_traj_idxs=curr_round.visited_env_traj_idxs)
    
    db.session.add(curr_round_tests_updated)
    db.session.commit()  

    return model_A, model_B, model_C, group_union, group_intersection



def retrieve_next_round() -> dict:
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
    group_usernames = retrieve_group_usernames()
    curr_group = db.session.query(Group).filter_by(id=group).order_by(Group.id.desc()).first()
    print('round:', round, 'Group status:', curr_group.status, 'Group experimental condition:', curr_group.experimental_condition)
    curr_group.status = "Gen_demos"
    db.session.commit()
    print('Group experimental condition:', curr_group.experimental_condition, 'Group status:', curr_group.status, 'Group id:', curr_group.id, 'Group members:', curr_group.member_A, curr_group.member_B, curr_group.member_C)
    experimental_condition = curr_group.experimental_condition
    vars_filename = 'data_group_' + str(group)

    # load previous round data
    if round > 0:
        prev_models = db.session.query(Round).filter_by(group_id=group, round_num=round).order_by(Round.id.desc()).first()
        group_union = prev_models.group_union
        group_intersection = prev_models.group_intersection
        model_A = prev_models.member_A_model
        model_B = prev_models.member_B_model
        model_C = prev_models.member_C_model

        variable_filter = prev_models.variable_filter
        min_BEC_constraints_running = prev_models.min_BEC_constraints_running
        visited_env_traj_idxs = prev_models.visited_env_traj_idxs

    else:
        # initialize models for first round/learning session
        particles_team_teacher, variable_filter, nonzero_counter, min_BEC_constraints_running, visited_env_traj_idxs, domain_params = initialize_teaching((params.teacher_learning_factor, pool, lock))
        
        # # save domain params to database (run only once for each domain)
        # curr_domain_params = DomainParams(
        #     domain_name = domain_params["domain_name"],
        #     min_subset_constraints_record = domain_params["min_subset_constraints_record"],
        #     env_record = domain_params["env_record"],
        #     traj_record = domain_params["traj_record"],
        #     traj_features_record = domain_params["traj_features_record"],
        #     mdp_features_record = domain_params["mdp_features_record"],
        #     consistent_state_count = domain_params["consistent_state_count"],
        #     min_BEC_constraints = domain_params["min_BEC_constraints"]
        # )

        # db.session.add(curr_domain_params)
        # db.session.commit()
        
        model_A = copy.deepcopy(particles_team_teacher['p1'])
        model_B = copy.deepcopy(particles_team_teacher['p2'])
        model_C = copy.deepcopy(particles_team_teacher['p3'])
        group_intersection = copy.deepcopy(particles_team_teacher['common_knowledge'])
        group_union = copy.deepcopy(particles_team_teacher['joint_knowledge'])

        # create a directory for the group
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.abspath(os.path.join(current_dir, 'group_teaching', 'results', params.data_loc['BEC']))

        
        full_path_filename = base_dir + '/ind_sim_trials/' + vars_filename

        if not os.path.exists(full_path_filename):
            print('Creating folder for this run: ', full_path_filename)
            os.makedirs(full_path_filename, exist_ok=True)


    # get demonstrations and tests for this round
    args = vars_filename, group_union, group_intersection, model_A, model_B, model_C, experimental_condition, variable_filter, min_BEC_constraints_running, visited_env_traj_idxs, pool, lock
    demo_mdps, test_mdps, group_union, group_intersection, model_A, model_B, model_C, experimental_condition, variable_filter, min_BEC_constraints_running, visited_env_traj_idxs = generate_demos_test_interaction_round(args)
    
    games = list()
    for i in range(len(demo_mdps)):
        games.append({"interaction type": "demo", "params": demo_mdps[i]})

    for i in range(len(test_mdps)):
        games.append({"interaction type": "diagnostic test", "params": test_mdps[i]})

    # print('Games: ', games)

    to_add = []
    for game in games:
        if game["interaction type"] == "diagnostic test":
            new_game = copy.deepcopy(game)
            new_game["interaction type"] = "answer"
            new_game["params"]["tag"] = -1   # this is for old format used by Mike and Shenai; params is recently a mdp list
            to_add.append(new_game)
    games.extend(to_add)


    curr_group = db.session.query(Group).filter_by(id=current_user.group).first()

    curr_group.A_EOR = False
    curr_group.B_EOR = False
    curr_group.C_EOR = False

    if round == 2:
        socketio.emit("congratulations!", to=group)


    new_round = Round(group_id=group, round_num=round+1, 
                      group_union=group_union,
                      group_intersection=group_intersection,
                      member_A_model=model_A,
                      member_B_model=model_B,
                      member_C_model=model_C,
                      round_info=games,
                      status ="demo_tests_generated",
                      variable_filter=variable_filter,
                      min_BEC_constraints_running=min_BEC_constraints_running,
                      visited_env_traj_idxs=visited_env_traj_idxs,)
    db.session.add(new_round)
    db.session.commit()

    return games




# takes in state, including user input etc
# and returns params for next state
@socketio.on("settings")
def settings(data):
    loop_cond = current_user.loop_condition
    curr_domain = current_user.curr_progress[-1]
    # print(curr_domain)
    print('Curr_progress:', current_user.curr_progress, 'Curr interaction:', current_user.interaction_type)
    
    if curr_domain == "1":
        domain = current_user.domain_1
    elif curr_domain == "2":
        domain = current_user.domain_2
    elif curr_domain == "3":
        domain = current_user.domain_3
    else:
        domain = ""
    
    response = {}
    curr_group = db.session.query(Group).filter_by(id=current_user.group).first()


    if current_user.interaction_type == "survey":
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


    elif current_user.iteration > 0:
        trial = Trial(
            user_id = current_user.id,
            domain = domain,
            round = current_user.round,
            interaction_type = current_user.interaction_type,
            iteration = current_user.iteration,
            subiteration = current_user.subiteration,
            likert = int(data["survey"]),
            moves = data["user input"]["moves"],
            coordinates = data["user input"]["agent_history_nonoffset"],
            is_opt_response = data["user input"]["opt_response"],
            percent_seen = -1, #TODO: later?
            mdp_parameters = data["user input"]["mdp_parameters"],
            duration_ms = data["user input"]["simulation_rt"],
            human_model = None #TODO: later?
        )
        db.session.add(trial)


    # get data from the trial that was just completed
    # THEN try to go next

    if data["movement"] == "next":
        if current_user.last_iter_in_round:
            # # Next round when first round is loaded by default
            # if (current_user.round > 0 and
            #     db.session.query(Round).filter_by(group_id=current_user.group, round_num=1).count() == 0):
            #     retrieve_next_round()
            # elif (current_user.round == 0 and
            #     db.session.query(Round).filter_by(group_id=current_user.group, round_num=1).count() == 0):
            #     #TODO: code to load first round info
            #     x = 1

            # generate all rounds in real-time (slow process)
            print("Current group status: ", curr_group.status)
            if (current_user.round == 0 and
                db.session.query(Round).filter_by(group_id=current_user.group, round_num=1).count() == 0 and 
                curr_group.status != "Gen_demos"):
                print('Generating first round...')
                retrieve_next_round()

            else:
                round_status = ""
                while round_status != "demo_tests_generated":
                    curr_round = db.session.query(Round).filter_by(group_id=current_user.group, round_num=current_user.round+1).first()
                    if curr_round is not None:
                        round_status = curr_round.status  
                    
            # update the user's round and iteration
            current_user.round += 1
            current_user.iteration = 1  # reset iteration to 1 for new round
        else:
            current_user.iteration += 1
    elif data["movement"] == "prev":
        current_user.iteration -= 1
    

    curr_round = db.session.query(Round).filter_by(group_id=current_user.group, round_num=current_user.round).first()
    print("current round data:", curr_round, 'current_user iteration: ', current_user.iteration, 'current_user round: ', current_user.round)
    mdp_params = curr_round.round_info[current_user.iteration - 1]
    # this will short circuit if not answer, ensuring the index is never out of bounds
    # check if we just went to last test
    if (mdp_params["interaction type"] == "answer" and 
        curr_round.round_info[current_user.iteration - 2]["interaction type"] == "diagnostic test"):
        # hit EOR
        if current_user.group_code == "A":
            curr_group.A_EOR = True
            print("A reached EOR here")
        elif current_user.group_code == "B":
            curr_group.B_EOR = True
            print("B reached EOR here")
        elif current_user.group_code == "C":
            curr_group.C_EOR = True
            print("C reached EOR here")
        db.session.commit()

        if curr_group.A_EOR:
            print("A reached EOR")
        if curr_group.B_EOR:
            print("B reached EOR")
        if curr_group.C_EOR:
            print("C reached EOR")
        
        if (curr_group.groups_all_EOR()):
            print("All groups reached EOR, so i'm trying to construct the next round")
            print("Current group status: ", curr_group.status)
            if curr_group.status == "Upd_demos":
                curr_group.status = "Upd_tests"
                db.session.commit()
                update_learner_models_from_tests()
                curr_group.status = "Gen_demos"
                db.session.commit()
            
            if curr_group.status == "Gen_demos":
                print("Generating next round...")
                retrieve_next_round()
            socketio.emit("all reached EOR", to=current_user.group)


    # print('Current iteration: ', current_user.iteration, 'current mdp params are:', mdp_params)
    response["params"] = mdp_params["params"]
    current_user.interaction_type = mdp_params["interaction type"]

    if current_user.iteration == len(curr_round.round_info):
        current_user.last_iter_in_round = True
        print("Hit last iteration")
    else:
        current_user.last_iter_in_round = False
    


    # check if current iteration has been already completed
    already_completed = "false"
    if current_user.interaction_type != "survey":
        num_times_completed = db.session.query(Trial).filter_by(user_id=current_user.id,
                                                                round=current_user.round,
                                                            domain=domain,
                                                            interaction_type=current_user.interaction_type,
                                                            iteration=current_user.iteration,
                                                            subiteration=current_user.subiteration).count()
        num_times_unfinished = db.session.query(Trial).filter_by(user_id=current_user.id,
                                                                 round=current_user.round,
                                                            domain=domain,
                                                            interaction_type=current_user.interaction_type,
                                                            iteration=current_user.iteration,
                                                            subiteration=current_user.subiteration,
                                                            likert=-1).count()
        num_times_finished = num_times_completed - num_times_unfinished
        if num_times_finished > 0:
            already_completed = "true"
            # response["params"]["tag"] = -1  # this is for old format used by Mike and Shenai; params is recently a mdp list

    go_prev = "true"
    if (current_user.iteration == 1 and current_user.interaction_type == "demo") or ("test" in current_user.interaction_type and already_completed == "false") or (current_user.interaction_type == "survey"):
        go_prev = "false"

    debug_string = f"domain={domain}, interaction type={current_user.interaction_type}, iteration={current_user.iteration}, round={current_user.round}"
    
    response["debug string"] = debug_string
    response["last answer"] = current_user.last_iter_in_round
    response["interaction type"] = current_user.interaction_type
    response["already completed"] = already_completed
    response["go prev"] = go_prev

    # response["domain"] = domain
    # response["interaction type"] = current_user.interaction_type
    # response["iteration"] = current_user.iteration
    # response["subiteration"] = current_user.subiteration
    db.session.commit()
    socketio.emit("settings configured", response, to=request.sid)


    ## update the learner models based on the demos
    if curr_group.status == "Gen_demos":
        
        curr_group.status = "Upd_demos"
        db.session.commit()
        update_learner_models_from_demos()

    ##
    all_rounds = db.session.query(Round).filter_by(group_id=current_user.group).all()
    for round_data in all_rounds:
        print(round_data.id, round_data.round_num, round_data.status, round_data.group_id)




    # if data["survey "]

    # need some cases
    # if survey completed, then push to the stack
    # if movement is prev,
        # if key in ctrl stack, then get the prev idx
        # if not, then get the -1 idx item
    # if movement is next,
        # search ctrl stack for the current key,

    # key = [it, iter, subiter]
    # last_test = False

    # if key not in current_user.control_stack and it != "survey":
    #     current_user.stack_push(key)

    # if data["movement"] == "prev":
    #     old_idx = current_user.control_stack.index(key)
    #     new_idx = old_idx - 1
    #     current_user.interaction_type = current_user.control_stack[new_idx][0]
    #     current_user.iteration = current_user.control_stack[new_idx][1]
    #     current_user.subiteration = current_user.control_stack[new_idx][2]
    #     current_user.curr_trial_idx = new_idx
    #     old_trials = db.session.query(Trial).filter_by(user_id=current_user.id,
    #                                                     domain=domain,
    #                                                     interaction_type=current_user.interaction_type,
    #                                                     iteration=current_user.iteration,
    #                                                     subiteration=current_user.subiteration).all()
    #     params_list = [trial.mdp_parameters for trial in old_trials]
    #     response["params"] = params_list[0]

    # elif data["movement"] == "next":

    #     # if key not in current_user.control_stack:
    #     #     current_user.stack_push(key)
    #     #     seen = "false"
    #     # current_user.curr_trial_idx = current_user.control_stack.index(key)
    #     # print(current_user.control_stack)

    #     arr = progression[loop_cond][domain]
    #     idx = 0
    #     if (it == "remedial test") or (it == "remedial feedback"):
    #         idx = arr.index([it, iter, subiter])
    #     else:
    #         idx = arr.index([it, iter])

    #     # taking care of next progs
    #     # here is a nice little jump table
    #     if idx == len(arr) - 2:
    #         last_test = True

    #     if loop_cond == "open" or loop_cond == "debug":
    #         current_user.interaction_type = arr[idx + 1][0]
    #         current_user.iteration = arr[idx + 1][1]
    #     elif loop_cond == "pl":
    #         # todo: Mike uncomment for remedial demos and tests
    #         # if it == "diagnostic test" and data["user input"]["opt_response"]:
    #         if it == "diagnostic test":
    #             current_user.interaction_type = arr[idx + 2][0]
    #             current_user.iteration = arr[idx + 2][1]
    #         else:
    #             current_user.interaction_type = arr[idx + 1][0]
    #             current_user.iteration = arr[idx + 1][1]
    #     elif loop_cond == "cl":
    #         # todo: Mike uncomment for remedial demos and tests
    #         # if it == "diagnostic test" and data["user input"]["opt_response"]:
    #         if it == "diagnostic test":
    #             current_user.interaction_type = arr[idx + 11][0]
    #             current_user.iteration = arr[idx + 11][1]
    #         # todo: Mike uncomment for remedial demos and tests
    #         # elif it == "remedial test" and data["user input"]["opt_response"]:
    #         elif it == "remedial test":
    #             jump = 2 * (4 - subiter)
    #             current_user.interaction_type = arr[idx + jump][0]
    #             current_user.iteration = arr[idx + jump][1]
    #             current_user.subiteration = 0
    #         else:
    #             current_user.interaction_type = arr[idx + 1][0]
    #             current_user.iteration = arr[idx + 1][1]
    #             if current_user.interaction_type == ("remedial test" or "remedial feedback"):
    #                 current_user.subiteration = arr[idx + 1][2]
    #             else:
    #                 current_user.subiteration = 0

    #     response["params"] = {}

    #     # REQUIRES: domain and loop condition are the same throughout this function
    #     # it, iter, and subiter are the old versions
    #     # current_user.{interaction_type, iteration, subiteration} are the new versions

    #     if domain == "at":
    #         domain_key = "augmented_taxi2"
    #     elif domain == "ct":
    #         domain_key = "colored_tiles"
    #     else:
    #         domain_key = "skateboard2"

    #     print(current_user.interaction_type)
    #     print(current_user.iteration)
    #     if loop_cond == "cl":
    #         if current_user.interaction_type == "final test":
    #             # todo: randomize the order of the tests and also potentially account for train_test_set (currently only using the first set)
    #             if current_user.iteration < 2:
    #                 response["params"] = jsons[domain_key][current_user.interaction_type]["low"][0][current_user.iteration]
    #             elif current_user.iteration < 4:
    #                 response["params"] = jsons[domain_key][current_user.interaction_type]["medium"][0][current_user.iteration - 2]
    #             else:
    #                 response["params"] = jsons[domain_key][current_user.interaction_type]["high"][0][current_user.iteration - 4]
    #         elif current_user.interaction_type == "diagnostic feedback" or current_user.interaction_type == "remedial feedback":
    #             # normalize the actions of the optimal and (incorrect) human trajectory such that they're the same length
    #             # (by causing the longer trajectory to wait at overlapping states)
    #             opt_actions = data['user input']['mdp_parameters']['opt_actions']
    #             opt_locations = data['user input']['mdp_parameters']['opt_locations']
    #             opt_locations_tuple = [tuple(opt_location) for opt_location in opt_locations]

    #             human_actions = data["user input"]["moves"]
    #             human_locations = data["user input"]["agent_history_nonoffset"]
    #             human_locations_tuple = [(human_location[0], human_location[1], int(human_location[2])) for human_location in human_locations]

    #             normalized_opt_actions, normalized_human_actions = normalize_trajectories(opt_locations_tuple, opt_actions, human_locations_tuple, human_actions)
    #             print(normalized_opt_actions)
    #             print(normalized_human_actions)

    #             # update the relevant mdp_parameter with the normalized versions of the trajectories
    #             updated_data = data['user input']['mdp_parameters'].copy()
    #             updated_data['normalized_opt_actions'] = normalized_opt_actions
    #             updated_data['normalized_human_actions'] = normalized_human_actions
    #             updated_data['tag'] = -2 # indicate that this is trajectory visualization
    #             updated_data['human_actions'] = human_actions
    #             response["params"] = updated_data
    #         elif current_user.interaction_type == "remedial demo" or current_user.interaction_type == "remedial test":
    #             policy_constraints, min_subset_constraints_record, env_record, traj_record, traj_features_record, reward_record, mdp_features_record, consistent_state_count = domain_background_vars[domain_key]
    #             prev_mdp_parameters = data['user input']['mdp_parameters']

    #             best_env_idx, best_traj_idx = prev_mdp_parameters['env_traj_idxs']
    #             opt_traj = traj_record[best_env_idx][best_traj_idx]
    #             opt_traj_features = traj_features_record[best_env_idx][best_traj_idx]

    #             print(prev_mdp_parameters)
    #             variable_filter = np.array(prev_mdp_parameters['variable_filter'])

    #             # obtain the constraint that the participant failed to demonstrate
    #             constraint = obtain_constraint(domain_key, prev_mdp_parameters, opt_traj, opt_traj_features)

    #             # todo: need to keep track of previous_demonstrations and visited_env_traj_idxs (the two back to back empty lists), maintain PF
    #             particle_positions = BEC_helpers.sample_human_models_uniform([], 50)
    #             particles = pf.Particles(particle_positions)

    #             if current_user.interaction_type == "remedial demo": type = 'training'
    #             else: type = 'testing'

    #             remedial_mdp_dict, visited_env_traj_idxs = obtain_remedial_demonstrations(domain_key, pool, particles, params.BEC['n_human_models'], constraint,
    #             min_subset_constraints_record, env_record, traj_record, traj_features_record, [], [], variable_filter, mdp_features_record, consistent_state_count, [],
    #             params.step_cost_flag, type=type, n_human_models_precomputed=params.BEC['n_human_models_precomputed'], web_based=True)

    #             response["params"] = remedial_mdp_dict
    #         elif current_user.interaction_type != "survey":
    #             response["params"] = jsons[domain_key][current_user.interaction_type][str(current_user.iteration)]
    #     else:
    #         if "test" in current_user.interaction_type:
    #             response["params"] = jsons[domain_key]["final test"]["low"][0][0]
    #         elif current_user.interaction_type != "survey":
    #             # this is just schmutz
    #             response["params"] = jsons[domain_key]["demo"]["0"]


    


@app.route("/sign_consent", methods=["GET", "POST"])
@login_required
def sign_consent():
    current_user.consent = 1
    db.session.commit()
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
    socketio.emit("incoming group data", data, to=current_user.group, include_self=False)

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
            cond = user.set_condition("in_person" if IS_IN_PERSON else "online")
            code = user.set_code()

            db.session.add(user)

            cond.users.append(user)
            cond.count += 1

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

    # if form.validate():
    #     print("valid")

    

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
        db.session.commit()


        # They are complete and can receive their payment code
        return redirect(url_for("index"))
    print(form.errors)
    return render_template(template,
                            methods=["GET", "POST"],
                            form=form,
                            round=round)
