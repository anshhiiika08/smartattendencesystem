from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId
from fastapi import HTTPException
from datetime import datetime
import os
import shutil

import cv2
import numpy as np
import face_recognition
import base64


# =====================================================
# FastAPI App
# =====================================================

app = FastAPI()

# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# MongoDB Connection
# =====================================================

client = MongoClient("mongodb://localhost:27017")

db = client["smart_attendance"]

students_collection = db["students"]
attendance_collection = db["attendance"]
admins_collection = db["admins"]

# =====================================================
# Upload Folder
# =====================================================

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# =====================================================
# Home Route
# =====================================================

@app.get("/")
def home():
    return {
        "message": "Smart Attendance API Running"
    }

# =====================================================
# Student Registration
# =====================================================

@app.post("/register-student")
async def register_student(
    name: str = Form(...),
    roll_number: str = Form(...),
    email: str = Form(...),
    department: str = Form(...),
    semester: str = Form(...),
    image: UploadFile = File(...)
):

    # Check duplicate roll number

    existing_student = students_collection.find_one(
        {"roll_number": roll_number}
    )

    if existing_student:
        return {
            "success": False,
            "message": "Roll Number Already Exists"
        }

    # Save Image

    image_path = os.path.join(
        UPLOAD_DIR,
        image.filename
    )

    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # Create Student Document

    student = {
        "name": name,
        "roll_number": roll_number,
        "email": email,
        "department": department,
        "semester": semester,
        "image_path": image_path
    }

    # Insert Into MongoDB

    result = students_collection.insert_one(student)

    return {
        "success": True,
        "message": "Student Registered Successfully",
        "student_id": str(result.inserted_id)
    }

# =====================================================
# Get All Students
# =====================================================

@app.get("/students")
def get_students():

    students = []

    for student in students_collection.find():

        student["_id"] = str(student["_id"])

        students.append(student)

    return students


# =====================================================
# login Data
# =====================================================
class Admin(BaseModel):
    name: str
    email: str
    password: str

@app.post("/signup")
def signup(admin: Admin):

    # Check if email already exists
    existing_admin = admins_collection.find_one({"email": admin.email})

    if existing_admin:
        return {
            "success": False,
            "message": "Email already exists"
        }

    # Save admin
    admins_collection.insert_one({
        "name": admin.name,
        "email": admin.email,
        "password": admin.password
    })

    return {
        "success": True,
        "message": "Account Created Successfully"
    }

class LoginData(BaseModel):
    email: str
    password: str
    
class ImageData(BaseModel):
    image: str
    
admins_collection = db["admins"]

@app.post("/login")
def login(data: dict):

    admin = admins_collection.find_one({
        "email": data["email"]
    })

    if not admin:
        return {
            "success": False,
            "message": "Admin not found"
        }

    if admin["password"] != data["password"]:
        return {
            "success": False,
            "message": "Incorrect password"
        }

    return {
        "success": True,
        "message": "Login Successful",
        "token": "admin-token"
    }

    
@app.post("/recognize")
async def recognize_face(data: ImageData):

    try:

        # Remove base64 header
        image_data = data.image.split(",")[1]

        # Decode image
        image_bytes = base64.b64decode(image_data)

        np_arr = np.frombuffer(image_bytes, np.uint8)

        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb)

        if len(face_locations) == 0:
            raise HTTPException(
                status_code=404,
                detail="No Face Detected"
            )

        face_encodings = face_recognition.face_encodings(
            rgb,
            face_locations
        )

        if len(face_encodings) == 0:
            raise HTTPException(
                status_code=404,
                detail="Face Encoding Failed"
            )

        unknown_encoding = face_encodings[0]

        # Search all registered students
        students = list(students_collection.find())

        for student in students:

            image_path = student["image_path"]

            if not os.path.exists(image_path):
                continue

            known_image = face_recognition.load_image_file(image_path)

            known_encodings = face_recognition.face_encodings(
                known_image
            )

            if len(known_encodings) == 0:
                continue

            known_encoding = known_encodings[0]

            match = face_recognition.compare_faces(
                [known_encoding],
                unknown_encoding,
                tolerance=0.45
            )

            if match[0]:

                today = datetime.now().strftime("%Y-%m-%d")

                existing = attendance_collection.find_one(
                    {
                        "roll_number": student["roll_number"],
                        "date": today
                    }
                )

                if existing:

                    return {
                        "success": True,
                        "message": "Attendance Already Marked",
                        "student": {
                            "name": student["name"],
                            "roll_number": student["roll_number"],
                            "department": student["department"]
                        }
                    }

                attendance_collection.insert_one({

                    "student_id": str(student["_id"]),

                    "name": student["name"],

                    "roll_number": student["roll_number"],

                    "department": student["department"],

                    "date": today,

                    "time": datetime.now().strftime("%H:%M:%S"),

                    "status": "Present"

                })

                return {

                    "success": True,

                    "message": "Attendance Marked",

                    "student": {

                        "name": student["name"],

                        "roll_number": student["roll_number"],

                        "department": student["department"]

                    }

                }

        raise HTTPException(
            status_code=404,
            detail="Face Not Recognized"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
        
        
@app.get("/attendance")
def get_attendance():

    attendance = []

    for record in attendance_collection.find():

        record["_id"] = str(record["_id"])

        attendance.append(record)

    return attendance

@app.get("/student-attendance/{roll_number}")
def student_attendance(roll_number: str):

    records = []

    for record in attendance_collection.find(
        {
            "roll_number": roll_number
        }
    ):

        record["_id"] = str(record["_id"])

        records.append(record)

    return records


@app.get("/daily-report")
def daily_report():

    today = datetime.now().strftime("%Y-%m-%d")

    present = list(
        attendance_collection.find(
            {
                "date": today
            }
        )
    )

    total_students = students_collection.count_documents({})

    return {

        "date": today,

        "total_students": total_students,

        "present": len(present),

        "absent": total_students - len(present)

    }
    
@app.get("/dashboard-stats")
def dashboard_stats():

    total_students = students_collection.count_documents({})

    total_attendance = attendance_collection.count_documents({})

    return {

        "total_students": total_students,

        "attendance_records": total_attendance

    }
    
    
@app.delete("/delete-student/{student_id}")
def delete_student(student_id: str):
    student = students_collection.find_one({"_id": ObjectId(student_id)})

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Delete uploaded image
    image_path = student.get("image_path")
    if image_path and os.path.exists(image_path):
        os.remove(image_path)

    # Delete student record
    students_collection.delete_one({"_id": ObjectId(student_id)})

    # Delete attendance records for that student
    attendance_collection.delete_many(
        {"roll_number": student["roll_number"]}
    )

    return {"message": "Student deleted successfully"}