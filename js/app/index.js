// import dialog
import './components/dialog.js';

// Sound effects
const hoverSound = document.getElementById('hoverSound');
const confirmSound = document.getElementById('confirmSound');
const cancelSound = document.getElementById('cancelSound');
const pauseSound = document.getElementById('pauseSound');

function playHoverSound() {
  hoverSound.currentTime = 0;
  hoverSound.play().catch(err => console.log('Hover sound play failed:', err));
}

function playConfirmSound() {
  confirmSound.currentTime = 0;
  confirmSound.play().catch(err => console.log('Confirm sound play failed:', err));
}

function playCancelSound() {
  cancelSound.currentTime = 0;
  cancelSound.play().catch(err => console.log('Cancel sound play failed:', err));
}

function playPauseSound() {
  pauseSound.currentTime = 0;
  pauseSound.play().catch(err => console.log('Pause sound play failed:', err));
}

let HAS_ACTIVE_DIALOG = false;
function exitGame() {
    HAS_ACTIVE_DIALOG = true;
    const dialog = document.createElement('app-dialog');
    dialog.setAttribute('dialog-title', 'Are you sure you want to exit?');
    dialog.setAttribute("confirmation", "true");
    dialog.setAttribute("confirm-text", "Exit");
    dialog.setAttribute("cancel-text", "Cancel");
    dialog.addEventListener('confirm', () => {
        if (window.electronAPI) {
            window.electronAPI.closeApp();
        } else {
            window.close();
        }
    });
    dialog.addEventListener('cancel', () => {
        document.body.removeChild(dialog);
        HAS_ACTIVE_DIALOG = false;
    });
    document.body.appendChild(dialog);
}

// Get all menu buttons and add event listeners
const buttons = document.querySelectorAll('.menu-btn');
buttons.forEach(button => {
  button.addEventListener('mouseenter', playHoverSound);
});

const exitBtn = document.getElementById('exit-btn');
exitBtn.addEventListener('click', function() {
    exitGame();
});

// Get all footer links and add event listeners
const footerLinks = document.querySelectorAll('.footer a');
footerLinks.forEach(link => {
  link.addEventListener('mouseenter', playHoverSound);
  link.addEventListener('click', function() {
    playConfirmSound();
  });
});

// Toggle full screen on alt+Enter
document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.altKey) {
        window.electronAPI?.toggleFullScreen();
        // Force focus on body to trigger repaint
        
    }
    if (e.key === "F12") {
        window.electronAPI?.openDevTools();
    }
    if (e.key === "Escape" && !HAS_ACTIVE_DIALOG) {
        exitGame();
    }
});