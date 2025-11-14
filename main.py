from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import json
import requests  # WICHTIG: fehlender Import nachgezogen


app = FastAPI(title="ZK Generator Backend")

# CORS – fürs Debuggen erstmal offen, später gern einschränken
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # später: ["https://burmeister12439-futur2.github.io"]
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
    api_key = os.getenv("ANTHROPIC_API_KEY")

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
- Beispiel GUT: "Kosteneffizienz ↔ Lebensschutz"
- Beispiel SCHLECHT: "Streeck ↔ Patientenschützer"

ANTWORT NUR als JSON ohne Markdown-Backticks:

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
                "content-type": "application/json",
            },
            json={
                "model": "claude-3-5-sonnet-20240620",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            },
            timeout=30,
        )

        # HTTP-Fehler der Anthropic-API explizit behandeln
        if response.status_code >= 400:
            # Log-Ausgabe für Railway-Logs (sichtbar im Dashboard)
            print("Anthropic API error:", response.status_code, response.text)
            raise HTTPException(
                status_code=502,
                detail=f"Anthropic API error ({response.status_code}). "
                       f"Details siehe Backend-Logs.",
            )

        result_data = response.json()

        # Laut Messages-API steckt der Text im ersten Content-Block
        response_text = result_data["content"][0]["text"]

        # Markdown-Reste entfernen
        response_text = (
            response_text.replace("```json", "")
            .replace("```", "")
            .replace("'''", "")
            .strip()
        )

        # JSON der KI parsen
        result = json.loads(response_text)

        # Pol-Bezeichnungen etwas aufräumen
        def clean_pole(s: str) -> str:
            import re

            s = re.sub(
                r"^(der|die|das|dem|den|ein|eine)\s+",
                "",
                s,
                flags=re.IGNORECASE,
            )
            s = re.sub(r'[„"\'`]*', "", s)
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
        # bereits korrekt gebaut → einfach weiterreichen
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
```

---

## **SCHRITT 5: Commit**

**Scroll nach oben**, klick auf **"Commit changes..."** (grüner Button)

**Commit message:**
```
Fix: Add missing requests import + use stable model
