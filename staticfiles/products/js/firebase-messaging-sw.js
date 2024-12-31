importScripts('https://www.gstatic.com/firebasejs/9.6.10/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/9.6.10/firebase-messaging.js');

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
    console.log('Received background message: ', payload);
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: payload.notification.icon
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
});
