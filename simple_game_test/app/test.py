import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
print("Using database:", app.config["SQLALCHEMY_DATABASE_URI"])
