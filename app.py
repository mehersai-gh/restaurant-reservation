import os

from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length
from tinydb import TinyDB, Query
from werkzeug.security import generate_password_hash, check_password_hash

#To import environmental Variables
from dotenv import load_dotenv

#Loading Environmental Variables
load_dotenv()

# Flask App Setup
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Flask-Login Setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# TinyDB Setup
db = TinyDB('db/db.json')  # Local database file
UserQuery = Query()

# User Model
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Login Manager Loader
@login_manager.user_loader
def load_user(user_id):
    user = db.get(UserQuery.username == user_id)
    if user:
        return User(user_id)
    return None

# Flask-WTF Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = db.get(UserQuery.username == username)
        if user and check_password_hash(user['password'], password):
            login_user(User(id=username))
            flash("Logged in successfully!", "success")
            return redirect(url_for('profile'))
        else:
            flash("Invalid username or password!", "danger")
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        if db.get(UserQuery.username == username):
            flash("Username already exists!", "warning")
        else:
            # Hash the password before storing it
            hashed_password = generate_password_hash(password, method='scrypt')
            db.insert({'username': username, 'password': hashed_password})
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.id)

# Run the app
if __name__ == "__main__":
    app.run(debug=True)