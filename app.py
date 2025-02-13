import json
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime

app = Flask(__name__)

# Path to the JSON file where the patient data will be stored
PATIENTS_FILE = "patients.json"
DOCTORS_FILE = "doctors.json"
NURSE_FILE = "nurse.json"
MANAGE_FILE = "manage.json"
LOGIN_FILE = "login.json"
APPOINTMENT_FILE = "appointment.json"
ID_TRACKER_FILE = "id_tracker.txt"

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
    

@app.route("/", methods=["GET", "POST"])
def index_main():
    if request.method == "POST":
        ppl = load_db(LOGIN_FILE)  # Load the list of users
        id = request.form["user"]
        psw = request.form["psw"]

        # Search for the user in the list
        for person in ppl:
            if id == person["id"] and psw == person["psw"]:
                navs = person["pos"] + "_index"

                # Check and update status for doctors and nurses
                d_count = load_db(DOCTORS_FILE)
                n_count = load_db(NURSE_FILE)
                current_date = datetime.now().date()

                # Update status for doctors
                for doctor in d_count:
                    end_date_str = doctor.get("endDate", "")
                    if end_date_str:
                        try:
                            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                            doctor["status"] = "expired" if end_date < current_date else "active"
                        except ValueError:
                            print(f"Invalid date format for doctor {doctor['id']}: {end_date_str}")
                    else:
                        print(f"Doctor {doctor['id']} has no endDate")

                # Save the updated doctors' data
                save_ppl(DOCTORS_FILE, d_count)

                # Update status for nurses
                for nurse in n_count:
                    end_date_str = nurse.get("endDate", "")
                    if end_date_str:
                        try:
                            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                            nurse["status"] = "expired" if end_date < current_date else "active"
                        except ValueError:
                            print(f"Invalid date format for nurse {nurse['id']}: {end_date_str}")
                    else:
                        print(f"Nurse {nurse['id']} has no endDate")

                # Save the updated nurses' data
                save_ppl(NURSE_FILE, n_count)

                print(navs)
                return redirect(url_for(navs, id=id))

        # If no match is found
        print("Invalid login")
        return render_template("main/index.html")

    return render_template("main/index.html")

# Access Management index page
@app.route("/manage/<string:id>")
def manage_index(id):
    ppls = load_db(MANAGE_FILE)

    d_count = load_db(DOCTORS_FILE)
    n_count = load_db(NURSE_FILE)
    p_count = load_db(PATIENTS_FILE)

    # Count total and active doctors and nurses
    active = sum(1 for doctor in d_count if doctor.get("status") == "active") + sum(1 for nurse in n_count if nurse.get("status") == "active")
    expired = sum(1 for doctor in d_count if doctor.get("status") == "expired") + sum(1 for nurse in n_count if nurse.get("status") == "expired")

    count = {
        "d_count": len(d_count),  # Total doctors
        "n_count": len(n_count),  # Total nurses
        "p_count": len(p_count),  # Total patients
        "active": active,
        "expired": expired
    }

    for ppl in ppls:
        if id == ppl["id"]:
            return render_template("manage/manage_index.html", ppl=ppl, count=count)


# Get databse 
@app.route("/<string:db_type>_db/<string:staff_id>")
def manage_db(db_type, staff_id):
    # Define a mapping between db_type and file/constants
    db_files = {
        "doctors": DOCTORS_FILE,
        "nurses": NURSE_FILE,
        "patients": PATIENTS_FILE,
    }

    # Check if the db_type is valid
    if db_type not in db_files:
        return "Invalid database type.", 404

    # Load the appropriate database
    data = load_db(db_files[db_type])
    # Render the corresponding template
    return render_template(f"manage/{db_type}_db.html", data=data, staff_id=staff_id)



##########################################################################################################
def get_current_ids():
    """Load the current IDs from the JSON file or initialize if not found."""
    try:
        with open(ID_TRACKER_FILE, "r") as file:
            ids = json.load(file)
    except FileNotFoundError:
        # Initialize IDs if the file does not exist
        ids = {
            "patient_id": 10000,
            "doctor_id": 1000,
            "nurse_id": 1000
        }
    return ids

def save_current_ids(ids):
    """Save the current IDs to the JSON file."""
    with open(ID_TRACKER_FILE, "w") as file:
        json.dump(ids, file)

def get_next_id(id_type):
    """Get the next ID for the given type (e.g., patient, doctor, nurse)."""
    ids = get_current_ids()
    
    if id_type not in ids:
        raise ValueError(f"Invalid ID type: {id_type}")
    
    # Increment the ID
    next_id = ids[id_type] + 1
    ids[id_type] = next_id
    
    # Save the updated IDs back to the JSON file
    save_current_ids(ids)
    if id_type == "doctor_id":
        return f"d{next_id}"
    elif id_type == "nurse_id":
        return f"n{next_id}"
    else:
        return next_id 


# Add new doctor/nurse (create new user with username and password for login the system)
@app.route("/<string:staff_type>_add/<string:staff_id>", methods=["GET", "POST"])
def add_record(staff_type, staff_id):
    # Mapping for file loaders, savers, and ID keys based on staff type
    staff_files = {
        "doctors": {"file": DOCTORS_FILE, "id_key": "doctor_id"},
        "nurses": {"file": NURSE_FILE, "id_key": "nurse_id"},
    }

    # Validate staff type
    if staff_type not in staff_files:
        return "Invalid staff type.", 404

    # Get the file and ID key for the specified staff type
    file_path = staff_files[staff_type]["file"]
    print(file_path)
    id_key = staff_files[staff_type]["id_key"]
    print(id_key)

    # Get the current ID for display purposes
    current_id = get_current_ids().get(id_key, 10000)
    if id_key == "doctor_id":
        id = f"d{current_id}"
    elif id_key == "nurse_id":
        id = f"n{current_id}"
    else:
        id = current_id 

    if request.method == "POST":
        # Load existing records
        records = load_db(file_path)

        # Generate the next ID for the given staff type
        record_id = id

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
        status = "active"

        # Append the new record
        records.append({
            "id": record_id,
            "name": name,
            "nic": nic,
            "dob": dob,
            "gender": gender,
            "phone": phone,
            "email": email,
            "department": department,
            'startDate': startDate,
            'endDate': endDate,
            "status": status
        })
        # Save the updated records list
        try:
            save_ppl(file_path, records)
        except Exception as e:
             print(f"File saving error: {e}")
        
        get_next_id(id_key)
        print("Saved")

        add_new = load_db(LOGIN_FILE)
        add_new.append({
            "id": record_id,
            "psw": nic,
            "pos": staff_type
        })
        save_ppl(LOGIN_FILE, add_new)
        
        add_appointment = load_db(APPOINTMENT_FILE)
        add_appointment.append({
            "doctor_id": record_id,
            "count": 1
        })
        
        save_ppl(APPOINTMENT_FILE, add_appointment)

        

        # Redirect to index after saving
        return redirect(url_for("manage_db",db_type=staff_type, staff_id=staff_id))
    else:
        return render_template(f"manage/{staff_type}_add.html", id=id, staff_id=staff_id)


###########################################################################################################
@app.route("/doctor/<string:id>")
def doctors_index(id):
    # Load nurse data from the database or file
    doctors = load_db(DOCTORS_FILE)
    patients = load_db(PATIENTS_FILE)
    
    db = []

    # Search for the doctor with the given ID
    for doctor in doctors:
        if id == doctor["id"]:
            print(doctor["name"])
            # Loop through the patients to find their appointments
            for patient in patients:
                if 'appointment' in patient:  # Ensure appointments exist for the patient
                    for app in patient['appointment']:
                        # Check if the appointment is for the doctor and on today's date
                        if app.get('doctor_name') == doctor['name']:
                            try:
                                appointment_date = datetime.strptime(app['date'], '%Y-%m-%d').date()
                                # Check if the appointment date is today
                                if appointment_date == datetime.now().date():  
                                    db.append(app)
                            except ValueError:
                                print(f"Skipping invalid date format: {app['date']}")
            break  # Assuming one doctor is found, no need to loop further
    
    db.sort(key=lambda app: datetime.strptime(f"{app['date']} {app['time']}", '%Y-%m-%d %H:%M'))
    print(db)  # Add print statements for debugging purposes
    return render_template("doctors/doctors_index.html", doctor=doctor, db=db, patients=patients)



@app.route("/nurse/<string:id>")
def nurses_index(id):
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
            return render_template("nurses/nurses_index.html", nurse=nurse, patient_db=patient_db)

##############################################################################################################

@app.route("/nurse_profile/<string:id>")
def nurse_profile(id):
    # Load nurse data from the database or file
    nurses = load_db(NURSE_FILE)
    
    # Search for the nurse with the given ID
    for nurse in nurses:
        if id == nurse["id"]:
            # Render the nurse profile page
            return render_template("nurses/nurses_profile.html", nurse=nurse)
    
    # Handle case when the nurse is not found
    return "Nurse not found", 404

@app.route("/doctor_profile/<string:id>")
def doctor_profile(id):
    # Load doctor data from the database or file
    doctors = load_db(DOCTORS_FILE)
    
    # Search for the doctor with the given ID
    for doctor in doctors:
        if id == doctor["id"]:
            # Render the doctor profile page
            return render_template("doctors/doctors_profile.html", doctor=doctor)
    
    # Handle case when the nurse is not found
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
@app.route("/patient/<string:staff_id>")
def index(staff_id):
    patients = load_db(PATIENTS_FILE)
    staff_id= staff_id
    return render_template("patients/patients_index.html", patients=patients, staff_id=staff_id)


# Add new patient in database
@app.route("/add/<string:department>/<string:staff_id>", methods=["GET", "POST"])
def add_patient(department, staff_id):
    if request.method == "POST":
        # Load existing patients
        patients = load_db(PATIENTS_FILE)

        # Get form data
        name = request.form["name"]
        nic = request.form["nic"]
        dob = request.form["dob"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]
        
        # Generate the next patient ID
        id = get_current_ids().get("patient_id", 10000)
        
        # Check if the NIC already exists in the patient database
        if any(patient["nic"] == nic for patient in patients):
            # If NIC is already registered, return an error message
            return render_template("patients/patients_add.html", 
                                   error="Patient with this NIC already exists.", 
                                   id=id, staff_id=staff_id, department=department)
        
        # Modify department to be a list (even if it's just one department)
        department_list = [department] if department else []

        # Append the new patient record with departments as a list
        patients.append({
            "id": id,
            "name": name,
            "nic": nic,
            "dob": dob,
            "gender": gender,
            "phone": phone,
            "email": email,
            "address": address,
            "departments": department_list  # Store department as a list
        })

        # Save updated patients list
        save_ppl(PATIENTS_FILE, patients)
        
        # Increment the patient ID counter
        get_next_id("patient_id")

        # Redirect to index after saving
        return redirect(url_for("nurses_index", id=staff_id))

    # Get the current patient ID for display purposes
    id = get_current_ids().get("patient_id", 10000)
    return render_template("patients/patients_add.html", id=id, staff_id=staff_id, department=department)



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
        return redirect(url_for("nurses_index", id=staff_id))

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
        return redirect(url_for("nurses_index", id=staff_id))

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

@app.route('/doctor_schedule/<string:id>', methods=["GET", "POST"])
def doctor_schedule(id):
    doctor = get_details_by_id(id, DOCTORS_FILE)
    patients = load_db(PATIENTS_FILE)
    
    db = []
    
    for patient in patients:
        # Check if patient has appointments and loop through them if it is a list
        if patient and 'appointment' in patient:
            for app in patient['appointment']:  # Loop through each appointment
                if app.get('doctor_name') == doctor['name']:  # Use .get() to avoid KeyError
                    db.append(app)
    
    # Sort the appointments by date and time in ascending order
    db.sort(key=lambda app: datetime.strptime(f"{app['date']} {app['time']}", '%Y-%m-%d %H:%M'))

    return render_template('doctors/doctors_schedule.html', id=id, db=db, patients=patients, doctor=doctor)







if __name__ == "__main__":
    app.run(debug=True, port=5000)
