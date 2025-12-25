const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')

const createWindow = () => {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    fullscreenable: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  })

  win.setMenuBarVisibility(false)
  win.loadFile('./js/app/index.html')

  // Open dev tools with Ctrl+Shift+I (or Cmd+Option+I on macOS)
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

// Very buggy fullscreen toggle workaround due to electron issues
let IS_TOGGLING_FULLSCREEN = false;
// Handle IPC messages from the renderer process
ipcMain.handle('toggleFullScreen', () => {
  if (IS_TOGGLING_FULLSCREEN) {return;}
  IS_TOGGLING_FULLSCREEN = true;
  const win = BrowserWindow.getFocusedWindow();
  const target = !win.isFullScreen();
  if (win && target) {
    win.setFullScreen(target);
    setTimeout(() => {
        win.setFullScreen(!win.isFullScreen());
        win.setFullScreen(target);
        IS_TOGGLING_FULLSCREEN = false;
    }, 300);
  } else if (win) {
    win.setFullScreen(target);
    // Delay resize to allow fullscreen exit to complete
    setTimeout(() => {
      win.setSize(1200, 800);
      IS_TOGGLING_FULLSCREEN = false;
    }, 100);
  }
});

ipcMain.on('openDevTools', () => {
  const win = BrowserWindow.getFocusedWindow();
  if (win) {
    win.webContents.openDevTools();
  }
});

ipcMain.on('closeApp', () => {
  app.quit();
});