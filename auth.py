from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import random
import smtplib
from email.mime.text import MIMEText
from db import user_activity_collection

# Check if Firebase app is already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")  # Update with your Firebase credentials path
    firebase_admin.initialize_app(cred)

db = firestore.client()
users_collection = db.collection('users')

def register_user(username, password, role, email):
    # Function to register a new user
    users_collection.document(username).set({
        'password': password,
        'role': role,
        'email': email  # Store email with user data
    })

def login_user(username, password):
    # Function to log in user
    user_doc = users_collection.document(username).get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        if user_data['password'] == password:
            log_user_activity(username)
            return True
    return False
    

def is_admin(username):
    user_doc = users_collection.document(username).get()
    if user_doc.exists:
        return user_doc.to_dict().get('role') == 'admin'
    return False

def is_trainer(username):
    user_doc = users_collection.document(username).get()
    if user_doc.exists:
        return user_doc.to_dict().get('role') == 'trainer'
    return False

def send_otp(email):
    try:
        otp = random.randint(100000, 999999)  # Generate a random 6-digit OTP
        subject = "Your OTP Code"
        body = f"Your OTP code is {otp}. It is valid for 10 minutes."
        
        # Setup your email server (Example: Gmail)
        sender_email = "vtu19288@veltech.edu.in"  # Update with your sender email
        sender_password = "bics fhoc slys wjyp"  # Use an app password if 2FA is enabled

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = email

        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Start TLS for security
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())

        print(f"OTP sent: {otp} to {email}")  # Debugging line to see the OTP sent
        return otp  # Return the generated OTP
    except Exception as e:
        print(f"Error sending OTP: {e}")  # Print error message for debugging
        return None

def verify_otp(input_otp, generated_otp):
    # Function to verify the provided OTP
    input_otp = input_otp.strip()  # Strip any whitespace
    generated_otp = str(generated_otp)  # Ensure it's a string
    print(f"Input OTP: {input_otp}, Generated OTP: {generated_otp}")  # Debugging line to check OTPs
    return input_otp == generated_otp

def update_password(username, new_password):
    # Function to update the user's password
    user_doc = users_collection.document(username).get()
    if user_doc.exists:
        user_doc.reference.update({"password": new_password})
        return True
    return False

def log_user_activity(username):
    activity_data = {
        'username': username,
        'timestamp': datetime.now(),
        'activity': 'Logged in'
    }
    # Use user_activity_collection directly to add the activity
    user_activity_collection.add(activity_data)