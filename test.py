import json
import os
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import supabase
from supabase import create_client, Client

app = Flask(__name__)

# Path to the JSON file where the patient data will be stored
PATIENTS_FILE = "patients.json"
DOCTORS_FILE = "doctors.json"
NURSE_FILE = "nurse.json"
MANAGE_FILE = "manage.json"
LOGIN_FILE = "login.json"
APPOINTMENT_FILE = "appointment.json"
ID_TRACKER_FILE = "id_tracker.txt"



# Your Supabase project URL and API key
SUPABASE_URL = "https://tmegfunkplvtdlmzgcvc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRtZWdmdW5rcGx2dGRsbXpnY3ZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk4NTcwMTUsImV4cCI6MjA1NTQzMzAxNX0.n5bYPpFujiJQoGF5ACI-TwfguLTsFROg8bK2XeqCLFY"

# Create a Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Function to a new person(nurse/doctor/patient) to the JSON file
def save_ppl(filePath,data):
    with open(filePath, "w") as file:
        json.dump(data, file, indent=4)

# Function to load database from the JSON file
def load_db(filePath):
    try:
        with open(filePath, "r") as file:
            return json.load(file)  # Return a list of dictionaries
    except FileNotFoundError:
        return []  # Return an empty list if the file does not exist

# Only allow Manager, Doctor and Nurse to LogIn DONE
@app.route("/", methods=["GET", "POST"])
def index_main():
    if request.method == "POST":
        user_id = request.form["user"].strip()
        password = request.form["psw"].strip()

        # Ensure username and password are identical
        if user_id != password:
            print("Invalid login: Username and password must be the same.")
            return render_template("main/index.html")

        # Determine the user's role based on ID prefix
        role_map = {
            "d": "doctor",
            "n": "nurse",
            "m": "manager",
        }
        
        role_prefix = user_id[0]  # Get the first character of the ID

        # Check if the ID prefix is valid (only doctors, nurses, or managers can log in)
        if role_prefix not in role_map:
            print("Invalid login: Patients are not allowed to log in.")
            return render_template("main/index.html")

        role_table = role_map[role_prefix]  # Get the Supabase table name

        try:
            # Query Supabase to check if the user exists
            response = supabase.table(role_table).select("*").eq("id", user_id).execute()

            if response.data:  # If user exists in the database
                navs = f"{role_table}_index"
                print(f"Login successful. Redirecting to {navs}")

                return redirect(url_for(navs, id=user_id))

            else:
                print("Invalid login: User does not exist.")
                return render_template("main/index.html")

        except Exception as e:
            print(f"Error during login: {e}")
            return render_template("main/index.html")

    return render_template("main/index.html")


# Access Management index page DONE
## NOTE: add code to check end date for status(expired/active/terminated)
@app.route("/manage/<string:id>")
def manager_index(id):
    # Fetch people data from Supabase
    m_response = supabase.table("manager").select("*").execute()

    # Fetch doctors and nurses data from Supabase
    d_response = supabase.table("doctor").select("*").execute()
    n_response = supabase.table("nurse").select("*").execute()

    # Initialize the count for doctors, nurses, and patients
    active = expired = terminated = 0  # Default counts for each status

    # Count active, expired, and terminated doctors
    if d_response.data:
        active += sum(1 for doctor in d_response.data if doctor.get("status") == "active")
        expired += sum(1 for doctor in d_response.data if doctor.get("status") == "expired")
        terminated += sum(1 for doctor in d_response.data if doctor.get("status") == "terminated")

    # Count active, expired, and terminated nurses
    if n_response.data:
        active += sum(1 for nurse in n_response.data if nurse.get("status") == "active")
        expired += sum(1 for nurse in n_response.data if nurse.get("status") == "expired")
        terminated += sum(1 for nurse in n_response.data if nurse.get("status") == "terminated")

    # Total counts for doctors, nurses, and patients
    count = {
        "d_count": len(d_response.data) if d_response.data else 0,  # Total doctors
        "n_count": len(n_response.data) if n_response.data else 0,  # Total nurses
        "p_count": len(m_response.data) if m_response.data else 0,  # Total people (patients)
        "active": active,
        "expired": expired,
        "terminated": terminated
    }

    # Find the specific person matching the id
    if m_response.data:
        for ppl in m_response.data:
            if id == ppl["id"]:
                return render_template("manage/manager_index.html", ppl=ppl, count=count)

    return "Person not found.", 404



# Retrieve the data from Supabase DONE
@app.route("/<string:db_type>_db/<string:staff_id>")
def manage_db(db_type, staff_id):
    # Define a mapping between db_type and the corresponding Supabase table
    table_map = {
        "doctors": "doctor",
        "nurses": "nurse",
        "patients": "patient",
    }

    # Check if the db_type is valid
    if db_type not in table_map:
        return "Invalid database type.", 404

    try:
        # Fetch the corresponding data from Supabase
        table_name = table_map[db_type]
        response = supabase.table(table_name).select("*").execute()

        # If the response data is available, assign it to the variable 'data'
        data = response.data if response.data else []

        # Initialize status counts only for doctors and nurses
        status_counts = None
        if db_type in ["doctors", "nurses"]:
            status_counts = {"active": 0, "expired": 0, "terminated": 0}
            for record in data:
                status = record.get("status", "").lower()  # Default to empty string if 'status' key is missing
                if status in status_counts:
                    status_counts[status] += 1

    except Exception as e:
        print(f"Error fetching data from Supabase: {e}")
        data = []
        status_counts = None if db_type == "patients" else {"active": 0, "expired": 0, "terminated": 0}

    # Render the corresponding template and pass the data and status counts (if applicable)
    return render_template(
        f"manage/{db_type}_db.html",
        data=data,
        staff_id=staff_id,
        count=status_counts if status_counts else {}
    )

# can delete since no more use .json file
##########################################################################################################
# def get_current_ids():
#     """Load the current IDs from the JSON file or initialize if not found."""
#     try:
#         with open(ID_TRACKER_FILE, "r") as file:
#             ids = json.load(file)
#     except FileNotFoundError:
#         # Initialize IDs if the file does not exist
#         ids = {
#             "patient_id": 10000,
#             "doctor_id": 1000,
#             "nurse_id": 1000
#         }
#     return ids

# def save_current_ids(ids):
#     """Save the current IDs to the JSON file."""
#     with open(ID_TRACKER_FILE, "w") as file:
#         json.dump(ids, file)

# def get_next_id(id_type):
#     """Get the next ID for the given type (e.g., patient, doctor, nurse)."""
#     ids = get_current_ids()
    
#     if id_type not in ids:
#         raise ValueError(f"Invalid ID type: {id_type}")
    
#     # Increment the ID
#     next_id = ids[id_type] + 1
#     ids[id_type] = next_id
    
#     # Save the updated IDs back to the JSON file
#     save_current_ids(ids)
#     if id_type == "doctor_id":
#         return f"d{next_id}"
#     elif id_type == "nurse_id":
#         return f"n{next_id}"
#     else:
#         return next_id 


# Add new doctor/nurse (create new user with username and password for login the system) DONE
@app.route("/<string:staff_type>_add/<string:staff_id>", methods=["GET", "POST"])
def add_record(staff_type, staff_id):
    # Mapping for table names and ID keys based on staff type
    staff_tables = {
        "doctors": {"table": "doctor", "id_key": "id", "prefix": "d"},  # Add prefix 'd' for doctors
        "nurses": {"table": "nurse", "id_key": "id", "prefix": "n"},    # Add prefix 'n' for nurses
    }

    # Validate staff type
    if staff_type not in staff_tables:
        return "Invalid staff type.", 404

    # Get the table and ID key for the specified staff type
    table_name = staff_tables[staff_type]["table"]
    id_key = staff_tables[staff_type]["id_key"]
    prefix = staff_tables[staff_type]["prefix"]  # Get the prefix based on staff type

    # Attempt to get the latest ID from the Supabase table
    try:
        response = supabase.table(table_name).select(id_key).order(id_key, desc=True).limit(1).execute()

        # Log the entire response to inspect its structure
        print(f"Response: {response}")

        if hasattr(response, 'error') and response.error:  # Check if the response contains an error
            print(f"Error fetching the latest ID: {response.error}")
            return f"Error fetching the latest ID: {response.error}", 500
        
        # Get the latest ID from the response data and generate the new ID
        latest_id = response.data[0][id_key][1:] if response.data else 10000  # Default to 10000 if no data
        next_id = int(latest_id) + 1  # Increment by 1 for the new ID
        record_id = f"{prefix}{next_id}"

        print(f"Generated new ID: {record_id}")
    except Exception as e:
        print(f"Error retrieving or generating ID: {e}")
        return f"Error retrieving or generating ID: {e}", 500

    if request.method == "POST":
        # Collect form data
        name = request.form["name"]
        nic = request.form["nic"]
        dob = request.form["dob"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]
        department = request.form["department"]
        startDate = request.form["startDate"]
        endDate = request.form["endDate"]

        # Determine the status based on endDate
        today = datetime.today().date()
        status = "active" if datetime.strptime(endDate, "%Y-%m-%d").date() > today else "expired"

        # Insert data into the Supabase table (doctor or nurse)
        try:
            insert_response = supabase.table(table_name).insert({
                "id": record_id,
                "name": name,
                "nic": nic,
                "dob": dob,
                "gender": gender,
                "phone": phone,
                "email": email,
                "department": department,
                "startdate": startDate,
                "enddate": endDate,
                "status": status
            }).execute()

            if hasattr(insert_response, 'error') and insert_response.error:
                print(f"Error inserting into Supabase: {insert_response.error}")
            else:
                print(f"{staff_type.capitalize()} {name} added successfully.")

        except Exception as e:
            print(f"Error inserting data: {e}")

        # Add login details in the Supabase login table
        try:
            login_response = supabase.table("login").insert({
                "id": record_id,
                "psw": nic,
                "pos": staff_type
            }).execute()

            if hasattr(login_response, 'error') and login_response.error:
                print(f"Error inserting login data into Supabase: {login_response.error}")
            else:
                print(f"Login details for {staff_type.capitalize()} {name} added successfully.")

        except Exception as e:
            print(f"Error adding login data: {e}")

        # Add appointment details for doctors (only applicable to doctors)
        if staff_type == "doctors":
            try:
                appointment_response = supabase.table("appointment").insert({
                    "doctor_id": record_id,
                    "count": 1
                }).execute()

                if hasattr(appointment_response, 'error') and appointment_response.error:
                    print(f"Error inserting appointment data into Supabase: {appointment_response.error}")
                else:
                    print(f"Appointment details for doctor {name} added successfully.")

            except Exception as e:
                print(f"Error adding appointment data: {e}")

        # Redirect to index after saving
        return redirect(url_for("manage_db", db_type=staff_type, staff_id=staff_id))

    else:
        return render_template(f"manage/{staff_type}_add.html", id=record_id, staff_id=staff_id)

###########################################################################################################
# Display functions that can be done by doctors only (Patient list, Schedule, Appointment for scan, Profile) DONE
@app.route("/doctor/<string:id>")
def doctor_index(id):
    try:
        # Fetch doctor details from Supabase (Ensuring the logged-in doctor exists)
        doctor_response = supabase.table("doctor").select("*").eq("id", id).execute()
        if not doctor_response.data:
            print(f"Doctor with ID {id} not found.")
            return "Doctor not found", 404

        doctor = doctor_response.data[0]  # Extract the doctor details

        # Fetch appointments from today onwards
        today_date = datetime.now().date().strftime('%Y-%m-%d')  # Format today's date
        appointment_response = (
            supabase.table("appointment")
            .select("id, patient_id, date, time, status, nurse_id")
            .eq("doctor_id", id)
            .eq("date", today_date)  # Get appointments for today and future dates
            .execute()
        )

        if not appointment_response.data:
            print(f"No appointments found for Doctor {id} today.")
            appointments = []
        else:
            appointments = appointment_response.data  # List of appointments from today onwards

            # Fetch patient names and nurse names
            patient_ids = list(set(app["patient_id"] for app in appointments if app["patient_id"]))
            nurse_ids = list(set(app["nurse_id"] for app in appointments if app["nurse_id"]))

            # Get patient names from the patient table
            patient_response = (
                supabase.table("patient")
                .select("id, name")
                .in_("id", patient_ids)
                .execute()
            )
            patient_map = {p["id"]: p["name"] for p in patient_response.data}  # Map patient ID to name

            # Get nurse names from the nurse table
            nurse_response = (
                supabase.table("nurse")
                .select("id, name")
                .in_("id", nurse_ids)
                .execute()
            )
            nurse_map = {n["id"]: n["name"] for n in nurse_response.data}  # Map nurse ID to name

            # Replace IDs with names in the appointments list
            for app in appointments:
                app["patient_name"] = patient_map.get(app["patient_id"], "Unknown")
                app["nurse_name"] = nurse_map.get(app["nurse_id"], "Unknown")

            # Remove unnecessary fields to return only required attributes
            for app in appointments:
                app.pop("patient_id", None)
                app.pop("nurse_id", None)

            # Sort appointments by date and then by time
            appointments.sort(
                key=lambda app: (datetime.strptime(app["date"], "%Y-%m-%d"), 
                                 datetime.strptime(app["time"], "%H:%M"))
            )

        print(appointments)  # Debugging output

        return render_template("doctors/doctor_index.html", doctor=doctor, appointments=appointments)

    except Exception as e:
        print(f"Error fetching doctor or appointment data: {e}")
        return "An error occurred while retrieving data", 500


@app.route("/nurse/<string:id>")
def nurse_index(id):
    # Load nurse data from the database or file
    nurses = load_db(NURSE_FILE)
    patients = load_db(PATIENTS_FILE)
    patient_db = [] 
    
    # Search for the nurse with the given ID
    for nurse in nurses:
        if id == nurse["id"]:
            for patient in patients:
                # Check if the nurse's department is in the patient's list of departments
                if nurse["department"] in patient.get("departments", []):
                    patient_db.append(patient)
            
            print(patient_db)
            return render_template("nurses/nurse_index.html", nurse=nurse, patient_db=patient_db)

##############################################################################################################

@app.route("/nurse_profile/<string:nurse_id>")
def nurse_profile(nurse_id):
    # Load nurse data from the database or file
    nurses = load_db(NURSE_FILE)
    
    # Search for the nurse with the given ID
    for nurse in nurses:
        if nurse_id == nurse["id"]:
            # Render the nurse profile page
            return render_template("nurses/nurses_profile.html", nurse=nurse)
    
    # Handle case when the nurse is not found
    return "Nurse not found", 404


# Display the doctor's data DONE
@app.route("/doctor_profile/<string:doctor_id>")
def doctor_profile(doctor_id):
    try:
        # Fetch only the required fields from the "doctor" table in Supabase
        response = supabase.table("doctor").select("id, name, dob, gender, phone, email, department").eq("id", doctor_id).execute()
        
        # Check if doctor data is retrieved
        if response.data:
            doctor = response.data[0]  # Get the first record since ID is unique
            return render_template("doctors/doctors_profile.html", doctor=doctor)
    
    except Exception as e:
        print(f"Error fetching doctor data from Supabase: {e}")

    return "Doctor not found", 404



def get_details_by_id(id,filePath):
    details = load_db(filePath)
    return next((p for p in details if p["id"] == id), None)

def save_profile(persons,filePath):
    with open(filePath, "w") as file:
        json.dump(persons, file, indent=4)

def update_nurse(id, name, dob, gender, phone, email, department):
    nurses = load_db(NURSE_FILE)
    for nurse in nurses:
        if nurse["id"] == id:
            nurse["name"] = name
            nurse["dob"] = dob
            nurse["gender"] = gender
            nurse["phone"] = phone
            nurse["email"] = email
            nurse["department"] = department
            break

    save_profile(nurses,NURSE_FILE)


def update_details(id, name,nic, dob, gender, department, phone, email, startDate, endDate, status,filePath):
    ppls = load_db(filePath)
    for ppl in ppls:
        if ppl["id"] == id:
            ppl["name"] = name
            ppl["nic"] = nic
            ppl["dob"] = dob
            ppl["gender"] = gender
            ppl["department"] = department
            ppl["phone"] = phone
            ppl["email"] = email
            ppl["startDate"] = startDate
            ppl["endDate"] = endDate
            ppl["status"] = status
            break

    save_profile(ppls,filePath)


@app.route("/update_contract/<string:staff_type>/<string:staff_id>/<string:id>", methods=['GET', 'POST'])
def update_contract(staff_type,staff_id,id):
    # Define a mapping between db_type and file/constants
    db_files = {
        "doctors": DOCTORS_FILE,
        "nurses": NURSE_FILE,
        "patients": PATIENTS_FILE,
    }
    print("OK 2")
    # Check if the db_type is valid
    if staff_type not in db_files:
        return "Invalid database type.", 404
    
    file_path = db_files[staff_type]
    ppl = get_details_by_id(id,file_path)

    print(ppl)
    if request.method == 'POST':
        startDate = request.form['startDate']
        endDate = request.form["endDate"]
        status = "active"

        print("OK 3")

        update_details(id, ppl["name"],ppl["nic"],ppl["dob"],ppl["gender"], 
                       ppl["department"], ppl["phone"], ppl["email"],
                       startDate, endDate,status,file_path)
        print("OK 4")
        return redirect(url_for("manage_db",db_type=staff_type, staff_id=staff_id))
    return render_template('manage/update_contract.html',ppl=ppl,staff_type=staff_type,staff_id=staff_id)



@app.route("/edit_profile/<string:id>", methods=['GET', 'POST'])
def edit_profile(id):
    # Check if id starts with 'n' or 'd'
    if id.startswith('n'):
        staff_type = 'nurse'
        staff = get_details_by_id(id, NURSE_FILE)
    elif id.startswith('d'):
        staff_type = 'doctor'
        staff = get_details_by_id(id, DOCTORS_FILE)
    else:
        # Handle the case if the id doesn't start with 'n' or 'd'
        return "Invalid ID", 400

    print(staff)

    if request.method == 'POST':
        phone = request.form['phone']
        email = request.form["email"]
      
        update_nurse(id, staff["name"], staff["dob"], staff["gender"], phone, email, staff["department"])
        return redirect(url_for(f'{staff_type}_profile', id=id))

    return render_template('main/update_profile.html', staff=staff, staff_type=staff_type)





#####################################################################################################################
# edit password for all users
@app.route("/edit_psw/<string:id>", methods=['GET', 'POST'])
def edit_psw(id):
    print(id)
    details = load_db(LOGIN_FILE)
    print("OK")
    if request.method == 'POST':
        print("OK2")
        for ppl in details:
            if ppl["id"] == id:
                print("id", id)
                current = ppl["psw"]
                print("psw", current)      
                  
    return render_template('main/edit_psw.html', id=id)


########################################################################################################
# Display Patient's data that had or have appointment with the doctor DONE
@app.route("/patient/<string:staff_id>")
def index(staff_id):
    try:
        # Query to get all patients with appointments for the given doctor
        appointment_response = supabase.table("appointment").select("patient_id").eq("doctor_id", staff_id).execute()
        
        if not appointment_response.data:
            return render_template("patients/patients_index.html", patients=[], staff_id=staff_id)

        # Extract patient IDs from appointments
        patient_ids = [appointment["patient_id"] for appointment in appointment_response.data]

        # Fetch patient details for these patient IDs
        patient_response = supabase.table("patient").select("id, name, nic, dob, gender").in_("id", patient_ids).execute()

        # Render the patients' details in the template
        patients = patient_response.data  # List of patients who have appointments with the doctor
        return render_template("patients/patients_index.html", patients=patients, staff_id=staff_id)

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


# Add new patient in database DONE
@app.route("/add/<string:department>/<string:staff_id>", methods=["GET", "POST"])
def add_patient(department, staff_id):
    # Fetch the latest patient ID from the patient table
    try:
        response = supabase.table("patient").select("id").order("id", desc=True).limit(1).execute()
            
        # Log the entire response to inspect its structure
        print(f"Response: {response}")

        if hasattr(response, 'error') and response.error:  # Check if the response contains an error
            print(f"Error fetching the latest ID: {response.error}")
            return f"Error fetching the latest ID: {response.error}", 500
            
        latest_id = response.data[0]["id"] if response.data else 10000  # Default to 10000 if no data
        next_id = int(latest_id) + 1  # Increment by 1 for the new ID
        record_id = f"{next_id}"
    except Exception as e:
        print(f"Error retrieving or generating ID: {e}")
        return f"Error retrieving or generating ID: {e}", 500
    
    
    if request.method == "POST":
        # Get form data
        name = request.form["name"]
        nic = request.form["nic"]
        dob = request.form["dob"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]

        # Query the nurse table to get the department of the logged-in nurse
        try:
            nurse_response = supabase.table("nurse").select("department").eq("id", staff_id).execute()
            if nurse_response.data:
                nurse_department = nurse_response.data[0]["department"]
            else:
                print("Error: Nurse department not found.")
                return redirect(url_for("nurse_index", id=staff_id))
        except Exception as e:
            print(f"Error fetching nurse department: {e}")
            return redirect(url_for("nurse_index", id=staff_id))

        

        # Check if the NIC already exists in the patient table
        try:
            nic_check_response = supabase.table("patient").select("nic").eq("nic", nic).execute()
            if nic_check_response.data:
                print("Error: NIC already exists.")
                return redirect(url_for("nurse_index", id=staff_id))
        except Exception as e:
            print(f"Error checking NIC existence: {e}")
            return redirect(url_for("nurse_index", id=staff_id))

        # Create the patient record
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
                "department": nurse_department,
                "nurse_id": staff_id
            }
            insert_response = supabase.table("patient").insert(patient_data).execute()
            if hasattr(insert_response, 'error') and insert_response.error:
                print(f"Error inserting into Supabase: {insert_response.error}")
                return redirect(url_for("nurse_index", id=staff_id))
            return redirect(url_for("nurse_index", id=staff_id))
        except Exception as e:
            print(f"Error inserting into Supabase: {e}")
            return redirect(url_for("nurse_index", id=staff_id))
    
    return render_template("patients/patients_add.html", id=record_id, staff_id=staff_id, department=department)



@app.route("/add_existing/<string:department>/<string:staff_id>", methods=["GET", "POST"])
def add_existing_or_search(department, staff_id):
    patients = load_db(PATIENTS_FILE)
    query = request.args.get("query", "") 

    # If the method is POST, update the patient with the department
    if request.method == "POST":
        patient_id = request.form["patient_id"] 
        existing_department = request.form["existing_department"] 

        # Find the patient and add the department
        for patient in patients:
            if str(patient["id"]) == patient_id:
                # Ensure "departments" is a list (initialize it if necessary)
                if not isinstance(patient.get("departments"), list):
                    patient["departments"] = [] 
                if existing_department not in patient["departments"]:
                    patient["departments"].append(existing_department)
                break

        save_ppl(PATIENTS_FILE, patients)
        return redirect(url_for("nurse_index", id=staff_id))

    if request.method == "GET":
        query = request.args.get("query", "").lower()  # Ensure query is a string and lowercase
    
    if query:  # If there is a query
        search_results = [
            patient for patient in patients
            if query in str(patient.get("id", "")).lower() or  # Convert id to string
               query in patient.get("nic", "").lower()   # nic is already text, just lowercase
        ]
    else:
        search_results = []
    
    return render_template(
        "patients/patients_add_department.html", 
        staff_id=staff_id, 
        department=department, 
        patients=search_results, 
        query=query
    )


# Update patient details (phone,email,address)
@app.route('/update/<int:patient_id>/<string:staff_id>', methods=['GET', 'POST'])
def update_patient_info(patient_id, staff_id):
    patient = get_details_by_id(patient_id, PATIENTS_FILE)
    
    if not patient:
        return "Patient not found", 404

    if request.method == 'POST':
        phone = request.form['phone']
        email = request.form["email"]
        address = request.form["address"]

        update_patient(patient_id, phone, email,address, PATIENTS_FILE)
        return redirect(url_for("nurse_index", id=staff_id))

    return render_template('patients/patients_update.html', patient=patient, staff_id=staff_id)

def update_patient(patient_id, phone, email, address, file_name):
    patients = load_db(file_name)
    for patient in patients: 
        if patient["id"] == patient_id:
            
            # Update only phone, email, and address
            patient["phone"] = phone
            patient["email"] = email
            patient["address"] = address
            break
        
    save_ppl(file_name, patients)

######################################################################################################################
# Appointment


@app.route('/appointment/<int:patient_id>/<string:staff_id>')
def get_appointment(patient_id, staff_id):
    patient = get_details_by_id(patient_id, PATIENTS_FILE)
    return render_template('patients/patients_appointment.html', patient=patient, staff_id=staff_id)

@app.route('/app_history/<int:patient_id>/<string:staff_id>')
def get_history(patient_id, staff_id):
    patient = get_details_by_id(patient_id, PATIENTS_FILE)
    nurse = get_details_by_id(staff_id, NURSE_FILE)
    return render_template('patients/patients_history.html', patient=patient, nurse=nurse)


@app.route('/add_appointment/<int:patient_id>/<string:staff_id>', methods=["GET", "POST"])
def new_appointment(patient_id, staff_id):
    patient = get_details_by_id(patient_id, PATIENTS_FILE)
    
    # Check if id starts with 'n' or 'd'
    if staff_id.startswith('n'):
        staff = get_details_by_id(staff_id, NURSE_FILE)
        
        doctors = load_db(DOCTORS_FILE)
        db = []
        for doctor in doctors:
            if doctor["department"] == staff["department"]:
                db.append(doctor)
        
        if request.method == "POST":            
            patients = load_db(PATIENTS_FILE)
            
            patient_id = request.form["patient_id"]
            patient_name = request.form["patient_name"]
            department = request.form["department"]
            doctor_name = request.form["doctor_name"]
            date = request.form["date"]
            time = request.form["time"]
            status = "active"
             
            for p in patients: 
                if p["id"] == int(patient_id):  # Make sure patient_id is compared as int
                    if "appointment" not in p:
                        p["appointment"] = []  # Ensure there's an appointment key
                    
                    count = len(p["appointment"])
                    print(count)
                    
                    p["appointment"].append({
                        "num": count + 1,
                        "patient_id": patient_id,
                        "patient_name": patient_name,
                        "department": department,
                        "doctor_name": doctor_name,
                        "date": date,
                        "time": time,
                        "status": status                    
                    })
                    break  # Stop loop once the patient is found
            
            # Save the updated records list
            try:
                save_ppl(PATIENTS_FILE, patients)  # This will save the modified patients list
                return redirect(url_for("get_appointment", patient_id=patient_id, staff_id=staff_id))
            except Exception as e:
                print(f"File saving error: {e}")
        
        return render_template('patients/patients_add_appointment.html', patient=patient, staff=staff, doctors=db)
   
    elif staff_id.startswith('d'):
        staff_type = 'doctor'
        staff = get_details_by_id(staff_id, DOCTORS_FILE)
        
    else:
        # Handle the case if the id doesn't start with 'n' or 'd'
        return "Invalid ID", 400
    
    
    return render_template('patients/patients_add_appointment.html', patient=patient,  staff=staff, doctors=doctors)


@app.route('/update_appointment/<int:patient_id>/<string:staff_id>/<int:appointment_index>', methods=["GET", "POST"])
def update_appointment(patient_id, staff_id, appointment_index):
    # Fetch patient details
    patient = get_details_by_id(patient_id, PATIENTS_FILE)
    staff = get_details_by_id(staff_id, NURSE_FILE)
    doctors_db = load_db(DOCTORS_FILE)
    doctors = []
    for doctor in doctors_db:
        if doctor["department"] == staff["department"]:
            doctors.append(doctor)
                
    # Check if patient has appointments
    if patient and 'appointment' in patient:
        try:
            # Get the specific appointment by its index
            app = patient['appointment'][appointment_index - 1]  # list is 0-indexed, so subtract 1
        except IndexError:
            # Handle case if index is out of range
            return "Appointment not found", 404

        if request.method == "POST":
            # Get updated data from the form
            doctor_name = request.form["doctor_name"]
            date = request.form["date"]
            time = request.form["time"]
            
            # Update the appointment details
            app['doctor_name'] = doctor_name
            app['date'] = date
            app['time'] = time
            
            # Save the updated patient record
            try:
                # Save the updated list of patients
                patients = load_db(PATIENTS_FILE)
                for p in patients:
                    if p['id'] == patient_id:
                        p['appointment'] = patient['appointment']
                        break
                save_ppl(PATIENTS_FILE, patients)
                return redirect(url_for('get_appointment', patient_id=patient_id, staff_id=staff_id))
            except Exception as e:
                return f"Error saving updates: {e}", 500

        # Render the form to update the appointment
        return render_template('patients/patients_update_appointment.html', patient_id=patient_id, staff_id=staff_id, app=app, doctors=doctors)
    
    return "Patient or appointment not found", 404

# Display the doctor's upcoming appointments DONE
@app.route("/doctor_schedule/<string:id>", methods=["GET", "POST"])
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

        query = supabase.table("appointment").select("id, patient_id, date, time, status, nurse_id").eq("doctor_id", id)
        query = query.eq("date", selected_date) if selected_date else query.gt("date", today_date)
        
        appointment_response = query.execute()
        appointments = appointment_response.data or []

        # Fetch patient and nurse details
        patient_map, nurse_map = {}, {}
        if appointments:
            patient_ids = {app["patient_id"] for app in appointments if app["patient_id"]}
            nurse_ids = {app["nurse_id"] for app in appointments if app["nurse_id"]}

            if patient_ids:
                patient_response = supabase.table("patient").select("id, name").in_("id", list(patient_ids)).execute()
                patient_map = {p["id"]: p["name"] for p in patient_response.data}

            if nurse_ids:
                nurse_response = supabase.table("nurse").select("id, name").in_("id", list(nurse_ids)).execute()
                nurse_map = {n["id"]: n["name"] for n in nurse_response.data}

            for app in appointments:
                app["patient_name"] = patient_map.get(app.pop("patient_id"), "Unknown")
                app["nurse_name"] = nurse_map.get(app.pop("nurse_id"), "Unknown")

            appointments.sort(
                key=lambda app: (datetime.strptime(app["date"], "%Y-%m-%d"),
                                 datetime.strptime(app["time"], "%H:%M"))
            )

        return render_template("doctors/doctors_schedule.html", id=id, doctor=doctor, appointments=appointments, selected_date=selected_date)
    except Exception as e:
        return f"Error fetching doctor schedule: {e}", 500





if __name__ == "__main__":
    app.run(debug=True, port=5000)
