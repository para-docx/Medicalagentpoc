from pymongo import MongoClient
from pymongo.server_api import ServerApi
from config import MONGODB_URI, DB_NAME

def get_database_connection():
    client = MongoClient(MONGODB_URI, server_api=ServerApi('1'))
    return client[DB_NAME]

def get_collection(collection_name):
    db = get_database_connection()
    return db[collection_name]

def get_distinct_specializations(doctors_collection):
    return doctors_collection.distinct("specialization") or ["General Practitioner"]
