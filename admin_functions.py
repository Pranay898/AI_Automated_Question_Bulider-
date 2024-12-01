import docx2txt
from pptx import Presentation
import pytesseract
import streamlit as st
from db import curricula_collection, generated_questions_collection, users_collection, performance_metrics_collection,feedback_collection,issues_collection,user_activity_collection
from datetime import datetime, timedelta
from utils import generate_questions
import os
import csv
import io
from io import StringIO, BytesIO
from fpdf import FPDF
import fitz  # PyMuPDF for PDF processing; install with 'pip install pymupdf'
from PIL import Image
from langchain_google_genai import GoogleGenerativeAI
from datetime import timedelta,datetime
import psutil
from ques_bank_gen import gen_que
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

api_key = "api.txt"
os.environ["GOOGLE_API_KEY"] = api_key

GMAIL_USER = ""
GMAIL_PASSWORD = ""
TECHNICAL_TEAM_EMAIL = ""


def admin_dashboard():
    
    option = st.sidebar.selectbox("Admin Options", ["Manage Users", "System Usage", "Generate Reports", "User Activity","Question Bank Generator", "Feedback and Issue Resolution"])
    
    if option == "Manage Users":
        st.title("Manage Users")
        
        # Remove user functionality
        st.subheader("Remove User")
        remove_username = st.text_input("Username to remove")
        if st.button("Remove User"):
            if remove_user(remove_username):
                st.success(f"User '{remove_username}' removed.")
            else:
                st.error(f"User '{remove_username}' not found.")
        # Add new user
        st.subheader("Add New User")
        add_username = st.text_input("Username (for new user)")
        add_password = st.text_input("Password (for new user)", type="password")
        add_role = st.selectbox("Role", ["user", "trainer", "admin"], key="add_role")
        if st.button("Add User"):
            add_user(add_username, add_password, add_role)
        
        # Update user role
        st.subheader("Update User Role")
        update_username = st.text_input("Username (to update role)")
        new_role = st.selectbox("Update Role", ["user", "trainer", "admin"], key="update_role")
        if st.button("Update User Role"):
            update_user_role(update_username, new_role)

    elif option == "Feedback and Issue Resolution":
        st.title("Feedback and Issue Resolution")
        
        resolution_option = st.selectbox("Select Option", ["Feedback Resolution", "Issue Resolution"])

        if resolution_option == "Feedback Resolution":
            feedback_resolution()
        elif resolution_option == "Issue Resolution":
            issue_resolution()

    elif option == "System Usage":
        st.title("System Usage")
        metrics = monitor_system()
        if metrics:
            st.write(f"Timestamp: {metrics['timestamp']}, CPU Usage: {metrics['cpu']}%, Memory Usage: {metrics['memory']}%")
    if option == "Generate Reports":
        st.title("Generate Reports")

        selected_date = st.date_input("Select Date for Report", datetime.now())

        if st.button("Generate Report"):
            selected_date_dt = datetime.combine(selected_date, datetime.min.time())
            generate_reports(selected_date_dt)
    elif option == "Question Bank Generator":
        gen_que()
    elif option == "User Activity":
        user_activity_ui()


def add_user(username, password, role):
    user_data = {
        "username": username,
        "password": password,
        "role": role
    }
    
    try:
        users_collection.document(username).set(user_data)
        st.success(f"User '{username}' added with role '{role}'.")
    except Exception as e:
        st.error(f"Error adding user: {e}")

def remove_user(username):
    try:
        users_collection.document(username).delete()
        st.success(f"User '{username}' removed.")
    except Exception as e:
        st.error(f"Error removing user: {e}")

def update_user_role(username, new_role):
    try:
        users_collection.document(username).update({"role": new_role})
        st.success(f"User '{username}' role updated to '{new_role}'.")
    except Exception as e:
        st.error(f"Error updating user role: {e}")

def upload_curriculum(file, technology):
    # Logic to upload curriculum from the file
    # This can be implemented based on the file structure and data required
    pass



def save_generated_questions(questions):
    # Document name format: que_bank{date & time downloaded}
    document_name = f"que_bank_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    questions_to_save = []

    for question in questions:
        questions_to_save.append({
            "question": question["question"],
            "answer": question.get("answer", "")  # Avoid KeyError
        })

    # Save to Firestore with the desired document name format
    generated_questions_collection.document(document_name).set({"questions": questions_to_save})

    return document_name, questions_to_save

def monitor_system():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_usage = psutil.virtual_memory().percent
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    performance_metrics_collection.add({
        "timestamp": timestamp,
        "cpu": cpu_usage,
        "memory": memory_usage
    })

    return {
        "timestamp": timestamp,
        "cpu": cpu_usage,
        "memory": memory_usage
    }


def generate_reports(selected_date):
    # Ensure selected_date is a datetime object
    if isinstance(selected_date, datetime):
        start_date = selected_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = selected_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        print(f"Querying metrics from {start_date} to {end_date}")

        # Query the metrics within the date range
        metrics_data = performance_metrics_collection.where('timestamp', '>=', start_date).where('timestamp', '<=', end_date).get()
        
        print(f"Retrieved {len(metrics_data)} metrics.")
        if not metrics_data:
            st.error("No metrics available for the selected date.")
            return
        
        # Create a buffer for CSV data
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["timestamp", "cpu", "memory"])

        for metric in metrics_data:
            data = metric.to_dict()
            writer.writerow([data["timestamp"], data["cpu"], data["memory"]])

        csv_buffer.seek(0)
        st.download_button(
            label="Download Report as CSV",
            data=csv_buffer.getvalue(),
            file_name=f"system_usage_report_{selected_date.strftime('%Y-%m-%d')}.csv",
            mime="text/csv"
        )
    else:
        st.error("Invalid date selected.")


def generate_user_activity_report(start_date, end_date):
    st.subheader("User Activity Report")

    activity_data = user_activity_collection.where('timestamp', '>=', start_date).where('timestamp', '<=', end_date).get()
    
    if not activity_data:
        st.error("No user activity data available for the selected date range.")
        return

    # Generate CSV for user activity
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["username", "timestamp", "activity"])

    for activity in activity_data:
        data = activity.to_dict()
        writer.writerow([data["username"], data["timestamp"], data["activity"]])

    csv_buffer.seek(0)
    st.download_button(
        label="Download User Activity Report as CSV",
        data=csv_buffer.getvalue(),
        file_name=f"user_activity_report_{start_date.date()}_to_{end_date.date()}.csv",
        mime="text/csv"
    )

# Function to display user activity report UI
def user_activity_ui():
    st.title("User Activity Reports")

    start_date = st.date_input("Select Start Date", value=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    end_date = st.date_input("Select End Date", value=datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999))

    if st.button("Retrieve User Activity"):
        start_timestamp = datetime.combine(start_date, datetime.min.time())
        end_timestamp = datetime.combine(end_date, datetime.max.time())
        generate_user_activity_report(start_timestamp, end_timestamp)

import streamlit as st
import pandas as pd
from datetime import datetime

# Assume feedback_collection is already defined and connected to your database

def feedback_resolution():
    st.subheader("Feedback Resolution")

    # Define start and end dates
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Retrieve feedbacks on button click
    if st.button("Retrieve Feedback"):
        feedbacks = feedback_collection.where("timestamp", ">=", start_datetime).where("timestamp", "<=", end_datetime).get()
        feedback_data = []

        for idx, feedback in enumerate(feedbacks):
            data = feedback.to_dict()
            feedback_data.append({
                "Serial No": idx + 1,
                "Date": data.get("timestamp"),
                "Name": data.get("name", "N/A"),
                "Email": data.get("email", "N/A"),
                "feedback": data.get("Feedback"),
                "Status": data.get("status", "Pending"),
                "Document ID": feedback.id
            })

        # Save the retrieved feedback data to session state
        st.session_state.feedback_data = feedback_data

    # Display feedback table only if feedback data is retrieved
    if "feedback_data" in st.session_state and st.session_state.feedback_data:
        df = pd.DataFrame(st.session_state.feedback_data)
        st.dataframe(df)

        # Select feedback by serial number and store in session state
        selected_serial_no = st.selectbox("Select Feedback by Serial Number", range(1, len(st.session_state.feedback_data) + 1), key="select_feedback")
        
        # Only update selected_feedback if a new selection is made
        if selected_serial_no and (selected_serial_no != st.session_state.get("last_selected_serial")):
            st.session_state.selected_feedback = st.session_state.feedback_data[selected_serial_no - 1]
            st.session_state.last_selected_serial = selected_serial_no  # Track the last selected item

        # Display selected feedback details
        if "selected_feedback" in st.session_state:
            feedback_details = st.session_state.selected_feedback
            st.write("Selected Feedback Details:")
            st.write(f"Name: {feedback_details['Name']}")
            st.write(f"Email: {feedback_details['Email']}")
            st.write(f"feedback: {feedback_details['feedback']}")

            # Convert to Issue button
            if st.button("Convert to Issue", key="convert_issue"):
                # Convert feedback to issue
                issue_data = {
                    "name": feedback_details["Name"],
                    "email": feedback_details["Email"],
                    "issue": feedback_details["feedback"],
                    "status": "Pending",
                    "timestamp": datetime.now()
                }
                issues_collection.add(issue_data)  # Store issue in issues collection
                st.success("Feedback converted successfully to an issue.")
                # Clear selected feedback after conversion
                st.session_state.pop("selected_feedback", None)
                st.session_state.pop("last_selected_serial", None)


# Assume issues_collection is already defined and connected to your database

def issue_resolution():
    st.subheader("Issue Resolution")

    # Define start and end dates
    start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
    end_date = st.date_input("End Date", datetime.now())
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # Retrieve issues on button click
    if st.button("Retrieve Issues"):
        issues = issues_collection.where("timestamp", ">=", start_datetime).where("timestamp", "<=", end_datetime).get()
        issue_data = []

        for idx, issue in enumerate(issues):
            data = issue.to_dict()
            issue_data.append({
                "Serial Number": idx + 1,
                "Issue": data.get("issue", "No issue provided"),
                "Date": data.get("timestamp"),
                "Name": data.get("name", "Unknown"),
                "Email": data.get("email", "Unknown"),
                "Status": data.get("status", "Pending"),
                "Document ID": issue.id
            })

        # Save the retrieved issue data to session state
        st.session_state.issue_data = issue_data

    # Display issue table only if issue data is retrieved
    if "issue_data" in st.session_state and st.session_state.issue_data:
        df = pd.DataFrame(st.session_state.issue_data)
        st.dataframe(df)

        # Select issue by serial number to update status
        selected_serial_no = st.selectbox("Select Issue by Serial Number to Update Status", range(1, len(st.session_state.issue_data) + 1), key="select_issue")

        # Only update selected_issue if a new selection is made
        if selected_serial_no and (selected_serial_no != st.session_state.get("last_selected_issue")):
            st.session_state.selected_issue = st.session_state.issue_data[selected_serial_no - 1]
            st.session_state.last_selected_issue = selected_serial_no  # Track last selected item

        # Display selected issue details
        if "selected_issue" in st.session_state:
            issue_details = st.session_state.selected_issue
            st.write("Selected Issue Details:")
            st.write(f"Issue: {issue_details['Issue']}")
            st.write(f"Status: {issue_details['Status']}")

            # Status update section
            status = st.selectbox("Update Status", ["Pending", "Resolved", "Not Resolved"], index=["Pending", "Resolved", "Not Resolved"].index(issue_details['Status']))

            if st.button("Update Status", key="update_status"):
                # Logic to update the status in the issues collection
                document_id = issue_details['Document ID']
                issues_collection.document(document_id).update({"status": status})  # Updating status in the database

                # Update the selected issue status in session state
                st.session_state.selected_issue["Status"] = status
                # Also update status in the main issue_data list
                st.session_state.issue_data[selected_serial_no - 1]["Status"] = status

                st.success("Issue status updated successfully.")

    # Send unresolved issues to the technical team
    if st.button("Send Unresolved Issues to Technical Team"):
        unresolved_issues = [issue for issue in st.session_state.issue_data if issue["Status"] == "Not Resolved"]

        if unresolved_issues:
            send_email_to_technical_team(unresolved_issues)
        else:
            st.info("No unresolved issues found.")


def notify_user(email, message):
    sender_email = ""  # Replace with your sender email
    sender_password = ""  # Replace with your sender email password

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = email
    msg['Subject'] = "Feedback Converted to Issue"

    # Add message body
    msg.attach(MIMEText(message, 'plain'))

    try:
        # Connect to the SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:  # For Gmail
            server.starttls()  # Upgrade the connection to a secure encrypted SSL/TLS connection
            server.login(sender_email, sender_password)  # Login to your email account
            server.send_message(msg)  # Send the email
            print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_email_to_technical_team(unresolved_issues):
    # Format the unresolved issues for email content
    email_content = "Unresolved Issues:\n\n"
    for issue in unresolved_issues:
        email_content += (
            f"Date: {issue['Date']}\n"
            f"Name: {issue['Name']}\n"
            f"Email: {issue['Email']}\n"
            f"Issue: {issue['Issue']}\n"
            f"Status: {issue['Status']}\n\n"
        )

    # Set up the email message
    message = MIMEMultipart()
    message['From'] = GMAIL_USER
    message['To'] = TECHNICAL_TEAM_EMAIL
    message['Subject'] = "Unresolved Issues Report"
    message.attach(MIMEText(email_content, 'plain'))

    try:
        # Connect to Gmail's SMTP server and send the email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, TECHNICAL_TEAM_EMAIL, message.as_string())
        st.success("Unresolved issues emailed to the technical team successfully.")
    except Exception as e:
        st.error(f"Failed to send email: {e}")
