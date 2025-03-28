from groq import Groq
from config import GROQ_API_KEY
import streamlit as st

class LLMService:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def get_response(self, prompt):
        placeholder = st.empty()
        placeholder.text("🤖 Generating response...")
        full_response = ""
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
                stream=True
            )
            for chunk in response:
                token = getattr(chunk.choices[0].delta, "content", "")
                token = token if token is not None else ""
                full_response += token
                placeholder.markdown(full_response)
            return full_response.strip()
        except Exception as e:
            st.error(f"LLM error: {str(e)}")
            return None

    def extract_symptoms(self, user_input):
        prompt = f"""Extract medical symptoms from this text:
        {user_input}
        Return only comma-separated lowercase terms."""
        return self.get_response(prompt)

    def generate_health_tips(self, symptoms):
        prompt = f"""The patient has these symptoms: {', '.join(symptoms)}
        Provide 3 practical first-aid tips.
        Format as bullet points.
        Do not provide medical advice."""
        return self.get_response(prompt)

llm_service = LLMService()
get_response = llm_service.get_response
extract_symptoms = llm_service.extract_symptoms
generate_health_tips = llm_service.generate_health_tips