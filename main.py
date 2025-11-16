from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import Anthropic
import os
from typing import List, Dict, Optional
import json

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Anthropic client
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class PolicyText(BaseModel):
    policy_text: str

class ThreeYesCheck(BaseModel):
    system_function: bool
    system_function_reasoning: str
    implementation_collision: bool
    implementation_reasoning: str
    current_pressure: bool
    pressure_reasoning: str

class GoalConflict(BaseModel):
    conflict: str
    function_a: str
    function_b: str
    implementation_collision: str
    centrality_score: float
    three_yes: ThreeYesCheck
    category: str

class MultiConflictResponse(BaseModel):
    conflicts: List[GoalConflict]
    total_count: int

# System prompt for multi-conflict detection
MULTI_DETECTION_PROMPT = """Du bist ein Experte für die Identifikation von Zielkonflikten in der deutschen Transformationspolitik.

AUFGABE: Analysiere den gegebenen Politiktext und identifiziere ALLE vorhandenen Zielkonflikte. Ein Zielkonflikt liegt vor, wenn zwei gesellschaftliche Funktionen in ihrer Umsetzung kollidieren.

WICHTIGE DEFINITIONEN:

1. GESELLSCHAFTLICHE FUNKTIONEN - Beispiele:
   - Wirtschaftswachstum und Wettbewerbsfähigkeit
   - Klimaschutz und Dekarbonisierung
   - Soziale Sicherheit und Gerechtigkeit
   - Gesundheitsversorgung
   - Bildung und Qualifikation
   - Wohnraumversorgung
   - Demokratische Teilhabe
   - Technologische Innovation
   - Infrastruktur und Mobilität
   - Natürlicher Ressourcenschutz

2. ZIELKONFLIKT-KRITERIEN (3-YES-REGEL):
   
   a) Systemfunktionalität: Sind beide Funktionen essentiell für das Funktionieren der Gesellschaft?
   
   b) Implementierungskollision: Behindern sich die Funktionen konkret in ihrer Umsetzung? (Nicht nur theoretische Spannung!)
   
   c) Aktueller Druck: Besteht derzeit politischer/gesellschaftlicher Handlungsdruck für beide Seiten?

3. KATEGORISIERUNG:
   - ZENTRAL: 3x JA bei 3-YES-Regel
   - PRÜF: 2x JA bei 3-YES-Regel
   - HINTERGRUND: 1x oder 0x JA bei 3-YES-Regel

ZENTRALITÄTS-BEWERTUNG:
Bewerte für jeden identifizierten Konflikt, wie zentral er im Text behandelt wird (0.0 - 1.0):
- 1.0: Hauptthema des Textes, ausführlich diskutiert
- 0.7-0.9: Deutlich behandelt, wichtiger Aspekt
- 0.4-0.6: Erwähnt und angedeutet
- 0.1-0.3: Nur am Rande erwähnt

VORGEHEN:
1. Lies den gesamten Text sorgfältig
2. Identifiziere ALLE Stellen, wo gesellschaftliche Funktionen erwähnt werden
3. Prüfe systematisch, ob zwischen diesen Funktionen Konflikte bestehen
4. Formuliere jeden Konflikt präzise
5. Bewerte Zentralität jedes Konflikts im Text
6. Führe 3-YES-Check für jeden Konflikt durch
7. Kategorisiere jeden Konflikt

WICHTIG:
- Finde ALLE Konflikte, nicht nur den offensichtlichsten
- Sei präzise in der Formulierung
- Unterscheide zwischen tatsächlichen Umsetzungskonflikten und bloßen Spannungsfeldern
- Ranke nach Zentralität im Text (nicht nach politischer Wichtigkeit!)

Antworte ausschließlich mit einem JSON-Array im folgenden Format:

{
  "conflicts": [
    {
      "conflict": "Präzise Formulierung des Zielkonflikts",
      "function_a": "Erste gesellschaftliche Funktion",
      "function_b": "Zweite gesellschaftliche Funktion",
      "implementation_collision": "Konkrete Beschreibung, wie sich die Umsetzung beider Funktionen behindert",
      "centrality_score": 0.85,
      "three_yes": {
        "system_function": true,
        "system_function_reasoning": "Begründung",
        "implementation_collision": true,
        "implementation_reasoning": "Begründung",
        "current_pressure": true,
        "pressure_reasoning": "Begründung"
      },
      "category": "ZENTRAL"
    }
  ]
}

Gib KEINE zusätzlichen Erklärungen, nur das JSON-Array. Falls keine Zielkonflikte identifiziert werden, gib ein leeres Array zurück: {"conflicts": []}
"""

@app.get("/")
async def root():
    return {
        "message": "ZK-RK Analysis API v8.0 - Multi-Conflict Detection",
        "endpoints": {
            "/analyze-multi": "POST - Analyze text for multiple goal conflicts with ranking"
        }
    }

@app.post("/analyze-multi", response_model=MultiConflictResponse)
async def analyze_multi_conflicts(data: PolicyText):
    """
    Analyze policy text and identify ALL goal conflicts, ranked by centrality
    """
    if not data.policy_text or len(data.policy_text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Text zu kurz. Bitte geben Sie einen aussagekräftigen Politiktext ein."
        )
    
    try:
        # Call Claude API for multi-conflict detection
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": f"{MULTI_DETECTION_PROMPT}\n\nZU ANALYSIERENDER TEXT:\n\n{data.policy_text}"
                }
            ]
        )
        
        # Extract and parse response
        response_text = message.content[0].text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()
        
        # Parse JSON response
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            print(f"Response text: {response_text}")
            raise HTTPException(
                status_code=500,
                detail="Fehler beim Parsen der Analyseergebnisse"
            )
        
        conflicts = result.get("conflicts", [])
        
        # Sort conflicts by centrality score (highest first)
        conflicts_sorted = sorted(
            conflicts,
            key=lambda x: x.get("centrality_score", 0),
            reverse=True
        )
        
        # Validate and structure response
        structured_conflicts = []
        for conflict in conflicts_sorted:
            try:
                structured_conflict = GoalConflict(
                    conflict=conflict["conflict"],
                    function_a=conflict["function_a"],
                    function_b=conflict["function_b"],
                    implementation_collision=conflict["implementation_collision"],
                    centrality_score=conflict.get("centrality_score", 0.5),
                    three_yes=ThreeYesCheck(**conflict["three_yes"]),
                    category=conflict["category"]
                )
                structured_conflicts.append(structured_conflict)
            except Exception as e:
                print(f"Error structuring conflict: {e}")
                continue
        
        return MultiConflictResponse(
            conflicts=structured_conflicts,
            total_count=len(structured_conflicts)
        )
        
    except Exception as e:
        print(f"Error in analyze_multi_conflicts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Fehler bei der Analyse: {str(e)}"
        )

# Keep original single-conflict endpoint for backwards compatibility
@app.post("/analyze")
async def analyze_single_conflict(data: PolicyText):
    """
    Original endpoint - returns only the primary (most central) conflict
    """
    multi_result = await analyze_multi_conflicts(data)
    
    if not multi_result.conflicts:
        raise HTTPException(
            status_code=404,
            detail="Kein Zielkonflikt im Text identifiziert"
        )
    
    # Return only the primary conflict (highest centrality)
    primary_conflict = multi_result.conflicts[0]
    
    return {
        "conflict": primary_conflict.conflict,
        "function_a": primary_conflict.function_a,
        "function_b": primary_conflict.function_b,
        "implementation_collision": primary_conflict.implementation_collision,
        "centrality_score": primary_conflict.centrality_score,
        "three_yes": primary_conflict.three_yes.dict(),
        "category": primary_conflict.category
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
