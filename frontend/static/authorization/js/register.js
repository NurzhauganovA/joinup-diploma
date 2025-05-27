let passwordInput = document.querySelector('#password-input');
let dropdownMenus = document.querySelectorAll('.dropdown_menu');


function checkPassword() {
    let password = passwordInput.value;

    let conditions = [
        password.length >= 8,
        /\d/.test(password),
        /[a-z]/i.test(password),
        /\W/.test(password)
    ];

    dropdownMenus.forEach(function(menu) {
        menu.classList.remove('active');
    });

    let conditionCount = 0;

    for (let i = 0; i < conditions.length; i++) {
        if (conditions[i]) {
            if (conditionCount < dropdownMenus.length) {
                dropdownMenus[conditionCount].classList.add('active');
                conditionCount++;
            }
        }
    }
}


passwordInput.addEventListener('input', checkPassword);