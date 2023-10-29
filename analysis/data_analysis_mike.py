import sqlite3
import pandas as pd
import pickle
import numpy as np
import scipy
from math import sqrt
from statsmodels.stats.power import TTestIndPower
import pdb
import pingouin as pg
import sys, os
import csv
from datetime import datetime

cur_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(cur_dir + '/../simple_game_test/app/augmented_taxi/policy_summarization'))
# import policy_summarization.BEC_helpers as BEC_helpers


# Pallavi To-do Items:
# [ ] Users never get the same rule 2x
# [ ] Disallow clicking on a card that has already been clicked
# [ ] Make "which of the two robots did you prefer" a radio response option, with a textbox for explanation afterwards.
# [ ] df_users['unpickled_feedback_counts'] = df_users['feedback_counts'].apply(pickle.loads) THIS IS A HOLDOVER FROM ROSHNI, DELETE FROM MODEL.


# ---------------------------------- Global Variables ---------------------------------- #
CONFIDENCE_MAPPING = {0: '0 - Strongly Disagree', 1: '1 - Disagree', 2: '2 - Neutral', 3: '3 - Agree',
                      4: '4 - Strongly Agree'}
FRUSTRATION_MAPPING = {0: '0 - Extremely Frustrating', 1: '1 - Somewhat Frustrating',
                       2: '2 - Neither Frustrating nor Pleasant', 3: '3 - Somewhat Pleasant',
                       4: '4 - Extremely Pleasant'}

ONLINE_INTERACTION_TYPES = ['no_feedback', 'showing', 'preference', 'binary_combined', 'credit_assignment']

alpha = 0.05

skip_users = []
# remove users who are missing data (reward weight estimates)
skip_users.extend(['58aca85e0da7f10001de92d4', '602fb33786b077cdbad2d5bb'])
# remove users who did not complete the study
skip_users.extend(['614b55e22ff3944a165736bb', '5f0214e58782120a8c970fd6'])
# remove users who perfectly went through the closed-loop teaching framework (and thus did not see any remedial instruction)
skip_users.extend(['59dbbdce5de9b000017ebf19'])
# remove users who underwent more than 3 std dev more interactions than the average in the closed-loop teaching framework
skip_users.extend(['5ebd5fa512c47d04402403da'])

# ---------------------------------- Data Processing ---------------------------------- #
def get_data():
    conn = sqlite3.connect('app.db')

    # Set up Users db
    df_users = pd.read_sql_query('SELECT * FROM user', conn)
    df_users['user_id'] = df_users['id'].astype(np.int64)
    df_users = df_users[df_users['study_completed'] != 0]
    # df_users = df_users[df_users['username'].map(lambda d: d not in ['mt1', 'mt3'])]  # remove users who didn't complete the study
    df_users['unpickled_study_type'] = df_users['study_type'].apply(pickle.loads)
    df_users['unpickled_ethnicity'] = df_users['ethnicity'].apply(pickle.loads)
    df_users['unpickled_final_feedback'] = df_users['final_feedback'].apply(pickle.loads)

    # only parse the columns that I want
    df_users = df_users[['username', 'consent', 'age', 'gender', 'unpickled_ethnicity', 'education', 'unpickled_final_feedback', 'loop_condition', 'domain_1', 'domain_2', 'domain_3', 'user_id']]

    # Set up Trials db
    df_trials = pd.read_sql_query('SELECT * FROM trial', conn)
    df_trials['user_id'] = df_trials['user_id'].astype(np.int64)
    df_trials = df_trials[df_trials['user_id'].map(lambda d: d in df_users.user_id.unique())] # remove users who didn't complete the study
    df_trials['unpickled_human_model_pf_weights'] = df_trials['human_model_pf_weights'].apply(pickle.loads)
    df_trials['unpickled_human_model_pf_pos'] = df_trials['human_model_pf_pos'].apply(pickle.loads)
    df_trials['unpickled_mdp_parameters'] = df_trials['mdp_parameters'].apply(pickle.loads)
    df_trials['unpickled_reward_ft_weights'] = df_trials['reward_ft_weights'].apply(pickle.loads)
    df_trials['unpickled_improvement_short_answer'] = df_trials['improvement_short_answer'].apply(pickle.loads)
    df_trials['unpickled_moves'] = df_trials['moves'].apply(pickle.loads)
    df_trials['test_difficulty'] = df_trials['unpickled_mdp_parameters'].apply(lambda x: x['test_difficulty'])


    # Set up Domain db (which contains the training likert scales)
    df_domain = pd.read_sql_query('SELECT * FROM domain', conn)
    df_domain['user_id'] = df_domain['user_id'].astype(np.int64)
    df_domain = df_domain[df_domain['user_id'].map(lambda d: d in df_users.user_id.unique())] # remove users who didn't complete the study
    df_domain['unpickled_engagement_short_answer'] = df_domain['engagement_short_answer'].apply(pickle.loads)
    df_domain = df_domain[['user_id', 'domain', 'attn1', 'attn2', 'attn3', 'use1', 'use2', 'use3', 'understanding', 'unpickled_engagement_short_answer']]

    df_trials = df_trials[df_trials.user_id.isin(df_users.user_id)]
    df_domain = df_domain[df_domain.user_id.isin(df_users.user_id)]

    df_trials = pd.merge(df_trials, df_users, on='user_id')
    df_domain = pd.merge(df_domain, df_users, on='user_id')

    conn.close()

    return df_users, df_trials, df_domain

# ---------------------------------- Helper Functions ---------------------------------- #
def id_to_confidence(id):
    return CONFIDENCE_MAPPING[int(id)]

def id_to_frustration(id):
    return FRUSTRATION_MAPPING[int(id)]

def print_demographics(df_users):
    print("\n========== DEMOGRAPHICS ==========")
    a = 2

    print("Conditions Represented (want 64 of each): ")
    print(df_users.loop_condition.value_counts())
    print("Conditions Represented (want 32 of each): ")
    print("cl: ")
    print(df_users[df_users.loop_condition == 'cl'].domain_1.value_counts())
    print("pl: ")
    print(df_users[df_users.loop_condition == 'pl'].domain_1.value_counts())
    print("open: ")
    print(df_users[df_users.loop_condition == 'open'].domain_1.value_counts())

    print("Ages (description)")
    ages = pd.to_numeric(df_users.age)
    print(ages.describe())

    print("Genders: ")
    gender_vals = [0, 0, 0, 0]
    mapping = {0: 'Male', 1: 'Female', 2: 'Non-binary', 3: 'Prefer not to disclose'} # todo: change to 0, 1, 2, 3 for the new data
    answers = df_users.gender
    for answer in answers:
        gender_vals[int(answer)] += 1

    for idx, num in enumerate(gender_vals):
        print(mapping[idx] + " : " + str(num) + " (" + str(num / (np.sum(gender_vals))) + "%)")


# ---------------------------------- Subjective Metrics ---------------------------------- #


# ----------------------------------  Objective Metrics ---------------------------------- #
def post_hoc(aov, location, dv, between, data):
    if ('p-GG-corr' in aov and aov['p-GG-corr'].iloc[location] < alpha) or ('p-GG-corr' not in aov and aov['p-unc'].iloc[location] < alpha):
        print('Reject H0: different distributions across {}. Perform post-hoc Tukey HSD.'.format(aov['Source'][location]))
        try:
            print("Corrected p-val: {}, DOF effect: {}, DOF error: {}, F: {}".format(aov['p-GG-corr'][location], aov['DF1'][location], aov['DF2'][location], aov['F'][location]))
        except:
            print("Uncorrected p-val: {}, DOF effect: {}, DOF error: {}, F: {}".format(aov['p-unc'][location], aov['DF1'][location], aov['DF2'][location], aov['F'][location]))

        pt = pg.pairwise_tukey(dv=dv, between=between, data=data)
        print(pt)
    else:
        print('Accept H0: Same distributions across {}.'.format(aov['Source'][location]))


def compare_feedback_domain_on_performance(df_trials):
    # todo: could consider analyzing the scaled rewards of answers rather than binary correctness

    print("\n========== ANOVA: TEST DEMONSTRATION PERFORMANCE ==========")
    aov = pg.mixed_anova(dv='is_opt_response', within='domain', subject='username', between='loop_condition',
                      data=df_trials, correction=True)

    post_hoc(aov, 0, 'is_opt_response', 'loop_condition', df_trials)
    post_hoc(aov, 1, 'is_opt_response', 'domain', df_trials)

    if ('p-GG-corr' in aov and aov['p-GG-corr'].iloc[2] < alpha) or ('p-GG-corr' not in aov and aov['p-unc'].iloc[2] < alpha):
        print("There is an interaction effect between {} and {}! Check out manually".format(aov['Source'][0], aov['Source'][1]))
    else:
        print("There is no interaction effect between {} and {}".format(aov['Source'][0], aov['Source'][1]))

def compare_feedback_domain_on_engagement(df_domain):
    print("\n========== ANOVA: ENGAGEMENT ==========")

    df_domain_engagement = pd.DataFrame(
        columns=['username', 'domain', 'loop_condition', 'engagement'])
    for username in np.unique(df_domain.username):
        for domain in np.unique(df_domain.domain):
            engagement = (df_domain[(df_domain.username == username) & (df_domain.domain == domain)].attn1 + df_domain[(df_domain.username == username) & (df_domain.domain == domain)].attn2 + \
                        df_domain[(df_domain.username == username) & (df_domain.domain == domain)].attn3 - df_domain[(df_domain.username == username) & (df_domain.domain == domain)].use1 - \
                        df_domain[(df_domain.username == username) & (df_domain.domain == domain)].use2 - df_domain[(df_domain.username == username) & (df_domain.domain == domain)].use3) / 6

            loop_condition = df_domain[df_domain.username == username].loop_condition.values[0]

            df_domain_engagement = pd.concat((df_domain_engagement, pd.DataFrame({'username': username, 'loop_condition': loop_condition, 'domain': domain,
                               'engagement': engagement})), axis=0, ignore_index=True)

    print("\n========== ANOVA: ENGAGEMENT ==========")
    aov = pg.mixed_anova(dv='engagement', within='domain', subject='username', between='loop_condition',
                      data=df_domain_engagement, correction=True)

    post_hoc(aov, 0, 'engagement', 'loop_condition', df_domain_engagement)
    post_hoc(aov, 1, 'engagement', 'domain', df_domain_engagement)

    if ('p-GG-corr' in aov and aov['p-GG-corr'].iloc[2] < alpha) or ('p-GG-corr' not in aov and aov['p-unc'].iloc[2] < alpha):
        print("There is an interaction effect between {} and {}! Check out manually".format(aov['Source'][0], aov['Source'][1]))
    else:
        print("There is no interaction effect between {} and {}".format(aov['Source'][0], aov['Source'][1]))


def compare_feedback_on_improvement(df_trials):
    print("\n========== KRUSKAL: IMPROVEMENT SUBJECTIVE RATING ==========")

    # check if feedback affects ratings on improvement
    data = df_trials[df_trials.likert > 0]

    df_trials_improvement = pd.DataFrame(
        columns=['username', 'domain', 'loop_condition', 'median_improvement'])

    for username in np.unique(data.username):
        for domain in np.unique(data.domain):
            median_improvement = float(np.median(data[(data.username == username) & (data.domain == domain)].likert))

            loop_condition = data[data.username == username].loop_condition.values[0]

            df_trials_improvement = pd.concat([df_trials_improvement, pd.DataFrame([{'username': username, 'loop_condition': loop_condition, 'domain': domain,
                                   'median_improvement': median_improvement}])], ignore_index=True)

    data_at = df_trials_improvement[df_trials_improvement.domain == 'at']
    kruskal = pg.kruskal(dv='median_improvement', between='loop_condition',
                         data=data_at)

    if kruskal['p-unc'][0] < alpha / 2:
        print("There is a significant difference on {} between the {} conditions for taxi!".format('median_improvement', 'loop'))

        # if the anova is significant, run a post-hoc test (per domain)
        mwu = pg.mwu(data_at[data_at.loop_condition == 'cl'].median_improvement,
                     data_at[data_at.loop_condition == 'open'].median_improvement)
        print(mwu)
        mwu = pg.mwu(data_at[data_at.loop_condition == 'cl'].median_improvement,
                     data_at[data_at.loop_condition == 'pl'].median_improvement)
        print(mwu)
        mwu = pg.mwu(data_at[data_at.loop_condition == 'pl'].median_improvement,
                     data_at[data_at.loop_condition == 'open'].median_improvement)
        print(mwu)
    else:
        print("There is no significant difference on {} between the {} conditions for taxi".format(
            'median_improvement', 'loop'))


    data_sb = df_trials_improvement[df_trials_improvement.domain == 'sb']
    kruskal = pg.kruskal(dv='median_improvement', between='loop_condition',
                         data=data_sb)

    if kruskal['p-unc'][0] < alpha / 2:
        print("There is a significant difference on {} between the {} conditions for skateboard!".format('median_improvement', 'loop'))

        # if the anova is significant, run a post-hoc test (per domain)
        mwu = pg.mwu(data_sb[data_sb.loop_condition == 'cl'].median_improvement,
                     data_sb[data_sb.loop_condition == 'open'].median_improvement)
        print(mwu)
        mwu = pg.mwu(data_sb[data_sb.loop_condition == 'cl'].median_improvement,
                     data_sb[data_sb.loop_condition == 'pl'].median_improvement)
        print(mwu)
        mwu = pg.mwu(data_sb[data_sb.loop_condition == 'pl'].median_improvement,
                     data_sb[data_sb.loop_condition == 'open'].median_improvement)
        print(mwu)
    else:
        print("There is no significant difference on {} between the {} conditions for skateboard".format(
            'median_improvement', 'loop'))


def calculate_avg_num_interactions(df_trials):
    print("\n========== AVERAGE & MEDIAN NUMBER OF INTERACTIONS ==========")

    # calculate the average number of interactions for the closed-loop condition
    avg_interactions_at = np.sum(df_trials[(df_trials.domain == 'at') & (df_trials.loop_condition == 'cl')].interaction_type != 'final test') / len(
        df_trials[df_trials.loop_condition == 'cl'].username.unique())
    avg_interactions_sb = np.sum(df_trials[(df_trials.domain == 'sb') & (df_trials.loop_condition == 'cl')].interaction_type != 'final test') / len(
        df_trials[df_trials.loop_condition == 'cl'].username.unique())

    exclude = ['diagnostic feedback', 'remedial feedback', 'final test']

    # obtain the number of times each person interacted with Chip in each domain
    num_interactions_at = []
    num_interactions_sb = []
    perfect_training = []
    for username in df_trials[df_trials.loop_condition == 'cl'].username.unique():
        num_interactions_at_user = sum(~df_trials[(df_trials.domain == 'at') & (
                df_trials.loop_condition == 'cl') & (df_trials.username == username)].interaction_type.isin(exclude))
        num_interactions_sb_user = sum(~df_trials[(df_trials.domain == 'sb') & (
                df_trials.loop_condition == 'cl') & (df_trials.username == username)].interaction_type.isin(exclude))
        num_interactions_at.append(num_interactions_at_user)
        num_interactions_sb.append(num_interactions_sb_user)

        if num_interactions_at_user == 9 and num_interactions_sb_user == 14:
            perfect_training.append(username)

    # calculate the average and median number of interactions for each domain
    print("Avg number of closed-loop interactions for taxi: {}".format(avg_interactions_at))
    print("Avg number of closed-loop interactions for skateboard: {}".format(avg_interactions_sb))

    median_interactions_at = np.median(num_interactions_at)
    median_interactions_sb = np.median(num_interactions_sb)
    print("Median number of closed-loop interactions for taxi: {}".format(median_interactions_at))
    print("Median number of closed-loop interactions for skateboard: {}".format(median_interactions_sb))

    # did anyone go through the training perfectly?
    print("Number of people who perfectly underwent taxi training: {}".format(np.sum(np.array(num_interactions_at) == 9)))
    print("Number of people who perfectly underwent skateboard training: {}".format(np.sum(np.array(num_interactions_sb) == 14)))
    print("People who perfectly went through both training: {}".format(perfect_training))

    # obtain the participants who saw the median number of interactions
    median_interactions_at_users = np.array(df_trials[df_trials.loop_condition == 'cl'].username.unique())[np.array(num_interactions_at) == median_interactions_at]
    median_interactions_sb_users = np.array(df_trials[df_trials.loop_condition == 'cl'].username.unique())[np.array(num_interactions_sb) == median_interactions_sb]
    median_training = []
    for at_user in median_interactions_at_users:
        if at_user in median_interactions_sb_users:
            median_training.append(at_user)
    print("People who went through both median training: {}".format(perfect_training))


def compare_education_domain_on_performance(df_trials):
    print("\n========== ANOVA: EDUCATION ON TEST DEMONSTRATION PERFORMANCE ==========")
    aov = pg.mixed_anova(dv='is_opt_response', within='domain', subject='username', between='education',
                         data=df_trials, correction=True)

    post_hoc(aov, 0, 'is_opt_response', 'education', df_trials)
    post_hoc(aov, 1, 'is_opt_response', 'domain', df_trials)

    if ('p-GG-corr' in aov and aov['p-GG-corr'].iloc[2] < alpha) or ('p-GG-corr' not in aov and aov['p-unc'].iloc[2] < alpha):
        print("There is an interaction effect between {} and {}! Check out manually".format(aov['Source'][0], aov['Source'][1]))
    else:
        print("There is no interaction effect between {} and {}".format(aov['Source'][0], aov['Source'][1]))


def composition_closed_loop(df_trials, summation=True):
    '''Calculate the composition of the closed-loop condition (i.e., how many users did the demo, test, feedback)'''

    # 'demo', 'final test', 'diagnostic test', 'diagnostic feedback',
    #        'remedial demo', 'remedial test', 'remedial feedback'

    interaction_types = ['demo', 'final test', 'diagnostic test', 'diagnostic feedback',
    'remedial demo', 'remedial test', 'remedial feedback']

    if summation:
        for domain in df_trials.domain.unique():
            for interaction_type in interaction_types:
                avg_interaction_count = np.sum(df_trials[(df_trials.domain == domain) & (df_trials.interaction_type == interaction_type)].loop_condition == 'cl') / len(df_trials.username.unique())
                print("Avg # of {} interactions for {}: {}".format(interaction_type, domain, avg_interaction_count))
    else:
        for username in df_trials.username.unique():
            print(username)
            for domain in df_trials.domain.unique():
                print(domain)
                if domain == 'at':
                    print(df_trials[(df_trials.username == username) & (df_trials.domain == domain)].interaction_type)

def individual_performances(df_trials):
    counter = 0
    for username in df_trials.username.unique():
        for domain in df_trials.domain.unique():
            if len(df_trials[(df_trials.username == username) & (df_trials.domain == domain)]) > 0:
                print("Performance for {} on {}: {}".format(username, domain, np.sum(df_trials[(df_trials.username == username) & (df_trials.domain == domain) & (df_trials.interaction_type == 'final test')].is_opt_response) / len(df_trials[(df_trials.username == username) & (df_trials.domain == domain) & (df_trials.interaction_type == 'final test')])))
                counter += 1

    print("Number of people who completed both domains: {}".format(counter))

def individual_reward_weight_predictions(df_trials):
    data = df_trials[df_trials['unpickled_reward_ft_weights'].map(lambda d: len(d) > 0)].unpickled_reward_ft_weights
    for username in df_trials.username.unique():
        for domain in df_trials.domain.unique():
            if len(df_trials[(df_trials.username == username) & (df_trials.domain == domain)]) > 0:
                # this person's data didn't get properly saved but they responded [-2, 1, -1] for the reward weights separately
                if username in ['5d49d17b3dad1f0001e2aba1']:
                    continue
                print("Estimation for {} on {}: {}".format(username, domain, data[
                    (df_trials.username == username) & (df_trials.domain == domain)].iloc[0]))


def print_qualitative_feedback(df_trials, df_users, df_domain):
    print("\n========== QUALITATIVE FEEDBACK ==========")

    data = df_trials[df_trials['unpickled_improvement_short_answer'].map(
        lambda d: len(d) > 0)]
    data_domain = df_domain[df_domain['unpickled_engagement_short_answer'].map(
        lambda d: len(d) > 0)]
    data_users = df_users[df_users['unpickled_final_feedback'].map(
        lambda d: len(d) > 0)]

    data.style.set_properties(**{'text-align': 'left'})
    pd.set_option('display.max_colwidth', None)
    width = data['unpickled_improvement_short_answer'].str.len().max()
    data2 = data.copy()
    data2['unpickled_improvement_short_answer'] = data['unpickled_improvement_short_answer'].str.ljust(width)

    for username in df_trials.username.unique():
        # print("Username: {}".format(username))
        if len(data2[data.username == username].unpickled_improvement_short_answer) > 0:
            print(data2[data.username == username].unpickled_improvement_short_answer)
        if len(data_domain[data_domain.username == username].unpickled_engagement_short_answer) > 0:
            print(data_domain[data_domain.username == username].unpickled_engagement_short_answer)
        if len(data_users[data_users.username == username].unpickled_final_feedback) > 0:
            print(data_users[data_users.username == username].unpickled_final_feedback)

def analyze_time_spent(df_trials):
    np.mean(df_trials[df_trials.interaction_type == 'final test'].duration_ms) / 1000

# ---------------------------------- Running the Analysis ---------------------------------- #

if __name__ == '__main__':
    # If we are getting the data from theorem, we should process it this way
    # if sys.argv[1] == 'remote':
    #     FLAG_LOCAL_VERSION = False
    #     data = get_data()
    df_users, df_trials, df_domain = get_data()

    #------------------------ helper functions ------------------------#
    calculate_avg_num_interactions(df_trials)

    print_demographics(df_users)

    #------------------------ descriptive statistics ------------------------#
    individual_performances(df_trials)
    individual_reward_weight_predictions(df_trials)
    # print_qualitative_feedback(df_trials, df_users, df_domain)


    # ------------------------ primary analyses ------------------------#

    # compare effect of feedback and domain on performance
    compare_feedback_domain_on_performance(df_trials)

    # compare effect of feedback and domain on engagement
    compare_feedback_domain_on_engagement(df_domain)

    # compare effect of feedback and domain on improvement
    compare_feedback_on_improvement(df_trials)


    #------------------------ secondary analyses ------------------------#

    # compare effect of education on performance
    compare_education_domain_on_performance(df_trials)

    # composition of closed-loop per domain
    # composition_closed_loop(df_trials, summation=False)

    # time spent
    analyze_time_spent(df_trials)

    # estimating reward weights (IRL)
    df_trials[df_trials['unpickled_reward_ft_weights'].map(lambda d: len(d) > 0)].unpickled_reward_ft_weights









    #
    # data = df_trials
    # df_trials_reward_weights = pd.DataFrame(
    #     columns=['username', 'domain', 'loop_condition', 'median_improvement'])
    #
    # for username in np.unique(data.username):
    #     for domain in np.unique(data.domain):
    #
    #         median_improvement = float(np.median(data[(data.username == username) & (data.domain == domain)].likert))
    #
    #         loop_condition = data[data.username == username].loop_condition.values[0]
    #
    #         df_trials_reward_weights = pd.concat([df_trials_reward_weights, pd.DataFrame(
    #             [{'username': username, 'loop_condition': loop_condition, 'domain': domain,
    #               'median_improvement': median_improvement}])], ignore_index=True)
    #
    #
    #
    df_trials_reward_weights = df_trials[df_trials['unpickled_reward_ft_weights'].map(lambda d: len(d) > 0)].copy()
    def normalize_reward_weights(weights):
        normalized_weights = np.array([[float(weights[0]), float(weights[1]), -1]])

        return normalized_weights / np.linalg.norm(normalized_weights[0, :], ord=2)

    df_trials_reward_weights['scaled_reward_ft_weights'] = df_trials_reward_weights['unpickled_reward_ft_weights'].apply(normalize_reward_weights)

    # BEC_helpers.sample_human_models_uniform([np.array([[0, 0, -1]])], 50)
    at_BEC_constraints = [np.array([[1, 1, 0]]), np.array([[-1, 0, 2]]), np.array([[0, -1, -4]])]
    sb_BEC_constraints = [np.array([[5, 2, 5]]), np.array([[-6,  4, -3]]), np.array([[ 3, -3,  1]])]