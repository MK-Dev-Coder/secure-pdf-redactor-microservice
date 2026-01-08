# Microservices Coursework

## 🚀 Live Cloud Deployment
**Access the Secure Redactor App here:**  
👉 [https://frontend-web.gentlemeadow-2504a69e.italynorth.azurecontainerapps.io](https://frontend-web.gentlemeadow-2504a69e.italynorth.azurecontainerapps.io)

---

## Part A: Local Development (Electron + Python)

### Prerequisites
- Python 3.x
- Node.js & npm
- Consul (Optional for local dev)

### 1. Redaction Service (Python FastAPI)
Located in `redaction_service/`.

**Setup:**
```bash
cd redaction_service
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

**Run:**
```bash
python main.py
```
The service will start on `http://localhost:8000`.

### 2. Frontend App (Electron)
Located in `frontend_app/`.

**Setup:**
```bash
cd frontend_app
npm install
```

**Run:**
```bash
npm start
```
Enter text in the UI and click "Redact & Download PDF".

---

## Part B: Cloud Deployment (Docker Containers)

This setup uses Docker Compose to orchestrate the backend, a web-based frontend, and Consul.

### Services
1.  **Redaction Service**: Python FastAPI (Port 8000)
2.  **Frontend Web**: Node.js Express Web App (Port 3000)
3.  **Consul**: Service Discovery (Port 8500)

### Running with Docker Compose

**Build and Start:**
```bash
docker-compose up --build
```

**Access the Web App:**
Open your browser and go to: [http://localhost:3000](http://localhost:3000)

**Architecture:**
- The **Web Frontend** (Port 3000) serves the UI and proxies requests to the backend.
- The **Redaction Service** (Port 8000) handles the NLP processing.
- **Consul** (Port 8500) is available for service discovery.
