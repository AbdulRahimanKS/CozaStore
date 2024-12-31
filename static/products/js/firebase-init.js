// firebase-init.js
import { initializeApp } from 'https://www.gstatic.com/firebasejs/11.0.1/firebase-app.js';
import { getMessaging, getToken, onMessage } from 'https://www.gstatic.com/firebasejs/11.0.1/firebase-messaging.js';

const firebaseConfig = {
    apiKey: "AIzaSyCu4u-B2epQV_EI3ydVh2xJR2EqcI3ExMM",
    authDomain: "cozastore-project-7a992.firebaseapp.com",
    projectId: "cozastore-project-7a992",
    storageBucket: "cozastore-project-7a992.appspot.com",
    messagingSenderId: "687617207315",
    appId: "1:687617207315:web:b10aff8c6b5b0e124fa3e6",
    measurementId: "G-QBQDVC2W6G"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

// Request permission to show notifications
function requestPermission() {
    Notification.requestPermission().then((permission) => {
        if (permission === 'granted') {
            console.log('Notification permission granted.');
            getToken(messaging, { vapidKey: 'BDm5qBd9dM-HsaSvqmRbnRfQl0J0t7jPScaGGu-C2x86nDppo2l-GM2HBygKNSy6vycxjn-LTbD-nndXDv2zPBg' }).then((currentToken) => {
                if (currentToken) {
                    console.log('Token received:', currentToken);
                }
            }).catch((err) => {
                console.log('An error occurred while retrieving token. ', err);
            });
        } else {
            console.log('Unable to get permission to notify.');
        }
    });
}

requestPermission();

onMessage(messaging, (payload) => {
    console.log('Message received. ', payload);
    const notificationTitle = payload.notification.title;
    const notificationOptions = {
        body: payload.notification.body,
        icon: '/firebase-logo.png'
    };

    new Notification(notificationTitle, notificationOptions);
});
