document.getElementById('submitBtn').addEventListener('click', async () => {
    const text = document.getElementById('inputText').value;
    const fileInput = document.getElementById('inputFile');
    const file = fileInput.files[0];
    const statusDiv = document.getElementById('status');

    if (!text && !file) {
        showStatus('Please enter text OR upload a PDF file.', 'error');
        return;
    }

    showStatus('Processing redaction...', 'loading');

    try {
        let response;

        if (file) {
            const formData = new FormData();
            formData.append('file', file);
            
            response = await fetch('/api/redact/pdf', {
                method: 'POST',
                body: formData
            });
        } else {
            response = await fetch('/api/redact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text: text })
            });
        }

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Redaction failed');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'redacted_document.pdf';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        showStatus('Redaction complete! PDF downloaded.', 'success');
    } catch (error) {
        console.error('Error:', error);
        showStatus(`Error: ${error.message}`, 'error');
    }
});

function showStatus(message, type) {
    const statusDiv = document.getElementById('status');
    statusDiv.textContent = message;
    statusDiv.className = ''; // Reset classes
    
    if (type === 'success') {
        statusDiv.classList.add('status-success');
        statusDiv.innerHTML = `<i class="fa-solid fa-check-circle"></i> ${message}`;
    } else if (type === 'error') {
        statusDiv.classList.add('status-error');
        statusDiv.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> ${message}`;
    } else if (type === 'loading') {
        statusDiv.classList.add('status-loading');
        statusDiv.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${message}`;
    }
    
    statusDiv.style.display = 'flex';
}

// Settings & Theme Logic
const settingsBtn = document.getElementById('settingsBtn');
const settingsDropdown = document.getElementById('settingsDropdown');

// Toggle Dropdown
settingsBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    settingsDropdown.classList.toggle('show');
});

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    if (!settingsBtn.contains(e.target) && !settingsDropdown.contains(e.target)) {
        settingsDropdown.classList.remove('show');
    }
});

// Theme Management
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    settingsDropdown.classList.remove('show');
}

// Load saved theme
const savedTheme = localStorage.getItem('theme') || 'light';
setTheme(savedTheme);
