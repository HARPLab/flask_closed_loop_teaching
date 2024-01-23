from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from sqlalchemy.ext.mutable import MutableList
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
    domain_3 = db.Column(db.String(2))
    interaction_type = db.Column(db.String(20))
    iteration = db.Column(db.Integer)
    subiteration = db.Column(db.Integer)

    control_stack = db.Column(MutableList.as_mutable(db.PickleType),
                                    default=[])
    curr_trial_idx = db.Column(db.Integer)
    group = db.Column(db.Integer)
    group_code = db.Column(db.String(1))

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


# class Trial(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
#     user_id = db.Column(db.String(64))
#     trial_num = db.Column(db.Integer)
#     duration_ms = db.Column(db.Float)
#     rule_str = db.Column(db.String(256))
#     fb_type = db.Column(db.String(32))
#     cards_played = db.Column(db.PickleType)
#     n_cards = db.Column(db.Integer)
#     n_cards_to_learn_rule = db.Column(db.Integer)
#     card_select_times = db.Column(db.PickleType)
#     n_hypotheses_remaining = db.Column(db.PickleType)
#     n_failed_terminations = db.Column(db.Integer)
#     terminate_confidences = db.Column(db.PickleType)
#     feedback_confidences = db.Column(db.PickleType)
#     terminate_record = db.Column(db.PickleType)
#     bonus_value = db.Column(db.String(256))
#     feedback_strings = db.Column(db.PickleType)

class Round(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer)
    group_union = db.Column(db.PickleType)
    group_intersection = db.Column(db.PickleType)
    member_A_model = db.Column(db.PickleType)
    member_B_model = db.Column(db.PickleType)
    member_C_model = db.Column(db.PickleType)
    round_info = db.Column(db.PickleType)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_ids = db.Column(MutableList.as_mutable(db.PickleType),
                                    default=[])
    status = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    current_round = db.Column(db.Integer)
    round_data = db.Column(MutableList.as_mutable(db.PickleType),
                                    default=[])

    member_A = db.Column(db.String(50), default="")
    member_B = db.Column(db.String(50), default="")
    member_C = db.Column(db.String(50), default="")
    num_members = db.Column(db.Integer, default=0)
    
    def groups_push(self, value):
        ret = ""
        if not self.member_A:
            self.member_A = value
            ret = "A"
        elif not self.member_B:
            self.member_B = value
            ret = "B"
        elif not self.member_C:
            self.member_C = value
            ret = "C"

        self.num_members += 1
        return ret

    def groups_remove(self, value):
        ret = ""
        if self.member_A == value:
            self.member_A = ""
            ret = "A"
        elif self.member_B == value:
            self.member_B = ""
            ret = "B"
        elif self.member_C == value:
            self.member_C = ""
            ret = "C"

        self.num_members -= 1
        return ret
    
    def get_group(self):
        return {"A":bool(self.member_A), "B":bool(self.member_B), "C":bool(self.member_C)}

class Trial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.String(64))
    duration_ms = db.Column(db.Float)
    domain = db.Column(db.String(2))
    interaction_type = db.Column(db.String(20))

    # new defining numbers, can reference round and iteration to 
    # retrieve the corresponding environment variables in the Round db
    round = db.Column(db.Integer)
    iteration = db.Column(db.Integer)

    # subiteration = db.Column(db.Integer)
    likert = db.Column(db.Integer)
    moves = db.Column(db.PickleType)
    coordinates = db.Column(db.PickleType)
    is_opt_response = db.Column(db.Boolean)
    percent_seen = db.Column(db.Float)
    mdp_parameters = db.Column(db.PickleType)
    human_model = db.Column(db.PickleType)

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


