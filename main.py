from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import re
import requests

app = FastAPI(title="ZK Generator Backend")

# CORS – fürs Debuggen erstmal offen, später gern einschränken
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    polA: str
    polB: str
    confidence: str
    explanation: str


@app.get("/")
async def root():
    return {
        "service": "ZK Generator Backend",
        "version": "1.0",
        "status": "operational",
    }


@app.get("/health")
async def health():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return {
        "status": "healthy",
        "api_key_configured": bool(api_key),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="API key not configured. Please set ANTHROPIC_API_KEY environment variable.",
        )
    
    if len(request.text) < 50:
        raise HTTPException(
            status_code=400,
            detail="Text too short. Minimum 50 characters required.",
        )
    
    # Text begrenzen
    text_truncated = request.text[:2000]
    
    prompt = f"""
Analysiere diesen deutschen Text und identifiziere den zentralen Zielkonflikt.
Ein ZK ist ein systemischer Konflikt zwischen zwei gesellschaftlichen Funktionen/Werten,
die sich gegenseitig behindern.

TEXT:
\"\"\"{text_truncated}\"\"\"

AUFGABE:
1. Finde die zwei gegensätzlichen Pole des Hauptkonflikts
2. Formuliere sie präzise und konkret (max. 50 Zeichen pro Pol)
3. Begründe kurz, warum das der Kernkonflikt ist

WICHTIG:
- Pole müssen abstrakte Systemfunktionen sein, keine Akteure
- Beispiel GUT: "Kosteneffizienz = Lebensschutz?"
- Beispiel SCHLECHT: "Streeck = Patienten­schützer"

ANTWORTE NUR als JSON ohne Markdown-Backticks:

{{
    "polA": "Prägnante Bezeichnung",
    "polB": "Prägnante Bezeichnung",
    "confidence": "hoch",
    "begründung": "1-2 Sätze Erklärung"
}}
""".strip()

    try:
        # Stabil dokumentiertes Modell verwenden
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Claude's Antwort extrahieren
        def clean_pole(s: str) -> str:
            s = re.sub(r'[„"\']+', '', s)
            return s.strip()
        
        return AnalyzeResponse(
            polA=clean_pole(result.get("polA", "")),
            polB=clean_pole(result.get("polB", "")),
            confidence=result.get("confidence", "mittel"),
            explanation=result.get("begründung", ""),
        )
    
    except json.JSONDecodeError as e:
        print("JSON parse error from Claude:", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse Claude response as JSON: {str(e)}",
        )
    except requests.exceptions.RequestException as e:
        print("Requests error to Anthropic:", str(e))
        raise HTTPException(
            status_code=502,
            detail=f"Network error talking to Anthropic API: {str(e)}",
        )
    except HTTPException:
        # bereits korrekt gebaut – einfach weiterreichen
        raise
    except Exception as e:
        print("Unexpected backend error:", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected backend error: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
