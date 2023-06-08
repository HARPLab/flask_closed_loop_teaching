from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
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


    def __repr__(self):
        return "<User {}>".format(self.username)

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


class Trial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.String(64))
    trial_num = db.Column(db.Integer)
    duration_ms = db.Column(db.Float)
    rule_str = db.Column(db.String(256))
    fb_type = db.Column(db.String(32))
    cards_played = db.Column(db.PickleType)
    n_cards = db.Column(db.Integer)
    n_cards_to_learn_rule = db.Column(db.Integer)
    card_select_times = db.Column(db.PickleType)
    n_hypotheses_remaining = db.Column(db.PickleType)
    n_failed_terminations = db.Column(db.Integer)
    terminate_confidences = db.Column(db.PickleType)
    feedback_confidences = db.Column(db.PickleType)
    terminate_record = db.Column(db.PickleType)
    bonus_value = db.Column(db.String(256))
    feedback_strings = db.Column(db.PickleType)

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


