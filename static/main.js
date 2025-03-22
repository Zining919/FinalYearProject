//   navbar function 
$(document).ready(function(){

    $('.fa-bars').click(function(){
        $(this).toggleClass('fa-times');
        $('.navbar').toggleClass('nav-toggle');
    });

    $(window).on('scroll load',function(){
        $('.fa-bars').removeClass('fa-times');
        $('.navbar').removeClass('nav-toggle');

        if($(Window).scrollTop()  >  30){
            $('header').addClass('header-active');
        }else{
            $('header').removeClass('header-active');
        }
    });

    
});


function loadSignUp() {
    // Hide other content
    $('#container').addClass('hidden-content');
    // Make AJAX call to load sign-up content
    $.ajax({
        url: 'signup.php',
        type: 'GET',
        success: function(response) {
            $('#signupModal .modal-body').html(response); // Load content into modal body
            $('#signupModal').modal('show'); // Show the modal
        },
        error: function(xhr, status, error) {
            console.error('Error loading signup.php:', error);
        }
    });
}

// Function to handle form submission
$('#loginForm').submit(function(e) {
    e.preventDefault(); // Prevent default form submission
    var formData = $(this).serialize(); // Serialize form data
    $.ajax({
        url: 'login.php',
        type: 'POST',
        data: formData, // Send form data
        success: function(response) {
            // Handle login response
            // For example, redirect to appropriate page based on role
            if (response.success) {
                switch (response.role) {
                    case 'admin':
                        window.location.href = 'admin/index.php';
                        break;
    
                    default:
                        console.error('Invalid role:', response.role);
                }
            } else{
                alert('Invalid Login Information');
            }
        },
        error:function(xhr, status, error) {
            console.error('Error',error);
            // body...
        }
    });
});

function validateLoginForm(){
    var username = document.getElementById("username").value;
    var password = document.getElementById("password").value;

    if (username.trim()==="") {
        alert("Please Enter Your Correct Username");
        return;
    }
    if (password.trim()==="") {
        alert("Please Enter Your Correct Password");
        return;
    }
    document.getElementById("loginForm").submit();
}