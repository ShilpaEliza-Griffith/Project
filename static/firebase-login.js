'use strict';

import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.2/firebase-app.js";
import { getAuth, createUserWithEmailAndPassword , signInWithEmailAndPassword, signOut} from "https://www.gstatic.com/firebasejs/9.22.2/firebase-auth.js";

console.log("test");

const firebaseConfig = {
  };

  window.addEventListener("load", function () {
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    updateUI(document.cookie);

    document.getElementById("sign-up").addEventListener('click', function () {
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;

        createUserWithEmailAndPassword(auth, email, password).then ((userCredential) => {
            const user =userCredential.user;
            console.log(user);

            user.getIdToken().then((token) => {
                console.log(token)
                document.cookie = "token" + token + ";path=/;SameSite=Strict";
                window.location = "/" ;
            });
        })
        .catch((error) => {
            console.log(error.code + ":" + error_message);
        })

    });
 

  document.getElementById("login").addEventListener('click', function () {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    signInWithEmailAndPassword(auth, email, password)
    .then((userCredential) => {
            const user =userCredential.user;
            console.log("Logged in");
            
            user.getIdToken().then((token) => {
                document.cookie = "token" + token + ";path=/;SameSite=Strict";
                window.location = "/" ;
            });
    })

    .catch((error) => {
        console.log(error.code + ":" + error.message);
    });
  });

  document.getElementById("sign-out").addEventListener('click', function () {
    signOut(auth)
    .then((output) => {
        document.cookie = 'token=;path=/;SameSite=Strict';
        window.location = "/";
    });
  });
  function updateUI(cookie) {
    var token = parseCookieToken(cookie);
    console.log(token);
    if (token.length > 0) {
        document.getElementById("login-box").hidden = true;
        document.getElementById("sign-out").hidden = false;
    } else {
        document.getElementById("login-box").hidden = false;
        document.getElementById("sign-out").hidden = true;
    }
  };
  function parseCookieToken(cookie) {
    console.log(cookie);
    
    var strings = cookie.split(';');
    console.log(strings);

    for (let i = 0; i < strings.length; i++) {
        var temp = strings[i].split('=');
        if(temp[0] =="token" )
            return temp[1];
    }
    return "";
  }
});