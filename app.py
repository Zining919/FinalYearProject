import json
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Path to the JSON file where the patient data will be stored
PATIENTS_FILE = "patients.json"
NURSE_FILE = "nurse.json"
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

def get_current_id():
    try:
        with open(ID_TRACKER_FILE, "r") as file:
            current_id = int(file.read().strip())
    except FileNotFoundError:
        current_id = 10000  # Start from 10000 if the file does not exist
    return current_id

def get_next_patient_id():
    current_id = get_current_id()
    next_id = current_id + 1
    with open(ID_TRACKER_FILE, "w") as file:
        file.write(str(next_id))
    return next_id

def load_nurse():
    try:
        with open(NURSE_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []  # Return an empty list if the file does not exist

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
                return redirect(url_for(navs, id=id)) 
        
        # If no match is found
        print("Invalid login")
        return render_template("main/index.html")         
    
    return render_template("main/index.html")



@app.route("/manage/<string:id>")
def manage_index(id):
    # Load nurse data from the database or file
    ppls = load_db(LOGIN_FILE)
    
    # Search for the nurse with the given ID
    for ppl in ppls:
        if id == ppl["id"]:
            pos = ppl["pos"]
            nav = pos + "/" + pos + "_index.html"
            return render_template(nav, ppl=ppl)


@app.route("/nurse/<string:id>")
def nurse_index(id):
    # Load nurse data from the database or file
    nurses = load_db(NURSE_FILE)
    
    # Search for the nurse with the given ID
    for nurse in nurses:
        if id == nurse["id"]:
            return render_template("nurse/nurse_index.html", nurse=nurse)






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

@app.route("/edit_profile/<string:id>", methods=['GET', 'POST'])
def nurse_edit_profile(id):
    nurse = get_details_by_id(id,NURSE_FILE)
    print(nurse)

    if request.method == 'POST':
        phone = request.form['phone']
        email = request.form["email"]

        update_nurse(id, nurse["name"],nurse["dob"],nurse["gender"], phone, email, nurse["department"])
        return redirect(url_for('nurse_profile',id=id))

    return render_template('nurse/nurse_update.html', nurse=nurse)









@app.route("/patient")
def index():
    patients = load_patients()
    return render_template("patient/patient_index.html", patients=patients)

@app.route("/add", methods=["GET", "POST"])
def add_patient():
    if request.method == "POST":
        patients = load_patients()
        id = get_current_id()
        name = request.form["name"]
        dob = request.form["dob"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]

        patients.append({"id": id, "name": name, "dob": dob, "gender": gender, "phone": phone, "email": email, "address": address})
        
        save_patients(patients)
        id = get_next_patient_id()
        return redirect(url_for("index"))

    id = get_current_id()
    return render_template("patient/patient_add.html", id=id)

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

    return render_template('patient/patient_update.html', patient=patient)

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
    return render_template('patient/patient_appointment.html', patient=patient)

@app.route('/app_history/<int:patient_id>')
def get_history(patient_id):
    patient = get_patient_by_id(patient_id)
    return render_template('patient/patient_history.html', patient=patient)


@app.route('/add_appointment/<int:patient_id>', methods=["GET","POST"])
def new_appointment(patient_id):
    patient = get_patient_by_id(patient_id)
    return render_template('patient/patient_history.html', patient=patient)

if __name__ == "__main__":
    app.run(debug=True)
