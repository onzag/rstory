const { contextBridge, ipcRenderer } = require('electron');

// create methods to communicate with the renderer process
// using ipcMain and ipcRenderer if needed
contextBridge.exposeInMainWorld('electronAPI', {
  toggleFullScreen: () => {
    console.log("Toggling full screen");
    ipcRenderer.invoke('toggleFullScreen');
  },
  openDevTools: () => {
    ipcRenderer.send('openDevTools');
  },
  closeApp: () => {
    ipcRenderer.send('closeApp');
  }
});