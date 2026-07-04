"""
# Updated: 2026-07-04T18:50:00
Analizador de Contratos Inmobiliarios — Backend API
Para colasjurist.se | Hugo Gutiérrez Colás, Abogado nr 6.539 ICALI
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx, json, os

app = FastAPI(title="Contrato Analyzer API", version="2.0.0")

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
    clause: Optional[str] = None  # recommended clause text in Spanish legalese
    documents: Optional[list[str]] = None  # documents buyer should request
    action: Optional[str] = None

class ContractAnalysis(BaseModel):
    score: int           # 0-100
    risk_level: str      # low | medium | high | critical
    alerts: list[AlertItem]
    missing_clauses: list[str]
    dangerous_clauses: list[str]
    recommended_actions: list[str]
    documents_to_request: list[str]   # NEW: master list of all docs to request
    summary: str

# ── Prompt ─────────────────────────────────────────────────────────────────────

def build_prompt(req: ContractRequest) -> str:
    lang_instruction = {
        "sv": "Respond entirely in Swedish (svenska). Use natural Swedish legal terminology. Clause text must remain in Spanish (it is contract language).",
        "es": "Responde completamente en español. Usa terminología jurídica española. El texto de las cláusulas debe estar en español.",
        "en": "Respond entirely in English. Use Spanish legal terms with English explanations. Clause text must remain in Spanish."
    }.get(req.language, "Respond in Swedish.")

    ctx = req.property_context or PropertyContext()

    context_block = f"""
PROPERTY CONTEXT (from prior analysis steps):
- Purchase price: {ctx.precio or 'unknown'} €
- Municipality: {ctx.municipio or 'unknown'}
- Property type: {ctx.tipo or 'unknown'}  (segunda-mano=resale, obra-nueva=new build, rustico=rural)
- Seller type: {ctx.vendedor or 'unknown'}  (particular=private, empresa=company, banco=bank, promotor=developer)
- Buyer resident in Spain: {ctx.comprador_residente or 'unknown'}
- Buyer needs mortgage: {ctx.hipoteca_comprador}
- Registered charges (Registro de la Propiedad): {ctx.cargas or 'none declared'}
- Catastro surface: {ctx.superficie_catastro or 0} m²
- Registry surface: {ctx.superficie_registro or 0} m²
- Pool registered in Catastro: {ctx.piscina_catastro}
- Undeclared works detected (Catastro vs Registry discrepancy): {ctx.obras_no_declaradas}
- Coastal zone (Ley de Costas risk): {ctx.zona_costera}
- Land classification: {ctx.tipo_suelo or 'urbano'}
- Valor de referencia catastral (AEAT reference value): {ctx.valor_referencia or 0} €
- Community of owners (comunidad de propietarios): {ctx.comunidad or 'unknown'}
"""

    contract_block = ""
    if req.contract_text and len(req.contract_text.strip()) > 50:
        contract_block = f"""
CONTRACT TEXT (pasted by user — analyze every clause):
---
{req.contract_text[:7000]}
---
"""
    else:
        q = ctx
        contract_block = f"""
CONTRACT QUESTIONNAIRE (no full text — analyze based on answers):
- Has arras (deposit) clause: {q.tiene_arras}
- Type of arras: {q.tipo_arras}  (penitenciales=either party can exit paying penalty; confirmatorias=no exit right)
- Buyer penalty if backs out: {q.penalizacion_comprador} €
- Seller penalty if backs out: {q.penalizacion_vendedor}  (doble=double the deposit returned)
- Financing condition (condición suspensiva de financiación): {q.condicion_financiacion}
- Charges/cargas cancellation clause present: {q.clausula_cargas}
- Free of occupants clause (libre de ocupantes): {q.clausula_ocupantes}
- IBI (annual property tax) settlement clause: {q.clausula_ibi}
- Community certificate clause (certificado de comunidad): {q.clausula_comunidad}
- Mortgage cancellation clause: {q.clausula_cancelacion_hipoteca}
- Days until escritura (notarial deed): {q.plazo_escritura_dias}
- Below-market price (possible black money / precio negro): {q.precio_negro}
"""

    return f"""You are a senior Spanish real estate lawyer (Abogado) with 19 years of experience in Costa Blanca, specializing in property transactions for Swedish buyers. You work for Colás Jurist (Hugo Gutiérrez Colás, Abogado nr 6.539 ICALI, colasjurist.se).

{lang_instruction}

{context_block}
{contract_block}

YOUR TASK: Produce a thorough, actionable contract analysis covering:
1. DANGEROUS clauses that put the buyer at risk
2. MISSING protective clauses that must be added before signing
3. SPECIFIC DOCUMENTS the buyer must request before or at signing
4. RECOMMENDED clause text for each red/orange issue (in Spanish legal language)
5. CROSS-REFERENCING: correlate contract clauses with property data from prior steps

MANDATORY SITUATIONAL RULES — apply ALL that match the data:

### MORTGAGE / CHARGES (cargas: hipoteca or embargo)
- If there is a registered hipoteca or embargo: FLAG as RED — buyer must demand:
  (a) "Certificado de deuda pendiente" from the lender showing exact outstanding balance
  (b) A retention clause (retención) in the contract: seller authorises buyer to withhold from purchase price the amount needed to cancel the mortgage at escritura
  (c) "Condición de cancelación registral previa a la escritura" — mortgage must be cancelled in Registro before or simultaneously with deed
- Recommended retention clause: "El comprador retendrá de la cantidad a entregar en escritura el importe necesario para la cancelación de la hipoteca que grava la finca, cuyo saldo será acreditado mediante certificado de deuda emitido por la entidad acreedora con una antelación máxima de 10 días hábiles a la fecha de otorgamiento de la escritura pública de compraventa."

### UNDECLARED WORKS / OBRA NUEVA NO DECLARADA
- If obras_no_declaradas is True OR catastro surface ≠ registry surface significantly:
  FLAG as RED — buyer must demand:
  (a) Seller legalises all works before escritura (declaración de obra nueva)
  (b) OR: price reduction + retention to cover estimated cost of legalisation
  (c) Document: "Nota simple actualizada del Registro de la Propiedad" + "Consulta descriptiva y gráfica del Catastro"
- Recommended clause: "El vendedor se obliga a declarar ante Notario la obra nueva correspondiente a [descripción] antes de la firma de la escritura pública de compraventa, siendo dicho trámite condición esencial del presente contrato. En caso de incumplimiento, el comprador podrá resolver el contrato con devolución del doble de las arras entregadas."

### POTENTIAL URBAN INFRACTIONS
- If tipo_suelo is 'no-urbanizable' or 'rustico', or zona_costera is True, or obras_no_declaradas:
  FLAG as ORANGE — buyer must request:
  (a) "Certificado de no infracción urbanística" from the Ayuntamiento
  (b) "Certificado de antigüedad" if applicable (to check prescription period)
  (c) Check whether constructions are inside "zona de servidumbre de costas" (100m from shore)
- Recommended clause: "El vendedor garantiza que la finca y todas las construcciones existentes en ella no son objeto de expediente de infracción urbanística, disciplina urbanística o procedimiento de demolición, comprometiéndose a aportar certificado del Ayuntamiento acreditativo de dicha circunstancia antes de la firma de escritura pública."

### SELLER IS NON-RESIDENT (vendedor no residente)
- If seller is non-resident (indicated by: empresa extranjera, or flag in contract):
  FLAG as RED — buyer MUST withhold 3% of purchase price and pay to AEAT via Modelo 211 within 30 days
- Recommended clause: "En cumplimiento del art. 25.2 LIRNR, el comprador retendrá el 3% del precio pactado ([amount] €) e ingresará dicho importe en la Agencia Tributaria mediante Modelo 211 en el plazo de un mes desde la escritura."

### PRICE BELOW VALOR DE REFERENCIA (precio negro risk)
- If precio < valor_referencia (both known):
  FLAG as RED — AEAT will tax buyer on valor_referencia, not purchase price → hidden extra tax
  FLAG if precio_negro is True → potential criminal liability for buyer

### ARRAS PENITENCIALES — ASYMMETRIC PENALTIES
- If tipo_arras = 'penitenciales' AND (penalizacion_vendedor = null or != 'doble'):
  FLAG as RED — contract is asymmetric: buyer loses deposit if backs out, but seller has no equivalent deterrent
- If penalizacion_comprador > 10% of precio: FLAG as ORANGE — penalty is unusually high

### FINANCING CONDITION MISSING
- If condicion_financiacion is False or null AND hipoteca_comprador is True:
  FLAG as RED — buyer will lose deposit if bank refuses mortgage
- Recommended clause: "La presente compraventa queda sujeta a la condición suspensiva de obtención de financiación hipotecaria por parte del comprador por un importe mínimo de [amount] € en un plazo máximo de [X] días desde la firma del presente contrato. De no obtenerse dicha financiación en el plazo indicado, el contrato quedará resuelto sin penalización para ninguna de las partes, con devolución íntegra de las cantidades entregadas."

### FREE OF OCCUPANTS
- If clausula_ocupantes is False or null:
  FLAG as ORANGE — without this clause, buyer cannot force seller to ensure property is vacant at escritura
- Recommended clause: "El vendedor garantiza que la finca objeto de la presente compraventa se entregará libre de cargas, gravámenes, arrendatarios y ocupantes de cualquier tipo en la fecha de otorgamiento de la escritura pública, siendo el incumplimiento de esta obligación causa de resolución del contrato con devolución del doble de las arras."

### IBI & COMMUNITY EXPENSES
- If clausula_ibi is False: FLAG as YELLOW — buyer may inherit IBI debt from prior years (up to 4 years)
  Document to request: "Recibo del IBI del año en curso" + "Certificado de estar al corriente de pago"
- If clausula_comunidad is False: FLAG as YELLOW — buyer may inherit community fee debts
  Document to request: "Certificado de deuda de la comunidad de propietarios" (obligatorio por ley)

### SHORT DEADLINE TO ESCRITURA
- If plazo_escritura_dias < 30: FLAG as ORANGE — insufficient time for searches, mortgage, legalisation

### NEW BUILD (obra nueva)
- If tipo = 'obra-nueva': FLAG as mandatory checks:
  (a) "Seguro decenal" (10-year structural insurance) — must be delivered at escritura
  (b) "Licencia de primera ocupación" (LPO) — must exist before escritura
  (c) "Certificado de fin de obra" signed by architect
  (d) IVA 10% + AJD 1.5% (not ITP) — buyer must understand tax structure

SCORING: Start at 100. Deduct:
- 25 per RED alert (critical — must fix before signing)
- 12 per ORANGE alert (important — strongly recommended)
- 5 per YELLOW alert (worth noting)
Minimum score: 0. Score as integer 0-100.

RISK LEVEL:
- 80-100: low
- 60-79: medium
- 40-59: high
- 0-39: critical

IMPORTANT OUTPUT RULES:
- Generate up to 10 alerts maximum. Prioritize RED first.
- For EVERY red and orange alert: include a "clause" field with the recommended protective clause text in Spanish legal language (use the examples above as style guide — formal, precise, 2-4 sentences).
- For EVERY alert: include a "documents" array listing the specific documents the buyer should request related to that issue.
- The "documents_to_request" top-level list must aggregate ALL documents from all alerts (deduplicated).
- "missing_clauses" = list of clause names not found in contract that should be there.
- "dangerous_clauses" = specific problematic clauses found in the contract text (if text was provided).
- "recommended_actions" = concrete numbered steps buyer should take NOW, in priority order.
- Be specific and practical — this analysis is what the buyer will use to negotiate or walk away.

Respond ONLY with valid JSON in this exact structure (no markdown fences):
{{
  "score": <integer 0-100>,
  "risk_level": "<low|medium|high|critical>",
  "summary": "<3-4 sentences: overall assessment, biggest risk, and key recommendation>",
  "alerts": [
    {{
      "level": "<red|orange|yellow|green>",
      "category": "<registro|catastro|fiscalidad|contrato|urbanismo|comunidad|hipoteca|ocupantes|obras|otro>",
      "title": "<concise title in {req.language}>",
      "body": "<detailed explanation for the buyer — what is the risk and why it matters>",
      "clause": "<recommended protective clause in Spanish, or null>",
      "documents": ["<document name>", ...],
      "action": "<specific action buyer should take now>"
    }}
  ],
  "missing_clauses": ["<clause name>", ...],
  "dangerous_clauses": ["<description of dangerous clause found>", ...],
  "recommended_actions": ["<concrete action step>", ...],
  "documents_to_request": ["<document name>", ...]
}}
"""

# ── Endpoint ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "contrato-analyzer",
        "version": "2.0.0",
        "api_key_set": bool(ANTHROPIC_KEY),
        "api_key_prefix": ANTHROPIC_KEY[:12] + "..." if ANTHROPIC_KEY else "NOT SET"
    }

@app.post("/analyze", response_model=ContractAnalysis)
async def analyze_contract(req: ContractRequest):
    if not ANTHROPIC_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")

    prompt = build_prompt(req)

    async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": prompt}]
            }
        )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Claude API error: {response.status_code} — {response.text[:300]}")

    data = response.json()
    text = data["content"][0]["text"].strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()

    try:
        result = json.loads(text)
        # Ensure new fields exist with defaults
        if "documents_to_request" not in result:
            docs = []
            for a in result.get("alerts", []):
                docs.extend(a.get("documents") or [])
            result["documents_to_request"] = list(dict.fromkeys(docs))
        return ContractAnalysis(**result)
    except json.JSONDecodeError:
        # JSON truncated — recover what we have
        try:
            import re
            score_m = re.search(r'"score":\s*(\d+)', text)
            risk_m = re.search(r'"risk_level":\s*"([^"]+)"', text)
            summary_m = re.search(r'"summary":\s*"([^"]+)"', text)
            # Extract complete alert objects (must have at least level+title+body)
            complete_alerts = []
            for m in re.finditer(r'\{[^{}]*"level"[^{}]*"title"[^{}]*"body"[^{}]*\}', text, re.S):
                try:
                    a = json.loads(m.group(0))
                    complete_alerts.append(a)
                except:
                    pass

            score = int(score_m.group(1)) if score_m else 40
            risk = risk_m.group(1) if risk_m else "high"
            summary = summary_m.group(1) if summary_m else "Analys genomförd — granska varningarna nedan."

            return ContractAnalysis(
                score=score,
                risk_level=risk,
                summary=summary,
                alerts=complete_alerts[:8],
                missing_clauses=[],
                dangerous_clauses=[],
                recommended_actions=["Kontakta Hugo Gutiérrez Colás för fullständig granskning av avtalet."],
                documents_to_request=[]
            )
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Parse error: {str(e2)}\nRaw: {text[:300]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
