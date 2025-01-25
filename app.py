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

# Function to load patients from the JSON file
def load_patients():
    try:
        with open(PATIENTS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []  # Return an empty list if the file does not exist

# Function to save patients to the JSON file
def save_patients(patients):
    with open(PATIENTS_FILE, "w") as file:
        json.dump(patients, file, indent=4)

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

def save_ppl(filePath,data):
    with open(filePath, "w") as file:
        json.dump(data, file, indent=4)

@app.route("/<string:staff_type>_add/<string:staff_id>", methods=["GET", "POST"])
def add_record(staff_type, staff_id):
    # Mapping for file loaders, savers, and ID keys based on staff type
    staff_files = {
        "patients": {"file": PATIENTS_FILE, "id_key": "patient_id"},
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
        print(add_new)

        save_ppl(LOGIN_FILE, add_new)
        print("OK")

        # Redirect to index after saving
        return redirect(url_for("manage_db",db_type=staff_type, staff_id=staff_id))
    else:
        return render_template(f"manage/{staff_type}_add.html", id=id, staff_id=staff_id)


###########################################################################################################
@app.route("/doctor/<string:id>")
def doctors_index(id):
    # Load nurse data from the database or file
    doctors = load_db(DOCTORS_FILE)

    # Search for the nurse with the given ID
    for doctor in doctors:
        if id == doctor["id"]:
            print(doctor["name"])
            return render_template("doctors/doctors_index.html", doctor=doctor)


@app.route("/nurse/<string:id>")
def nurses_index(id):
    # Load nurse data from the database or file
    nurses = load_db(NURSE_FILE)
    
    # Search for the nurse with the given ID
    for nurse in nurses:
        if id == nurse["id"]:
            return render_template("nurses/nurses_index.html", nurse=nurse)

##############################################################################################################

@app.route("/nurse_profile/<string:id>")
def nurse_profile(id):
    # Load nurse data from the database or file
    nurses = load_db(NURSE_FILE)
    
    # Search for the nurse with the given ID
    for nurse in nurses:
        if id == nurse["id"]:
            # Render the nurse profile page
            return render_template("nurse/nurse_profile.html", nurse=nurse)
    
    # Handle case when the nurse is not found
    return "Nurse not found", 404


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
def nurse_edit_profile(id):
    nurse = get_details_by_id(id,NURSE_FILE)
    print(nurse)

    if request.method == 'POST':
        phone = request.form['phone']
        email = request.form["email"]

        update_nurse(id, nurse["name"],nurse["dob"],nurse["gender"], phone, email, nurse["department"])
        return redirect(url_for('nurse_profile',id=id))

    return render_template('nurses/nurses_update.html', nurse=nurse)

#####################################################################################################################




@app.route("/patient/<string:staff_id>")
def index(staff_id):
    patients = load_patients()
    staff_id= staff_id
    return render_template("patients/patients_index.html", patients=patients, staff_id=staff_id)

@app.route("/add/<string:staff_id>", methods=["GET", "POST"])
def add_patient(staff_id):
    if request.method == "POST":
        # Load existing patients
        patients = load_patients()

        # Generate the next patient ID
        id = get_next_id("patient_id")

        # Get form data
        name = request.form["name"]
        dob = request.form["dob"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]

        # Append the new patient record
        patients.append({
            "id": id,
            "name": name,
            "dob": dob,
            "gender": gender,
            "phone": phone,
            "email": email,
            "address": address
        })

        # Save updated patients list
        save_patients(patients)

        # Redirect to index after saving
        return redirect(url_for("index", staff_id=staff_id))

    # Get the current patient ID for display purposes
    id = get_current_ids().get("patient_id", 10000)
    return render_template("patients/patients_add.html", id=id, staff_id=staff_id)


@app.route("/delete/<int:patient_id>")
def delete_patient(patient_id):
    patients = load_patients()
    patients = [patient for patient in patients if patient["id"] != patient_id]
    save_patients(patients)
    return redirect(url_for("index"))

@app.route('/update/<int:patient_id>', methods=['GET', 'POST'])
def update_patient_info(patient_id):
    patient = get_patient_by_id(patient_id)

    if not patient:
        return "Patient not found", 404

    if request.method == 'POST':
        name = request.form['name']
        dob = request.form['dob']
        gender = request.form['gender']
        phone = request.form['phone']
        email = request.form["email"]
        address = request.form["address"]

        update_patient(patient_id, name, dob, gender, phone, email, address)
        return redirect(url_for('index'))

    return render_template('patients/patients_update.html', patient=patient)

def get_patient_by_id(patient_id):
    patients = load_patients()
    return next((p for p in patients if p["id"] == patient_id), None)

def update_patient(patient_id, name, dob, gender, phone, email, address):
    patients = load_patients()
    for patient in patients:
        if patient["id"] == patient_id:
            patient["name"] = name
            patient["dob"] = dob
            patient["gender"] = gender
            patient["phone"] = phone
            patient["email"] = email
            patient["address"] = address
            break
        
    save_patients(patients)

@app.route('/appointment/<int:patient_id>')
def get_appointment(patient_id):
    patient = get_patient_by_id(patient_id)
    return render_template('patients/patients_appointment.html', patient=patient)

@app.route('/app_history/<int:patient_id>')
def get_history(patient_id):
    patient = get_patient_by_id(patient_id)
    return render_template('patients/patients_history.html', patient=patient)


@app.route('/add_appointment/<int:patient_id>', methods=["GET","POST"])
def new_appointment(patient_id):
    patient = get_patient_by_id(patient_id)
    return render_template('patients/patients_history.html', patient=patient)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
