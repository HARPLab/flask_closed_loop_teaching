# Improving the Transparency of Agent Decision Making Using Demonstrations

This repository contains code for the methods and user studies described in chapter 6 the following [thesis](https://symikelee.github.io/papers/ml5_phd_ri_2024.pdf): 

- Michael S. Lee, **Improving the Transparency of Agent Decision Making Using Demonstrations**, Carnegie Mellon University, 2024,

which introduces a closed-loop teaching framework for teaching agent decision making to humans through demonstrations of key agent decisions, intermittent testing of human understanding, and provision of remedial instruction as necessary.

The thesis (and code for the methods and user studies of other chapters, e.g. chapters 4 and 5) are available at https://symikelee.github.io/.

# Methods for in situ Demonstration Selection

The code for the methods can be found in `closed_loop_teaching_study/simple_game_test/app/augmented_taxi/*` and are called in `closed_loop_teaching_study/simple_game_test/app/routes.py`, where `routes.py` contains the main logic for how the user study should flow. 

Of particular interest are algorithms for maintaining a running model of the human's beliefs (in a particle filter) and determining the next demonstration or test to provide, which live in `simple_game_test/app/augmented_taxi/policy_summarization/*`.

# User Study

## Running the study locally
- Install the following packages, preferably in an isolated environment like [conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html). If you get an error, try installing the specific versions listed: 

```
- python 3.9
- flask 2.0.3
- flask-wtf 1.0.1
- flask-login 0.6.2
- flask-sqlalchemy 2.5.1
- flask-migrate 4.0.0
- flask-socketio 5.3.4
- sqlalchemy 1.4.27
- (the following package versions could be more flexible) 
- numpy 1.24.3
- scipy 1.10.1 
- matplotlib 3.7.1 
- pandas 2.0.1
- pingouin 0.5.3
- email-validator 2.0.0.post2
```
* In `simple_game_test`, run the study with `python -m flask run`
* The main study code lives in `simple_game_test/app/routes.py`, which you can modify e.g. to change the experimental conditions (called `loop_conditions`). 

## Recreating the database (app.db) 

The database must be created for the user study to run if it doesn't already exist, and it must be recreated whenever changes are made to the structure. 

To create a new database:

- Comment out bottom half of `simple_game_test/app/__init__.py` 
- Create the database using

```
flask db init
flask db migrate 
flask db upgrade
```

- Uncomment the bottom half of `simple_game_test/app/__init__.py` before running the study again. 

And when making changes to the structure of the database (e.g. adding a new column), purge the previous one with the following commands before recreating the database

```angular2html
rm -r app.db
rm -rf migrations
```

## Database Access

Opening the database in sqlite3:

```sqlite3 app.db```

Some helpful commands while in splite3:

```
# List all tables:
.tables

# List data in a table:
SELECT * FROM <table_name>;

# List all column names and data types in a table:
PRAGMA table_info(<table_name>);

# Export table to a .csv:
.mode csv
.output <filename>.csv
SELECT * FROM <table_name>;
.output stdout
```

To exit from sqlite, press Ctrl+D

# Data analysis

* The data collected from the user studies mentioned in chapter 6 of the above thesis can found in `analysis/dfs_f23_processed.pickle` and the analyses presented in that chapter can be recreated by running `analysis/data_analysis.py`.
