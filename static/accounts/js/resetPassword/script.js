document.addEventListener("DOMContentLoaded", function () {
    let toastElList = [].slice.call(document.querySelectorAll('.toast'));
    let toastList = toastElList.map(function (toastEl) {
        return new bootstrap.Toast(toastEl, { delay: 3000 });
    });
    toastList.forEach(toast => toast.show());
});