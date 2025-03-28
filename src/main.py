import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

from database import get_collection, get_distinct_specializations
from llm_service import LLMService
from doctor_service import DoctorService
from config import PAGE_TITLE, PAGE_ICON, CUSTOM_CSS

# Load environment variables
load_dotenv()



# Setup
doctors_collection = get_collection("doctors")
symptoms = get_collection("symptoms")

llm_service = LLMService()
doctor_service = DoctorService(doctors_collection, llm_service)
# Streamlit App Configuration
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="centered")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Define conversation memory class within main.py
class ConversationMemory:
    def __init__(self):
        self.history = []

    def add_message(self, role, content):
        self.history.append({"role": role, "content": content})

    def get_history(self):
        return self.history

    def clear(self):
        self.history = []

# Set up conversation memory in session_state if not already done
if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()

# Initialize session_state variables for chat state if not already present
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

if "initial_task_complete" not in st.session_state:
    st.session_state.initial_task_complete = False
    
# Display conversation
st.title("🏥 HealthAssist Pro")
st.caption("Your AI-powered medical assistant for xyz hospital")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Main input for symptom description (only if conversation is still in the main flow)
if not st.session_state.symptoms and (prompt := st.chat_input("Describe your symptoms...")):
    st.session_state.memory.add_message("user", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Process symptoms using the LLM
    llm_response = llm_service.extract_symptoms(prompt)
    symptoms_list = [s.strip().lower() for s in llm_response.split(",")] if llm_response else []
    st.session_state.symptoms = symptoms_list

    if symptoms_list:
        response_text = f"Understood. You mentioned: {', '.join(symptoms_list)}"
    else:
        response_text = "I don't see any specific symptoms. Could you describe how you're feeling?"
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.session_state.memory.add_message("assistant", response_text)
    st.rerun()

# Once symptoms have been processed, run the remaining workflow once
if st.session_state.symptoms and not st.session_state.matched_specializations:
    specialization = doctor_service.find_specialization(st.session_state.symptoms) or "General Practitioner"
    st.session_state.matched_specializations = [specialization]
    spec_message = f"Based on your symptoms, I recommend seeing a {specialization}."
    st.session_state.messages.append({"role": "assistant", "content": spec_message})
    st.session_state.memory.add_message("assistant", spec_message)
    
    tips = llm_service.generate_health_tips(st.session_state.symptoms) or "- Consult a medical professional"
    formatted_tips = [t.strip() for t in tips.split("\n") if t.strip()]
    st.session_state.health_tips = formatted_tips[:3]
    tips_message = "Here are some tips while you wait:\n" + "\n".join(f"- {tip}" for tip in formatted_tips[:3])
    st.session_state.messages.append({"role": "assistant", "content": tips_message})
    st.session_state.memory.add_message("assistant", tips_message)
    
    doctors_list = doctor_service.check_availability(specialization)
    st.session_state.available_doctors = doctors_list[:3]
    avail_message = f"Found {len(doctors_list)} available doctors. Would you like to check for an appointment." if doctors_list else "No available doctors at this time."
    st.session_state.messages.append({"role": "assistant", "content": avail_message})
    st.session_state.memory.add_message("assistant", avail_message)
    st.session_state.initial_task_complete = True
    st.rerun()

# Follow-up Q&A: Allow the user to ask additional questions combining conversation history
if st.session_state.initial_task_complete:
    if qa := st.chat_input("Ask a follow-up question about your disease or doctor:"):
        st.session_state.memory.add_message("user", qa)
        st.session_state.messages.append({"role": "user", "content": qa})
        with st.chat_message("user"):
            st.markdown(qa)
        
        # Build conversation context from the memory history for LLM prompt
        conversation_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.memory.get_history()])
        answer = llm_service.get_response(conversation_context)
        st.session_state.memory.add_message("assistant", answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
        
        st.rerun()
