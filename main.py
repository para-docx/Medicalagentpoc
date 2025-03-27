import streamlit as st
from datetime import datetime
from groq import Groq
from pymongo import MongoClient
import os
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
from datetime import datetime, time 
from pymongo import MongoClient
# Load environment variables
load_dotenv()

# MongoDB Setup
uri = "mongodb+srv://docxpara12:XOP93MPOOTcipQwe@cluster0.434x6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["hospital_system"]
doctors = db["doctors"]
symptoms = db["symptoms"]

# Groq Setup
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Streamlit App
st.set_page_config(page_title="HealthAssist Pro", page_icon="🏥", layout="centered")

# Custom CSS for modern UI
st.markdown("""
<style>
    .stApp {
        background-color: #000000;
    }
    .stTextInput > div > div > input {
        border-radius: 20px;
        padding: 10px;
    }
    .stButton > button {
        border-radius: 20px;
        background-color: #4CAF50;
        color: white;
        padding: 10px 24px;
        border: none;
    }
    .stMarkdown {
        font-family: 'Arial', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# State Management
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "🏥 Welcome to HealthAssist Pro! How can I help you today?"}]

if "symptoms" not in st.session_state:
    st.session_state.symptoms = []

if "matched_specializations" not in st.session_state:
    st.session_state.matched_specializations = []

if "health_tips" not in st.session_state:
    st.session_state.health_tips = []

if "available_doctors" not in st.session_state:
    st.session_state.available_doctors = []

# Helper Functions
def get_llm_response(prompt):
    try:
        response = groq_client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"LLM Error: {str(e)}")
        return None

def extract_symptoms(user_input):
    prompt = f"""Extract medical symptoms from this text:
    {user_input}
    Return only comma-separated lowercase terms."""
    return get_llm_response(prompt)

def find_specialization(symptoms: list) -> str:
    """
    Find medical specialization using LLM with MongoDB validation.
    Returns a specialization name that exists in the database.
    """
    try:
        # Get unique specializations from the database with a safe default
        specializations = doctors.distinct("specialization") or ["General Practitioner"]

        prompt = f"""Analyze these symptoms: {', '.join(symptoms)}
Recommend a specialization from this list: {', '.join(specializations)}
Return only the specialization name from the list."""
        
        response = get_llm_response(prompt)
        if response:
            spec = response.strip()
            # Check for an exact match first
            if spec in specializations:
                return spec
            # If no exact match, perform a fuzzy matching (case-insensitive substring comparison)
            for s in specializations:
                if spec.lower() in s.lower() or s.lower() in spec.lower():
                    return s
        return "General Practitioner"
    except Exception as e:
        st.error(f"Specialization error: {str(e)}")
        return "General Practitioner"

    
def generate_health_tips(symptoms):
    prompt = f"""The patient has these symptoms: {', '.join(symptoms)}
    Provide 3 practical first-aid tips.
    Format as bullet points.
    Do not provide medical advice."""
    return get_llm_response(prompt)

def check_availability(specialization: str) -> list:
    """
    Check doctor availability and next available slots.
    Returns list of doctors with current and next availability.
    """
    def get_next_slot(doctor, days_order, today_idx, current_time_str):
        """Find next available slot for a doctor"""
        for offset in range(7):
            day_idx = (today_idx + offset) % 7
            day = days_order[day_idx]
            
            # Check all slots for this day, normalizing the day name
            for slot in doctor.get("availability", []):
                slot_day = slot.get("day", "").strip().lower()
                if slot_day == day.lower():
                    # For today - check for a future slot
                    if day.lower() == current_day.lower():
                        if slot.get("start") > current_time_str:
                            return {
                                "day": "Today",
                                "time": f"{slot['start']}-{slot['end']}",
                                "slots": slot.get("max_patients", 0) - doctor.get("current_appointments", 0)
                            }
                    # For other days - return the first slot found
                    else:
                        return {
                            "day": day,
                            "time": f"{slot['start']}-{slot['end']}",
                            "slots": slot.get("max_patients", 0) - doctor.get("current_appointments", 0)
                        }
        return None

    current_day = datetime.now().strftime("%A")
    current_time_str = datetime.now().strftime("%H:%M")
    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_idx = days_order.index(current_day)
    doctors_list = []

    try:
        for doc in doctors.find({"specialization": specialization}):
            doctor_info = {
                "name": doc.get("name", "Unknown Doctor"),
                "available_now": False,
                "current_slots": 0,
                "next_available": None
            }

            # Check current availability with normalized day names
            for slot in doc.get("availability", []):
                slot_day = slot.get("day", "").strip().lower()
                if (slot_day == current_day.lower() and
                    slot.get("start") <= current_time_str <= slot.get("end") and
                    doc.get("current_appointments", 0) < slot.get("max_patients", 0)):
                    
                    doctor_info["available_now"] = True
                    doctor_info["current_slots"] = slot["max_patients"] - doc["current_appointments"]
                    break

            # Find next available slot if not currently available
            if not doctor_info["available_now"]:
                doctor_info["next_available"] = get_next_slot(doc, days_order, today_idx, current_time_str)

            doctors_list.append(doctor_info)

        return doctors_list

    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return []
    

# Chat Interface
st.title("🏥 HealthAssist Pro")
st.caption("Your AI-powered medical assistant for xyz hospital")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Describe your symptoms..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process symptoms
    llm_response = extract_symptoms(prompt)
    symptoms = [s.strip().lower() for s in llm_response.split(",")] if llm_response else []
    st.session_state.symptoms = symptoms
    
    # Add bot response for symptoms
    if symptoms:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Understood. You mentioned: {', '.join(symptoms)}"
        })
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "I don't see any specific symptoms. Could you describe how you're feeling?"
        })
        st.stop()
    
    # Find specialization
    specialization = find_specialization(symptoms) or "General Practitioner"
    st.session_state.matched_specializations = [specialization]
    st.session_state.messages.append({
        "role": "assistant",
        "content": f"Based on your symptoms, I recommend seeing a {specialization}."
    })
    
    # Generate health tips
    tips = generate_health_tips(symptoms) or "- Consult a medical professional"
    formatted_tips = [t.strip() for t in tips.split("\n") if t.strip()]
    st.session_state.health_tips = formatted_tips[:3]
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Here are some tips while you wait:\n" + "\n".join(f"- {tip}" for tip in formatted_tips[:3])
    })
    
    # Check doctor availability
    available = check_availability(specialization)
    st.session_state.available_doctors = available[:3]
    if available:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Found {len(available)} available doctors"
        })
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "No available doctors at this time."
        })
    
    # Display after getting doctor availability
    if available:
        response = ["Medical Assistance:"]
        response.append("\nAvailable Doctors:")
        current_available = [doc for doc in available if doc["available_now"]]
        future_available = [doc for doc in available if not doc["available_now"] and doc["next_available"]]
        
        if current_available:
            response.append("\nAvailable now:")
            for doc in current_available:
                response.append(
                    f"- {doc['name']}: {doc['current_slots']} slots left (Open until {doc['next_available']['time'] if doc['next_available'] else 'unknown'})"
                )
        else:
            response.append("No doctors available right now, Checking for next available slots...")
            
        if future_available:
            response.append("\nNext available:")
            for doc in future_available:
                response.append(
                    f"- {doc['name']}: {doc['next_available']['day']} at {doc['next_available']['time']} ({doc['next_available']['slots']} slots)"
                )
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": "\n".join(response)
        })
    else:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "No available doctors at this time"})
    # Rerun to display new messages
    st.rerun()
