const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const fs = require('fs');
const os = require('os');

const CHARACTER_CACHE = {};

if (!fs.existsSync(path.join(app.getPath('home'), '.dreamengine'))) {
    fs.mkdirSync(path.join(app.getPath('home'), '.dreamengine'));
}

if (!fs.existsSync(path.join(app.getPath('home'), '.dreamengine', 'init-config.json'))) {
    fs.writeFileSync(path.join(app.getPath('home'), '.dreamengine', 'init-config.json'), JSON.stringify({
        fullscreen: false
    }));
}

const initconfig = JSON.parse(fs.readFileSync(path.join(app.getPath('home'), '.dreamengine', 'init-config.json')));

async function saveInitConfig() {
    await fs.promises.writeFile(path.join(app.getPath('home'), '.dreamengine', 'init-config.json'), JSON.stringify(initconfig));
}

const userDataPath = path.join(os.homedir(), '.dreamengine');
let userData = {};
try {
    userData = JSON.parse(fs.readFileSync(path.join(userDataPath, 'settings.json'), 'utf-8'));
} catch (e) { }


const createWindow = () => {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    fullscreenable: true,
    fullscreen: initconfig.fullscreen || false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
    },
  })

  win.setMenuBarVisibility(false)
  win.loadFile('./js/app/index.html')

  // Open dev tools with Ctrl+Shift+I (or Cmd+Option+I on macOS)
  // win.webContents.openDevTools();
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
// Handle IPC messages from the renderer process
ipcMain.handle('toggleFullScreen', () => {
  const win = BrowserWindow.getFocusedWindow();
  const target = !win.isFullScreen();
  if (win && target) {
    win.setFullScreen(target);
    initconfig.fullscreen = true;
    saveInitConfig();
  } else if (win) {
    win.setFullScreen(target);
    initconfig.fullscreen = false;
    saveInitConfig();
  }
});

ipcMain.on('openDevTools', () => {
  const win = BrowserWindow.getFocusedWindow();
  if (win) {
    win.webContents.openDevTools({ mode: 'detach' });
  }
});

ipcMain.on('closeApp', () => {
  app.quit();
});

ipcMain.handle('loadStringFromUserData', async (event, key, group, characterFile) => {
    const splitted = key.split(".");
    let current = userData;
    if (group && characterFile) {
        if (!CHARACTER_CACHE[group]) {
            CHARACTER_CACHE[group] = {};
        }
        let notFoundInCache = false;
        if (!CHARACTER_CACHE[group][characterFile]) {
            CHARACTER_CACHE[group][characterFile] = {};
            notFoundInCache = true;
        }
        if (notFoundInCache) {
            const CHARACTER_FOLDER = path.join(app.getPath('home'), '.dreamengine', 'characters');
            const filePath = path.join(CHARACTER_FOLDER, group, characterFile);
            if (fs.existsSync(filePath)) {
                const data = await fs.promises.readFile(filePath, 'utf-8');
                CHARACTER_CACHE[group][characterFile] = JSON.parse(data);
            }
        }
        current = CHARACTER_CACHE[group][characterFile] || {};
    }
    for (let i = 0; i < splitted.length; i++) {
        if (current[splitted[i]] === undefined) {
            return null;
        }
        current = current[splitted[i]];
    }
    return current || null;
});

ipcMain.handle('setStringIntoUserData', (event, key, group, characterFile, value) => {
    const splitted = key.split(".");
    let current = userData;
    if (group && characterFile) {
        if (!CHARACTER_CACHE[group]) {
            CHARACTER_CACHE[group] = {};
        }
        if (!CHARACTER_CACHE[group][characterFile]) {
            CHARACTER_CACHE[group][characterFile] = {};
        }
        current = CHARACTER_CACHE[group][characterFile];
    }
    for (let i = 0; i < splitted.length - 1; i++) {
        if (current[splitted[i]] === undefined) {
            current[splitted[i]] = {};
        }
        current = current[splitted[i]];
    }
    current[splitted[splitted.length - 1]] = value;
});

ipcMain.on('saveSettingsToDisk', () => {
    if (!fs.existsSync(userDataPath)) {
        fs.mkdirSync(userDataPath, { recursive: true });
    }
    fs.writeFileSync(path.join(userDataPath, 'settings.json'), JSON.stringify(userData, null, 2), 'utf-8');
});

const CHARACTER_FOLDER = path.join(app.getPath('home'), '.dreamengine', 'characters');
if (!fs.existsSync(CHARACTER_FOLDER)) {
    fs.mkdirSync(CHARACTER_FOLDER, { recursive: true });
}

async function createGroupIfNotExists(group) {
    const groupPath = path.join(CHARACTER_FOLDER, group);
    if (!fs.existsSync(groupPath)) {
        CHARACTER_CACHE[group] = {};
        await fs.promises.mkdir(groupPath, { recursive: true });
    }
}

// Character file management IPC handlers
ipcMain.handle('createEmptyCharacterFile', async () => {
    await createGroupIfNotExists('default');
    const filePath = path.join(CHARACTER_FOLDER, 'default', `unnamed_character_${Date.now()}.json`);
    await fs.promises.writeFile(filePath, JSON.stringify({}, null, 2), 'utf-8');
    CHARACTER_CACHE["default"] = CHARACTER_CACHE["default"] || {};
    CHARACTER_CACHE["default"][path.basename(filePath)] = {};
    return { group: 'default', characterFile: path.basename(filePath) };
});

ipcMain.handle('checkCharacterFileExists', async (event, group, characterFile) => {
    const filePath = path.join(CHARACTER_FOLDER, group, characterFile);
    return fs.existsSync(filePath);
});

ipcMain.handle('updateCharacterFileFromCache', async (event, originalGroup, originalCharacterFile, newCharacterFile) => {
    const currentData = CHARACTER_CACHE[originalGroup][originalCharacterFile]
    const newGroup = (currentData.group || "default").trim();
    if (originalGroup !== currentData.group) {
        await createGroupIfNotExists(newGroup);
    }
    const filePath = path.join(CHARACTER_FOLDER, newGroup, newCharacterFile);
    await fs.promises.writeFile(filePath, JSON.stringify(currentData, null, 2), 'utf-8');
    delete CHARACTER_CACHE[originalGroup]?.[originalCharacterFile];
    CHARACTER_CACHE[currentData.group] = CHARACTER_CACHE[currentData.group] || {};
    CHARACTER_CACHE[currentData.group][newCharacterFile] = currentData;
    return true;
});

ipcMain.handle("deleteCharacterFile", async (event, group, characterFile) => {
    const filePath = path.join(CHARACTER_FOLDER, group, characterFile);
    delete CHARACTER_CACHE[group]?.[characterFile];
    if (fs.existsSync(filePath)) {
        await fs.promises.unlink(filePath);
        return true;
    }
    return false;
});

ipcMain.handle("deleteAllCharacterFilesInGroup", async (event, group) => {
    const groupPath = path.join(CHARACTER_FOLDER, group);
    delete CHARACTER_CACHE[group];
    if (fs.existsSync(groupPath)) {
        const files = await fs.promises.readdir(groupPath);
        for (const file of files) {
            const filePath = path.join(groupPath, file);
            await fs.promises.unlink(filePath);
        }
        await fs.promises.rmdir(groupPath);
        return true;
    }
    return false;
});

ipcMain.handle('loadCharacterFile', async (event, group, characterFile) => {
    const filePath = path.join(CHARACTER_FOLDER, group, characterFile);
    CHARACTER_CACHE[group] = CHARACTER_CACHE[group] || {};
    if (CHARACTER_CACHE[group][characterFile]) {
        return CHARACTER_CACHE[group][characterFile];
    }
    if (fs.existsSync(filePath)) {
        const data = await fs.promises.readFile(filePath, 'utf-8');
        CHARACTER_CACHE[group][characterFile] = JSON.parse(data);
        return CHARACTER_CACHE[group][characterFile];
    }
    return null;
});

ipcMain.handle('listCharacterFiles', async (event, group) => {
    const groupPath = path.join(CHARACTER_FOLDER, group);
    if (fs.existsSync(groupPath)) {
        const files = await fs.promises.readdir(groupPath);
        return files.filter(file => file.endsWith('.json'));
    }
    return [];
});

ipcMain.handle('listCharacterGroups', async () => {
    const groups = await fs.promises.readdir(CHARACTER_FOLDER, { withFileTypes: true });
    return groups.filter(dirent => dirent.isDirectory()).map(dirent => dirent.name);
});