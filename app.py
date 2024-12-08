import os

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from tinydb import TinyDB, Query
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

#Importing Forms
from forms.user_forms import LoginForm, RegisterForm
from forms.restaurant_forms import RestaurantForm

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

# TinyDB Setup -  Local database file
user_db = TinyDB('db/user_db.json')  
restaurant_db = TinyDB('db/restaurant_db.json')

# User Model
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Login Manager Loader
@login_manager.user_loader
def load_user(user_id):
    user = user_db.get(Query().username == user_id)
    if user:
        return User(user_id)
    return None

# Routes
@app.route('/')
def index():
    # Fetch all restaurants to display on the home page
    restaurants = restaurant_db.all()
    return render_template('home.html', restaurants=restaurants)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = user_db.get(Query().username == username)
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
        if user_db.get(Query().username == username):
            flash("Username already exists!", "warning")
        else:
            # Hash the password before storing it
            hashed_password = generate_password_hash(password, method='scrypt')
            user_db.insert({'username': username, 'password': hashed_password})
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


@app.route('/restaurant/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    # Fetch restaurant details using the restaurant ID
    restaurant = restaurant_db.get(Query().id == restaurant_id)
    if not restaurant:
        abort(404)  # Return a 404 page if the restaurant doesn't exist
    return render_template('restaurant/detail.html', restaurant=restaurant)

#Admin Functionality
@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.id != 'admin':
        abort(403)  # Return a "Forbidden" error

    form = RestaurantForm()
    if form.validate_on_submit():
        # Process form data
        name = form.name.data
        four_table = form.four_table.data
        two_table = form.two_table.data
        photo = form.photo.data

        # Save the photo file
        filename = secure_filename(photo.filename)
        photo.save(os.path.join("static/images", filename))

        # Insert restaurant data into TinyDB
        restaurant_id = len(restaurant_db) + 1  # Simple ID generation
        restaurant_db.insert({
            'id': restaurant_id,
            'name': name,
            'four_table': four_table,
            'two_table': two_table,
            'four_table_rem': four_table,
            'two_table_rem': two_table,
            'photo': filename
        })

        flash('Restaurant added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/home.html', form=form)

# Run the app
if __name__ == "__main__":
    app.run(debug=True)