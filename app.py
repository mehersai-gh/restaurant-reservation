from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired

# Flask App Setup
app = Flask(__name__)

# Flask-Login Setup
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Dummy User Database
users = {"admin": {"password": "password"}}

# User Model
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Login Manager Loader
@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

# Flask-WTF Form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

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
        if username in users and users[username]['password'] == password:
            user = User(id=username)
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for('profile'))
        else:
            flash("Invalid username or password!", "danger")
    return render_template('login.html', form=form)

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