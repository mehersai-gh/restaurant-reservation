import os

from flask import Flask, render_template, redirect, url_for, request, flash, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from tinydb import TinyDB, Query
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

#Importing functions
from helpers.smtp import send_email

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
bookings_db = TinyDB('db/bookings_db.json')

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
        email = form.email.data  # Ensure your form has an email field

        if user_db.get(Query().username == username):
            flash("Username already exists!", "warning")
        else:
            hashed_password = generate_password_hash(password, method='scrypt')
            user_db.insert({'username': username, 'password': hashed_password, 'email': email})

            # Send confirmation email using the new templating system
            send_email(email, "register", username=username)

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
    return render_template('profile/details.html', name=current_user.id)

# Profile Page to View Bookings
@app.route('/profile/bookings')
@login_required
def profile_bookings():
    # Fetch bookings for the current user
    user_bookings = bookings_db.search(Query().user == current_user.id)

    # Segregate bookings by status
    completed = [b for b in user_bookings if b['status'] == 'completed']
    ongoing = [b for b in user_bookings if b['status'] == 'ongoing']
    cancelled = [b for b in user_bookings if b['status'] == 'cancelled']

    return render_template(
        'profile/bookings.html',
        completed=completed,
        ongoing=ongoing,
        cancelled=cancelled
    )

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    # Fetch the booking by ID
    booking = bookings_db.get(Query().id == booking_id)
    if not booking or booking['user'] != current_user.id:
        flash("Unauthorized or invalid booking!", "danger")
        return redirect(url_for('profile_bookings'))

    # Fetch the restaurant details
    restaurant = restaurant_db.get(Query().id == booking['restaurant_id'])
    if not restaurant:
        flash("Restaurant not found!", "danger")
        return redirect(url_for('profile_bookings'))

    # Get the booking's date and slot
    booking_date = booking['date']
    booking_slot = booking['slot']

    # Update the specific slot's availability
    slots = restaurant['slots']
    if booking_date in slots and booking_slot in slots[booking_date]:
        slots[booking_date][booking_slot]['four_table_rem'] += booking['four_table']
        slots[booking_date][booking_slot]['two_table_rem'] += booking['two_table']

        # Update the restaurant slots in the database
        restaurant_db.update({'slots': slots}, Query().id == restaurant['id'])

    # Update the booking status to "cancelled"
    bookings_db.update({'status': 'cancelled'}, Query().id == booking_id)

    try:
        # Fetch user details (assuming you store email in user_db)
        user = user_db.get(Query().username == current_user.id)
        if user and "email" in user:
            send_email(
                to_email=user["email"],
                subject="Booking Cancellation Confirmation",
                usage="booking_cancellation",
                username=user["username"],
                restaurant_name=restaurant["name"],
                booking_date=booking_date,
                booking_slot=booking_slot
            )
    except Exception as e:
        flash(e)

    flash("Booking cancelled successfully! An email confirmation has been sent.", "success")
    return redirect(url_for('profile_bookings'))


@app.route('/restaurant/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    # Fetch restaurant details using the restaurant ID
    restaurant = restaurant_db.get(Query().id == restaurant_id)
    if not restaurant:
        abort(404)  # Return a 404 page if the restaurant doesn't exist
    return render_template('restaurant/detail.html', restaurant=restaurant)

@app.route('/restaurant/<int:restaurant_id>/book', methods=['GET', 'POST'])
@login_required
def restaurant_booking(restaurant_id):
    # Fetch restaurant details
    restaurant = restaurant_db.get(Query().id == restaurant_id)
    if not restaurant:
        abort(404)

    today = datetime.now().date()
    available_dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    if request.method == 'POST':
        # Get form data
        selected_date = request.form.get('date')
        selected_slot = request.form.get('slot')
        num_four_table = int(request.form.get('four_table', 0))
        num_two_table = int(request.form.get('two_table', 0))
        special_request = request.form.get('special_request', '')

        # Validate booking
        if selected_date not in restaurant['slots'] or selected_slot not in restaurant['slots'][selected_date]:
            flash("Invalid date or time slot selected!", "danger")
            return redirect(url_for('restaurant_booking', restaurant_id=restaurant_id))

        slot_data = restaurant['slots'][selected_date][selected_slot]
        if num_four_table > slot_data['four_table_rem'] or num_two_table > slot_data['two_table_rem']:
            flash("Not enough tables available for your booking!", "danger")
            return redirect(url_for('restaurant_booking', restaurant_id=restaurant_id))

        # Update table availability
        slot_data['four_table_rem'] -= num_four_table
        slot_data['two_table_rem'] -= num_two_table
        restaurant['slots'][selected_date][selected_slot] = slot_data
        restaurant_db.update({'slots': restaurant['slots']}, Query().id == restaurant_id)

        # Add booking to the bookings table
        booking_id = len(bookings_db) + 1
        bookings_db.insert({
            'id': booking_id,
            'user': current_user.id,
            'restaurant_id': restaurant_id,
            'restaurant_name': restaurant['name'],
            'four_table': num_four_table,
            'two_table': num_two_table,
            'date': selected_date,
            'slot': selected_slot,
            'special_request': special_request,
            'status': 'ongoing'
        })

        flash("Booking confirmed!", "success")
        return redirect(url_for('profile'))

    return render_template('restaurant/book.html', restaurant=restaurant, available_dates=available_dates)

#Admin Functionality
@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if current_user.id != 'admin':
        abort(403)  # Return a "Forbidden" error

    # Fetch all restaurants to display on the admin page
    restaurants = restaurant_db.all()
    return render_template('admin/home.html', restaurants=restaurants)

@app.route('/admin_dashboard/add', methods=['GET', 'POST'])
@login_required
def admin_dashboard_add():
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

        # Initialize slots for the next 7 days
        slots = {}
        today = datetime.now().date()
        time_slots = [
            "9am-11am", "11am-1pm", "1pm-3pm", "3pm-5pm", "5pm-7pm", "7pm-9pm", "9pm-11pm"
        ]
        for i in range(7):
            date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            slots[date] = {
                slot: {"four_table_rem": four_table, "two_table_rem": two_table} for slot in time_slots
            }

        # Insert restaurant data into TinyDB
        restaurant_id = len(restaurant_db) + 1
        restaurant_db.insert({
            'id': int(restaurant_id),
            'name': name,
            'photo': filename,
            'slots': slots,
            'four_table': four_table,
            'two_table':two_table
        })

        flash('Restaurant added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_restaurant.html', form=form)

@app.route('/delete_restaurant/<int:restaurant_id>', methods=['POST'])
@login_required
def delete_restaurant(restaurant_id):
    if current_user.id != 'admin':
        abort(403)  # Return a "Forbidden" error

    print(restaurant_db.get(Query().id == 1))
    # Fetch the restaurant by ID and delete it
    restaurant = restaurant_db.get(Query().id == restaurant_id)
    if restaurant:
        restaurant_db.remove(Query().id == restaurant_id)
        flash(f"Restaurant '{restaurant['name']}' has been deleted.", 'success')
    else:
        flash("Restaurant not found.", 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/update_slots', methods=['POST'])
def update_slots():
    today = datetime.now().date()
    next_week_dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 8)]
    time_slots = [
        "9am-11am", "11am-1pm", "1pm-3pm", "3pm-5pm", "5pm-7pm", "7pm-9pm", "9pm-11pm"
    ]

    try:
        for restaurant in restaurant_db.all():
            slots = restaurant['slots']

            # Remove past dates (before today)
            slots = {date: data for date, data in slots.items() if date >= today.strftime("%Y-%m-%d")}

            # Add missing dates for the next week
            for date in next_week_dates:
                if date not in slots:
                    slots[date] = {
                        slot: {"four_table_rem": restaurant['four_table'], "two_table_rem": restaurant['two_table']}
                        for slot in time_slots
                    }

            # Update restaurant slots in the database
            restaurant_db.update({'slots': slots}, Query().id == restaurant['id'])

        flash("Slots have been successfully updated.", "success")
    except Exception as e:
        flash("An error occurred while updating slots: " + str(e), "danger")

    return redirect(url_for('admin_dashboard'))

# Run the app
if __name__ == "__main__":
    app.run(debug=True)