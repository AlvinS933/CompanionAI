import { app, BrowserWindow, screen, ipcMain } from 'electron';
import { spawn } from 'child_process';
import path from 'path';



app.whenReady().then(() => {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  const preloadPath = path.join(app.getAppPath(), '.vite/build/preload.js');

  // 1. Launch the Python PyQt6 UI
  const uiProcess = spawn('python', [path.join(app.getAppPath(), 'pythonUI/Jinx_ui.py')], {
    stdio: ['pipe', 'pipe', 'inherit'],
  });

  // 2. Launch the AI Agent
  const pythonProcess = spawn('python', [path.join(app.getAppPath(), 'AI/agent.py')], {
    stdio: ['pipe', 'pipe', 'inherit'],
  });

  // Handle AI responses - Logging to console
  let buffer = '';
  pythonProcess.stdout.on('data', (chunk: Buffer) => {
    buffer += chunk.toString();
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      const text = line.trim();
      if (!text || text === 'You:') continue;
      console.log(`AI: ${text}`); // See responses in your terminal
      uiProcess.stdin.write(text + '\n');
    }
  });

  // Listen to the UI process for events
  uiProcess.stdout.on('data', (data) => {
    const msg = data.toString().trim();
    
    if (msg === "EVENT:DRAGGED") {
      // Translate the physical action into a text prompt for the AI
      const prompt = "*The user is dragging you across the desktop screen*";
      
      // Push this into the agent's stdin just like a user message
      pythonProcess.stdin.write(prompt + '\n');
    }
  });


  ipcMain.on('user-message', (_event, text: string) => {
    pythonProcess.stdin.write(text + '\n');
  });

  ipcMain.on('quit-app', () => {
    pythonProcess.kill();
    uiProcess.kill();
    app.quit();
  });

  // Fine-grained toggle from the pull-tab hover
  ipcMain.on('set-ignore-mouse', (_event, ignore: boolean) => {
    mainWindow.setIgnoreMouseEvents(ignore, { forward: true });
  });

    // 3. Frameless, transparent overlay window pinned to the bottom of the screen
  const panelHeight = 300; // max expanded height of the chat panel
  const panelWidth = 640;  // matches max-width in index.html
 
  const mainWindow = new BrowserWindow({
    x: Math.round((width - panelWidth) / 2),
    y: height - panelHeight,
    width: panelWidth,
    height: panelHeight,
    frame: false,
    transparent: true,
    hasShadow: false,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    type: 'toolbar',
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
 
  mainWindow.loadURL('http://localhost:5173');
 
  // Let clicks pass through the transparent portions of the window
  mainWindow.setIgnoreMouseEvents(true, { forward: true });
  // If you want click-through on the transparent bg, use:
  // mainWindow.setIgnoreMouseEvents(true, { forward: true });
  // and toggle it off via IPC when the panel is open
 


  mainWindow.on('closed', () => {
    pythonProcess.kill();
    uiProcess.kill();
    app.quit();
  });
});