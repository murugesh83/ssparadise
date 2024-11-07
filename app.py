import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "ss_paradise_secret_key"
# Using SQLite for development
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ss_paradise.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

from routes import *

with app.app_context():
    db.create_all()
