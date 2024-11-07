import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

app = Flask(__name__)

# Configuration settings
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "ss_paradise_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ss_paradise.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["DEBUG"] = True  # Enable debug mode
app.config["HOST"] = "0.0.0.0"  # Listen on all interfaces
app.config["PORT"] = 5000

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Import routes after app initialization to avoid circular imports
from routes import *

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"]
    )
