import streamlit as st
from auth import register_user, login_user, is_admin, is_trainer, send_otp, verify_otp
from db import users_collection, generated_questions_collection, performance_metrics_collection, curricula_collection, feedback_collection, user_requests_collection
from datetime import datetime
import pandas as pd
from admin_functions import add_user, remove_user, update_user_role, monitor_system, generate_reports, admin_dashboard
import os
from fpdf import FPDF
from io import BytesIO
from langchain_google_genai import GoogleGenerativeAI
from utils import generate_questions
from trainer_dashboard import trainer_dashboard
from employee_dashboard import employee_dashboard
import tempfile
from ques_bank_gen import gen_que

# Page setup
st.set_page_config(page_title="AI Question Builder", layout="wide")

# Set API key for Google Gemini
api_key = "api.txt"  # Replace with your actual API key
os.environ["GOOGLE_API_KEY"] = api_key



with open('app.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        

# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "generated_otp" not in st.session_state:
    st.session_state["generated_otp"] = None
if "otp_sent" not in st.session_state:
    st.session_state["otp_sent"] = False
if "password_reset" not in st.session_state:
    st.session_state["password_reset"] = False  # To track password reset status

# Login and Registration Page
if not st.session_state["logged_in"]:
    st.title("AI Question Builder - Login")
    
    login_tab, register_tab = st.tabs(["Login", "Register"])
    
    # Login tab
    with login_tab:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            if login_user(username, password):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success("Successfully logged in!")
            else:
                st.error("Invalid credentials.")
        
        # Forgot password section
        st.subheader("Forgot Password?")
        username_for_otp = st.text_input("Username for OTP", key="otp_username")
        if st.button("Send OTP", key="send_otp_button"):
            if username_for_otp:
                user_doc = users_collection.document(username_for_otp).get()
                if user_doc.exists:
                    email_for_otp = user_doc.to_dict().get("email")
                    generated_otp = send_otp(email_for_otp)
                    if generated_otp:
                        st.session_state["generated_otp"] = generated_otp
                        st.session_state["otp_sent"] = True
                        st.success("OTP sent to your registered email!")
                    else:
                        st.error("Failed to send OTP. Please check your email.")
                else:
                    st.error("Username not found. Please check and try again.")

        if st.session_state["otp_sent"]:
            otp_input = st.text_input("Enter OTP", key="otp_input")
            if st.button("Verify OTP"):
                print(f"User OTP: {otp_input}, Generated OTP: {st.session_state['generated_otp']}")  # Debug print
                if verify_otp(otp_input, str(st.session_state["generated_otp"])):
                    st.success("OTP verified! You can now set a new password.")
                    st.session_state["otp_sent"] = False  # Reset OTP sent status
                    st.session_state["password_reset"] = True  # Set the password reset status
                else:
                    st.error("Invalid OTP. Please check and try again.")

        if st.session_state["password_reset"]:  # Check if password reset is active
            new_password = st.text_input("New Password", type="password", key="reset_new_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reset_confirm_password")
            if st.button("Reset Password"):
                if new_password == confirm_password:
                    # Reset password logic
                    users_collection.document(username_for_otp).update({"password": new_password})
                    st.success("Password reset successful! You can now log in.")
                    st.session_state["generated_otp"] = None  # Clear the generated OTP
                    st.session_state["password_reset"] = False  # Reset password status
                else:
                    st.error("Passwords do not match.")

    # Registration tab
    with register_tab:
        new_username = st.text_input("New Username", key="new_username")
        new_password = st.text_input("New Password", type="password", key="new_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        email = st.text_input("Email", key="new_email")
        
        if st.button("Register", key="register_button"):
            if new_password == confirm_password:
                try:
                    register_user(new_username, new_password, "user", email)  # Default role as 'user'
                    st.success("Registration successful! You can now log in.")
                except Exception as e:
                    st.error(f"Registration failed: {e}")
            else:
                st.error("Passwords do not match.")

# Main Dashboard
else:
    st.sidebar.title("Dashboard")
    
    if is_admin(st.session_state["username"]):
        role = "admin"
    elif is_trainer(st.session_state["username"]):
        role = "trainer"
    else:
        role = "employee"

    # Sidebar options for Admin
    if role == "admin":
        admin_dashboard()
    
    # Trainer Dashboard
    elif role == "trainer":
        trainer_dashboard()
    
    # Employee Dashboard (default view after login)
    else:
        employee_dashboard()

    st.sidebar.button("Logout", on_click=lambda: st.session_state.clear(), key="logout_button")
