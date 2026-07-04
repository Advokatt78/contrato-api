"""
Analizador de Contratos Inmobiliarios — Backend API
Para colasjurist.se | Hugo Gutiérrez Colás, Abogado nr 6.539 ICALI
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx, json, os

app = FastAPI(title="Contrato Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://colasjurist.se", "http://localhost", "*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Models ─────────────────────────────────────────────────────────────────────

class PropertyContext(BaseModel):
    precio: Optional[float] = None
    municipio: Optional[str] = None
    tipo: Optional[str] = None          # segunda-mano | obra-nueva | rustico
    vendedor: Optional[str] = None      # particular | empresa | banco | promotor
    comprador_residente: Optional[str] = None  # si | no
    hipoteca_comprador: Optional[bool] = None
    cargas: Optional[str] = None        # ninguna | hipoteca | embargo | usufructo | unknown
    superficie_catastro: Optional[float] = None
    superficie_registro: Optional[float] = None
    piscina_catastro: Optional[bool] = None
    obras_no_declaradas: Optional[bool] = None
    zona_costera: Optional[bool] = None
    tipo_suelo: Optional[str] = None    # urbano | no-urbanizable | urbanizable
    valor_referencia: Optional[float] = None
    comunidad: Optional[str] = None     # si | no
    # Contract-level questionnaire (when no full text)
    tiene_arras: Optional[str] = None
    tipo_arras: Optional[str] = None    # penitenciales | confirmatorias | desconocido
    penalizacion_comprador: Optional[float] = None  # € amount
    penalizacion_vendedor: Optional[str] = None     # doble | otro
    condicion_financiacion: Optional[bool] = None
    clausula_cargas: Optional[bool] = None
    clausula_ocupantes: Optional[bool] = None
    clausula_ibi: Optional[bool] = None
    clausula_comunidad: Optional[bool] = None
    clausula_cancelacion_hipoteca: Optional[bool] = None
    plazo_escritura_dias: Optional[int] = None
    precio_negro: Optional[bool] = None

class ContractRequest(BaseModel):
    contract_text: Optional[str] = None   # full text pasted by user
    property_context: Optional[PropertyContext] = None
    language: str = "sv"  # sv | es | en
    mode: str = "public"  # public | internal

class AlertItem(BaseModel):
    level: str   # red | orange | yellow | green
    category: str
    title: str
    body: str
    clause: Optional[str] = None  # recommended clause text
    action: Optional[str] = None

class ContractAnalysis(BaseModel):
    score: int           # 0-100
    risk_level: str      # low | medium | high | critical
    alerts: list[AlertItem]
    missing_clauses: list[str]
    dangerous_clauses: list[str]
    recommended_actions: list[str]
    summary: str

# ── Prompt ─────────────────────────────────────────────────────────────────────

def build_prompt(req: ContractRequest) -> str:
    lang_instruction = {
        "sv": "Respond entirely in Swedish (svenska). Use natural Swedish legal terminology, not literal translations.",
        "es": "Responde completamente en español. Usa terminología jurídica española.",
        "en": "Respond entirely in English. Use Spanish legal terminology with English explanations."
    }.get(req.language, "Respond in Swedish.")

    ctx = req.property_context or PropertyContext()
    
    context_block = f"""
PROPERTY CONTEXT (from prior analysis):
- Purchase price: {ctx.precio or 'unknown'} €
- Municipality: {ctx.municipio or 'unknown'}
- Property type: {ctx.tipo or 'unknown'}
- Seller type: {ctx.vendedor or 'unknown'}
- Buyer resident in Spain: {ctx.comprador_residente or 'unknown'}
- Buyer mortgage: {ctx.hipoteca_comprador}
- Registered charges: {ctx.cargas or 'none declared'}
- Catastro surface: {ctx.superficie_catastro or 0} m²
- Registry surface: {ctx.superficie_registro or 0} m²
- Pool in Catastro: {ctx.piscina_catastro}
- Undeclared works detected: {ctx.obras_no_declaradas}
- Coastal zone (Ley de Costas): {ctx.zona_costera}
- Land type: {ctx.tipo_suelo or 'urbano'}
- Valor de referencia catastral: {ctx.valor_referencia or 0} €
- Community of owners: {ctx.comunidad or 'unknown'}
"""

    contract_block = ""
    if req.contract_text and len(req.contract_text.strip()) > 50:
        contract_block = f"""
CONTRACT TEXT (pasted by user):
---
{req.contract_text[:8000]}
---
"""
    else:
        # Questionnaire mode
        q = ctx
        contract_block = f"""
CONTRACT QUESTIONNAIRE (no full text available):
- Has arras clause: {q.tiene_arras}
- Type of arras: {q.tipo_arras}
- Buyer penalty if backs out: {q.penalizacion_comprador} €
- Seller penalty: {q.penalizacion_vendedor}
- Financing condition clause: {q.condicion_financiacion}
- Charges/cargas clause present: {q.clausula_cargas}
- Free of occupants clause: {q.clausula_ocupantes}
- IBI clause: {q.clausula_ibi}
- Community certificate clause: {q.clausula_comunidad}
- Mortgage cancellation clause: {q.clausula_cancelacion_hipoteca}
- Days until escritura: {q.plazo_escritura_dias}
- Below-market price (possible black money): {q.precio_negro}
"""

    return f"""You are a Spanish real estate lawyer specializing in property transactions for foreign (especially Swedish) buyers in Spain, particularly in Comunidad Valenciana and Costa Blanca. You work for Colás Jurist (Hugo Gutiérrez Colás, Abogado nr 6.539 ICALI, colasjurist.se).

{lang_instruction}

Your task: Analyze this real estate purchase contract (or the available information about it) and identify:
1. DANGEROUS clauses that put the buyer at risk
2. MISSING clauses that should be present to protect the buyer
3. RISKS from cross-referencing contract with property data (e.g. charges in registry but no retention clause)
4. RECOMMENDED protective clauses for detected risks

{context_block}
{contract_block}

CRITICAL RULES:
- Never invent facts not in the data. If something is unknown, say so.
- Flag when price is below "valor de referencia catastral" — tax authority (AEAT) will use VR as tax base.
- Flag when seller is non-resident — buyer must withhold 3% (Modelo 211).
- Flag when there are registered charges (hipoteca/embargo) but no retention/cancellation clause.
- Flag when there are undeclared constructions but no regularization clause.
- Flag when arras are "penitenciales" — explain consequences clearly.
- Flag missing financing condition (condición suspensiva de financiación).
- Flag missing free-of-occupants clause.
- Flag short deadlines (less than 30 days to escritura).
- For each RED alert, generate a specific protective clause in Spanish legal language.

SCORING: Start at 100. Deduct:
- 20 per RED alert (dangerous/missing critical clause)
- 10 per ORANGE alert (risky but manageable)  
- 5 per YELLOW alert (worth noting)
Minimum score: 0. Report as integer 0-100.

RISK LEVEL based on score:
- 80-100: low
- 60-79: medium
- 40-59: high
- 0-39: critical

Respond ONLY with valid JSON in this exact structure:
{{
  "score": <integer 0-100>,
  "risk_level": "<low|medium|high|critical>",
  "summary": "<2-3 sentences executive summary in {req.language}>",
  "alerts": [
    {{
      "level": "<red|orange|yellow|green>",
      "category": "<registro|catastro|fiscalidad|contrato|urbanismo|comunidad|hipoteca|ocupantes|otro>",
      "title": "<concise title>",
      "body": "<detailed explanation for buyer>",
      "clause": "<recommended clause text in Spanish legalese, or null if not applicable>",
      "action": "<what buyer should do now>"
    }}
  ],
  "missing_clauses": ["<list of missing clause names>"],
  "dangerous_clauses": ["<list of dangerous clause descriptions found in text>"],
  "recommended_actions": ["<list of concrete next steps for buyer>"]
}}

Generate up to 12 alerts maximum. Focus on the most important risks first.
"""

# ── Endpoint ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "contrato-analyzer",
        "api_key_set": bool(ANTHROPIC_KEY),
        "api_key_prefix": ANTHROPIC_KEY[:12] + "..." if ANTHROPIC_KEY else "NOT SET"
    }

@app.post("/analyze", response_model=ContractAnalysis)
async def analyze_contract(req: ContractRequest):
    if not ANTHROPIC_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")
    
    prompt = build_prompt(req)
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt[:6000]}]
            }
        )
    
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Claude API error: {response.status_code}")
    
    data = response.json()
    text = data["content"][0]["text"].strip()
    
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    
    try:
        result = json.loads(text)
        return ContractAnalysis(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse error: {str(e)}\nRaw: {text[:500]}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
