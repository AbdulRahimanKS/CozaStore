importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.10.0/firebase-messaging.js');

const firebaseConfig = {
    apiKey: "AIzaSyCu4u-B2epQV_EI3ydVh2xJR2EqcI3ExMM",
    authDomain: "cozastore-project-7a992.firebaseapp.com",
    projectId: "cozastore-project-7a992",
    storageBucket: "cozastore-project-7a992.appspot.com",
    messagingSenderId: "687617207315",
    appId: "1:687617207315:web:b10aff8c6b5b0e124fa3e6",
    measurementId: "G-QBQDVC2W6G"
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: payload.notification.icon || 'https://w7.pngwing.com/pngs/55/409/png-transparent-product-notification-message-reminder-alert-attention-in-stock-online-shopping-fill-shoppers-features-icon.png'
    };
    self.registration.showNotification(notificationTitle, notificationOptions);
});


