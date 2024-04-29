import json
import sys, os
import random
sys.path.append(os.path.join(os.path.dirname(__file__), 'augmented_taxi'))

with open(os.path.join(os.path.dirname(__file__), 'user_study_dict.json'), 'r') as f:
    jsons = json.load(f)



def send_signal(passed_test): 
    num_demos = 1 #random.randint(1,3)
    num_tests = 1 #random.randint(1,2)
    res = []
    for d in range(num_demos):
        # print(blah)
        params = jsons["augmented_taxi2"]["demo"][str(random.randint(0, 4))]
        res.append({"interaction type": "demo", "params": params})
    for t in range(num_tests):
        params = jsons["augmented_taxi2"]["diagnostic test"][str(random.randint(0, 3))]
        res.append({"interaction type": "test", "params": params})
    return res