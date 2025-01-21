import json
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Path to the JSON file where the patient data will be stored
PATIENTS_FILE = "patients.json"
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

@app.route("/")
def index():
    patients = load_patients()
    message = request.args.get("message")
    return render_template("patient_index.html", patients=patients, message=message)

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

        return redirect(url_for("index", message="Patient added successfully!"))

    id = get_current_id()
    return render_template("patient_add.html", id=id)

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

    return render_template('patient_update.html', patient=patient)

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

if __name__ == "__main__":
    app.run(debug=True)
