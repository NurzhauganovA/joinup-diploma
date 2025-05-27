const inputs = document.querySelectorAll('.otp-card-inputs input');
const button = document.querySelector('.button_block_login_container button');


inputs.forEach(input => {
    let lastInputStatus = 0;
    input.onkeyup = (event) => {
        const currentElement = event.target;
        const nextElement = input.nextElementSibling;
        const prevElement = input.previousElementSibling;

        if (prevElement && event.keyCode === 8) {
            if (lastInputStatus === 1) {
                prevElement.value = '';
                prevElement.focus();
            }
            button.setAttribute('disabled', true);
            lastInputStatus = 1;
        }
        else {
            const reg = /^[0-9]+$/;
            if (!reg.test(currentElement.value)) {
                currentElement.value = currentElement.value.replace(/\D/g, '');
            }
            else if (currentElement.value) {
                if (nextElement) {
                    nextElement.focus();
                }
                else {
                    button.removeAttribute('disabled');
                    lastInputStatus = 0;
                }
            }
        }
    }
});
