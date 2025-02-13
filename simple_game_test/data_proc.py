
import sqlite3
import pandas as pd
import dill as pickle
import sys
from pathlib import Path

# Add the project root directory to Python path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.group_teaching.codes.simple_rl import *

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import teams.particle_filter_team as pf_team
from numpy import array
import os, sys



def print_table_data(database_file):
    try:
        
        print("Database file exists:", os.path.exists(database_file))

        
        
        # Connect to the database
        conn = sqlite3.connect(database_file)
        cursor = conn.cursor()

        # Fetch all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        # cursor.execute("SELECT * FROM [group]")   # Since group is a reserved keyword, you need to escape it in queries.
        # cursor.execute("SELECT * FROM [1]")  



        tables = cursor.fetchall()

        if not tables:
            print("No tables found in the database.")
            return

        # Iterate through each table and print its data
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            cursor.execute(f"SELECT * FROM [{table_name}]")
            rows = cursor.fetchall()

            # Fetch column names
            column_names = [description[0] for description in cursor.description]
            print(" | ".join(column_names))  # Print column headers

            # # Print each row
            # for row in rows:
            #     print(" | ".join(map(str, row)))

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Close the database connection
        if conn:
            conn.close()




def convert_db_to_excel(database_file, output_excel_file):
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(database_file)
        
        # Fetch all table names
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if not tables:
            print("No tables found in the database.")
            return

        # Create a Pandas Excel writer
        with pd.ExcelWriter(output_excel_file, engine='openpyxl') as writer:
            # Iterate through each table and save its data to a separate Excel sheet
            for table in tables:
                table_name = table[0]
                print(f"Exporting table: {table_name}")

                # Escape table names that may contain reserved keywords
                escaped_table_name = f"[{table_name}]"

                # Read table data
                cursor.execute(f"SELECT * FROM {escaped_table_name}")
                rows = cursor.fetchall()

                # Fetch column names
                column_names = [description[0] for description in cursor.description]
                print(" | ".join(column_names))  # Print column headers

                # Process rows to deserialize PickleType columns
                processed_rows = []
                for row in rows:
                    processed_row = []
                    for value in row:
                        # Attempt to deserialize pickle data, otherwise keep the original value
                        if isinstance(value, bytes):
                            try:
                                processed_value = pickle.loads(value)
                            except (pickle.UnpicklingError, EOFError, AttributeError):
                                processed_value = value  # Leave as-is if unpickling fails
                        else:
                            processed_value = value
                        processed_row.append(processed_value)
                    processed_rows.append(processed_row)

                # Convert to a DataFrame
                df = pd.DataFrame(processed_rows, columns=column_names)

                # Write DataFrame to an Excel sheet
                df.to_excel(writer, sheet_name=table_name, index=False)

                # Write DataFrame to a pickle file
                df.to_pickle(f"{table_name}.pkl")

        
        print(f"Database converted to Excel file: {output_excel_file}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Close the database connection
        if conn:
            conn.close()



#################################################################


def plot_prob_learning():
    # # Load the data from the Excel file
    # file_path = 'output.xlsx'
    # round_data = pd.read_excel(file_path, sheet_name='round')
    # domain_params_data = pd.read_excel(file_path, sheet_name='domain_params')

    with open('round.pkl', 'rb') as f:
        round_data = pickle.load(f)

    with open('domain_params.pkl', 'rb') as f:
        domain_params_data = pickle.load(f)

    # # Extract 'min_BC_constraints' from the domain_params sheet
    # domain_params_data['min_BC_constraints'] = domain_params_data['min_BEC_constraints'].apply(
    #     lambda x: np.array(eval(x)[0]) if isinstance(x, str) else None
    # )


    # Group data by domain, group, and player for separate analysis
    grouped_round_data = round_data.groupby(['domain', 'group_id'])

    # Process each group for separate plotting
    for (domain, group), group_data in grouped_round_data:
        print(f"\nDomain: {domain}, Group: {group}")
        if group==18:
            rounds = group_data['round_num'].tolist()
            statuses = group_data['status'].tolist()
            kc_ids = group_data['kc_id'].tolist()

            prob_unit_learning = {}
            prob_BEC_learning = {}
            prob_learning = {}
            member_info = {}

            for rnd_id, rnd in group_data.iterrows():
                members_statuses = rnd.members_statuses
                min_kc_constraints = np.array(rnd['min_KC_constraints'])
                min_bec_constraints = np.array(rnd['min_BEC_constraints_running'])
                domain_constraints = np.array(domain_params_data[(domain_params_data['domain_name'] == domain)]['min_BEC_constraints'])

                if domain == 'sb':
                    domain_constraints = np.array([np.array([[5, 2, 5]]), np.array([[ 3, -3,  1]]), np.array([[-6,  4, -3]])])
                elif domain == 'at':
                    domain_constraints = np.array([np.array([[1, 1, 0]]), np.array([[ 0, -1, -4]]), np.array([[-1,  0,  2]])])

                # print('Domain constraints:', domain_constraints)

                
                for model_id in range(3):    
                    if members_statuses[model_id] == 'joined':   
                        particles_pos = np.array(rnd.ind_member_models_pos[0][model_id])
                        particles_weights = np.array(rnd.ind_member_models_weights[0][model_id])

                        # print(particles_pos)
                        # print(particles_weights)
                        # print(min_kc_constraints)
                        # print(min_bec_constraints)
                        # print(domain_constraints)

                        member_str = f'Rnd: {rnd_id}, Model: {model_id}'

                        pf = pf_team.Particles_team(particles_pos, 0.8, 36)
                        pf.weights = particles_weights

                        member_info[model_id] = member_str

                        # Calculate probabilities
                        if model_id not in prob_unit_learning:
                            prob_unit_learning[model_id] = []
                            prob_BEC_learning[model_id] = []
                            prob_learning[model_id] = []
                        pf.calc_particles_probability(min_kc_constraints)
                        prob_unit_learning[model_id].append(pf.particles_prob_correct)
                        # print('prob_unit_learning:', prob_unit_learning)

                        pf.calc_particles_probability(min_bec_constraints)
                        prob_BEC_learning[model_id].append(pf.particles_prob_correct)
                        # print('prob_BEC_learning:', prob_BEC_learning)

                        pf.calc_particles_probability(domain_constraints)
                        prob_learning[model_id].append(pf.particles_prob_correct)
                        # print('prob_learning:', prob_learning)
                    


    # Plot the probabilities for the current domain, group, and player
    for model_id in range(3):
        if len(prob_unit_learning[model_id]) > 0:  # Only plot if data exists
            plt.figure(figsize=(12, 6))
            plt.plot(rounds, prob_unit_learning[model_id], label=f'Model {model_id} Probability Unit Learning', marker='o', linestyle='-')
            plt.plot(rounds, prob_BEC_learning[model_id], label=f'Model {model_id} Probability BEC Learning', marker='x', linestyle='--')
            plt.plot(rounds, prob_learning[model_id], label=f'Model {model_id} Probability BC Learning', marker='s', linestyle=':')
            plt.xlabel('Round')
            plt.ylabel('Probability of Learning')
            plt.title(f'Learning Probabilities for Domain: {domain}, Group: {group}, Player: {model_id}')
            plt.legend()
            plt.grid()
            plt.show()

#####################################



# Replace 'app.db' with your database file and 'output.xlsx' with the desired Excel file name
convert_db_to_excel('app.db', 'output_debug_feb13.xlsx')

# print_table_data('app_bf_jan30.db')

# plot_prob_learning()




