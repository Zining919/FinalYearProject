
  // Import the functions you need from the SDKs you need
  import { initializeApp } from "https://www.gstatic.com/firebasejs/11.3.1/firebase-app.js";
  import { getDatabase, ref, set, get, child } from "https://www.gstatic.com/firebasejs/11.3.1/firebase-database.js";


  // Your web app's Firebase configuration
  const firebaseConfig = {
    apiKey: "AIzaSyBSMySbLXYTWi3MldKL8oKldHqLDxEPA9E",
    authDomain: "fyp-medical-image.firebaseapp.com",
    databaseURL: "https://fyp-medical-image-default-rtdb.firebaseio.com",
    projectId: "fyp-medical-image",
    storageBucket: "fyp-medical-image.firebasestorage.app",
    messagingSenderId: "332639037018",
    appId: "1:332639037018:web:caff89b058cb05c7345a63"
  };

  // Initialize Firebase
  const app = initializeApp(firebaseConfig);

  // get ref to database services
  const db = getDatabase(app);

  document.getElementById("submit").addEventListener("click", function(e){
    e.preventDefault();
    set(ref(db, 'doctor/'+ document.getElementById("name").value),
    {

        name: document.getElementById("name").value, 
        nic: document.getElementById("nic").value,
        dob: document.getElementById("dob").value,
        gender1: document.getElementById("gender1").value,
        gender2: document.getElementById("gender2").value,
        phone: document.getElementById("phone").value,
        email: document.getElementById("email").value,
        department1: document.getElementById("department1").value,
        department2: document.getElementById("department2").value,
        department3: document.getElementById("department3").value,
        department4: document.getElementById("department4").value,
        startDate: document.getElementById("startDate").value,
        endDate: document.getElementById("endDate").value,

    })

    alert("Login Succesful !");

  })
