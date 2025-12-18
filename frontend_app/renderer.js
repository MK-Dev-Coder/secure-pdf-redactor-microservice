const { ipcRenderer } = require('electron');

document.getElementById('submitBtn').addEventListener('click', async () => {
    const text = document.getElementById('inputText').value;
    if (!text) return;

    const statusDiv = document.getElementById('status');
    
    // Reset classes
    statusDiv.className = '';
    statusDiv.classList.add('status-loading');
    statusDiv.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';

    const result = await ipcRenderer.invoke('redact-text', text);

    statusDiv.className = ''; // Clear loading class

    if (result.success) {
        if (result.path) {
            statusDiv.classList.add('status-success');
            statusDiv.innerHTML = `<i class="fa-solid fa-check-circle"></i> Success! Saved to: <strong>${result.path}</strong>`;
        } else {
            statusDiv.classList.add('status-error'); //  Or neutral
            statusDiv.innerHTML = '<i class="fa-solid fa-circle-info"></i> Save cancelled.';
        }
    } else {
        statusDiv.classList.add('status-error');
        statusDiv.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Error: ${result.error}`;
    }
});
