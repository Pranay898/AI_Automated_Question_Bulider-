import os
import time
from langchain_google_genai import GoogleGenerativeAI
import streamlit as st
from turtle import shape
import streamlit as st
from db import curricula_collection, generated_questions_collection
from datetime import datetime
import pandas as pd
import csv
from io import StringIO, BytesIO
from fpdf import FPDF
import fitz  # PyMuPDF for PDF processing
from PIL import Image
import pytesseract
import docx2txt
from pptx import Presentation
import os
# Set API key for Google Gemini
api_key = "api.txt"  # Replace with your actual API key
os.environ["GOOGLE_API_KEY"] = api_key

def generate_questions(api_key, num_questions=10, difficulty="easy", text_prompt=""):
    llm = GoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=0.7)

    # Adjust prompt structure for low question counts
    if num_questions <= 5:
        prompt = (
            f"Generate at least {num_questions} concise multiple-choice questions at '{difficulty}' level. "
            "Each question should have four answer options labeled A, B, C, and D, with the correct answer specified as 'Answer: [correct option]'. "
            f"Include this context: '{text_prompt}'."
        )
    else:
        prompt = (
            f"Generate {num_questions} concise multiple-choice questions at '{difficulty}' level. "
            "Each question should have four answer options labeled A, B, C, and D, with the correct answer specified as 'Answer: [correct option]'. "
            f"Include this context: '{text_prompt}'."
        )

    # Attempt generating questions with structured retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)

            # Check if response contains content before processing
            if response and isinstance(response, str):
                questions = []
                blocks = response.split("\n\n")  # Split by double newlines

                for block in blocks:
                    lines = block.split("\n")
                    if len(lines) >= 5:
                        question_text = lines[0].strip()
                        options = [line.strip() for line in lines[1:5]]
                        answer = lines[5].split(":")[-1].strip() if "Answer:" in lines[5] else ""

                        # Reformat to your specified format and append to list
                        questions.append({
                            "question": question_text,
                            "option-1": options[0] if len(options) > 0 else "",
                            "option-2": options[1] if len(options) > 1 else "",
                            "option-3": options[2] if len(options) > 2 else "",
                            "option-4": options[3] if len(options) > 3 else "",
                            "answer": answer
                        })

                # Check if questions were successfully parsed
                if questions:
                    return questions
                else:
                    st.warning("No valid questions were parsed. Retrying...")

        except Exception as e:
            st.error(f"Attempt {attempt + 1} - Error: {e}")
            time.sleep(1)  # Brief wait before retrying

    st.error("Failed to generate questions after multiple attempts.")
    return []

def extract_text_from_file(file):
    """Extract text based on file type (PDF, CSV, JPG/PNG, DOCX, PPTX, XLSX)"""
    try:
        if file.type == "application/pdf":
            text = ""
            with fitz.open(stream=file.read(), filetype="pdf") as pdf:
                for page in pdf:
                    text += page.get_text("text")
            return text.strip() if text else "PDF file is empty or cannot be parsed."
        
        elif file.type == "text/csv":
            df = pd.read_csv(file)
            return df.to_string(index=False)
        
        elif file.type in ["image/jpeg", "image/png"]:
            image = Image.open(file)
            return pytesseract.image_to_string(image)
        
        elif file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return docx2txt.process(file).strip()
        
        elif file.type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            ppt = Presentation(file)
            return "\n".join([shape.text for slide in ppt.slides if hasattr(shape, "text")]).strip()
        
        elif file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            df = pd.read_excel(file)
            return df.to_string(index=False)
    except Exception as e:
        return f"Error parsing file: {str(e)}"
