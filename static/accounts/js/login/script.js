document.addEventListener("DOMContentLoaded", function () {
    let toastElList = [].slice.call(document.querySelectorAll('.toast'));
    let toastList = toastElList.map(function (toastEl) {
        return new bootstrap.Toast(toastEl, { delay: 3000 });
    });
    toastList.forEach(toast => toast.show());
});

function togglePassword() {
    let passwordInput = document.getElementById("pwd");
    let showPasswordCheckbox = document.getElementById("show-password");

    if (showPasswordCheckbox.checked) {
        passwordInput.type = "text";
    } else {
        passwordInput.type = "password";
    }
}