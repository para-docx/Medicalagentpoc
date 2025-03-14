import os
from typing import TypedDict, List, Dict, Annotated
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import warnings

# Load environment variables
load_dotenv()

# MongoDB Setup
uri = "mongodb+srv://docxpara12:XOP93MPOOTcipQwe@cluster0.434x6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
warnings.filterwarnings('ignore', category=DeprecationWarning)
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["hospital_system"]
doctors = db["doctors"]
symptoms = db["symptoms"]

# Groq Setup
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class MedicalState(TypedDict):
    messages: Annotated[List[str], add_messages]
    symptoms: List[str]
    matched_specializations: List[str]
    health_tips: List[str]
    available_doctors: List[Dict]
    raw_input: str
    stop: bool

class LLMHelper:
    @staticmethod
    def get_llm_response(prompt, temperature=0.3):
        try:
            response = groq_client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM Error: {str(e)}")
            return None

def greet_user(state: MedicalState) -> MedicalState:
    return {
        "messages": ["🏥 Welcome to HealthAssist Pro! How can I help you today?"],
        "symptoms": [],
        "matched_specializations": [],
        "health_tips": [],
        "available_doctors": [],
        "raw_input": "",
        "stop": False
    }


def get_symptoms(state: MedicalState) -> MedicalState:
    """Get user input and extract symptoms"""
    # Only prompt if we don't have symptoms yet
    if not state["symptoms"]:
        print("\nUser: ", end="")  # Prompt for input
        user_input = input().strip()
        
        # Extract symptoms from ACTUAL user input
        prompt = f"""Extract medical symptoms from this text:
        {user_input}
        Return only comma-separated lowercase terms."""
        
        llm_response = LLMHelper.get_llm_response(prompt)
        symptoms = [s.strip().lower() for s in llm_response.split(",")] if llm_response else []
        
        return {
            **state,
            "messages": [f"Identified symptoms: {', '.join(symptoms)}" if symptoms else "No symptoms identified"],
            "symptoms": symptoms,
            "raw_input": user_input
        }
    return state

    
def find_specialization(state: MedicalState) -> MedicalState:
    """Determine appropriate specialization"""
    if not state["symptoms"]:
        return {
            **state,
            "messages": ["I don't see any specific symptoms. Could you describe how you're feeling?"],
            "stop": True
        }
    
    prompt = f"""Based on these symptoms: {', '.join(state['symptoms'])}
    Recommend one specialization from: Cardiologist, Dermatologist, General Practitioner.
    Return only the specialization name."""
    
    specialization = LLMHelper.get_llm_response(prompt) or "General Practitioner"
    
    return {
        **state,
        "messages": [f"Based on your symptoms, I recommend seeing a {specialization}."],
        "matched_specializations": [specialization]
    }

def generate_health_tips(state: MedicalState) -> MedicalState:
    if not state["symptoms"]:
        return {
            **state,
            "messages": ["Let's start over. Please describe your symptoms."],
            "stop": True
        }
    
    prompt = f"""The patient has these symptoms: {', '.join(state['symptoms'])}
    Provide 3 practical first-aid tips.
    Format as bullet points.
    Do not provide medical advice."""
    
    tips = LLMHelper.get_llm_response(prompt) or "- Consult a medical professional"
    formatted_tips = [t.strip() for t in tips.split("\n") if t.strip()]
    
    return {
        **state,
        "messages": ["Here are some tips while you wait:"],
        "health_tips": formatted_tips[:3]
    }

def check_availability(state: MedicalState) -> MedicalState:
    """Check doctor availability with proper MongoDB query"""
    today = datetime.now().strftime("%A")
    current_time = datetime.now().strftime("%H:%M")
    available = []
    
    try:
        # Find doctors with matching specialization and availability
        for doc in doctors.find({"specialization": {"$in": state["matched_specializations"]}}):
            for slot in doc.get("availability", []):
                if (slot["day"] == today and
                    slot["start"] <= current_time <= slot["end"] and
                    doc.get("current_appointments", 0) < slot.get("max_patients", 0)):
                    available.append(doc)
                    break
        
        return {
            "messages": [f"Found {len(available)} available doctors"],
            "available_doctors": available[:3],
            "stop": len(available) == 0,
            **{k: v for k, v in state.items() if k not in ["messages", "available_doctors", "stop"]}
        }
    except Exception as e:
        print(f"Database error: {str(e)}")
        return {
            **state,
            "messages": ["⚠️ Error checking doctor availability. Please try again later."],
            "available_doctors": [],
            "stop": True
        }


def format_response(state: MedicalState) -> MedicalState:
    today = datetime.now().strftime("%A")
    response = ["\nI understand you're not feeling well. Let me help you with that!"]
    
    # Add symptoms acknowledgment
    symptoms_text = ", ".join(state["symptoms"])
    response.append(f"Based on your symptoms of {symptoms_text}, here are some helpful tips:")
    
    # Add health tips with better formatting
    for tip in state["health_tips"][:3]:
        response.append(f"👉 {tip}")
    
    # Doctor availability section
    response.append("\n🏥 Available Medical Professionals:")
    if state["available_doctors"]:
        for i, doc in enumerate(state["available_doctors"][:3], 1):
            slot = next(s for s in doc["availability"] if s["day"] == today)
            response.append(
                f"✨ Dr. {doc['name']} ({doc['specialization']}) "
                f"can see you until {slot['end']}. "
                f"They have {slot['max_patients'] - doc['current_appointments']} slots remaining."
            )
    else:
        response.append("I apologize, but there are no doctors available at this moment. "
                       "Please consider visiting the emergency room if this is urgent, "
                       "or try again during regular office hours.")
    
    # Closing message
    response.append("\nIs there anything else you'd like to know? Take care! 🌟")
    
    return {
        "messages": response,
        **{k: v for k, v in state.items() if k != "messages"}
    }

def setup_workflow():
    workflow = StateGraph(MedicalState)
    
    # Define nodes
    workflow.add_node("greet", greet_user)
    workflow.add_node("get_symptoms", get_symptoms)
    workflow.add_node("find_specialization", find_specialization)
    workflow.add_node("generate_tips", generate_health_tips)
    workflow.add_node("check_availability", check_availability)
    workflow.add_node("format_response", format_response)

    # Set up proper transitions
    workflow.set_entry_point("greet")
    workflow.add_edge("greet", "get_symptoms")
    workflow.add_edge("get_symptoms", "find_specialization")
    workflow.add_edge("find_specialization", "generate_tips")
    workflow.add_edge("generate_tips", "check_availability")
    workflow.add_edge("check_availability", "format_response")
    workflow.add_edge("format_response", END)
    
    # Add conditional loop for symptom collection
    workflow.add_conditional_edges(
        "get_symptoms",
        lambda s: "find_specialization" if s["symptoms"] 
                  else "get_symptoms"  # Loop back if no symptoms
    )
    
    return workflow.compile()

def run_medical_assistant():
    print("Starting medical assistant...\n")
    try:
        app = setup_workflow()
        state = app.invoke({"messages": [], "symptoms": [], "stop": False})
        
        # Process conversation flow
        while True:
            # Print bot messages
            for msg in state.get("messages", []):
                print(f"Bot: {msg}")
            
            # Exit condition
            if state.get("stop"):
                break
            
            # Get next state
            state = app.invoke(state)
            
            # Handle user input at the right stage
            if "get_symptoms" in state.get("__end__", ""):
                print("\nUser: ", end="")
                user_input = input().strip()
                state = app.invoke({
                    **state,
                    "raw_input": user_input,
                    "messages": []
                })
        
        print("\n✅ Consultation complete")
        
    except Exception as e:
        print(f"\n⚠️ System error: {str(e)}")
        print("Please contact hospital staff directly")

if __name__ == "__main__":
    run_medical_assistant()
