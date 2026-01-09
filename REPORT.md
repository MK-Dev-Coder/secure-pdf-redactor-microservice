# Microservices Implementation and Cloud Deployment Report

## Executive Summary

This report documents the design, implementation, and deployment of a secure microservices-based application for document redaction. The system is designed to identify and mask Personally Identifiable Information (PII) such as names, email addresses, and street addresses from text and PDF documents. The solution adopts a distributed architecture utilizing a Python FastAPI backend (Producer) and a Node.js Express frontend (Consumer), orchestrated via Consul for service discovery.

The project fulfills two key phases: Part A focuses on the local development of RESTful microservices and their interaction, while Part B addresses containerization, cloud clustering on Azure, scaling strategies, and advanced CI/CD implementation including rolling updates.

---

## Part A: Microservices Development

### 1. System Architecture
The application follows a decoupled microservices pattern, ensuring separation of concerns between the user interface and the core processing logic.

*   **Producer Service (Redaction Service)**: A Python-based REST API built with FastAPI. It handles the CPU-intensive tasks of Natural Language Processing (NLP) and Optical Character Recognition (OCR).
*   **Consumer Service (Web Frontend)**: A Node.js Express application that serves the user interface and acts as an API gateway, forwarding user requests to the producer.
*   **Service Discovery**: HashiCorp Consul is employed to manage service registration, allowing dynamic discovery of the backend service without hardcoded IP addresses.

### 2. Service Discovery Implementation
To satisfy the requirement for dynamic service location, the Redaction Service integrates with **Consul**. 

On application startup, the service utilizes the `python-consul2` library to register itself with the Consul agent. The registration process involves:
1.  **Health Check**: Providing a route (root `/`) that Consul can ping to verify the service status.
2.  **Metadata Registration**: The service registers with a request ID, IP address, and port (8000).
3.  **Tags**: The service applies tags such as `"redaction"` and `"pdf"` to facilitate filtering during discovery.

This mechanism ensures that if the Producer service is scaled or moved to a different host, the Consumer (or the load balancer in a cluster context) can automatically resolve the new location.

### 3. Producer Service: Business Logic and Controllers
The core "business logic" is encapsulated within the `redaction_service`. The service exposes RESTful endpoints using **FastAPI**, which provides automatic validation via Pydantic models.

#### 3.1 Controllers
The service implements two primary controllers for redaction:

*   **`POST /redact`**: Accepts raw text input. It returns a JSON object containing the base64-encoded PDF of the redacted text.
*   **`POST /redact/pdf`**: Accepts a binary PDF file upload. It returns a redacted PDF file.

#### 3.2 Implemented Logic
The redaction logic is robust, employing a hybrid approach of Regular Expressions (Regex) and Machine Learning (NLP):

*   **Pattern Matching**: Regex is used for strictly structured data.
    *   *Emails*: Matches standard email formats (e.g., `user@domain.com`).
    *   *Street Addresses*: Identifies patterns starting with digits followed by street suffixes (e.g., "123 Main St", "Baker Avenue").
*   **Natural Language Processing (NLP)**: The **SpaCy** library with the `en_core_web_sm` model is utilized for Named Entity Recognition (NER).
    *   *Names*: Entities labeled as `PERSON` are identified.
    *   *Locations*: Entities labeled as `GPE` (Geopolitical Entity) or `LOC` are identified.
*   **Visual Redaction (PDF Processing)**: Unlike simple text overlay, the service performs true visual redaction on uploaded PDFs.
    1.  **Conversion**: The PDF is converted into images using `pdf2image`.
    2.  **OCR**: Tesseract OCR scans the images to locate the coordinates (bounding boxes) of sensitive words.
    3.  **Drawing**: Implementation uses the `Pillow` library to draw solid black rectangles over the identified coordinates, ensuring the information is visually and digitally irretrievable.

### 4. Consumer Microservice
The `frontend_web` service acts as the client-facing component. It is built using **Node.js** and **Express**.

*   **User Interface**: A responsive HTML/CSS interface allows users to input text or upload files. It includes accessibility features and theme customization (e.g., "Stars" or "Meme" backgrounds).
*   **Proxy Logic**: The Express server implements an API proxy pattern. When the browser sends a request to `/api/redact`, the Express server forwards this request to the backend service. This solves Cross-Origin Resource Sharing (CORS) issues and hides the backend infrastructure from the public internet.
*   **Response Handling**: The consumer receives the base64 encoded PDF from the producer, decodes the buffer, and triggers a browser download for the user.

---

## Part B: Cloud Deployment and Advanced Features

### 5. Containerization
Both microservices are containerized using **Docker** to ensure consistency across development and production environments.

*   **Redaction Service Dockerfile**: Uses a lightweight Python 3.12-slim base image. Crucially, it installs system-level dependencies required for image processing (`tesseract-ocr`, `poppler-utils`, `libgl1`) before installing Python requirements via `pip`.
*   **Frontend Dockerfile**: Uses a Node.js Alpine image for minimal footprint. It installs dependencies defined in `package.json` and exposes port 3000.
*   **Orchestration**: A `docker-compose.yml` file defines the multi-container setup, linking the Producer, Consumer, and a Consul agent on a shared network. This allows for simple "one-command" local execution (`docker-compose up`).

### 6. Cluster Creation and Scaling
The project is deployed to **Azure Kubernetes Service (AKS)**, providing a fully managed, production-grade Kubernetes cluster.

*   **Cluster Infrastructure**:
    To fulfill the coursework requirement for *at least 2 nodes*, a dedicated AKS cluster was provisioned with a **2-node pool** (Virtual Machine Scale Set). This infrastructure provides physical isolation and redundancy for the microservices.
    
    *   **Registry**: An Azure Container Registry (ACR) integrates directly with the cluster for secure image pulling.
    *   **Deployment**: A GitHub Actions pipeline builds Docker images and deploys standard Kubernetes manifests (`Deployment` and `Service` YAMLs) to the cluster.

*   **Scaling Strategy**: 
    The `redaction-service` is explicitly configured for high availability using a Kubernetes **Deployment** with **3 replicas**.
    
    ```yaml
    spec:
      replicas: 3
    ```

    The Kubernetes scheduler automatically distributes these 3 pods across the 2 available nodes. This ensures that if one node fails or experiences high load, the application remains available, satisfying the "scale up" requirement.

### 7. Hashing and HATEOAS
To meet the requirements for advanced API maturity, the application implements Level 3 of the Richardson Maturity Model (Hypermedia Controls).

#### 7.1 Hashing Functionality
A dedicated endpoint `POST /hash` was added to the microservice. 
*   **Input**: JSON object containing text.
*   **Process**: Computes the SHA-256 hash of the input text.
*   **Output**: Returns the hexadecimal hash string. This functionality allows users to verify data integrity or generate unique signatures for documents.

#### 7.2 HATEOAS Implementation
Hypermedia as the Engine of Application State (HATEOAS) is implemented in the primary redaction endpoint. When a user successfully requests a redaction (`POST /redact`), the response body includes not just the result, but also navigational links (`_links`).

**Example Response:**
```json
{
    "message": "Redaction successful",
    "pdf_base64": "JVBERi0x...",
    "_links": {
        "self": {
            "href": "/redact", 
            "method": "POST"
        },
        "hash": {
            "href": "/hash", 
            "method": "POST",
            "title": "Generate Hash of content"
        }
    }
}
```
This informs the client that a related action (hashing) is available, adhering to RESTful verification standards.

### 8. CI/CD and Rolling Updates
Automation is handled via **GitHub Actions** in the `.github/workflows/azure-deploy.yml` file.

#### 8.1 Continuous Integration
Every push to the `main` branch triggers the pipeline:
1.  **Testing**: Unit tests (`pytest`) are executed against the Python backend to ensure logic integrity.
2.  **Building**: Docker images are built for both services, tagged with the unique Git SHA (for versioning) and `latest`.

#### 8.2 Rolling Update Strategy
The deployment utilizes the native **Kubernetes Rolling Update** strategy, which is the default behavior for Kubernetes Deployments.

When the CI/CD pipeline applies a new image tag (via `kubectl apply`):
1.  **New ReplicaSet**: Kubernetes creates a new ReplicaSet for the new version.
2.  **Surge/Unavailable**: It spins up new pods (e.g., 1 at a time) and waits for their Readiness Probes (`/health`) to pass.
3.  **Traffic Shift**: Once a new pod is ready, the Service starts sending traffic to it.
4.  **Termination**: It simultaneously spins down old pods.

This guarantees zero downtime during updates (like the "Meme" theme deployment) and ensures that bad updates are not fully rolled out if the health checks fail.

---

## Conclusion
The developed solution successfully demonstrates a comprehensive microservices lifecycle. By combining robust backend processing (OCR/NLP) with a native **Kubernetes (AKS)** cluster deployment, the project satisfies the functional requirements of data security while adhering to strict infrastructure requirements (2-node cluster, 3-replica scaling). The implementation validates the ability to orchestrate complex distributed systems in the cloud.
