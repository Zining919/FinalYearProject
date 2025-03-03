import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime, timedelta, timezone
import supabase
from supabase import create_client
import random
import uuid
from werkzeug.utils import secure_filename
#import mimetypes
import supabase
# import tensorflow as tf
# from io import BytesIO
from PIL import Image
#from werkzeug.utils import secure_filename
from keras.models import load_model
from keras.preprocessing.image import img_to_array
import numpy as np
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Your Supabase project URL and API key
SUPABASE_URL = "https://tmegfunkplvtdlmzgcvc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRtZWdmdW5rcGx2dGRsbXpnY3ZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk4NTcwMTUsImV4cCI6MjA1NTQzMzAxNX0.n5bYPpFujiJQoGF5ACI-TwfguLTsFROg8bK2XeqCLFY"
SUPABASE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRtZWdmdW5rcGx2dGRsbXpnY3ZjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczOTg1NzAxNSwiZXhwIjoyMDU1NDMzMDE1fQ.GRq14NfLHUA3nOTwJY6ri5VsynS-HXOvx_zQQfgcEhM"

# Create a Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load Models
CT_MODEL_PATH = "ct_effnet_best_model.keras"
MRI_MODEL_PATH = "ct_effnet_best_model.keras"

ct_model = load_model(CT_MODEL_PATH)
mri_model = load_model(MRI_MODEL_PATH)

# Define label mappings (adjust the mapping if needed)
brain_labels = {0: "glioma", 1: "meningioma", 2: "notumor", 3: "pituitary"}
lung_labels = {0: "adenocarcinoma", 1: "large.cell.carcinoma", 2: "normal", 3: "squamous.cell.carcinoma"}

# Allowed file extensions
UPLOAD_FOLDER = "/upload/image"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'jfif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to a new person(nurse/doctor/patient) to the JSON file
def save_ppl(filePath,data):
    with open(filePath, "w") as file:
        json.dump(data, file, indent=4)


print(supabase.auth.get_session())

# # Only allow Manager, Doctor and Nurse to LogIn DONE
@app.route("/", methods=["GET", "POST"])
def index_main():
    if request.method == "POST":
        email = request.form["email"].strip().lower()  # Convert to lowercase to avoid case issues
        password = request.form["psw"].strip()

        try:
            # Authenticate user with Supabase
            response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            
            if response.user:
                first_letter = email[0]  # Get first character of email
                
                # Determine the user role and fetch ID + status
                if first_letter == "d":  # Doctor
                    user_response = supabase.table("doctor").select("id", "startdate", "enddate", "status").eq("email", email).execute()
                elif first_letter == "n":  # Nurse
                    user_response = supabase.table("nurse").select("id", "startdate", "enddate", "status").eq("email", email).execute()
                else:  # Manager
                    user_response = supabase.table("manager").select("id").eq("email", email).execute()

                if not user_response.data:
                    return render_template("main/index.html", error="User not found in records.")

                user_data = user_response.data[0]
                user_id = user_data["id"]

                # Skip status checks for managers (assuming they don't have contracts)
                if first_letter in ["d", "n"]:
                    today = datetime.today().date()
                    start_date = datetime.strptime(user_data["startdate"], "%Y-%m-%d").date()
                    end_date = datetime.strptime(user_data["enddate"], "%Y-%m-%d").date()
                    status = user_data["status"]

                    # Automatically update status if needed
                    if status == "pending" and start_date <= today:
                        status = "active"
                        supabase.table("doctor" if first_letter == "d" else "nurse").update({"status": "active"}).eq("id", user_id).execute()
                    elif status == "active" and today > end_date:
                        status = "expired"
                        supabase.table("doctor" if first_letter == "d" else "nurse").update({"status": "expired"}).eq("id", user_id).execute()

                    # Restrict login for non-active users
                    if status != "active":
                        return render_template("main/index.html", error=f"Access denied. Your account status is {status}.")

                # Redirect based on role
                session["user"] = email  # Store session
                if first_letter == "d":
                    return redirect(url_for("doctor_index", id=user_id))
                elif first_letter == "n":
                    return redirect(url_for("nurse_index", id=user_id))
                else:
                    return redirect(url_for("manager_index", id=user_id))

            return render_template("main/index.html", error="Wrong Email or Password Entered.")

        except Exception as e:
            print(f"Error during login: {e}")
            return render_template("main/index.html", error="An error occurred. Please try again.")

    return render_template("main/index.html")



# 🔹 Route: Logout
@app.route("/logout")
def logout():
    session.pop("user", None)  # Remove user from session
    supabase.auth.sign_out()
    return redirect(url_for("index_main"))

# Access Management index page DONE
## NOTE: add code to check end date for status(expired/active/terminated)
@app.route("/manage/<string:id>")
def manager_index(id):
    # Fetch manager data
    m_response = supabase.table("manager").select("*").execute()

    # Fetch doctors and nurses data
    d_response = supabase.table("doctor").select("*").execute()
    n_response = supabase.table("nurse").select("*").execute()

    # Fetch doctor leave requests with department details
    leave_response = (
        supabase.table("doctor_leave")
        .select("id, doctor_id, leave_date, reason, status, doctor(id, name, department_id)")
        .eq('status', 'Pending')
        .execute()
    )

    # Fetch all departments
    departments = supabase.table("department").select("id, name").execute()

    # ✅ Create a lookup dictionary for department names
    department_lookup = {dept["id"]: dept["name"] for dept in departments.data} if departments.data else {}

    # ✅ Process the leave response and assign department names
    pending_leaves = []
    if leave_response.data:
        for leave in leave_response.data:  
            doc = leave.get("doctor", {})
            department_id = doc.get("department_id")
                
            # ✅ Make sure department_name is assigned correctly
            leave["department_name"] = department_lookup.get(department_id, "Unknown")
                
            pending_leaves.append(leave)

    # ✅ Count active, expired, and terminated doctors and nurses
    pending = active = expired = terminated = 0  

    if d_response.data:
        pending += sum(1 for doctor in d_response.data if doctor.get("status") == "pending")
        active += sum(1 for doctor in d_response.data if doctor.get("status") == "active")
        expired += sum(1 for doctor in d_response.data if doctor.get("status") == "expired")
        terminated += sum(1 for doctor in d_response.data if doctor.get("status") == "terminated")

    if n_response.data:
        pending += sum(1 for nurse in n_response.data if nurse.get("status") == "pending")
        active += sum(1 for nurse in n_response.data if nurse.get("status") == "active")
        expired += sum(1 for nurse in n_response.data if nurse.get("status") == "expired")
        terminated += sum(1 for nurse in n_response.data if nurse.get("status") == "terminated")

    count = {
        "d_count": len(d_response.data) if d_response.data else 0,
        "n_count": len(n_response.data) if n_response.data else 0,
        "p_count": len(m_response.data) if m_response.data else 0,
        "pending": pending,
        "active": active,
        "expired": expired,
        "terminated": terminated
    }

    # ✅ Find the specific manager
    if m_response.data:
        for ppl in m_response.data:
            if id == ppl["id"]:
                return render_template("manage/manager_index.html", ppl=ppl, count=count, leave_requests=pending_leaves, staff_id = id)

    return "Person not found.", 404



# Retrieve the data from Supabase DONE
@app.route("/<string:db_type>_db/<string:staff_id>")
def manage_db(db_type, staff_id):
    table_map = {
        "doctors": "doctor",
        "nurses": "nurse",
        "patients": "patient",
    }

    if db_type not in table_map:
        return "Invalid database type.", 404

    try:
        table_name = table_map[db_type]

        # ✅ Fetch data for doctors and nurses (simple join)
        if db_type in ["doctors", "nurses"]:
            response = (
                supabase.table(table_name)
                .select("*, department(name)")  # ✅ Correct join for department name
                .order("id", desc=False)
                .execute()
            )

        # ✅ Fetch data for patients (handling multiple departments)
        else:
            response = (
                supabase.table("patient")
                .select("*, patient_department!inner(department_id, department(name))")
                .order("id", desc=False)
                .execute()
            )

        print("Supabase Response:", response)  # Debugging output

        data = response.data if response.data else []
        if not data:
            print("No data retrieved from Supabase.")

        # ✅ Process department names for patients
        if db_type == "patients":
            processed_data = {}
            for record in data:
                patient_id = record["id"]
                department = record.get("patient_department", [])

                # Extract department names
                department_names = [dept["department"]["name"] for dept in department]

                if patient_id not in processed_data:
                    processed_data[patient_id] = {**record, "department": ", ".join(department_names)}
                else:
                    processed_data[patient_id]["department"] = ", ".join(
                        set(processed_data[patient_id]["department"].split(", ") + department_names)
                    )

            # Convert dict back to list
            data = list(processed_data.values())

        # ✅ Count statuses for doctors and nurses
        status_counts = {"active": 0, "expired": 0, "terminated": 0} if db_type in ["doctors", "nurses"] else None
        if status_counts:
            for record in data:
                status = record.get("status", "").lower()
                if status in status_counts:
                    status_counts[status] += 1

    except Exception as e:
        print(f"Error fetching data from Supabase: {e}")
        data = []
        status_counts = None if db_type == "patients" else {"active": 0, "expired": 0, "terminated": 0}

    return render_template(
        f"manage/{db_type}_db.html",
        db_type = db_type,
        data=data,
        staff_id=staff_id,
        count=status_counts if status_counts else {}
    ) 
    
@app.route("/terminate/<string:staff_type>/<string:staff_id>", methods=["POST"])
def terminate_staff(staff_type, staff_id):
    """Updates the status of a doctor or nurse to 'terminated'."""
    
    staff_tables = {
        "doctors": "doctor",
        "nurses": "nurse",
    }

    if staff_type not in staff_tables:
        return "Invalid staff type.", 404

    table_name = staff_tables[staff_type]

    try:
        # Update the status in the database
        supabase.table(table_name).update({"status": "terminated"}).eq("id", staff_id).execute()
        print(f"{staff_type.capitalize()} {staff_id} has been terminated.")
        
        return redirect(url_for("manage_db", db_type=staff_type, staff_id=staff_id))

    except Exception as e:
        return f"Error updating status: {e}", 500



# Add new doctor/nurse (create new user with username and password for login the system) DONE
@app.route("/<string:staff_type>_add/<string:staff_id>", methods=["GET", "POST"])
def add_record(staff_type, staff_id):
    """Adds a new doctor or nurse and registers them in authentication."""
    
    staff_tables = {
        "doctors": {"table": "doctor", "id_key": "id", "prefix": "d", "position": "doctor"},
        "nurses": {"table": "nurse", "id_key": "id", "prefix": "n", "position": "nurse"},
    }

    if staff_type not in staff_tables:
        return "Invalid staff type.", 404

    table_name = staff_tables[staff_type]["table"]
    id_key = staff_tables[staff_type]["id_key"]
    prefix = staff_tables[staff_type]["prefix"]
    #position = staff_tables[staff_type]["position"]

    try:
        # Fetch latest ID for doctors/nurses
        response = supabase.table(table_name).select(id_key).order(id_key, desc=True).limit(1).execute()
        latest_id = response.data[0][id_key][1:] if response.data else 10000
        next_id = int(latest_id) + 1
        record_id = f"{prefix}{next_id}"

        # Fetch department list for selection
        department_response = supabase.table("department").select("id, name").execute()
        departments = department_response.data if department_response.data else []

    except Exception as e:
        return f"Error retrieving or generating ID: {e}", 500

    if request.method == "POST":
        name = request.form["name"]
        nic = request.form["nic"]
        dob = request.form["dob"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]
        department_id = request.form["department_id"]
        startDate = request.form["startDate"]
        endDate = request.form["endDate"]

        today = datetime.today().date()
        start_date_obj = datetime.strptime(startDate, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(endDate, "%Y-%m-%d").date()

        # Assign status based on contract dates
        if start_date_obj > today:
            status = "pending"
        elif start_date_obj <= today <= end_date_obj:
            status = "active"
        else:
            status = "expired"

        try:
            # Insert into doctors/nurses table
            supabase.table(table_name).insert({
                "id": record_id,
                "name": name,
                "nic": nic,
                "dob": dob,
                "gender": gender,
                "phone": phone,
                "email": email,
                "department_id": department_id,
                "startdate": startDate,
                "enddate": endDate,
                "status": status
            }).execute()

            print(f"{staff_type.capitalize()} {name} added successfully.")

        except Exception as e:
            return f"Error inserting staff data: {e}", 500

        if status == "active":
            try:
                # Register the staff in Supabase Authentication only if status is active
                auth_response = supabase.auth.sign_up({
                    "email": email,
                    "password": nic  # Default password is their staff ID
                })

                if "error" in auth_response:
                    return f"Error creating authentication account: {auth_response['error']['message']}", 500

                print(f"Authentication account created for {name}")
                confirm_user_email(email)
            
            except Exception as e:
                return f"Error registering staff in authentication: {e}", 500

        # try:
        #     # Fetch latest login ID
        #     login_response = supabase.table("login").select("id").order("id", desc=True).limit(1).execute()
        #     latest_login_id = int(login_response.data[0]["id"][1:]) + 1 if login_response.data else 1000
        #     login_record_id = f"l{latest_login_id}"

        #     # Insert login credentials
        #     supabase.table("login").insert({
        #         "id": login_record_id,
        #         "username": record_id,
        #         "password": record_id,
        #         "position": position
        #     }).execute()

        #     print(f"Login details added for {name}.")

        # except Exception as e:
        #     return f"Error adding login data: {e}", 500

        return redirect(url_for("manage_db", db_type=staff_type, staff_id=staff_id))

    return render_template(
        f"manage/{staff_type}_add.html",
        id=record_id,
        staff_id=staff_id,
        departments=departments
    )

def confirm_user_email(email):
    """Marks a user's email as confirmed in Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/rpc/update_user_email_confirmed"
    headers = {
        "apikey": SUPABASE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_ROLE_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "email_confirmed_at": datetime.now(timezone.utc).isoformat()
    }
    
    response = requests.patch(url, json=data, headers=headers, params={"email": f"eq.{email}"})
    
    if response.status_code == 200:
        print(f"✅ Email {email} successfully confirmed!")
    else:
        print(f"❌ Failed to confirm email {email}: {response.text}")


@app.route("/staff_contract/<string:staff_id>/<status>")
def staff_contract(staff_id, status):
    try:
        # Ensure status is valid
        valid_statuses = ["pending", "active", "expired", "terminated"]
        if status not in valid_statuses:
            return "Invalid status", 400  # Return error for invalid status
        
        # Fetch doctors and nurses with the given status
        doctors_response = supabase.table("doctor").select("id, name, nic, startdate, enddate, department_id, department(name)").eq("status", status).order("startdate", desc=False).execute()
        nurses_response = supabase.table("nurse").select("id, name, nic, startdate, enddate, department_id, department(name)").eq("status", status).order("startdate", desc=False).execute()
        department_response = supabase.table("department").select("id, name").execute()
        
        doctors = doctors_response.data if doctors_response.data else []
        nurses = nurses_response.data if nurses_response.data else []
        department = department_response.data if department_response.data else []

        return render_template(f"/main/staff_contract.html", doctors=doctors, nurses=nurses, status=status, department = department, staff_id = staff_id)
    
    except Exception as e:
        print(f"Error fetching staff data: {e}")
        return "Database error", 500

###########################################################################################################
# Display functions that can be done by doctors only (Patient list, Schedule, Appointment for scan, Profile) DONE
# @app.route("/doctor/<string:id>")
# def doctor_index(id):
#     try:
#         # Fetch doctor details
#         doctor_response = supabase.table("doctor").select("*").eq("id", id).execute()
#         if not doctor_response.data:
#             print(f"Doctor with ID {id} not found.")
#             return "Doctor not found", 404

#         doctor = doctor_response.data[0]  # Extract doctor details
#         department_id = doctor.get("department_id", "")
        
#         # Get today's date in YYYY-MM-DD format
#         today_date = datetime.now().strftime('%Y-%m-%d')

#         # Fetch appointments ONLY for today
#         appointment_response = (
#             supabase.table("appointment")
#             .select("id, patient_id, date, time, status")
#             .eq("doctor_id", id)
#             .eq("status", "Active")
#             .eq("date", today_date)  # Only today's appointments
#             .execute()
#         )
#         appointment_id = appointment_response.data[0]["id"]
#         appointments = appointment_response.data if appointment_response.data else []

#         if appointments:
#             # Fetch patient names for today's appointments
#             patient_ids = list(set(app["patient_id"] for app in appointments))
            
#             if patient_ids:  # Ensure patient_ids is not empty before querying
#                 patient_response = (
#                     supabase.table("patient")
#                     .select("id, name")
#                     .in_("id", patient_ids)
#                     .execute()
#                 )
#                 patient_map = {p["id"]: p["name"] for p in patient_response.data} if patient_response.data else {}
#             else:
#                 patient_map = {}

#             # Add patient names to appointments
#             for app in appointments:
#                 app["patient_name"] = patient_map.get(app["patient_id"], "Unknown")

#             # Sort appointments by time
#             appointments.sort(key=lambda app: datetime.strptime(app["time"], "%H:%M"))

#         print(appointments)  # Debugging output
        
#         #**Determine which template to render**
#         # if department_id == "dep1002":  # Radiology department
#         #     print("➡️ Rendering Radiology Template")
#         #     return render_template("image/radio_index.html", doctor=doctor, appointments=appointments)

#         return render_template("doctors/doctor_index.html", doctor=doctor, appointment_id=appointment_id, patient_ids = patient_ids, appointments=appointments)

#     except Exception as e:
#         print(f"Error fetching doctor or appointment data: {e}")
#         return "An error occurred while retrieving data", 500

@app.route("/doctor/<string:id>")
def doctor_index(id):
    try:
        # Fetch doctor details
        doctor_response = supabase.table("doctor").select("*").eq("id", id).execute()
        if not doctor_response.data:
            print(f"Doctor with ID {id} not found.")
            return "Doctor not found", 404

        doctor = doctor_response.data[0]  # Extract doctor details
        department_id = doctor.get("department_id", "")

        # Get today's date in YYYY-MM-DD format
        today_date = datetime.now().strftime('%Y-%m-%d')

        # Fetch appointments ONLY for today
        appointment_response = (
            supabase.table("appointment")
            .select("id, patient_id, date, time, status")
            .eq("doctor_id", id)
            .eq("status", "Active")
            .eq("date", today_date)  # Only today's appointments
            .execute()
        )
        appointments = appointment_response.data if appointment_response.data else []

        if appointments:
            appointment_id = appointments[0]["id"]  # Only access if appointments exist

            # Fetch patient names for today's appointments
            patient_ids = list(set(app["patient_id"] for app in appointments))
            
            if patient_ids:  # Ensure patient_ids is not empty before querying
                patient_response = (
                    supabase.table("patient")
                    .select("id, name")
                    .in_("id", patient_ids)
                    .execute()
                )
                patient_map = {p["id"]: p["name"] for p in patient_response.data} if patient_response.data else {}
            else:
                patient_map = {}

            # Add patient names to appointments
            for app in appointments:
                app["patient_name"] = patient_map.get(app["patient_id"], "Unknown")

            # Sort appointments by time
            appointments.sort(key=lambda app: datetime.strptime(app["time"], "%H:%M"))

        else:
            appointment_id = None  # No appointments for today
            patient_ids = []

        print(appointments)  # Debugging output

        return render_template("doctors/doctor_index.html", 
                               doctor=doctor, 
                               appointment_id=appointment_id, 
                               patient_ids=patient_ids, 
                               appointments=appointments)

    except Exception as e:
        print(f"Error fetching doctor or appointment data: {e}")
        return "An error occurred while retrieving data", 500


# not neccesary to have a radio_index.html since the doctor also have the same function 
# just different appointment and the appointment is based on the doctor_id 

# @app.route("/doctor/<string:id>")
# def doctor_index(id):
#     try:
#         # Fetch doctor details, including department_id
#         doctor_response = supabase.table("doctor").select("id, name, department_id").eq("id", id).execute()
        
#         if not doctor_response.data:
#             print(f"❌ Doctor with ID {id} not found.")
#             return "Doctor not found", 404

#         doctor = doctor_response.data[0]  # Extract doctor details
#         department_id = doctor.get("department_id", "")
        
#         print(f"✅ Doctor found: {doctor}")  # DEBUG: Check doctor details

#         # # Determine appointment type based on department
#         # if department_id == "dep1002":  # Radiology department → Show only "Scan" appointments
#         #     appointment_filter = ["CT Scan", "MRI Scan"]
#         # else:  # Other doctors → Show "Consultation/Follow-up" appointments
#         #     appointment_filter = ["Consultation/Follow up"]

#         #print(f"📌 Department ID: {department_id}, Filter: {appointment_filter}")  # DEBUG: Check department and filter

#         # Get today's date in YYYY-MM-DD format
#         today_date = datetime.now().strftime('%Y-%m-%d')
#         print(f"📅 Today's date: {today_date}")  # DEBUG: Check today's date

#         # Fetch appointments ONLY for today with correct purpose
#         appointment_response = (
#             supabase.table("appointment")
#             .select("id, patient_id, date, time, status, purpose")
#             .eq("doctor_id", id)
#             #.in_("purpose", appointment_filter)  # ✅ FIXED: Use .in_() instead of .eq()
#             .eq("status", "Active")
#             .eq("date", today_date)  # Only today's appointments
#             .execute()
#         )

#         appointments = appointment_response.data if appointment_response.data else []
#         print(f"📝 Appointments retrieved: {appointments}")  # DEBUG: Check retrieved appointments

#         if not appointments:
#             print("⚠️ No active appointments found for today.")
        
#         if appointments:
#             # Fetch patient names for today's appointments
#             patient_ids = list(set(app["patient_id"] for app in appointments))
            
#             if patient_ids:  # Ensure patient_ids is not empty before querying
#                 patient_response = (
#                     supabase.table("patient")
#                     .select("id, name")
#                     .in_("id", patient_ids)
#                     .execute()
#                 )
#                 patient_map = {p["id"]: p["name"] for p in patient_response.data} if patient_response.data else {}
#             else:
#                 patient_map = {}

#             # Add patient names to appointments
#             for app in appointments:
#                 app["patient_name"] = patient_map.get(app["patient_id"], "Unknown")

#             # Sort appointments by time
#             appointments.sort(key=lambda app: datetime.strptime(app["time"], "%H:%M"))

#         print(f"📋 Final Appointments List: {appointments}")  # DEBUG: Check processed appointments

#         # **Determine which template to render**
#         if department_id == "dep1002":  # Radiology department
#             print("➡️ Rendering Radiology Template")
#             return render_template("image/radio_index.html", doctor=doctor, appointments=appointments)

#         print("➡️ Rendering Doctor Template")
#         return render_template("doctors/doctor_index.html", doctor=doctor, appointments=appointments)

#     except Exception as e:
#         print(f"❌ Error fetching doctor or appointment data: {e}")
#         return "An error occurred while retrieving data", 500






@app.route("/nurse/<string:id>")
def nurse_index(id):
    # Fetch nurse data, including department_id
    nurse_data = (
        supabase.table("nurse")
        .select("id, name, department_id")  # Fetch department_id instead of department name
        .eq("id", id)
        .single()
        .execute()
    )
    
    if not nurse_data.data:
        return "Nurse not found", 404
    
    nurse = nurse_data.data
    nurse_department_id = nurse["department_id"]  # Get the department_id of the nurse
    
    # Fetch patient IDs in the same department from patient_department table
    patient_department_data = (
        supabase.table("patient_department")
        .select("patient_id")  
        .eq("department_id", nurse_department_id)  # Filter by nurse's department_id
        .execute()
    )
    
    if not patient_department_data.data:
        return render_template("nurses/nurse_index.html", nurse=nurse, patient_db=[])  # No patients found
    
    patient_ids = [entry["patient_id"] for entry in patient_department_data.data]  # Extract patient IDs
    
    # Fetch patient details from patient table using patient_ids
    patient_data = (
        supabase.table("patient")
        .select("id, name, nic, dob, gender, phone, email, address")
        .in_("id", patient_ids)  # Retrieve patients whose IDs match
        .execute()
    )
    
    patients = patient_data.data if patient_data.data else []
    
    return render_template("nurses/nurse_index.html", nurse=nurse, patient_db=patients)



##############################################################################################################

# Display the doctor's or nurse's data DONE
@app.route("/staff_profile/<string:staff_id>")
def staff_profile(staff_id):
    try:
        # Determine table and type based on ID prefix
        if staff_id.startswith("d"):
            table_name = "doctor"
            staff_type = "doctor"
        elif staff_id.startswith("n"):
            table_name = "nurse"
            staff_type = "nurse"
        else:
            return "Invalid staff ID", 400  # Invalid request

        # Fetch staff details along with department name
        response = (
            supabase.table(table_name)
            .select("id, name, nic, dob, gender, phone, email, department_id, department(name)")
            .eq("id", staff_id)
            .execute()
        )

        # Debugging: Print the response to check if data exists
        print(f"Supabase Response: {response}")

        if response and hasattr(response, "data") and response.data:
            staff = response.data[0]  # Get first record

            # Extract department name from nested response
            department_name = staff.get("department", {}).get("name", "Unknown Department")

            return render_template(
                "main/staff_profile.html",
                staff=staff,
                staff_type=staff_type,
                department_name=department_name
            )

    except Exception as e:
        print(f"Error fetching {table_name} data from Supabase: {e}")

    return "Staff not found", 404










# update the contract start date and end date DONE
@app.route("/update_contract/<string:staff_type>/<string:staff_id>/<string:id>", methods=['GET', 'POST'])
def update_contract(staff_type, staff_id, id):
    # Define table mapping
    table_mapping = {
        "doctors": "doctor",
        "nurses": "nurse",
        "patients": "patient"
    }
    
    # Validate staff_type
    if staff_type not in table_mapping:
        return "Invalid staff type.", 404
    
    table_name = table_mapping[staff_type]
    
    # Fetch user details from Supabase
    response = supabase.table(table_name).select("*, department(name)").eq("id", id).single().execute()
    if "error" in response:
        return "User not found.", 404
    
    staff_data = response.data
    
    if request.method == 'POST':
        start_date = request.form['startDate']
        end_date = request.form['endDate']
        
        today = datetime.today().date()
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Assign status based on contract dates
        if start_date_obj > today:
            status = "pending"
        elif start_date_obj <= today <= end_date_obj:
            status = "active"
        else:
            status = "expired"
        
        # Update contract details in Supabase
        update_response = supabase.table(table_name).update({
            "startdate": start_date,
            "enddate": end_date,
            "status": status
        }).eq("id", id).execute()
        
        if "error" in update_response:
                return f"Error updating profile: {update_response['error']}", 500
        
        return redirect(url_for("manage_db", db_type=staff_type, staff_id=staff_id))
    
    return render_template('manage/update_contract.html', ppl=staff_data, staff_type=staff_type, staff_id=staff_id)


# Update the doctor's or nurse's phone or email in supabase DONE
@app.route("/edit_profile/<string:id>", methods=['GET', 'POST'])
def edit_profile(id):
    try:
        # Determine the correct table and staff type
        if id.lower().startswith('d'):
            table_name = "doctor"
            staff_type = "doctor"
        elif id.lower().startswith('n'):
            table_name = "nurse"
            staff_type = "nurse"
        else:
            return "Invalid ID", 400  # Handle invalid IDs

        # Fetch staff details along with department name by joining tables
        response = (
            supabase.table(table_name)
            .select("id, name, nic, dob, gender, phone, email, department_id, department(name)")
            .eq("id", id)
            .execute()
        )

        if not response.data:
            return "Staff not found", 404  # Handle missing staff

        staff = response.data[0]  # Extract staff details

        # Extract department name from nested response
        department_name = staff.get("department", {}).get("name", "Unknown Department")

        if request.method == 'POST':
            # Get updated phone and email values from the form
            phone = request.form.get('phone')

            # Update the staff details in Supabase
            update_response = supabase.table(table_name).update({
                "phone": phone
            }).eq("id", id).execute()

            if "error" in update_response:
                return f"Error updating profile: {update_response['error']}", 500

            flash("Profile updated successfully!", "success")  # Flash success message
            return redirect(url_for("edit_profile", id=id))  # Redirect back to edit page

        return render_template(
            'main/update_profile.html',
            staff=staff,
            staff_type=staff_type,
            department_name=department_name  # Pass department name to template
        )

    except Exception as e:
        print(f"Error fetching/updating {table_name} data: {e}")
        return f"Error: {str(e)}", 500  # Return error message if something fails




#####################################################################################################################
# edit password for doctor and nurse DONE
@app.route("/edit_psw/<string:id>", methods=['GET', 'POST'])
def edit_psw(id):
    try:
        # Fetch staff email
        try:
            # Determine the user type based on id prefix
            if id.startswith("n"):
                table_name = "nurse"
            elif id.startswith("d"):
                table_name = "doctor"
            else:
                return "Invalid Staff ID", 400  # Return error if the ID does not match expected format

            # Fetch staff details from the corresponding table
            staff_response = supabase.table(table_name).select("email").eq("id", id).execute()
            
            staff = staff_response.data if staff_response.data else None
            print(staff)

            if not appointment:
                return "Staff not found", 404

        except Exception as e:
            print(f"Error fetching staff: {e}")
            return "Database error", 500
        
        user_email = staff_response.data[0]["email"]  # Get logged-in user's email

        if request.method == 'POST':
            current_password = request.form["current_psw"].strip()
            new_password = request.form["new_psw"].strip()
            confirm_password = request.form["confirm_psw"].strip()

            # Step 2: Reauthenticate User
            auth_response = supabase.auth.sign_in_with_password({
                "email": user_email,
                "password": current_password
            })

            if "error" in auth_response:
                return render_template('/main/edit_psw.html', id=id, error="Incorrect current password.")

            # Step 3: Ensure new password and confirmation password match
            if new_password != confirm_password:
                return render_template('/main/edit_psw.html', id=id, error="Passwords do not match.")

            # Step 4: Update password in Supabase Authentication
            update_response = supabase.auth.update_user({"password": new_password})

            if "error" in update_response:
                return render_template('/main/edit_psw.html', id=id, error="Error updating password.")

            return render_template('/main/edit_psw.html', id=id, success="Password changed successfully.")
    
    except Exception as e:
        print(f"Error updating password: {e}")
        return render_template('/main/edit_psw.html', id=id, error="An unexpected error occurred.")

    return render_template('/main/edit_psw.html', id=id,)



########################################################################################################
# Display Patient's data that had or have appointment with the doctor DONE
@app.route("/patient/<string:staff_id>")
def index(staff_id):
    try:
        # Query to get all patients with appointments for the given doctor
        appointment_response = supabase.table("appointment").select("id, patient_id").eq("doctor_id", staff_id).execute()
        
        if not appointment_response.data:  # If no appointments found
            return render_template("patients/patients_index.html", patients=[], staff_id=staff_id)

        # Extract appointment ID and patient IDs
        appointment_id = appointment_response.data[0]["id"] if appointment_response.data else None
        patient_ids = [appointment["patient_id"] for appointment in appointment_response.data]

        if not patient_ids:  # If there are no patient IDs, render empty response
            return render_template("patients/patients_index.html", patients=[], staff_id=staff_id)

        # Fetch patient details for these patient IDs
        patient_response = supabase.table("patient").select("id, name, nic, dob, gender").in_("id", patient_ids).execute()

        if not patient_response.data:  # If no patient details found
            return render_template("patients/patients_index.html", patients=[], staff_id=staff_id, appointment_id=appointment_id)

        # Extract first patient ID safely
        patient_id = patient_response.data[0]["id"] if patient_response.data else None

        # Render the patients' details in the template
        return render_template("patients/patients_index.html", patients=patient_response.data, staff_id=staff_id, appointment_id=appointment_id, patient_id=patient_id)

    except Exception as e:
        print(f"Error fetching patient list: {e}")
        return f"An error occurred while retrieving data: {e}", 500


# Search patient in the patient table DONE
@app.route("/doctors/search_patient/<string:staff_id>", methods=["GET"])
def search_patient(staff_id):
    query = request.args.get("query")  # Get search input from the doctor

    # If no query, return empty search results
    if not query:
        # Redirect to the doctor-specific patient list if no search query is provided
        return render_template("patients/patients_index.html", patients=[], staff_id=staff_id)

    try:
        # Check if query is numeric (possible patient ID)
        if query.isdigit():
            # If query is a patient ID, search by ID
            patient_response = (
                supabase.table("patient")
                .select("id, name, nic, dob, gender")  # Select required fields
                .eq("id", query)  # Exact match for patient ID
                .execute()
            )
        else:
            # If query is a name, search by name
            patient_response = (
                supabase.table("patient")
                .select("id, name, nic, dob, gender")  # Select required fields
                .ilike("name", f"%{query}%")  # Case-insensitive search for patient name
                .execute()
            )

        patients = patient_response.data
        # Return the search results, passing the patients and staff_id
        return render_template("patients/patients_index.html", patients=patients, staff_id=staff_id)

    except Exception as e:
        print(f"Error searching patient: {e}")
        return "An error occurred while searching", 500


# # Add new patient in database DONE
@app.route("/add/<string:department_id>/<string:staff_id>", methods=["GET", "POST"])
def add_patient(department_id, staff_id):
    try:
        response = supabase.table("patient").select("id").order("id", desc=True).limit(1).execute()
        latest_id = response.data[0]["id"] if response.data else 10000  # Default to 10000 if no data
        next_id = int(latest_id) + 1  
        record_id = str(next_id)
    except Exception as e:
        return f"Error retrieving ID: {e}", 500

    if request.method == "POST":
        name = request.form["name"]
        nic = request.form["nic"]
        dob = request.form["dob"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]

        # Validate NIC (must be exactly 12 digits)
        if not nic.isdigit() or len(nic) != 12:
            return "Error: NIC must be exactly 12 digits.", 400

        # Fetch department_id of the nurse
        try:
            nurse_response = supabase.table("nurse").select("department_id").eq("id", staff_id).single().execute()
            department_id = nurse_response.data["department_id"] if nurse_response.data else None
            if not department_id:
                return redirect(url_for("nurse_index", id=staff_id))
        except Exception as e:
            return redirect(url_for("nurse_index", id=staff_id))

        # Check if NIC already exists
        try:
            nic_check = supabase.table("patient").select("nic").eq("nic", nic).execute()
            if nic_check.data:
                return "Error: NIC already exists.", 400
        except Exception as e:
            return redirect(url_for("nurse_index", id=staff_id))

        # Insert into patient table
        try:
            patient_data = {
                "id": record_id,
                "name": name,
                "nic": nic,
                "dob": dob,
                "gender": gender,
                "phone": phone,
                "email": email,
                "address": address,
                "nurse_id": staff_id
            }
            supabase.table("patient").insert(patient_data).execute()
        except Exception as e:
            return redirect(url_for("nurse_index", id=staff_id))

        # Insert patient_id and department_id into patient_department table
        try:
            patient_department_data = {
                "patient_id": record_id,
                "department_id": department_id
            }
            supabase.table("patient_department").insert(patient_department_data).execute()
        except Exception as e:
            return redirect(url_for("nurse_index", id=staff_id))

        return redirect(url_for("nurse_index", id=staff_id))

    # Fetch department name from department table
    try:
        department_response = supabase.table("department").select("name").eq("id", department_id).single().execute()
        department_name = department_response.data["name"] if department_response.data else "Unknown Department"
    except Exception as e:
        department_name = "Unknown Department"

    return render_template("patients/patients_add.html", id=record_id, staff_id=staff_id, department_name=department_name, department_id=department_id)


# Add patient from other department to nurse's department DONE
@app.route("/add_existing/<string:department_id>/<string:staff_id>", methods=["GET", "POST"])
def add_existing_or_search(department_id, staff_id):
    query = request.args.get("query", "").strip()  # Get search query
    
    patient_data = None
    patient_departments = []
    department_name = None
    error_message = None
    can_add_department = False

    # Retrieve department name instead of just ID
    try:
        dept_response = supabase.table("department").select("name").eq("id", department_id).execute()
        if dept_response.data:
            department_name = dept_response.data[0]["name"]
        else:
            department_name = "Unknown"
    except Exception as e:
        department_name = "Error retrieving department"

    if request.method == "POST":
        patient_id = request.form["patient_id"]

        # Check if the patient is already in the department
        try:
            department_check = (
                supabase.table("patient_department")
                .select("department_id")
                .eq("patient_id", patient_id)
                .execute()
            )
            existing_departments = {entry["department_id"] for entry in department_check.data}

            if department_id in existing_departments:
                error_message = "Patient is already in this department."
            else:
                # Add patient to the department
                supabase.table("patient_department").insert(
                    {"patient_id": patient_id, "department_id": department_id}
                ).execute()
                return redirect(url_for("nurse_index", id=staff_id))
        except Exception as e:
            error_message = f"Error adding patient to department: {e}"

    elif query:  # If there's a search query
        try:
            # Search for patient by ID or NIC
            response = (
                supabase.table("patient")
                .select("*")
                .or_(f"id.eq.{query},nic.eq.{query}")
                .execute()
            )
            
            if response.data:
                patient_data = response.data[0]
                patient_id = patient_data["id"]

                # Fetch departments the patient is in (including department names)
                dept_response = (
                    supabase.table("patient_department")
                    .select("department_id, department(name)")
                    .eq("patient_id", patient_id)
                    .execute()
                )

                if dept_response.data:
                    patient_departments = [
                        {"id": dept["department_id"], "name": dept["department"]["name"]}
                        for dept in dept_response.data
                    ]

                # Check if patient is already in the nurse's department
                if department_id in [dept["id"] for dept in patient_departments]:
                    error_message = "Patient is already in this department."
                else:
                    can_add_department = True
            else:
                error_message = "No patient found with this ID or NIC."
        except Exception as e:
            error_message = f"Error retrieving patient data: {e}"

    return render_template(
        "patients/patients_add_department.html",
        staff_id=staff_id,
        department_id=department_id,
        department_name=department_name,
        patient=patient_data,
        patient_departments=patient_departments,
        error_message=error_message,
        can_add_department=can_add_department,
        query=query,
    )


# Update patient details (phone, email and address) DONE
@app.route('/update/<string:patient_id>/<string:staff_id>', methods=['GET', 'POST'])
def update_patient_info(patient_id, staff_id):
    try:
        # ✅ Retrieve patient details from Supabase
        response = supabase.table("patient").select("id, name, nic, dob, gender, phone, email, address").eq("id", patient_id).execute()
        
        if hasattr(response, 'error') and response.error:
            print(f"Error fetching patient data: {response.error}")
            return "Error retrieving patient data", 500
        
        if not response.data:
            return "Patient not found", 404

        patient = response.data[0]
        
    except Exception as e:
        print(f"Exception occurred: {e}")
        return "Error retrieving patient data", 500

    if request.method == 'POST':
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']

        try:
            # ✅ Update patient details in Supabase
            update_response = supabase.table("patient").update({
                "phone": phone,
                "email": email,
                "address": address
            }).eq("id", patient_id).execute()
            
            if hasattr(update_response, 'error') and update_response.error:
                print(f"Error updating patient data: {update_response.error}")
                return "Error updating patient data", 500

        except Exception as e:
            print(f"Exception occurred while updating: {e}")
            return "Error updating patient data", 500

        return redirect(url_for("nurse_index", id=staff_id))
    
    return render_template('patients/patients_update.html', patient=patient, staff_id=staff_id)

######################################################################################################################
# Appointment
# Generate apopointment id based on apopointment purpose DONE
def generate_appointment_id(purpose):
    """Generate unique appointment ID with prefix based on purpose"""
    if purpose in ["Consultation/Follow Up"]:
        prefix = "CONS"
    elif purpose == "CT Scan":
        prefix = "CTSCAN"
    else:
        prefix = "MRISCAN"
        
    base_number = 10000  # Start IDs from 10000
    
    # Get the latest appointment with this prefix
    result = (
        supabase.table("appointment")
        .select("id")
        .like("id", f"{prefix}-%")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    
    
    if result.data:
        # Extract last numeric part and increment
        last_id = result.data[0]["id"]
        last_num = int(last_id.split("-")[1]) + 1
    else:
        last_num = base_number  # First appointment for this type starts at 10000
    
    return f"{prefix}-{last_num}"  # Generates IDs like "CONS-10000", "SCAN-10000"



# Display the appoitment of the patient chosen DONE
@app.route('/appointment/<int:patient_id>/<string:staff_id>')
def appointment(patient_id, staff_id):
    try:
        # Fetch patient details
        patient_response = supabase.table("patient").select(
            "id, name, nic, dob, gender"
        ).eq("id", patient_id).single().execute()

        if hasattr(patient_response, 'error') and patient_response.error:
            print(f"Error fetching patient data: {patient_response.error}")
            return "Error retrieving patient data", 500

        patient = patient_response.data  # Get patient details

        # Fetch patient appointments
        appointments_response = supabase.table("appointment").select(
            "id, purpose, date, time, status, "
            "doctor(name, department(name))"
        ).eq("patient_id", patient_id).execute()

        if hasattr(appointments_response, 'error') and appointments_response.error:
            print(f"Error fetching appointments: {appointments_response.error}")
            return "Error retrieving appointments", 500

        appointments = appointments_response.data

        # Convert data to match expected template format
        patient["appointment"] = [
            {
                "num": idx + 1,
                "id": app["id"],
                "department": app["doctor"]["department"]["name"],
                "doctor_name": app["doctor"]["name"],
                "purpose": app["purpose"],
                "date": app["date"],
                "time": app["time"],
                "status": app["status"]
            }
            for idx, app in enumerate(appointments)
        ]

    except Exception as e:
        print(f"Exception occurred: {e}")
        return "Error retrieving appointment data", 500

    return render_template('patients/patients_appointment.html', patient=patient, staff_id=staff_id)


# Add new appointment for the patient DONE
@app.route('/add_appointment/<int:patient_id>/<string:staff_id>', methods=["GET", "POST"])
def new_appointment(patient_id, staff_id):
    # Fetch patient details from Supabase
    patient_response = supabase.table("patient").select("id, name, " "department(name)").eq("id", patient_id).single().execute()
    patient = patient_response.data if patient_response.data else None
    
    if not patient:
        return "Patient not found", 404
    
    # Check if the staff ID belongs to a nurse and fetch the department
    if staff_id.startswith('n'):
        staff_response = supabase.table("nurse").select("id, name, department_id, " "department(name)").eq("id", staff_id).single().execute()
        staff = staff_response.data if staff_response.data else None
        
        if not staff:
            return "Nurse not found", 404
        
        # Fetch doctors in the same department
        doctors_response = supabase.table("doctor").select("id, name").eq("department_id", staff["department_id"]).execute()
        doctors = doctors_response.data if doctors_response.data else []
        print("Doctors found:", doctors_response.data)  # Debugging statement
        
        if request.method == "POST":
            purpose = request.form["purpose"]
            doctor_name = request.form["doctor_name"]
            date = request.form["date"]
            time = request.form["time"]
            notes = request.form["notes"]
            status = "Active"
            
            # Get doctor ID from doctor name
            doctor_response = supabase.table("doctor").select("id").eq("name", doctor_name).single().execute()
            doctor = doctor_response.data if doctor_response.data else None
            if not doctor:
                return "Doctor not found", 404
            
            print("OK")
            doctor_id = doctor["id"]
            appointment_id = generate_appointment_id(purpose)
            
            # Insert into the appointment table
            appointment_data = {
                "id": appointment_id,
                "patient_id": patient_id,
                "doctor_id": doctor_id,
                "purpose": purpose,
                "date": date,
                "time": time,
                "notes": notes,
                "status": status
            }
            
            supabase.table("appointment").insert(appointment_data).execute()
            
            return redirect(url_for("appointment", patient_id=patient_id, staff_id=staff_id))
        
        return render_template('patients/patients_add_appointment.html', patient=patient, staff=staff, doctors=doctors)
    
    return "Invalid Staff ID", 400

# filter only available doctor for consultation DONE
@app.route('/get_available_doctors/<string:staff_id>/<string:date>', methods=["GET"])
def get_available_doctors(staff_id, date):
    # Fetch staff details to determine the department
    staff_response = supabase.table("nurse").select("id, department_id").eq("id", staff_id).single().execute()
    staff = staff_response.data if staff_response.data else None
    
    if not staff:
        return jsonify({"error": "Nurse not found"}), 404
    
    department_id = staff["department_id"]

    # Get doctors in the same department who are NOT on leave on the selected date
    doctors_response = supabase.table("doctor").select("id, name").eq("department_id", department_id).execute()
    all_doctors = doctors_response.data if doctors_response.data else []

    # Fetch doctors who are on leave on the selected date
    leave_response = supabase.table("doctor_leave").select("doctor_id").eq("leave_date", date).execute()
    doctors_on_leave = {leave["doctor_id"] for leave in leave_response.data} if leave_response.data else set()

    # Filter out unavailable doctors
    available_doctors = [doctor for doctor in all_doctors if doctor["id"] not in doctors_on_leave]

    return jsonify(available_doctors)

# Update patient's appointment DONE
@app.route('/update_appointment/<int:patient_id>/<string:staff_id>/<int:appointment_index>', methods=["GET", "POST"])
def update_appointment(patient_id, staff_id, appointment_index):
    try:
        # ✅ Fetch staff (nurse) details
        staff_response = supabase.table("nurse").select("department_id").eq("id", staff_id).single().execute()
        if not staff_response.data:
            return "Nurse not found", 404

        department_id = staff_response.data["department_id"]

        # ✅ Fetch department name
        department_response = supabase.table("department").select("name").eq("id", department_id).single().execute()
        department_name = department_response.data["name"] if department_response.data else "Unknown"

        # ✅ Fetch patient details
        patient_response = supabase.table("patient").select("id, name").eq("id", patient_id).single().execute()
        if not patient_response.data:
            return "Patient not found", 404

        patient = patient_response.data

        # ✅ Fetch all appointments for the patient
        appointment_response = (
            supabase.table("appointment")
            .select("id, doctor_id, date, time")
            .eq("patient_id", patient_id)
            .execute()
        )

        # ✅ Check if the requested appointment index is valid
        if not appointment_response.data or appointment_index <= 0 or appointment_index > len(appointment_response.data):
            return "Appointment not found", 404

        # ✅ Get the correct appointment using the 1-based index
        app = appointment_response.data[appointment_index - 1]  # Adjust for zero-based index

        # ✅ Fetch doctor name from doctor table
        doctor_response = supabase.table("doctor").select("name").eq("id", app["doctor_id"]).single().execute()
        app["doctor_name"] = doctor_response.data["name"] if doctor_response.data else "Unknown"

        # ✅ Fetch list of doctors in the same department as the nurse
        doctors_response = supabase.table("doctor").select("id, name").eq("department_id", department_id).execute()
        doctors = doctors_response.data if doctors_response.data else []

        if request.method == "POST":
            # ✅ Get updated data from the form
            doctor_id = request.form["doctor_id"]  # Correct field name
            date = request.form["date"]
            time = request.form["time"]

            # ✅ Update the appointment details in Supabase
            update_response = (
                supabase.table("appointment")
                .update({"doctor_id": doctor_id, "date": date, "time": time})
                .eq("id", app["id"])
                .execute()
            )

            if hasattr(update_response, 'error') and update_response.error:
                print(f"Error fetching appointment data: {update_response.error}")
                return "Error retrieving appointment data", 500


            return redirect(url_for("appointment", patient_id=patient_id, staff_id=staff_id))

        # ✅ Render the update appointment form
        return render_template(
            'patients/patients_update_appointment.html',
            patient=patient,
            staff_id=staff_id,
            department=department_name,
            app=app,
            doctors=doctors,
            appointment_index=appointment_index  # Pass the index for reference
        )

    except Exception as e:
        print(f"Exception occurred: {e}")
        return "Error retrieving appointment data", 500



##############################################################################################################################
# def is_radiologist_available(radiologist, new_start_time, duration, patients,slot_durations):
#     """Check if the radiologist is available by ensuring no overlapping appointments."""
#     new_end_time = new_start_time + timedelta(minutes=duration)

#     for p in patients:
#         if "appointment" in p:
#             for appointment in p["appointment"]:
#                 if appointment["doctor_name"] == radiologist["name"]:  # Same radiologist
#                     existing_start = datetime.strptime(f"{appointment['date']} {appointment['time']}", "%Y-%m-%d %H:%M")
#                     existing_end = existing_start + timedelta(minutes=slot_durations.get(appointment["purpose"], 20))

#                     # Check if the new slot overlaps with an existing appointment
#                     if (new_start_time < existing_end and new_end_time > existing_start):
#                         return False  # Conflict found, radiologist is not available
#     return True  # No conflicts, radiologist is available

# Add new appointment for scan DONE
@app.route('/scan_appointment/<int:patient_id>/<string:staff_id>', methods=["GET", "POST"])
def scan_appointment(patient_id, staff_id):
    # Retrieve patient data from Supabase
    patient_response = supabase.table("patient").select("id, name").eq("id", patient_id).single().execute()
    patient = patient_response.data if patient_response.data else None

    if not patient:
        return "Patient not found", 404

    # Retrieve all radiologists from department "dep1002"
    radiologists_response = supabase.table("doctor").select("id, name").eq("department_id", "dep1002").execute()
    radiologists = radiologists_response.data if radiologists_response.data else []

    slot_durations = {"CT Scan": 20, "MRI Scan": 30}  # Slot durations

    if request.method == "POST":
        patient_id = request.form["patient_id"]
        purpose = request.form["purpose"]
        date = request.form["date"]
        time = request.form["time"]
        notes = request.form.get("notes", "")

        # Validate date and time
        selected_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        if selected_datetime < datetime.now():
            flash("Cannot book an appointment in the past", "error")
            return redirect(request.url)

        if selected_datetime.hour < 9 or selected_datetime.hour > 17:
            flash("Appointment time must be between 9 AM and 5 PM", "error")
            return redirect(request.url)

        duration = slot_durations.get(purpose, 20)

        # Retrieve the latest active appointment for the patient
        current_appointment_response = supabase.table("appointment") \
            .select("id, status") \
            .eq("patient_id", patient_id) \
            .eq("status", "Active") \
            .order("date", desc=True) \
            .limit(1) \
            .single() \
            .execute()

        current_appointment = current_appointment_response.data if current_appointment_response.data else None

        if current_appointment:
            # Update the current appointment's status to "Done"
            supabase.table("appointment") \
                .update({"status": "Done"}) \
                .eq("id", current_appointment["id"]) \
                .execute()

        # Generate new appointment ID based on the purpose
        new_appointment_id = generate_appointment_id(purpose)

        # Select a random doctor from department "dep1002" to receive the notification
        if not radiologists:
            flash("No doctors available in this department", "error")
            return redirect(request.url)

        selected_doctor = random.choice(radiologists)  # Pick a random radiologist
        doctor_id = selected_doctor["id"]

        # Insert new scan appointment into Supabase
        new_appointment = {
            "id": new_appointment_id,
            "patient_id": patient_id,
            "purpose": purpose,
            "doctor_id": doctor_id,
            "date": date,
            "time": time,
            "status": "Active",
            "notes": notes
        }

        supabase.table("appointment").insert(new_appointment).execute()

        # # Send notification to the selected doctor
        # notification_message = f"New scan appointment for Patient {patient_id} on {date} at {time}"
        # supabase.table("notifications").insert({"doctor_id": doctor_id, "message": notification_message}).execute()

        # flash(f"Notification sent to {selected_doctor['name']}!", "success")
        return redirect(url_for("doctor_index", id=staff_id))

    return render_template('doctors/scan_appointment.html', patient=patient, staff_id=staff_id)


# def find_available_doctor(department_id, proposed_time, duration):
#     """Find an available doctor from a specific department for the given time slot."""
#     # Retrieve all doctors in the department
#     doctors_response = supabase.table("doctor").select("id, name").eq("department_id", department_id).execute()
#     doctors = doctors_response.data if doctors_response.data else []

#     if not doctors:
#         return None  # No doctors found in this department

#     # Retrieve all appointments
#     appointments_response = supabase.table("appointment").select("*").execute()
#     appointments = appointments_response.data if appointments_response.data else []

#     # Retrieve doctors on leave for the selected date
#     leave_response = supabase.table("doctor_leave").select("doctor_id").eq("leave_date", proposed_time).eq("status", "Approved").execute()
#     doctors_on_leave = {leave["doctor_id"] for leave in leave_response.data} if leave_response.data else set()

#     # Check each doctor for availability
    

#     return None  # No available doctor found


# def is_radiologist_available(radiologist, new_start_time, duration, appointments, slot_durations):
#     """Check if the radiologist is available by ensuring no overlapping appointments."""
#     new_end_time = new_start_time + timedelta(minutes=duration)

#     # Retrieve all appointments for the given radiologist from Supabase
#     appointments_response = supabase.table("appointments") \
#         .select("doctor_id, date, start_time, purpose") \
#         .eq("doctor_id", radiologist["id"]) \
#         .execute()
    
#     existing_appointments = appointments_response.data if appointments_response.data else []

#     for appointment in existing_appointments:
#         existing_start = datetime.strptime(f"{appointment['date']} {appointment['start_time']}", "%Y-%m-%d %H:%M")
#         existing_end = existing_start + timedelta(minutes=slot_durations.get(appointment["purpose"], 20))

#         # Check if the new slot overlaps with an existing appointment
#         if new_start_time < existing_end and new_end_time > existing_start:
#             return False  # Conflict found, radiologist is not available

#     return True  # No conflicts, radiologist is available

















#####################################################################################################################
# Display the patient data that had and will have appointment with the doctor
@app.route('/doctor_schedule/<string:id>', methods=["GET", "POST"])
def doctor_schedule(id):
    try:
        # Fetch doctor details
        doctor_response = supabase.table("doctor").select("*").eq("id", id).execute()
        if not doctor_response.data:
            return "Doctor not found", 404
        doctor = doctor_response.data[0]

        # Get selected date or default to future appointments
        selected_date = request.form.get("selected_date")
        today_date = datetime.now().date().strftime('%Y-%m-%d')

        query = supabase.table("appointment").select("id, patient_id, date, time, status, notes").eq("doctor_id", id)
        query = query.eq("date", selected_date) if selected_date else query.gt("date", today_date)
        
        appointment_response = query.execute()
        appointments = appointment_response.data or []

        # Fetch patient and nurse details
        patient_map, nurse_map = {}, {}
        if appointments:
            patient_ids = {app["patient_id"] for app in appointments if app["patient_id"]}
            #nurse_ids = {app["nurse_id"] for app in appointments if app["nurse_id"]}

            if patient_ids:
                patient_response = supabase.table("patient").select("id, name").in_("id", list(patient_ids)).execute()
                patient_map = {p["id"]: p["name"] for p in patient_response.data}

            # if nurse_ids:
            #     nurse_response = supabase.table("nurse").select("id, name").in_("id", list(nurse_ids)).execute()
            #     nurse_map = {n["id"]: n["name"] for n in nurse_response.data}

            for app in appointments:
                app["patient_name"] = patient_map.get(app.pop("patient_id"), "Unknown")
                #app["nurse_name"] = nurse_map.get(app.pop("nurse_id"), "Unknown")

            appointments.sort(
                key=lambda app: (datetime.strptime(app["date"], "%Y-%m-%d"),
                                 datetime.strptime(app["time"], "%H:%M"))
            )

        return render_template("doctors/doctors_schedule.html", id=id, doctor=doctor, appointments=appointments, selected_date=selected_date)
    except Exception as e:
        return f"Error fetching doctor schedule: {e}", 500



# @app.route('/available-doctors', methods=['GET'])
# def available_doctors():
#     department_id = request.args.get("department_id")
#     appointment_date = request.args.get("date")

#     if not department_id or not appointment_date:
#         return jsonify({"error": "Missing department ID or date"}), 400

#     # Get doctors in the department
#     doctors = supabase.table("doctor").select("id, name").eq("department_id", department_id).execute()

#     # Get doctors on leave for the given date
#     leaves = supabase.table("doctor_leave").select("doctor_id").eq("leave_date", appointment_date).eq("status", "Approved").execute()
#     doctors_on_leave = {leave["doctor_id"] for leave in leaves.data}

#     # Filter out doctors on leave
#     available_doctors = [doctor for doctor in doctors.data if doctor["id"] not in doctors_on_leave]

#     return jsonify(available_doctors)

# done
@app.route('/not_available/<doctor_id>')
def not_available_dates(doctor_id):
    return render_template("/doctors/not_available.html", doctor_id=doctor_id)


# done
@app.route('/update-leave-status/<string:leave_id>', methods=['POST'])
def update_leave_status(leave_id):
    try:
        data = request.get_json()
        new_status = data.get("action")

        print(f"Received request to update leave_id: {leave_id} to status: {new_status}")  # Debugging

        if new_status not in ["Approved", "Rejected"]:
            return jsonify({"success": False, "message": "Invalid action"}), 400
        
        # ✅ Debug: Print before updating
        print(f"Attempting to update leave request with ID: {leave_id}")

        # ✅ Update the status in Supabase
        update_response = (
            supabase.table("doctor_leave")
            .update({"status": new_status})
            .eq("id", leave_id)
            .execute()
        )

        print(f"Update response: {update_response.data}")  # Debugging

        if update_response.data:
            return jsonify({"success": True, "message": f"Leave request {new_status} successfully."})
        else:
            return jsonify({"success": False, "message": "Failed to update leave status."}), 500

    except Exception as e:
        print(f"Error: {str(e)}")  # Debugging
        return jsonify({"success": False, "message": str(e)}), 500




# Add doctor leave DONE
@app.route('/add_doctor_leave/<string:doctor_id>', methods=['GET', 'POST'])
def add_doctor_leave(doctor_id):
    try:
        # Retrieve doctor_id based on staff_id
        response = supabase.table("doctor").select("id").eq("id", doctor_id).single().execute()
        
        if not response.data:
            return jsonify({"success": False, "error": "Doctor ID not found"}), 404
        
        doctor_id = response.data['id']
        
        if request.method == 'POST':
            leave_date = request.form["leave_date"]
            leave_reason = request.form["leave_reason"]
            
            # Insert leave request into Supabase
            supabase.table("doctor_leave").insert({
                "doctor_id": doctor_id,
                "leave_date": leave_date,
                "reason": leave_reason,
                "status": "Pending"
            }).execute()
            
            return redirect(url_for("add_doctor_leave", doctor_id=doctor_id))
        
        return render_template('doctors/not_available.html')
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/radio_upload/<string:appointment_id>/<string:staff_id>', methods=["GET", "POST"])
def radio_upload(appointment_id, staff_id):
    # Fetch appointment details (includes patient_id)
    print(f"Received POST Appointment ID: {appointment_id}")
    try:
        appointment_response = supabase.table("appointment").select("id, purpose, patient_id").eq("id", appointment_id).execute()
        appointment = appointment_response.data if appointment_response.data else None
        print(appointment)
        if not appointment:
            return "Appointment not found", 404
    except Exception as e:
        print(f"Error fetching appointment: {e}")
        return "Database error", 500


    patient_id = appointment_response.data[0]["patient_id"]
    appointment_purpose = appointment_response.data[0]["purpose"]

    # Fetch patient details using patient_id
    patient_response = supabase.table("patient").select("id, name, department(name)").eq("id", patient_id).single().execute()
    patient = patient_response.data if patient_response.data else None
    if not patient:
        return "Patient not found", 404
    
    # Fetch doctor details
    try:
        doctor_response = supabase.table("doctor").select("id, department_id").eq("id", staff_id).single().execute()
        doctor = doctor_response.data if doctor_response.data else None
        if not doctor:
            return "Doctor not found", 404
    except Exception as e:
        print(f"Error fetching doctor: {e}")
        return "Database error", 500

    # Fetch latest ID for patient images
    try:
        id_response = supabase.table("patient_images").select("id").order("id", desc=True).limit(1).execute()
        latest_id = id_response.data[0]["id"][2:] if id_response.data else "10000"
        next_id = int(latest_id) + 1
        record_id = f"PI{next_id}"
    except Exception as e:
        return f"Error generating new ID: {e}", 500

    if request.method == "POST":
        image = request.files.get("image")  

        if not image:
            print("Request files:", request.files)  # Debugging
            return "No image uploaded", 400

        if image.filename == "" or not allowed_file(image.filename):
            return "Invalid image format", 400

        # Save image
        filename = secure_filename(f"{uuid.uuid4()}_{image.filename}")
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image.save(image_path)

        # Upload to Supabase Storage
        with open(image_path, "rb") as file_data:
            supabase.storage.from_("patient_images").upload(f"upload/{filename}", file_data)

        image_url = f"{SUPABASE_URL}/storage/v1/object/public/patient_images/upload/{filename}"

        # Select model based on appointment purpose
        if "CT" in appointment_purpose:
            selected_model = ct_model
            label_dict = lung_labels
        elif "MRI" in appointment_purpose:
            selected_model = mri_model
            label_dict = brain_labels
        else:
            selected_model = None  # No model needed for other purposes

        if selected_model:  
            # Run model prediction
            image = Image.open(image_path).resize((350, 350)).convert("RGB")
            image_array = img_to_array(image)
            image_array = np.expand_dims(image_array, axis=0)
            image_array /= 255.0  # Normalization (if your model was trained with normalized images)
            prediction = selected_model.predict(image_array)
            class_idx = np.argmax(prediction, axis=1)[0]
            model_prediction = label_dict.get(class_idx, "Unknown")
            # Get the predicted class index
            # predicted_class = np.argmax(prediction)

            # # Map prediction to corresponding label
            # model_prediction = label_dict[predicted_class]

            print("Predicted Diagnosis:", model_prediction)
        else:
            model_prediction = "N/A"  # No prediction needed for non-imaging purposes

        # Save to Supabase
        image_data = {
            "id": record_id,
            "appointment_id": appointment_id,  # Now using appointment_id instead of patient_id
            "image_url": image_url,
            "model_prediction": model_prediction,
            "comment": None
        }
        supabase.table("patient_images").insert(image_data).execute()
        
        try:
            supabase.table("appointment").update({"status": "Done"}).eq("id", appointment_id).execute()
            print(f"Updated appointment {appointment_id} status to Done.")
        except Exception as e:
            print(f"Error updating appointment status: {e}")
            return "Failed to update appointment status", 500

        return redirect(url_for("doctor_index", id=staff_id))

    return render_template("image/radio_upload.html", patient=patient, staff_id=staff_id, appointment_id= appointment_id, doctor=doctor)



@app.route('/doctor_review/<string:image_id>/<string:appointment_id>', methods=["GET", "POST"])
def doctor_review(image_id, appointment_id):
    # Fetch image details
    try:
        image_response = supabase.table("patient_images").select("*").eq("id", image_id).single().execute()
        image_data = image_response.data if image_response.data else None
        if not image_data:
            return "Image not found", 404
    except Exception as e:
        print(f"Error fetching image: {e}")
        return "Database error", 500

    # Fetch appointment details
    try:
        appointment_response = supabase.table("appointment").select("id, purpose, doctor_id, patient_id").eq("id", appointment_id).execute()
        appointment = appointment_response.data if appointment_response.data else None
        if not appointment:
            return "Appointment not found", 404
    except Exception as e:
        print(f"Error fetching appointment: {e}")
        return "Database error", 500

    patient_id = appointment_response.data[0]["patient_id"]
    doctor_id = appointment_response.data[0]["doctor_id"]

    # Fetch patient details
    patient_response = supabase.table("patient").select("id, name, department(name)").eq("id", patient_id).single().execute()
    patient = patient_response.data if patient_response.data else None
    if not patient:
        return "Patient not found", 404

    # Check if a comment already exists
    existing_comment = image_data.get("comment")

    if request.method == "POST":
        if existing_comment:  # If a comment exists, prevent submission
            return "Diagnosis already submitted. Editing is not allowed.", 403

        comment = request.form.get("comment")
        if not comment:
            return "Comment cannot be empty", 400

        # Update the comment in the database
        try:
            supabase.table("patient_images").update({"comment": comment}).eq("id", image_id).execute()
        except Exception as e:
            print(f"Error updating comment: {e}")
            return "Database error", 500

        return redirect(url_for("doctor_index", id=doctor_id))

    return render_template("image/result.html", image_data=image_data, appointment_id=appointment_id, patient=patient, doctor_id=doctor_id)


def get_patient_appointments(patient_id):
    try:
        response = supabase.table("patient_images") \
            .select("appointment_id, created_at") \
            .eq("patient_id", patient_id) \
            .execute()
        
        if response.data:
            return response.data
        else:
            return []
    
    except Exception as e:
        print(f"Error fetching appointments: {e}")
        return []



@app.route('/medical_image/<string:patient_id>/<string:staff_id>')
def medical_image(patient_id, staff_id):
    # Fetch patient details
    patient_response = (
        supabase.table("patient")
        .select("id, name, dob, gender")
        .eq("id", patient_id)
        .single()
        .execute()
    )
    patient = patient_response.data if patient_response.data else None

    if not patient:
        return "Patient not found", 404

    # Fetch appointments linked to the patient by joining patient_images with appointment
    try:
        response = (
            supabase.table("patient_images")
            .select("id, appointment_id, model_prediction, appointment(id, patient_id, date, time)")
            .execute()
        )

        appointments = [
            {
                "appointment_id": item["appointment_id"],
                "date": item["appointment"]["date"],
                "time": item["appointment"]["time"],
                "model_prediction": item["model_prediction"],
                "image_id": item["id"]
            }
            for item in response.data if item["appointment"]["patient_id"] == patient_id
        ]
        
    except Exception as e:
        print(f"Error fetching appointments: {e}")
        return "Database error", 500

    

    return render_template(
        "/image/doctors_view.html",
        patient=patient,
        staff_id=staff_id,
        appointments=appointments
    )



















if __name__ == "__main__":
    app.run(debug=True, port=5000)
