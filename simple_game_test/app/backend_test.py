import json
import sys, os
import random
sys.path.append(os.path.join(os.path.dirname(__file__), 'augmented_taxi'))

with open(os.path.join(os.path.dirname(__file__), 'user_study_dict.json'), 'r') as f:
    jsons = json.load(f)

def send_signal(passed_test): 
    num_demos = random.randint(1,3)
    num_tests = random.randint(1,3)
    demo = jsons["augmented_taxi2"]["demo"]["0"]
    test = jsons["augmented_taxi2"]["diagnostic test"]["0"]
    res = [demo]*num_demos
    res.extend([test]*num_tests)
    return res