import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('companion', {
  sendMessage: (text: string) => ipcRenderer.send('user-message', text),
  onResponse: (cb: (text: string) => void) =>
    ipcRenderer.on('ai-response', (_event, text) => cb(text)),
  quit: () => ipcRenderer.send('quit-app'),

  // Tell main process whether the panel is open (disables/enables click-through)
  setPanelOpen: (open: boolean) =>
    ipcRenderer.send(open ? 'panel-open' : 'panel-close'),

  // Fine-grained control for the pull-tab hover effect
  setIgnoreMouse: (ignore: boolean) =>
    ipcRenderer.send('set-ignore-mouse', ignore),
});