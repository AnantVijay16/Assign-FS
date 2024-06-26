import random
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_pymongo import PyMongo
from flask_mail import Mail, Message
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB configuration for user profiles
app.config['MONGO_URI'] = 'mongodb+srv://adarshmishra:1234@messportal.qrkbtya.mongodb.net/Assign-FS'
mongo = PyMongo(app)
collection = mongo.db.profiles
assignments_collection = mongo.db['assignments']

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your SMTP server address
app.config['MAIL_PORT'] = 587  # Replace with your SMTP server port (usually 587 for TLS)
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'fittrack2@gmail.com'  # Replace with your email username
app.config['MAIL_PASSWORD'] = 'ksdvgulnzqkcjpgj'  # Replace with your email password
mail = Mail(app)

# Generate OTP
def generate_otp():
    return str(random.randint(1000, 9999))

# Route for Sign Up Page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        college_email = request.form['college_email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        phone = request.form['phone']

        # Check if email is already registered
        existing_user = collection.find_one({'college_email': college_email})
        if existing_user:
            return render_template('signup.html', error='Email already exists. Please choose another.')

        # Check if passwords match
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match. Please try again.')

        # Generate OTP
        otp = generate_otp()

        # Send OTP to user's email
        msg = Message('Signup - OTP Verification', sender='fittrack2@gmail.com', recipients=[college_email])
        msg.body = f'Your OTP for signup is: {otp}'
        mail.send(msg)

        # Store OTP in session
        session['otp'] = otp

        # Store user data in session
        session['name'] = name
        session['college_email'] = college_email
        session['password'] = password
        session['phone'] = phone

        # Redirect to OTP verification page
        return redirect(url_for('verify_signup_otp'))

    return render_template('signup.html')

# Route for OTP Verification Page
@app.route('/verify_signup_otp', methods=['GET', 'POST'])
def verify_signup_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        if 'otp' in session and user_otp == session['otp']:
            # OTP verification successful, insert user data into the database
            user_data = {
                'name': session['name'],
                'college_email': session['college_email'],
                'password': session['password'],
                'phone': session['phone']
            }
            collection.insert_one(user_data)

            # Clear session data
            session.pop('otp')
            session.pop('name')
            session.pop('college_email')
            session.pop('password')
            session.pop('phone')

            # Redirect to login page after successful sign up
            return redirect(url_for('login'))
        else:
            # Incorrect OTP entered, display error message
            error_message = "Incorrect OTP. Please try again."
            return render_template('verify_otp.html', error=error_message)

    return render_template('verify_otp.html')

# Route for Password Reset Page
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password != confirm_password:
            return render_template('reset_password.html', error='Passwords do not match. Please try again.')
        
        # Update user's password in the database
        collection.update_one({'mobile_number': session['mobile_number']}, {'$set': {'password': new_password}})
        session.pop('otp')
        session.pop('mobile_number')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        college_email = request.form['college_email']
        password = request.form['password']

        user = collection.find_one({'college_email': college_email, 'password': password})

        if user:
            session['college_email'] = college_email
            session['name'] = user.get('name', 'User')
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid college email or password')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'college_email' in session:
        name = session.get('name', 'User')
        return render_template('dashboard.html', name=name)
    else:
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('college_email', None)
    session.pop('name', None)
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'college_email' in session:
        user = collection.find_one({'college_email': session['college_email']})
        if user:
            if request.method == 'POST':
                contact_number = request.form['contact_number']
                branch = request.form['branch']
                collection.update_one({'college_email': session['college_email']}, {'$set': {'contact_number': contact_number, 'branch': branch}})
                return redirect(url_for('profile'))
            return render_template('profile.html', user=user)
    return redirect(url_for('login'))

#Developer Profile
@app.route('/developer')
def developer():
    return render_template('developer.html')

# Routes for assignments

@app.route('/submit_assignment', methods=['POST'])
def submit_assignment():
    data = request.json
    student_id = data.get('student_id')
    assignment_text = data.get('assignment_text')
    
    # Store assignment in MongoDB
    assignments_collection.insert_one({'student_id': student_id, 'assignment_text': assignment_text})
    
    return jsonify({'message': 'Assignment submitted successfully'})

@app.route('/evaluate_assignments', methods=['POST'])
def evaluate_assignments():
    data = request.json
    teacher_id = data.get('teacher_id')
    
    # Fetch all assignments
    all_assignments = assignments_collection.find()
    
    # Evaluate each assignment for plagiarism and calculate scores
    evaluation_results = []
    for assignment in all_assignments:
        plagiarism_percentage = detect_plagiarism(assignment['assignment_text'])
        score = 10 - (plagiarism_percentage // 10)
        evaluation_results.append({'student_id': assignment['student_id'], 'score': score})
    
    return jsonify({'evaluation_results': evaluation_results})

def detect_plagiarism(assignment_text):
    # Perform plagiarism detection logic here (this is just a placeholder)
    # You'll need a more sophisticated algorithm or library for this task
    # For example, you might compare assignment_text against a database of existing assignments
    
    # For simplicity, let's assume plagiarism percentage is randomly generated between 0 and 100
    import random
    return random.randint(0, 100)

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True)
