import { Clerk } from 'https://cdn.jsdelivr.net/npm/@clerk/clerk-js@5/dist/clerk.mjs';

const publishableKey = document.querySelector('meta[name="clerk-publishable-key"]')?.content;

if (!publishableKey) {
    console.warn('Clerk: missing publishable key. Run clerk env pull in churn-app.');
} else {
    const clerk = new Clerk(publishableKey);

    clerk.load().then(function () {
        updateNavAuth(clerk);

        clerk.addListener(function () {
            updateNavAuth(clerk);
        });

        var signInRoot = document.getElementById('clerk-sign-in-root');
        if (signInRoot) {
            clerk.mountSignIn(signInRoot, {
                routing: 'path',
                path: '/sign-in',
                signUpUrl: '/sign-up',
                afterSignInUrl: '/dashboard',
            });
        }

        var signUpRoot = document.getElementById('clerk-sign-up-root');
        if (signUpRoot) {
            clerk.mountSignUp(signUpRoot, {
                routing: 'path',
                path: '/sign-up',
                signInUrl: '/sign-in',
                afterSignUpUrl: '/dashboard',
            });
        }
    }).catch(function (err) {
        console.error('Clerk failed to load:', err);
    });
}

function updateNavAuth(clerk) {
    var signedOut = document.getElementById('clerk-signed-out');
    var signedIn = document.getElementById('clerk-signed-in');
    var userBtn = document.getElementById('clerk-user-button');

    if (!signedOut || !signedIn) return;

    if (clerk.user) {
        signedOut.classList.add('hidden');
        signedIn.classList.remove('hidden');
        if (userBtn && !userBtn.dataset.mounted) {
            clerk.mountUserButton(userBtn, {
                afterSignOutUrl: '/',
            });
            userBtn.dataset.mounted = '1';
        }
    } else {
        signedIn.classList.add('hidden');
        signedOut.classList.remove('hidden');
    }
}
