# db.py
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase_credentials.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
users_collection = db.collection("users")
generated_questions_collection = db.collection("generated_questions")
performance_metrics_collection = db.collection("performance_metrics")
curricula_collection = db.collection("curriculum_uploads")
feedback_collection = db.collection("feedback")  # For storing employee feedback
issues_collection = db.collection("issues")  # For storing employee-reported issues
user_requests_collection = db.collection("user_requests")
user_activity_collection = db.collection("user_activity")
