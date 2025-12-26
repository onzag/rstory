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
    },
    loadStringFromUserData: async (key, group, characterFile) => {
        const result = await ipcRenderer.invoke('loadStringFromUserData', key, group, characterFile);
        return result;
    },
    setStringIntoUserData: async (key, group, characterFile, value) => {
        await ipcRenderer.invoke('setStringIntoUserData', key, group, characterFile, value);
    },
    saveSettingsToDisk: () => {
        ipcRenderer.send('saveSettingsToDisk');
    },

    createEmptyCharacterFile: async () => {
        const result = await ipcRenderer.invoke('createEmptyCharacterFile');
        return result;
    },
    checkCharacterFileExists: async (group, characterFile) => {
        const result = await ipcRenderer.invoke('checkCharacterFileExists', group, characterFile);
        return result;
    },
    updateCharacterFileFromCache: async (originalGroup, originalCharacterFile, newCharacterFile) => {
        const result = await ipcRenderer.invoke('updateCharacterFileFromCache', originalGroup, originalCharacterFile, newCharacterFile);
        if (originalCharacterFile !== newCharacterFile || originalGroup !== newGroup) {
            await ipcRenderer.invoke('deleteCharacterFile', originalGroup, originalCharacterFile);
        }
        return result;
    },
    loadCharacterFile: async (group, characterFile) => {
        const result = await ipcRenderer.invoke('loadCharacterFile', group, characterFile);
        return result;
    },
    deleteCharacterFile: async (group, characterFile) => {
        const result = await ipcRenderer.invoke('deleteCharacterFile', group, characterFile);
        return result;
    },
    deleteAllCharacterFilesInGroup: async (group) => {
        const result = await ipcRenderer.invoke('deleteAllCharacterFilesInGroup', group);
        return result;
    },
    listCharacterFiles: async (group) => {
        const result = await ipcRenderer.invoke('listCharacterFiles', group);
        return result;
    },
    listCharacterGroups: async () => {
        const result = await ipcRenderer.invoke('listCharacterGroups');
        return result;
    },
});