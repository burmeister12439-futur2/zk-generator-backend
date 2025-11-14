# ZK Generator Backend

Backend-Server für KI-gestützte Zielkonflikt-Analyse.

## 🚀 Deployment auf Render

### Schritt 1: GitHub Repo erstellen

1. Gehe zu: https://github.com/new
2. **Name:** `zk-generator-backend`
3. **Public**
4. **Create repository**

### Schritt 2: Files hochladen

Upload diese 3 Files:
- `main.py`
- `requirements.txt`
- `render.yaml`

### Schritt 3: Render Account

1. Gehe zu: https://render.com
2. **Sign Up** (kostenlos)
3. **Connect GitHub Account**

### Schritt 4: Deploy

1. **Dashboard** → **"New +"** → **"Web Service"**
2. **Connect Repository:** `zk-generator-backend`
3. Render erkennt automatisch `render.yaml`
4. **Create Web Service**

### Schritt 5: API-Key hinzufügen

**WICHTIG:** Nach dem ersten Deploy:

1. **Dashboard** → Dein Service → **"Environment"**
2. **Add Environment Variable:**
   - **Key:** `ANTHROPIC_API_KEY`
   - **Value:** `sk-ant-api03-...` (dein echter Key)
3. **Save** → Service wird neu gestartet

---

## 🧪 Testing

### Health Check

```bash
curl https://zk-generator-backend.onrender.com/health
```

**Expected:**
```json
{
  "status": "healthy",
  "api_key_configured": true
}
```

### Test Analysis

```bash
curl -X POST https://zk-generator-backend.onrender.com/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Ohne Förderung kein Fortschritt: Kommunen warten auf neues Innenstadtprogramm..."}'
```

**Expected:**
```json
{
  "polA": "Förderung",
  "polB": "Fortschritt",
  "confidence": "hoch",
  "explanation": "..."
}
```

---

## 💰 Kosten

**Render Free Tier:**
- ✅ 750 Stunden/Monat (= 24/7)
- ✅ Automatisches HTTPS
- ⚠️ Service schläft nach 15 Min Inaktivität
- ⚠️ Erster Request nach Sleep: ~30 Sek Aufwachzeit

**Anthropic API:**
- ~$0.003 pro Analyse
- Bezahlt über deinen Anthropic Account

---

## 🔒 Sicherheit

**API-Key Protection:**
- ✅ Key nur auf Server (nicht im Frontend)
- ✅ CORS beschränkt auf deine GitHub Pages Domain
- ✅ Keine Logs des Keys

**Rate Limiting:**
- Aktuell: Keine Limits
- Bei Bedarf: Kann hinzugefügt werden

---

## 🐛 Troubleshooting

### "API key not configured"

→ Environment Variable `ANTHROPIC_API_KEY` in Render Settings hinzufügen

### "Service unavailable"

→ Free Tier Service war im Sleep-Modus. Warte 30 Sek für Aufwachen.

### CORS Error im Frontend

→ Prüfe ob deine GitHub Pages URL in `allow_origins` steht

---

## 📊 Monitoring

**Render Dashboard zeigt:**
- Request Count
- Response Times  
- Error Rates
- Logs (live)

---

## 🔄 Updates

**Code ändern:**
1. Update Files im GitHub Repo
2. Render deployed automatisch
3. Warte ~2 Min

**Environment Variables ändern:**
1. Render Dashboard → Environment
2. Update Variable
3. Save → Auto-restart

---

**Backend bereit für Production! 🎉**
