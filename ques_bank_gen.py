import streamlit as st
from db import curricula_collection, generated_questions_collection, user_requests_collection
from datetime import datetime
import pandas as pd
import csv
from io import StringIO, BytesIO
from fpdf import FPDF
import os
import PyPDF2  # Ensure you have this library installed for PDF handling
from utils import generate_questions

def gen_que():
    st.title("Question Bank Generator")

    # Dropdown to select generation method
    generation_method = st.selectbox("Select Generation Method", 
                                      ["By Technology and Topic", 
                                       "By Prompt", 
                                       "By Uploaded Curriculum",
                                       "Learning Requests from Employees"])

    # Custom document name input
    document_name = st.text_input("Enter Document Name", key="document_name_input")

    if generation_method == "By Technology and Topic":
        generate_by_technology_and_topic(document_name)
    elif generation_method == "By Prompt":
        generate_by_prompt(document_name)
    elif generation_method == "By Uploaded Curriculum":
        generate_by_uploaded_curriculum(document_name)
    elif generation_method == "Learning Requests from Employees":
        generate_by_learning_requests(document_name)

def generate_by_technology_and_topic(document_name):
    st.header("Generate by Technology and Topic")
    technology = st.selectbox("Select Technology", ["Python", "Java", "C"], key="technology_select")
    
    topics = {
        "Python": ["Data Structures", "OOP", "Web Development", "Machine Learning", "Data Analysis"],
        "Java": ["Collections", "OOP", "Concurrency", "JavaFX", "Spring"],
        "C": ["Pointers", "Memory Management", "Data Structures", "File I/O", "Algorithms"]
    }
    selected_topics = topics.get(technology, [])
    selected_topic = st.selectbox("Select Topic", selected_topics, key="topic_select")

    num_questions = st.slider("Number of Questions", min_value=10, max_value=90, key="num_questions")
    difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], key="difficulty")

    if st.button("Generate Question Bank from Technology and Topic", key="generate_tech_topic_button"):
        combined_prompt = f"Generate {num_questions} questions from the topic {selected_topic} in {technology} at {difficulty} level."
        generate_and_display_questions(combined_prompt, num_questions, difficulty, document_name)

def generate_by_prompt(document_name):
    st.header("Generate by Prompt")
    text_prompt = st.text_area("Provide a text prompt for question generation", key="text_prompt")
    file_prompt = st.file_uploader("Or upload a file as a prompt", type=["pdf", "csv", "jpg", "png", "docx", "pptx", "xlsx"])
    prompt_text = extract_text_from_file(file_prompt) if file_prompt is not None else text_prompt.strip()

    num_questions = st.slider("Number of Questions", min_value=10, max_value=90, key="num_questions_prompt")
    difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], key="difficulty_prompt")

    if st.button("Generate Question Bank from Prompt", key="generate_prompt_button"):
        if not prompt_text.strip():
            st.error("Please provide valid prompt text or upload a file with content.")
            return
        generate_and_display_questions(prompt_text, num_questions, difficulty, document_name)

def generate_by_uploaded_curriculum(document_name):
    st.header("Generate by Uploaded Curriculum")
    curricula_list = [doc.to_dict() for doc in curricula_collection.stream()]
    curriculum_filenames = [curriculum.get("filename") for curriculum in curricula_list if "filename" in curriculum]

    selected_curriculum = st.selectbox("Select Uploaded Curriculum", curriculum_filenames, key="curriculum_select", index=0)
    custom_prompt = st.text_input("Ask a custom prompt about the curriculum (optional)", key="custom_prompt")
    num_questions = st.slider("Number of Questions", min_value=10, max_value=90, key="num_questions_curriculum")
    difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], key="difficulty_curriculum")

    if st.button("Generate Question Bank from Curriculum", key="generate_curriculum_button"):
        curriculum_content = extract_curriculum_content(selected_curriculum)
        if curriculum_content:
            full_prompt = curriculum_content
            if custom_prompt.strip():
                full_prompt += f"\n{custom_prompt}"
            generate_and_display_questions(full_prompt, num_questions, difficulty, document_name)
        else:
            st.error("No content found for the selected curriculum.")

def generate_by_learning_requests(document_name):
    st.header("Generate by Learning Requests from Employees")
    # Retrieve and list the employee requests from the database
    requests_list = [doc.to_dict() for doc in user_requests_collection.stream()]
    request_titles = [
        f"{req.get('technology', '')} - {req.get('specific_areas', '')}" 
        for req in requests_list 
        if req.get('technology') and req.get('specific_areas')
    ]
    
    if not request_titles:
        st.warning("No valid learning requests available.")
        return

    selected_request = st.selectbox("Select Learning Request", request_titles, key="request_select", index=0)
    # Fetch the request data based on the selected index
    selected_request_data = requests_list[request_titles.index(selected_request)]
    technology = selected_request_data.get("technology")
    specific_areas = selected_request_data.get("specific_areas")

    num_questions = st.slider("Number of Questions", min_value=10, max_value=90, key="num_questions_requests")
    difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard"], key="difficulty_requests")

    if st.button("Generate Question Bank from Learning Request", key="generate_request_button"):
        # Construct the prompt using the selected learning request details
        prompt_text = (
            f"Generate {num_questions} multiple-choice questions on the topic of {selected_request}, "
            f"with a focus on {specific_areas}. The difficulty level should be {difficulty}."
        )
        
        # Use the prompt to generate and display questions
        generate_and_display_questions(prompt_text, num_questions, difficulty, document_name)


def extract_curriculum_content(selected_curriculum):
    curriculum_doc = curricula_collection.where("filename", "==", selected_curriculum).get()
    if curriculum_doc:
        for doc in curriculum_doc:
            curriculum_data = doc.to_dict()
            content = curriculum_data.get("content")
            return content
    return None

def extract_text_from_file(uploaded_file):
    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            text = [page.extract_text() for page in reader.pages]
            return "\n".join(text)
        else:
            return uploaded_file.getvalue().decode("utf-8")
    return ""

def generate_and_display_questions(prompt_text, num_questions, difficulty, document_name):
    # Generate questions based on the prompt
    generated_questions = generate_questions(
        api_key=os.environ["GOOGLE_API_KEY"],
        num_questions=num_questions,
        difficulty=difficulty,
        text_prompt=prompt_text
    )

    if not generated_questions:
        st.error("No valid questions generated. Please check your input.")
        return

    # Format questions for storage
    formatted_questions = format_questions(generated_questions)

    # Save questions to the database with custom document name
    generated_questions_collection.document(document_name).set({"questions": formatted_questions})

    # Display questions in the old style
    st.subheader("Generated Questions")
    for index, entry in enumerate(formatted_questions, start=1):
        st.write(f"**Question {index}:** {entry['question']}")
        st.write(f"A) {entry['option-1']}")
        st.write(f"B) {entry['option-2']}")
        st.write(f"C) {entry['option-3']}")
        st.write(f"D) {entry['option-4']}")
        st.write(f"**Answer:** {entry['answer']}")
        st.write("\n")  # Empty line between questions for better readability

    # Provide download options in CSV and PDF
    download_options(formatted_questions, document_name)

def format_questions(generated_questions):
    return [
        {
            "question": entry["question"],
            "option-1": entry.get("option-1", ""),
            "option-2": entry.get("option-2", ""),
            "option-3": entry.get("option-3", ""),
            "option-4": entry.get("option-4", ""),
            "answer": entry.get("answer", "")
        }
        for entry in generated_questions
    ]

def download_options(formatted_questions, document_name):
    csv_data = StringIO()
    csv_writer = csv.writer(csv_data)
    csv_writer.writerow(["Question", "Option 1", "Option 2", "Option 3", "Option 4", "Answer"])

    for q in formatted_questions:
        csv_writer.writerow([q['question'], q['option-1'], q['option-2'], q['option-3'], q['option-4'], q['answer']])

    st.download_button("Download as CSV", data=csv_data.getvalue(), file_name=f"{document_name}.csv", mime="text/csv")

    if st.button("Download as PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        for q in formatted_questions:
            pdf.multi_cell(0, 10, f"Question: {q['question']}")
            pdf.multi_cell(0, 10, f"A) {q['option-1']}")
            pdf.multi_cell(0, 10, f"B) {q['option-2']}")
            pdf.multi_cell(0, 10, f"C) {q['option-3']}")
            pdf.multi_cell(0, 10, f"D) {q['option-4']}")
            pdf.multi_cell(0, 10, f"Answer: {q['answer']}")
            pdf.ln(10)  # Adds a new line after each question set

        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)
        st.download_button("Download as PDF", data=pdf_output, file_name=f"{document_name}.pdf", mime="application/pdf")