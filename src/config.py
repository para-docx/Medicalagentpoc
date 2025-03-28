from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = "mongodb+srv://docxpara12:XOP93MPOOTcipQwe@cluster0.434x6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "hospital_system"

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# UI Configuration
PAGE_TITLE = "HealthAssist Pro"
PAGE_ICON = "🏥"
CUSTOM_CSS = """
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
"""
