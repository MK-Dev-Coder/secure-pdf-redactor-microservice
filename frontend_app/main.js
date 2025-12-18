const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const axios = require('axios');

function createWindow() {
    const win = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false 
        }
    });

    win.loadFile('index.html');
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

ipcMain.handle('redact-text', async (event, text) => {
    try {
        // In a real scenario with Consul, we would query Consul for the service URL first.
        // For Part A dev, we might hardcode or use an env var.
        // Let's assume localhost:8000 for now.
        const serviceUrl = 'http://127.0.0.1:8000/redact';
        
        const response = await axios.post(serviceUrl, { text });
        const data = response.data;

        if (!data.pdf_base64) {
            throw new Error('Invalid response from service');
        }

        const pdfBuffer = Buffer.from(data.pdf_base64, 'base64');

        const { filePath } = await dialog.showSaveDialog({
            buttonLabel: 'Save PDF',
            defaultPath: 'redacted.pdf',
            filters: [{ name: 'PDF', extensions: ['pdf'] }]
        });

        if (filePath) {
            fs.writeFileSync(filePath, pdfBuffer);
            return { success: true, path: filePath };
        }
        return { success: false, message: 'Cancelled' };
    } catch (error) {
        console.error(error);
        return { success: false, error: error.message };
    }
});
