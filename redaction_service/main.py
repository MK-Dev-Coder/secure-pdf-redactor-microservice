from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from fpdf import FPDF
from pypdf import PdfReader
import io
import re
import consul
import socket
import os
import uuid
import spacy
import hashlib
import base64
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import pytesseract
from pytesseract import Output
from pdf2image import convert_from_bytes
from PIL import Image, ImageDraw

app = FastAPI()

# Database Setup (SQLite)
DATABASE_URL = "sqlite:///./redaction.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Model
class RedactionLog(Base):
    __tablename__ = "redaction_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    request_type = Column(String)  # 'text' or 'pdf'
    item_count = Column(Integer)   # Length of text or number of pages

# Create Tables
Base.metadata.create_all(bind=engine)

# Load SpaCy Model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading language model...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Consul Configuration
CONSUL_HOST = os.getenv("CONSUL_HOST", "localhost")
CONSUL_PORT = int(os.getenv("CONSUL_PORT", 8500))
SERVICE_NAME = "redaction-service"
SERVICE_PORT = 8000

def register_service():
    try:
        c = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)
        # Get local IP - in a real container setup, this might need adjustment
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        
        c.agent.service.register(
            name=SERVICE_NAME,
            service_id=f"{SERVICE_NAME}-{uuid.uuid4()}",
            address=ip_address,
            port=SERVICE_PORT,
            tags=["redaction", "pdf"]
        )
        print(f"Registered {SERVICE_NAME} with Consul")
    except Exception as e:
        print(f"Failed to register with Consul: {e}")

@app.on_event("startup")
async def startup_event():
    register_service()

class TextRequest(BaseModel):
    text: str

class HashRequest(BaseModel):
    text: str

@app.post("/hash")
async def hash_text(request: HashRequest):
    # Create SHA256 hash
    hash_object = hashlib.sha256(request.text.encode())
    hex_dig = hash_object.hexdigest()
    return {"hash": hex_dig}

def redact_text(text: str) -> str:
    # Redaction Logic
    
    # 1. Email Addresses (Regex is usually better/faster for strict patterns like email)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    text = re.sub(email_pattern, '[REDACTED EMAIL]', text)
    
    # 2. Street Addresses (Regex Heuristic)
    address_pattern = r'\b\d+\s+[A-Za-z0-9\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Court|Ct|Plaza|Plz)\b'
    text = re.sub(address_pattern, '[REDACTED ADDRESS]', text, flags=re.IGNORECASE)
    
    # 3. Names and Locations (Using SpaCy NLP)
    doc = nlp(text)
    
    # We need to replace entities. To avoid messing up indices while replacing,
    # we can rebuild the string or replace from end to start.
    # A simple way is to replace the text of the entity.
    
    # Filter for PERSON (Names) and GPE (Cities, States, Countries) entities
    entities_to_redact = [ent for ent in doc.ents if ent.label_ in ["PERSON", "GPE"]]
    
    # Sort entities by start position in descending order to replace from end to start
    entities_to_redact.sort(key=lambda x: x.start_char, reverse=True)
    
    for ent in entities_to_redact:
        start = ent.start_char
        end = ent.end_char
        replacement = "[REDACTED NAME]" if ent.label_ == "PERSON" else "[REDACTED LOCATION]"
        text = text[:start] + replacement + text[end:]
    
    return text

@app.post("/redact")
async def redact_and_pdf(request: TextRequest):
    redacted_content = redact_text(request.text)
    
    # Log to Database
    db = SessionLocal()
    try:
        log_entry = RedactionLog(request_type="text", item_count=len(request.text))
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        db.close()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, redacted_content)
    
    output_filename = f"redacted_{uuid.uuid4()}.pdf"
    pdf.output(output_filename)
    
    # Read file and encode to base64
    with open(output_filename, "rb") as f:
        pdf_data = f.read()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
    
    # Clean up file
    os.remove(output_filename)
    
    # HATEOAS Response
    return {
        "message": "Redaction successful",
        "pdf_base64": pdf_base64,
        "_links": {
            "self": {"href": "/redact", "method": "POST"},
            "hash": {"href": "/hash", "method": "POST"}
        }
    }

@app.post("/redact/pdf")
async def redact_pdf_file(file: UploadFile = File(...)):
    # Read the uploaded file
    content = await file.read()
    pdf_file = io.BytesIO(content)
    
    # Extract text from PDF
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    
    # Fallback to OCR if text is empty (Scanned PDF)
    if len(text.strip()) < 5:
        print("Standard extraction failed. Running OCR...")
        try:
            images = convert_from_bytes(content)
            redacted_images = []
            
            for img in images:
                # 1. Get OCR Data (Words + Coordinates)
                # Use PSM 11 (Sparse Text) to better detect spread out words/numbers
                custom_config = r'--psm 11'
                data = pytesseract.image_to_data(img, output_type=Output.DICT, config=custom_config)
                draw = ImageDraw.Draw(img)
                n_boxes = len(data['text'])
                
                # 2. Analyze Content for Sensitive Info
                # We reconstruct the text to run NLP on the full context
                # Note: This simple reconstruction might lose some spacing, but usually works for NER
                valid_words = [w for w in data['text'] if w.strip()]
                full_page_text = " ".join(valid_words)
                
                # Run NLP
                doc = nlp(full_page_text)
                sensitive_tokens = set()
                
                # Add Named Entities (Names, Locations)
                for ent in doc.ents:
                    if ent.label_ in ["PERSON", "GPE"]:
                        # Setup individual tokens for matching loop
                        for token in ent:
                            sensitive_tokens.add(token.text)
                
                # 3. Iterate and Redact
                for i in range(n_boxes):
                    word = data['text'][i].strip()
                    if not word: continue
                    
                    should_redact = False
                    
                    # Check Regex (Email)
                    if re.match(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}', word):
                        should_redact = True

                    # Check Regex (House Numbers / Phone portions)
                    # aggressive: redact matches for ANY digit sequence in images 
                    # This catches vertical numbers like "1", "0", "3", "5" often split by OCR
                    if re.match(r'^\d+$', word):
                        should_redact = True

                    # Check Regex (Address Context words)
                    if re.match(r'^(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Court|Ct|Plaza|Plz)$', word, re.IGNORECASE):
                        should_redact = True
                        
                    # Check NLP Match (Token based)
                    # We strip punctuation to match tokens like "Mike," -> "Mike"
                    clean_word = re.sub(r'[^\w\s]', '', word)
                    if word in sensitive_tokens or clean_word in sensitive_tokens:
                        should_redact = True
                    
                    if should_redact:
                        (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                        # Draw black box
                        draw.rectangle([x, y, x + w, y + h], fill="black")
                
                redacted_images.append(img)
            
            # Save images back to PDF
            pdf_bytes = io.BytesIO()
            if redacted_images:
                redacted_images[0].save(pdf_bytes, format='PDF', save_all=True, append_images=redacted_images[1:])
            pdf_bytes.seek(0)
            pdf_base64 = base64.b64encode(pdf_bytes.read()).decode('utf-8')
            
            return {
                "message": "PDF (OCR) Redaction successful",
                "pdf_base64": pdf_base64,
                "_links": {
                    "self": {"href": "/redact/pdf", "method": "POST"},
                    "hash": {"href": "/hash", "method": "POST"}
                }
            }

        except Exception as e:
            print(f"OCR Failed: {e}")
            # Fall through to standard text logic if OCR fails completely

    # Redact the extracted text
    redacted_content = redact_text(text)
    
    # Log to Database
    db = SessionLocal()
    try:
        log_entry = RedactionLog(request_type="pdf", item_count=len(reader.pages))
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        db.close()
    
    # Generate new PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Handle encoding for FPDF (standard font supports latin-1)
    safe_text = redacted_content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, safe_text)
    
    output_filename = f"redacted_{uuid.uuid4()}.pdf"
    pdf.output(output_filename)
    
    # Read file and encode to base64
    with open(output_filename, "rb") as f:
        pdf_data = f.read()
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
    
    # Clean up file
    os.remove(output_filename)
    
    return {
        "message": "PDF Redaction successful",
        "pdf_base64": pdf_base64,
        "_links": {
            "self": {"href": "/redact/pdf", "method": "POST"},
            "hash": {"href": "/hash", "method": "POST"}
        }
    }

@app.get("/stats")
async def get_stats():
    db = SessionLocal()
    try:
        total_requests = db.query(RedactionLog).count()
        text_requests = db.query(RedactionLog).filter(RedactionLog.request_type == "text").count()
        pdf_requests = db.query(RedactionLog).filter(RedactionLog.request_type == "pdf").count()
        
        # Get last 5 requests
        recents = db.query(RedactionLog).order_by(RedactionLog.timestamp.desc()).limit(5).all()
        recent_logs = [{"id": r.id, "type": r.request_type, "time": r.timestamp.isoformat()} for r in recents]
        
        return {
            "total_redactions": total_requests,
            "text_redactions": text_requests,
            "pdf_redactions": pdf_requests,
            "recent_activity": recent_logs
        }
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=SERVICE_PORT)
