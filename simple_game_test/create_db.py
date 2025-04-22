''' To manually create the flask db without migrations'''

from app import app, db
with app.app_context():
    db.create_all()