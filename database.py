from pymongo import MongoClient

MONGO_URL = "mongodb://localhost:27017"

client = MongoClient(MONGO_URL)

db = client["smart_attendance"]

students_collection = db["students"]
attendance_collection = db["attendance"]