from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm.attributes import flag_modified
import random
import string

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    
    # trials = db.relationship("Trial", backref="author", lazy="dynamic")
    demos = db.relationship("Demo", backref="author", lazy="dynamic")
    surveys = db.relationship("Survey", backref="author", lazy="dynamic")

    condition_id = db.Column(db.Integer, db.ForeignKey("condition.id"))
    online_condition_id = db.Column(db.Integer, db.ForeignKey("online_condition.id"))
    in_person_condition_id = db.Column(db.Integer, db.ForeignKey("in_person_condition.id"))

    study_type = db.Column(db.PickleType)
    code = db.Column(db.String(20))
    feedback_counts = db.Column(db.PickleType)
    consent = db.Column(db.Integer)
    training = db.Column(db.Integer)
    age = db.Column(db.Integer)
    gender = db.Column(db.Integer)
    ethnicity = db.Column(db.PickleType)
    education = db.Column(db.Integer)
    robot = db.Column(db.Integer)
    browser = db.Column(db.String(256))
    final_robot_choice = db.Column(db.Integer)
    final_feedback = db.Column(db.PickleType)
    num_trials_completed = db.Column(db.Integer)

    attention_check = db.Column(db.Integer)
    study_completed = db.Column(db.Integer)

    curr_progress = db.Column(db.String(50))
    loop_condition = db.Column(db.String(4))
    domain_1 = db.Column(db.String(2))
    domain_2 = db.Column(db.String(2))
    # domain_3 = db.Column(db.String(2))
    interaction_type = db.Column(db.String(20))
    iteration = db.Column(db.Integer)
    subiteration = db.Column(db.Integer)

    # refers to the corresponding number in the round database
    # the round database will have a primary key but it'll also have a column for group number and round number in that group
    # the round attribute for the user will refer to that round number; you can find this by querying the round w/ group number
    round = db.Column(db.Integer, default=0)
    # last_iter_in_domain = db.Column(db.Boolean, default=False)
    last_iter_in_round = db.Column(db.Boolean, default=True)
    last_test_in_round = db.Column(db.Boolean, default=True)

    control_stack = db.Column(MutableList.as_mutable(db.PickleType),
                                    default=[])
    curr_trial_idx = db.Column(db.Integer)
    group = db.Column(db.Integer)
    group_code = db.Column(db.Integer)
    group_member_id = db.Column(db.Integer)

    def __repr__(self):
        return "<User {}>".format(self.username)
    
    def stack_push(self, value):
        self.control_stack.append(value)
        return self.control_stack

    def set_curr_progress(self, value):
        self.curr_progress = value
        return value

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_attention_check(self, value):
        self.attention_check = value
        return value

    def set_browser(self, value):
        self.browser = value
        return value

    def set_condition(self, cond_type=""):
        min_count = 0
        min_cond = ""
        if cond_type == "online":
            min_count = db.session.query(func.min(OnlineCondition.count)).scalar()
            min_cond = db.session.query(OnlineCondition).filter_by(count = min_count).first()
            print(min_cond)
        elif cond_type == "in_person":
            min_count = db.session.query(func.min(InPersonCondition.count)).scalar()
            min_cond = db.session.query(InPersonCondition).filter_by(count = min_count).first()
        else: # Roshni default code
            min_count = db.session.query(func.min(Condition.count)).scalar()
            min_cond = db.session.query(Condition).filter_by(count = min_count).first()
        self.condition_id 
        self.study_type = cond_type
        return min_cond

    def set_code(self, code='CYTO5M8C'):
        self.code = code
        return code

    def set_completion(self, status):
        self.study_completed = status
        return status

    def set_num_trials_completed(self, num):
        self.num_trials_completed = num
        return num

@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(2))
    status = db.Column(db.String(20)) #demos_tests_generated, demos_updated, tests_updated
    group_id = db.Column(db.Integer)
    round_num = db.Column(db.Integer)
    members_statuses = db.Column(db.PickleType)
    kc_id = db.Column(db.PickleType)
    min_KC_constraints = db.Column(db.PickleType)
    variable_filter = db.Column(db.PickleType)
    nonzero_counter = db.Column(db.PickleType)
    min_BEC_constraints_running = db.Column(db.PickleType)
    prior_min_BEC_constraints_running = db.Column(db.PickleType)
    visited_env_traj_idxs = db.Column(db.PickleType)
    round_info = db.Column(db.PickleType)  # the MDPS of demos and tests
    last_round = db.Column(db.Boolean) # only know this after the last round is completed

    # list of list; one for each iteration
    ind_member_models_pos = db.Column(MutableList.as_mutable(db.PickleType), default=[])
    ind_member_models_weights = db.Column(MutableList.as_mutable(db.PickleType), default=[])
    group_union_model_pos = db.Column(MutableList.as_mutable(db.PickleType), default=[])
    group_union_model_weights = db.Column(MutableList.as_mutable(db.PickleType), default=[])
    group_intersection_model_pos = db.Column(MutableList.as_mutable(db.PickleType), default=[])
    group_intersection_model_weights = db.Column(MutableList.as_mutable(db.PickleType), default=[])
    group_knowledge = db.Column(MutableList.as_mutable(db.PickleType), default=[])


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_ids = db.Column(MutableList.as_mutable(db.PickleType),
                                    default=[])
    status = db.Column(db.String(10)) # 
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    current_round = db.Column(db.Integer, default=0)
    round_data = db.Column(MutableList.as_mutable(db.PickleType),
                                    default=[])
    
    members = db.Column(db.PickleType)
    member_user_ids = db.Column(db.PickleType)
    num_members = db.Column(db.Integer, default=0)
    num_active_members = db.Column(db.Integer, default=0)
    members_statuses = db.Column(db.PickleType)
    members_EOR = db.Column(db.PickleType)

    members_last_test = db.Column(db.PickleType)

    ind_member_models = db.Column(db.PickleType)
    group_union_model = db.Column(db.PickleType)
    group_intersection_model = db.Column(db.PickleType)
    models_update_iteration = db.Column(db.Integer, default=0)

    group_knowledge = db.Column(db.PickleType)


    first_round_status = db.Column(db.String(20))
    experimental_condition = db.Column(db.String(50))

    # domain_1 = db.Column(db.String(2), default="at")
    # domain_2 = db.Column(db.String(2))
    # domain_3 = db.Column(db.String(2))

    domains = ["at", "sb"]
    # rand.shuffle(domains)
    domain_1 = domains[0]
    domain_2 = domains[1]

    curr_progress = "domain_1"


    def groups_all_EOR(self):
        EOR_list = []
        for idx in range(self.num_members):
            if self.members_statuses[idx] == "joined":
                EOR_list.append(self.members_EOR[idx])

        return all(EOR_list)

    def group_last_test(self):
        last_test_list = []
        for idx in range(self.num_members):
            if self.members_statuses[idx] == "joined":
                last_test_list.append(self.members_last_test[idx])

        return all(last_test_list)


    
    def groups_push(self, value, user_id):
        
        ret = ""
        print('Before. num_members:', self.num_members, 'member statuses:', self.members_statuses, 'members:', self.members, 'members EOR:', self.members_EOR, 'members user ids:', self.member_user_ids)
        for idx in range(self.num_members):
            if self.members_statuses[idx] != "joined":
                self.members[idx] = value
                self.member_user_ids[idx] = user_id
                self.members_statuses[idx] = "joined"
                self.num_active_members += 1
                ret = int(idx)

                # mark changes
                flag_modified(self, "members")
                flag_modified(self, "member_user_ids")
                flag_modified(self, "members_statuses")
                flag_modified(self, "num_active_members")
                break
        if ret == "":
            RuntimeError("Member cannot be added to group")
        
        print('After. num_members:', self.num_members, 'member statuses:', self.members_statuses, 'members:', self.members, 'members EOR:', self.members_EOR, 'members user ids:', self.member_user_ids)
        
        return self, ret, self.domain_1, self.domain_2
    
    def groups_remove(self, value):

        ret = ""
        print('num_members:', self.num_members, 'member statuses:', self.members_statuses, 'members:', self.members, 'members EOR:', self.members_EOR, 'members user ids:', self.member_user_ids)
        for idx in range(self.num_members):
            if self.members[idx] == value:
                self.members_statuses[idx] = "left"
                ret = int(idx)
                self.num_active_members -= 1
                flag_modified(self, "members_statuses")
                flag_modified(self, "num_active_members")
                flag_modified(self, "members")
                break

        if ret == "":
            RuntimeError("No member found to remove")

        return ret
    
    # def get_group(self):
    #     return {"A":bool(self.member_A), "B":bool(self.member_B), "C":bool(self.member_C)}


class Trial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.String(64))
    group_code = db.Column(db.String(1))
    duration_ms = db.Column(db.Float)
    domain = db.Column(db.String(2))
    interaction_type = db.Column(db.String(20))

    # new defining numbers, can reference round and iteration to 
    # retrieve the corresponding environment variables in the Round db
    group = db.Column(db.Integer)
    round = db.Column(db.Integer)
    iteration = db.Column(db.Integer)

    subiteration = db.Column(db.Integer) # don't need this
    likert = db.Column(db.Integer)
    moves = db.Column(db.PickleType)
    coordinates = db.Column(db.PickleType)
    is_opt_response = db.Column(db.Boolean)
    mdp_parameters = db.Column(db.PickleType)
    human_model = db.Column(db.PickleType) # don't need this
    is_first_time = db.Column(db.Boolean, default=True)
    num_visits = db.Column(db.Integer)



class Domain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.String(64))
    domain_name = db.Column(db.String(2))
    attn1 = db.Column(db.Integer)
    attn2 = db.Column(db.Integer)
    attn3 = db.Column(db.Integer)
    use1 = db.Column(db.Integer)
    use2 = db.Column(db.Integer)
    use3 = db.Column(db.Integer)
    short_answer = db.Column(db.PickleType)


class DomainParams(db.Model):
    domain_name = db.Column(db.String(2), primary_key=True)
    min_subset_constraints_record = db.Column(db.PickleType)
    env_record = db.Column(db.PickleType)
    traj_record = db.Column(db.PickleType) 
    traj_features_record = db.Column(db.PickleType) 
    mdp_features_record = db.Column(db.PickleType) 
    consistent_state_count = db.Column(db.PickleType)
    min_BEC_constraints = db.Column(db.PickleType)



class Demo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    round_num = db.Column(db.Integer)
    demo_num = db.Column(db.Integer)
    card_num = db.Column(db.Integer)
    correct_bin = db.Column(db.Integer)
    rule_set = db.Column(db.PickleType)

class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    round_num = db.Column(db.Integer)
    frustration = db.Column(db.Integer)
    utility_of_feedback = db.Column(db.Integer)
    ease_of_teaching = db.Column(db.Integer)
    opt_text = db.Column(db.Text)
   
class Condition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    difficulty = db.Column(db.PickleType)
    nonverbal = db.Column(db.PickleType)
    count = db.Column(db.Integer)
    users = db.relationship('User', backref='person', lazy="dynamic")

class OnlineCondition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trials = db.Column(db.PickleType)
    feedback_type = db.Column(db.PickleType)
    no_feedback_trial = db.Column(db.PickleType)
    feedback_trial = db.Column(db.PickleType)
    count = db.Column(db.Integer)
    users = db.relationship('User', backref='online_user', lazy="dynamic")

class InPersonCondition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trials = db.Column(db.PickleType)
    trial_1 = db.Column(db.PickleType)
    trial_2 = db.Column(db.PickleType)
    trial_3 = db.Column(db.PickleType)
    trial_4 = db.Column(db.PickleType)
    trial_5 = db.Column(db.PickleType)
    count = db.Column(db.Integer)
    users = db.relationship('User', backref='in_person_user', lazy="dynamic")


