########## POLICY UPDATE ##########

#!/usr/bin/env python3
"""
AI-Driven Compliance Guardian API
---------------------------------
Serves the unified inference pipeline (Regex + BERT + PII NER + Hybrid ML)
as a REST API endpoint using FastAPI.

This version supports:
 - Policy-driven risk handling (via config/policy_rules.yaml)
 - Safe JSON conversion for model outputs
 - Robust import handling for both dev & package execution
"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ==========================================================
#  FIX IMPORT PATHS
# ==========================================================
# Ensure project root (where app/ folder lives) is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Now import model inference pipeline
try:
    from app.compliance_guardian import analyze_text, safe_convert
except ModuleNotFoundError as e:
    raise RuntimeError(
        f"❌ Failed to import compliance_guardian. "
        f"Make sure you're running from project root.\nDetails: {e}"
    )

# ==========================================================
#  FASTAPI APP SETUP
# ==========================================================
app = FastAPI(
    title="AI-Driven Compliance Guardian API",
    description="Unified Compliance Detection API — PII, Secrets, and Unsafe Text",
    version="2.1",
)

# Enable CORS (for browser testing, UI dashboards, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for production: restrict to known domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
#  REQUEST / RESPONSE MODELS
# ==========================================================
class TextInput(BaseModel):
    text: str

class AnalyzeResponse(BaseModel):
    input: str
    masked_output: str | None
    regex_findings: list[str]
    secret_confidence: float
    ml_confidence: float
    pii_entities: list[str]
    action: str
    sources: list[str | None]

# ==========================================================
#  ROUTES
# ==========================================================
@app.get("/", tags=["Root"])
def root():
    """
    Root route for basic health check and usage guidance.
    """
    return {
        "message": "✅ Welcome to the AI-Driven Compliance Guardian API!",
        "usage": "POST your text to /analyze to evaluate compliance risk.",
        "example": {"text": "My SSN is 123-45-6789"},
    }

@app.post("/analyze", response_model=AnalyzeResponse, tags=["Analysis"])
def analyze_endpoint(payload: TextInput):
    """
    Run compliance analysis on input text.
    Returns unified action ('block', 'mask', or 'allow')
    and confidence scores from Regex, ML, and BERT models.
    """
    try:
        result = analyze_text(payload.text)
        return safe_convert(result)
    except Exception as e:
        # Capture and log errors for debugging / monitoring
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during analysis: {str(e)}",
        )

@app.get("/health", tags=["Health"])
def health_check():
    """
    Lightweight endpoint for container health probes / monitoring.
    """
    return {"status": "ok", "models_loaded": True, "policy_mode": "enabled"}

# ==========================================================
#  SERVER ENTRY POINT
# ==========================================================
if __name__ == "__main__":
    uvicorn.run(
        "app.api.guardian_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )