import io
from tkinter import Image
import docx2txt
import fitz
from pptx import Presentation
import pytesseract
import streamlit as st
from db import (
    generated_questions_collection,
    feedback_collection,
    user_requests_collection,
    issues_collection,
    users_collection,
)
from datetime import datetime
from fpdf import FPDF
from io import BytesIO
import pandas as pd
import tempfile
from utils import generate_questions
import os
from ques_bank_gen import gen_que

# Set API Key for Google services
api_key = "AIzaSyCkhwdytqyr039-BnhACY2RzexSUZZcwB4"
os.environ["GOOGLE_API_KEY"] = api_key

def employee_dashboard():
    st.sidebar.title("Employee Dashboard")
    option = st.sidebar.selectbox(
        "Employee Options",
        [
            "Self-Assessment",
            "Learning and Development",
            "Request Learning Plan",
            "Feedback Submission",
            "Report an Issue",
        ],
    )

    if option == "Self-Assessment":
        st.title("Self-Assessment")

        question_banks = generated_questions_collection.stream()
        question_bank_ids = [q.id for q in question_banks]

        selected_question_bank = st.selectbox("Select Question Bank", question_bank_ids)

        # Initialize questions and user_answers variables
        questions = []  # Default to an empty list
        if selected_question_bank:
            question_bank = generated_questions_collection.document(selected_question_bank).get().to_dict()
            if question_bank and "questions" in question_bank:
                questions = question_bank["questions"]

        # Reset answers when a new question bank is selected
        if 'user_answers' not in st.session_state or selected_question_bank != st.session_state.get('selected_question_bank'):
            st.session_state.user_answers = [None] * len(questions) if questions else []  # Reset answers to None
            st.session_state.selected_question_bank = selected_question_bank  # Update the selected bank
            # Clear the radio button selections
            for idx in range(len(questions)):
                st.session_state[f'q{idx + 1}'] = None  # Reset each radio button's state

        if questions:
            st.subheader("Complete the Self-Assessment to earn your certificate!")

            for idx, entry in enumerate(questions):
                st.write(entry["question"])
                options = [
                    entry.get("option-1", ""),
                    entry.get("option-2", ""),
                    entry.get("option-3", ""),
                    entry.get("option-4", ""),
                ]
                # Provide the key for the radio button to ensure each one is independent
                user_answer = st.radio(f"Select your answer for Q{idx + 1}:", options, key=f"q{idx + 1}")
                st.session_state.user_answers[idx] = user_answer  # Store user answers in session state

            if st.button("Generate Score"):
                correct_answers = sum(
                    1 for idx, entry in enumerate(questions)
                    if st.session_state.user_answers[idx] and st.session_state.user_answers[idx].startswith(entry["answer"].strip()[:1])
                )
                score = (correct_answers / len(questions)) * 100
                st.write(f"Your Score: {score:.2f}%")

                if score >= 70:
                    username = st.session_state.get("username", "Unknown User")
                    pdf_data = create_certificate("Employee Name", username, score, selected_question_bank)
                    st.download_button(
                        label="Download Completion Certificate",
                        data=pdf_data,
                        file_name="completion_certificate.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.warning("You need at least 70% to earn the certificate.")
        else:
            st.warning("No questions available in the selected question bank.")

    elif option == "Feedback Submission":
        st.title("Feedback")
        st.subheader("Please provide your Feedback and details below:")

        name = st.text_input("Name")
        email = st.text_input("Email")
        feedback = st.text_area("Describe your Feedback")

        if st.button("Submit Feedback"):
            if name and email and feedback:
                feedback_timestamp = datetime.now().strftime("Feedback_%Y_%m_%d_%H_%M_%S")
                feedback_entry = {
                    "name": name,
                    "email": email,
                    "Feedback": feedback,
                    "timestamp": datetime.now(),
                }
                feedback_collection.document(feedback_timestamp).set(feedback_entry)
                st.success("Feedback submitted successfully.")
            else:
                st.error("Please fill in all fields.")

    elif option == "Learning and Development":
        st.title("Learning and Development")
        st.subheader("Access Learning Materials")

        question_banks = generated_questions_collection.stream()
        question_bank_ids = [q.id for q in question_banks]

        selected_question_bank = st.selectbox("Select Question Bank to Download", question_bank_ids)

        if selected_question_bank:
            question_bank = generated_questions_collection.document(selected_question_bank).get().to_dict()
            if question_bank and "questions" in question_bank:
                questions = question_bank["questions"]

                text_data = "\n".join(
                    [
                        f"Q: {q['question']}\nA: {q['option-1']}\nB: {q['option-2']}\nC: {q['option-3']}\nD: {q['option-4']}\nA: {q['answer']}\n"
                        for q in questions
                    ]
                )
                st.download_button(
                    label="Download as Text",
                    data=text_data,
                    file_name=f"{selected_question_bank}.txt",
                    mime="text/plain",
                )

    elif option == "Request Learning Plan":
        st.title("Request Learning Plan for Technical Upskill")

        tech = st.selectbox("Technology", ["Python", "Java", "JavaScript", "C++", "SQL"])
        specific_areas = st.text_input("Specific Areas of Improvement")
        urgency = st.selectbox("Urgency Level", ["Low", "Medium", "High"])

        if st.button("Submit Request"):
            learning_request = {
                "technology": tech,
                "specific_areas": specific_areas,
                "urgency": urgency,
                "timestamp": datetime.now(),
            }
            user_requests_collection.add(learning_request)
            st.success("Learning request submitted successfully!")

    elif option == "Report an Issue":
        st.title("Report an Issue")
        st.subheader("If you encounter any issues, please provide your details below:")

        name = st.text_input("Name")
        email = st.text_input("Email")
        issue = st.text_area("Describe your issue")

        if st.button("Submit Issue"):
            if name and email and issue:
                issue_timestamp = datetime.now().strftime("issue_%Y_%m_%d_%H_%M_%S")
                issue_entry = {
                    "name": name,
                    "email": email,
                    "issue": issue,
                    "timestamp": datetime.now(),
                }
                issues_collection.document(issue_timestamp).set(issue_entry)
                st.success("Issue submitted successfully! We will contact you shortly.")
            else:
                st.error("Please fill in all fields.")

        st.markdown("For immediate assistance, please contact us at: **support@example.com**")


def create_certificate(employee_name, username, score, question_bank_name):
    # Create an instance of FPDF
    pdf = FPDF()
    pdf.add_page()

    # Set background color for the certificate (light gray)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(5, 5, 200, 287, 'F')  # Adds a filled rectangle to serve as the background

    # Set font for title and add a title
    pdf.set_font("Arial", "B", 24)
    pdf.set_text_color(50, 50, 150)  # Dark blue for title
    pdf.cell(0, 30, "Self-Assessment Completion Certificate", ln=True, align="C")

    # Add a line separator
    pdf.set_line_width(1)
    pdf.set_draw_color(50, 50, 150)
    pdf.line(10, 40, 200, 40)  # Horizontal line below title

    # Subtitle
    pdf.set_font("Arial", "I", 16)
    pdf.set_text_color(80, 80, 80)  # Dark gray for subtitle
    pdf.cell(0, 20, "This is to certify that", ln=True, align="C")

    # Employee's name in larger font
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(20, 20, 20)  # Black for name
    pdf.cell(0, 20, f" {username}", ln=True, align="C")

    # Add the username below the employee's name
    #pdf.set_font("Arial", "", 16)
    #pdf.set_text_color(80, 80, 80)  # Dark gray for username
    #pdf.cell(0, 20, f"Username: {username}", ln=True, align="C")

    # Add certificate details
    pdf.set_font("Arial", "", 14)
    pdf.set_text_color(80, 80, 80)  # Dark gray for details
    pdf.cell(0, 15, f"has successfully completed the self-assessment with a score of {score:.2f}%", ln=True, align="C")

    # Bold the question bank name
    pdf.set_font("Arial", "B", 14)  # Make the font bold for question bank name
    pdf.cell(0, 15, f"using the question bank: {question_bank_name}.", ln=True, align="C")

    # Add completion date
    pdf.set_font("Arial", "", 14)  # Revert back to normal font for the date
    pdf.set_text_color(80, 80, 80)  # Dark gray for date
    pdf.cell(0, 20, f"Completion Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="C")

    # Footer with congratulations
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 20, "Congratulations!", ln=True, align="C")

    # Save the PDF to a temporary file
    temp_filename = "certificate.pdf"
    pdf.output(temp_filename)

    # Read the file back into a BytesIO object
    with open(temp_filename, 'rb') as f:
        pdf_data = BytesIO(f.read())

    # Clean up the temporary file
    os.remove(temp_filename)

    return pdf_data  # Return the BytesIO object containing the PDF