from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.models import User, Trial, Demo, Survey, Domain, Group, Round, DomainParams, OnlineCondition, InPersonCondition
import matplotlib.pyplot as plt


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy object
db = SQLAlchemy(app)


# @app.route('/rounds')
# def get_rounds():
#     rounds = Round.query.all()  # Fetch all records from the 'Round' table
    
#     # Prepare the data as a list of dictionaries
#     rounds_data = []
#     for rnd in rounds:
#         rounds_data.append({
#             'id': rnd.id,
#             'status': rnd.status,
#             'group_id': rnd.group_id,
#             'round_num': rnd.round_num,
#             'group_union': rnd.group_union,
#             'group_intersection': rnd.group_intersection,
#             'member_A_model': rnd.member_A_model,
#             'member_B_model': rnd.member_B_model,
#             'member_C_model': rnd.member_C_model,
#             'variable_filter': rnd.variable_filter,
#             'min_BEC_constraints_running': rnd.min_BEC_constraints_running,
#             'visited_env_traj_idxs': rnd.visited_env_traj_idxs,
#             'round_info': rnd.round_info,
#             'last_round': rnd.last_round
#         })
    
#     return {"rounds": rounds_data}

# Function to plot member_A_model for the last few rounds
def plot_last_few_rounds(group_id):
    # Fetch the last few rounds ordered by round_num or id, limited by the 'limit' parameter
    last_few_rounds = Round.query.filter_by(group_id=group_id).order_by(Round.round_num.desc()).all()
    
    for rnd in last_few_rounds:
        if rnd.member_A_model:
            # Assuming member_A_model has a plot function
            plt.figure()  # Create a new figure for each plot
            rnd.member_A_model.plot()  # Call the plot method of the class
            
            # Save the plot or display it
            plt.title(f"Plot for member A Round {rnd.id} (Round Number: {rnd.round_num})")
            plt.savefig(f'plot_round_memb_A_{rnd.id}.png')  # Save the plot to a file
            plt.close()  # Close the figure after saving to avoid memory issues
        else:
            print(f"No member_A_model for round {rnd.id}")

        if rnd.member_B_model:
            # Assuming member_A_model has a plot function
            plt.figure()  # Create a new figure for each plot
            rnd.member_B_model.plot()  # Call the plot method of the class
            
            # Save the plot or display it
            plt.title(f"Plot for member B Round {rnd.id} (Round Number: {rnd.round_num})")
            plt.savefig(f'plot_round_memb_B_{rnd.id}.png')  # Save the plot to a file
            plt.close()  # Close the figure after saving to avoid memory issues
        else:
            print(f"No member_B_model for round {rnd.id}")

        if rnd.member_C_model:
            # Assuming member_A_model has a plot function
            plt.figure()  # Create a new figure for each plot
            rnd.member_C_model.plot()  # Call the plot method of the class
            
            # Save the plot or display it
            plt.title(f"Plot for member C Round {rnd.id} (Round Number: {rnd.round_num})")
            plt.savefig(f'plot_round_memb_C_{rnd.id}.png')  # Save the plot to a file
            plt.close()  # Close the figure after saving to avoid memory issues
        else:
            print(f"No member_C_model for round {rnd.id}")


# Running the Flask app
if __name__ == '__main__':
    with app.app_context():
        plot_last_few_rounds(1)  # Call the function to plot the last 5 rounds