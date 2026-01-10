const express = require('express');
const path = require('path');
const axios = require('axios');
const multer = require('multer');
const FormData = require('form-data');

const app = express();
const PORT = process.env.PORT || 3000;
const upload = multer({ storage: multer.memoryStorage() });

// Serve static files from 'public' directory
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// Define backend service URL, configurable via environment variables.
// Default configuration targets the docker-compose service entry.
// Use IPv4 loopback address to ensure compatibility across environments.
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

// Implement proxy endpoint to forward redaction requests to the backend service.
// Proxies requests to mitigate CORS restrictions and abstract backend logic.
app.post('/api/redact', async (req, res) => {
    try {
        console.log(`Forwarding request to: ${BACKEND_URL}/redact`);
        const response = await axios.post(`${BACKEND_URL}/redact`, req.body);
        
        const data = response.data;
        if (data.pdf_base64) {
            const pdfBuffer = Buffer.from(data.pdf_base64, 'base64');
            
            // Forward the PDF back to the client
            res.set('Content-Type', 'application/pdf');
            res.set('Content-Disposition', 'attachment; filename="redacted.pdf"');
            res.send(pdfBuffer);
        } else {
             throw new Error('Invalid response format from backend');
        }
    } catch (error) {
        console.error('Backend error:', error.message);
        if (error.code === 'ECONNREFUSED') {
             res.status(503).json({ error: 'Redaction service is unavailable.' });
        } else {
             res.status(500).json({ error: 'Failed to process request.' });
        }
    }
});

app.post('/api/redact/pdf', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }

        console.log(`Forwarding PDF to: ${BACKEND_URL}/redact/pdf`);
        
        const form = new FormData();
        form.append('file', req.file.buffer, req.file.originalname);

        const response = await axios.post(`${BACKEND_URL}/redact/pdf`, form, {
            headers: {
                ...form.getHeaders()
            }
        });
        
        const data = response.data;
        if (data.pdf_base64) {
            const pdfBuffer = Buffer.from(data.pdf_base64, 'base64');
            res.set('Content-Type', 'application/pdf');
            res.set('Content-Disposition', 'attachment; filename="redacted.pdf"');
            res.send(pdfBuffer);
        } else {
             throw new Error('Invalid response format from backend');
        }
    } catch (error) {
        console.error('Backend error:', error.message);
        res.status(500).json({ error: 'Failed to process PDF.' });
    }
});

// Proxy for stats
app.get('/api/stats', async (req, res) => {
    try {
        const response = await axios.get(`${BACKEND_URL}/stats`);
        res.json(response.data);
    } catch (error) {
         console.error('Stats error:', error.message);
         res.status(500).json({ error: 'Failed to fetch stats.' });
    }
});

app.listen(PORT, () => {
    console.log(`Web frontend running on http://localhost:${PORT}`);
});
