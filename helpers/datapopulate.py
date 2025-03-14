import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def populate_sample_data():
    # Connect to MongoDB
    uri = "mongodb+srv://docxpara12:XOP93MPOOTcipQwe@cluster0.434x6.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client["hospital_system"]
    doctors = db["doctors"]
    
    try:
        # Clear existing data
        doctors.delete_many({})
        
        json_file_path = os.path.join(os.path.dirname(__file__), "data.json")
        with open(json_file_path, "r") as f:
            sample_doctors = json.load(f)
        # Sample doctor data
    
        
        # Insert sample data
        result = doctors.insert_many(sample_doctors)
        print(f"Inserted {len(result.inserted_ids)} doctors")
        
        # Verify insertion
        print(f"Total doctors in database: {doctors.count_documents({})}")
        
    except FileNotFoundError:
        print("Error: doctors.json file not found")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in doctors.json")
    except Exception as e:
        print(f"Error populating data: {str(e)}")
    finally:
        client.close()
        
if __name__ == "__main__":
    populate_sample_data()