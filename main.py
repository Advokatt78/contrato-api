"""
# Updated: 2026-07-04T19:00:00 — v3 Due Diligence Completa
Analizador de Due Diligence Inmobiliaria — Backend API
Para colasjurist.se | Hugo Gutiérrez Colás, Abogado nr 6.539 ICALI
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, Any, Union
import httpx, json, os, tempfile, io

app = FastAPI(title="Due Diligence Inmobiliaria API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://colasjurist.se", "http://localhost", "*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Models ─────────────────────────────────────────────────────────────────────

def _to_bool(v):
    """Coerce string 'si'/'no'/'true'/'false' to bool, pass through bool/None."""
    if v is None: return None
    if isinstance(v, bool): return v
    if isinstance(v, str):
        return v.lower() in ('si', 'yes', 'true', '1', 'sí')
    return bool(v)


class PropertyContext(BaseModel):
    model_config = {'arbitrary_types_allowed': True}

    # Basic property data
    precio: Optional[float] = None
    municipio: Optional[str] = None
    tipo: Optional[str] = None
    vendedor: Optional[str] = None
    comprador_residente: Optional[str] = None
    hipoteca_comprador: Optional[Any] = None

    # Registry
    cargas: Optional[str] = None
    titularidad: Optional[str] = None
    superficie_registro: Optional[float] = None
    superficie_parcela_registro: Optional[float] = None
    anno_construccion_registro: Optional[int] = None
    obra_nueva_inscrita: Optional[Any] = None
    division_horizontal: Optional[Any] = None
    cuota_participacion: Optional[float] = None

    # Catastro
    superficie_catastro: Optional[float] = None
    superficie_parcela_catastro: Optional[float] = None
    anno_construccion_catastro: Optional[int] = None
    piscina_catastro: Optional[Any] = None
    garaje_catastro: Optional[Any] = None
    trastero_catastro: Optional[Any] = None
    obras_no_declaradas: Optional[Any] = None
    valor_referencia: Optional[float] = None
    valor_catastral: Optional[float] = None

    # Urban planning
    zona_costera: Optional[Any] = None
    tipo_suelo: Optional[str] = None
    tiene_licencia_primera_ocupacion: Optional[str] = None
    expediente_urbanistico: Optional[str] = None

    # Community
    comunidad: Optional[Any] = None
    certificado_deuda_comunidad: Optional[str] = None
    actas_comunidad: Optional[str] = None
    derramas_pendientes: Optional[str] = None
    alquiler_turistico_permitido: Optional[str] = None

    # Fiscal
    ibi_al_corriente: Optional[str] = None
    vendedor_no_residente: Optional[str] = None
    precio_negro: Optional[Any] = None

    # Contract fields
    tipo_contrato: Optional[str] = None
    tiene_arras: Optional[str] = None
    tipo_arras: Optional[str] = None
    importe_senyal: Optional[float] = None
    penalizacion_comprador: Optional[float] = None
    penalizacion_vendedor: Optional[str] = None
    condicion_financiacion: Optional[Any] = None
    clausula_cargas: Optional[Any] = None
    clausula_ocupantes: Optional[Any] = None
    clausula_ibi: Optional[Any] = None
    clausula_comunidad: Optional[Any] = None
    clausula_cancelacion_hipoteca: Optional[Any] = None
    clausula_retencion_3pct: Optional[Any] = None
    clausula_plusvalia: Optional[str] = None
    plazo_escritura_dias: Optional[int] = None
    documentos_aportados: Optional[list] = None

    @model_validator(mode='before')
    @classmethod
    def coerce_bools(cls, data):
        """Convert string 'si'/'no' to bool for all bool fields."""
        bool_fields = [
            'hipoteca_comprador','obra_nueva_inscrita','division_horizontal',
            'piscina_catastro','garaje_catastro','trastero_catastro','obras_no_declaradas',
            'zona_costera','comunidad','precio_negro',
            'condicion_financiacion','clausula_cargas','clausula_ocupantes',
            'clausula_ibi','clausula_comunidad','clausula_cancelacion_hipoteca',
            'clausula_retencion_3pct'
        ]
        if isinstance(data, dict):
            for f in bool_fields:
                if f in data:
                    data[f] = _to_bool(data[f])
        return data


class ContractRequest(BaseModel):
    contract_text: Optional[str] = None
    additional_documents: Optional[str] = None   # nota simple, cert energia, cedula urbanistica, otros
    cert_energia_estado: Optional[str] = None    # si | no | caducado
    cert_energia_calificacion: Optional[str] = None  # A-G
    cedula_urbanistica_tipo: Optional[str] = None
    property_context: Optional[PropertyContext] = None
    language: str = "sv"
    mode: str = "public"


class AlertItem(BaseModel):
    level: str          # red | orange | yellow | green
    category: str       # registral | catastral | urbanismo | comunidad | fiscal | contrato | posesion | licencias | costas | otro
    title: str
    body: str
    clause: Optional[str] = None
    documents: Optional[list[str]] = None
    actuacion_previa: Optional[str] = None   # what must be done BEFORE signing
    quien_asume: Optional[str] = None        # vendedor | comprador | ambos
    action: Optional[str] = None


class DueDiligenceReport(BaseModel):
    # Scoring
    score: int
    risk_level: str     # low | medium | high | critical
    clasificacion_final: str  # puede_firmarse | puede_firmarse_con_modificaciones | no_deberia_firmarse

    # Executive summary
    summary: str

    # Alerts by category
    alerts: list[AlertItem]

    # Structured report sections
    documentacion_aportada: list[str]
    documentacion_pendiente: list[str]
    missing_clauses: list[str]
    dangerous_clauses: list[str]
    actuaciones_previas_imprescindibles: list[str]
    actuaciones_recomendadas: list[str]
    clausulas_adicionales_recomendadas: list[str]
    recommended_actions: list[str]
    documents_to_request: list[str]

    # Checklists
    checklist_antes_de_firmar: list[str]
    checklist_antes_de_escritura: list[str]

    # Follow-up questions (dynamic)
    preguntas_adicionales: list[str]


# ── Master Due Diligence Prompt ─────────────────────────────────────────────────

def get_lang_sys(language: str) -> str:
    sv = (
        "ABSOLUTE RULE - LANGUAGE OUTPUT: You MUST write every single JSON field in Swedish (svenska). "
        "Non-negotiable. Documents may be in Spanish or English - fine, read them, but WRITE in Swedish. "
        "ALL these fields in Swedish: summary, alerts[].title, alerts[].body, alerts[].action, "
        "documentacion_pendiente[], actuaciones_previas_imprescindibles[], recommended_actions[], "
        "documents_to_request[], missing_clauses[], checklist_antes_de_firmar[], "
        "checklist_antes_de_escritura[], preguntas_adicionales[]. "
        "ONLY alerts[].clause stays in Spanish legal language. "
        "Writing Spanish outside alerts[].clause = task failure."
    )
    es = "Responde en espanol en todos los campos JSON. Las clausulas tambien en espanol."
    en = (
        "ABSOLUTE RULE - LANGUAGE: Write every JSON field in English. "
        "ONLY exception: alerts[].clause stays in Spanish legal language."
    )
    return {"sv": sv, "es": es, "en": en}.get(language, sv)


def build_prompt(req: ContractRequest) -> str:
    lang_instruction = {
        "sv": """CRITICAL LANGUAGE RULE — NON-NEGOTIABLE: You MUST write ALL output in Swedish (svenska). 
This is mandatory regardless of the language of the contract text provided.
The contract may be in Spanish or English — that does not matter. YOUR ANALYSIS must be in Swedish.
Every field in the JSON — summary, alerts[].title, alerts[].body, alerts[].action, 
alerts[].actuacion_previa, documentacion_pendiente[], actuaciones_previas_imprescindibles[], 
actuaciones_recomendadas[], clausulas_adicionales_recomendadas[], recommended_actions[], 
documents_to_request[], checklist_antes_de_firmar[], checklist_antes_de_escritura[], 
missing_clauses[], dangerous_clauses[], preguntas_adicionales[] — ALL in Swedish.
ONLY exception: the alerts[].clause field must remain in Spanish legal language (it is contract text).
If you write a single sentence in Spanish or English (except clause texts), you have failed.""",
        "es": """REGLA DE IDIOMA OBLIGATORIA: Responde completamente en español en todos los campos JSON.
El texto de las cláusulas también en español.""",
        "en": """CRITICAL LANGUAGE RULE: You MUST write ALL output in English regardless of contract language.
ONLY exception: alerts[].clause field stays in Spanish legal language."""
    }.get(req.language, "Write ALL output in Swedish.")

    ctx = req.property_context or PropertyContext()

    docs_aportados = ctx.documentos_aportados or []
    docs_str = ", ".join(docs_aportados) if docs_aportados else "ninguno declarado"

    context_block = f"""
=== PROPERTY DATA (from prior analysis steps) ===

BASIC:
- Purchase price: {ctx.precio or 'unknown'} €
- Municipality: {ctx.municipio or 'unknown'}
- Property type: {ctx.tipo or 'unknown'}  (segunda-mano=resale | obra-nueva=new build | rustico=rural)
- Seller type: {ctx.vendedor or 'unknown'}  (particular | empresa | banco | promotor)
- Buyer resident in Spain: {ctx.comprador_residente or 'unknown'}
- Buyer needs mortgage: {ctx.hipoteca_comprador}

REGISTRY (Registro de la Propiedad):
- Registered charges: {ctx.cargas or 'unknown'}
- Ownership: {ctx.titularidad or 'unknown'}
- Registry built area: {ctx.superficie_registro or 0} m²
- Registry plot area: {ctx.superficie_parcela_registro or 0} m²
- Year of construction (registry): {ctx.anno_construccion_registro or 'unknown'}
- Obra nueva inscrita: {ctx.obra_nueva_inscrita}
- División horizontal (community): {ctx.division_horizontal}
- Participation coefficient: {ctx.cuota_participacion or 'unknown'} %

CATASTRO:
- Catastro built area: {ctx.superficie_catastro or 0} m²
- Catastro plot area: {ctx.superficie_parcela_catastro or 0} m²
- Year of construction (catastro): {ctx.anno_construccion_catastro or 'unknown'}
- Pool in Catastro: {ctx.piscina_catastro}
- Garage in Catastro: {ctx.garaje_catastro}
- Storage room in Catastro: {ctx.trastero_catastro}
- Undeclared works detected: {ctx.obras_no_declaradas}
- Valor de referencia catastral: {ctx.valor_referencia or 0} €
- Valor catastral: {ctx.valor_catastral or 0} €

URBAN PLANNING:
- Coastal zone (Ley de Costas): {ctx.zona_costera}
- Land classification: {ctx.tipo_suelo or 'urbano'}
- First occupation licence (LPO): {ctx.tiene_licencia_primera_ocupacion or 'unknown'}
- Urban infraction expedient: {ctx.expediente_urbanistico or 'unknown'}

COMMUNITY (Propiedad Horizontal):
- Part of community: {ctx.comunidad}
- Community debt certificate: {ctx.certificado_deuda_comunidad or 'not provided'}
- Community minutes (actas): {ctx.actas_comunidad or 'not provided'}
- Pending special levies (derramas): {ctx.derramas_pendientes or 'unknown'}
- Tourist rental permitted: {ctx.alquiler_turistico_permitido or 'unknown'}

FISCAL:
- IBI up to date: {ctx.ibi_al_corriente or 'unknown'}
- Non-resident seller: {ctx.vendedor_no_residente or 'unknown'}
- Below-market price (possible precio negro): {ctx.precio_negro}

CONTRACT:
- Contract type: {ctx.tipo_contrato or 'unknown'}
- Arras clause: {ctx.tiene_arras or 'unknown'}
- Type of arras: {ctx.tipo_arras or 'unknown'}
- Deposit paid: {ctx.importe_senyal or 0} €
- Buyer penalty if backs out: {ctx.penalizacion_comprador or 0} €
- Seller penalty: {ctx.penalizacion_vendedor or 'unknown'}
- Financing condition clause: {ctx.condicion_financiacion}
- Charges cancellation clause: {ctx.clausula_cargas}
- Free of occupants clause: {ctx.clausula_ocupantes}
- IBI clause: {ctx.clausula_ibi}
- Community certificate clause: {ctx.clausula_comunidad}
- Mortgage cancellation clause: {ctx.clausula_cancelacion_hipoteca}
- 3% non-resident retention clause: {ctx.clausula_retencion_3pct}
- Plusvalía clause: {ctx.clausula_plusvalia or 'unknown'}
- Days until escritura: {ctx.plazo_escritura_dias or 'unknown'}

DOCUMENTS PROVIDED BY USER: {docs_str}
"""

    contract_block = ""
    if req.contract_text and len(req.contract_text.strip()) > 50:
        contract_block = f"""
=== CONTRACT TEXT (analyze every clause) ===
---
{req.contract_text[:6000]}
---
"""

    # Additional documents block
    additional_block = ""
    if req.additional_documents and len(req.additional_documents.strip()) > 20:
        additional_block = f"""
=== ADDITIONAL DOCUMENTS PROVIDED BY USER ===
Analyze each document carefully and cross-reference with the contract and property data.
---
{req.additional_documents[:4000]}
---
"""

    # Energy certificate rules
    energia_block = ""
    if req.cert_energia_estado:
        if req.cert_energia_estado == 'no':
            energia_block = "ENERGY CERTIFICATE: NOT PROVIDED. FLAG as orange alert — certificado de eficiencia energética is mandatory for property sales in Spain (RD 235/2013, art. 14). Without it, seller cannot legally sell and buyer can claim nullity or price reduction."
        elif req.cert_energia_estado == 'caducado':
            energia_block = f"ENERGY CERTIFICATE: PROVIDED BUT EXPIRED. FLAG as orange alert — expired certificate is invalid. Must be renewed before escritura. Rating was: {req.cert_energia_calificacion or 'unknown'}."
        elif req.cert_energia_estado == 'si':
            rating = req.cert_energia_calificacion or 'unknown'
            if rating in ('F', 'G'):
                energia_block = f"ENERGY CERTIFICATE: Valid, rating {rating} (very low efficiency). Note for buyer: high energy costs likely. Mention as yellow alert."
            else:
                energia_block = f"ENERGY CERTIFICATE: Valid, rating {rating}. No issues."

    if energia_block:
        additional_block = (additional_block or "") + "\n" + energia_block

    lang_reminder = {
        "sv": "ALL JSON fields in SWEDISH. Only alerts[].clause in Spanish.",
        "es": "Todo en español.",
        "en": "ALL JSON fields in ENGLISH. Only alerts[].clause in Spanish."
    }.get(req.language, "ALL JSON fields in SWEDISH.")

    return f"""You are Hugo Gutiérrez Colás, Abogado español colegiado nr 6.539 ICALI, with 19 years of experience in real estate law on Costa Blanca, Spain. You work through Colás Jurist (colasjurist.se) and specialize in protecting Swedish buyers in Spanish property transactions.

{lang_instruction}

{context_block}
{contract_block}
{additional_block}

=== YOUR MISSION ===

You are performing a COMPLETE REAL ESTATE DUE DILIGENCE. Your job is NOT to summarize documents — your job is to determine whether this transaction is LEGALLY SAFE TO PROCEED.

The constant question you must ask yourself: "What is missing that would allow me to confirm this purchase is legally safe?"

You must reason and act EXACTLY like an expert real estate lawyer — detecting not only what appears in the data, but above all what is ABSENT and what needs to be verified or obtained before recommending the transaction.

Never assume that the documentation provided is sufficient.
Never finalize the analysis while relevant aspects remain unverified.
Always propose the legal solution for every risk you identify.
Always draft specific clause text for every contractual gap.

=== MANDATORY ANALYSIS AREAS ===

**1. REGISTRO DE LA PROPIEDAD**
Check: ownership (titularity), ownership percentages, mortgages, embargos, condiciones resolutorias, usufructos, servidumbres, anotaciones preventivas, afecciones fiscales, limitaciones, prohibiciones de disponer, registered description, surface area, obra nueva inscrita, división horizontal, community quotas.
For ANY registered charge: state risk + consequences + additional documents needed + prior action required + who must assume it + recommended contract clause.

**2. CATASTRO**
Check: reference, use classification, surface area, constructions, pools, garages, annexes, year, valor catastral, differences vs Registry.
If discrepancies exist: explain ALL legal consequences, request necessary documentation, propose corrective action. Flag: undeclared pools, terraces, extensions, garages, porches, pergolas, auxiliary constructions.

**3. URBANISMO / URBAN PLANNING**
Detect: unlicensed works, unregistered extensions, change of use, fuera de ordenación status, demolition risk, urban infraction expedients. For rural/rústico land: very high alert — dwelling on rústico land typically illegal in Comunitat Valenciana.
Always specify: what risks exist, what actions must be taken, who bears cost, what clauses to add.

**4. LEY DE COSTAS**
If coastal zone indicated OR property near coast: MANDATORY questions about deslinde, servidumbre de protección (0-100m), servidumbre de tránsito, concesión administrativa, pending expedients. Explain consequences fully.

**5. HIPOTECAS Y EMBARGOS**
If mortgage exists: Is it economically cancelled? Registrally cancelled? Who cancels? Before or simultaneous with escritura? Recommend: retention clause, simultaneous cancellation, outstanding balance certificate.
If embargo: risk level, purchase viability, cancellation necessity, creditor intervention, required clauses.

**6. PROPIEDAD HORIZONTAL (if applicable)**
MANDATORY questions if community property — flag as missing if not provided:
- Community debt certificate (certificado de deuda)
- Last 3 sets of minutes (actas)
- Community statutes (estatutos)
- Internal regulations (normas internas)
- Approved special levies (derramas aprobadas)
- Planned works
- Litigation
- Defaulting owners
- Tourist rental permission
- Statutory restrictions
- Rehabilitation plans
- Judicial claims

**7. FISCALIDAD**
Check: ITP vs IVA+AJD (correct tax regime), plusvalía municipal (who pays), 3% non-resident retention (Modelo 211), IBI settlement, basura (waste tax). Flag any fiscal risk.

**8. CONTRACT ANALYSIS**
Classify contract type. Detect: abusive clauses, dangerous clauses, missing clauses, insufficient deadlines, incorrect expense distribution, missing suspensive conditions, missing charges clauses, missing urbanistic clauses, missing community clauses, missing fiscal clauses, missing occupant regulation, missing utilities regulation, missing furniture regulation, missing mortgage cancellation regulation, missing embargo cancellation, missing licence regulation.

**9. SITUACIÓN POSESORIA**
Is the property occupied? By whom? Tenants? Squatters? When will it be vacated? What is the legal title of the occupant?

**10. LICENCIAS**
For new builds: seguro decenal, licencia de primera ocupación, certificado de fin de obra, signed by architect. For resale: verify LPO exists and is valid.

=== SITUATIONAL RULES — APPLY ALL THAT MATCH ===

MORTGAGE REGISTERED:
→ RED alert. Request: (a) "Certificado de deuda pendiente" from lender; (b) retention clause authorising buyer to withhold from price the mortgage cancellation amount; (c) clause requiring registral cancellation before or simultaneous with escritura.
→ Clause: "El comprador retendrá de la cantidad a entregar en escritura el importe necesario para la cancelación registral de la hipoteca que grava la finca, cuyo saldo será acreditado mediante certificado de deuda emitido por la entidad acreedora con una antelación máxima de 10 días hábiles a la fecha de la escritura pública de compraventa."

UNDECLARED WORKS / DISCREPANCY CATASTRO-REGISTRO:
→ RED alert. Require seller to: (a) declare obra nueva before escritura; (b) OR agree price retention for cost of legalisation; (c) provide declaración de antigüedad certificate.
→ Clause: "El vendedor se obliga a declarar ante Notario la obra nueva correspondiente a [descripción] antes de la firma de la escritura pública de compraventa, siendo dicho trámite condición esencial del presente contrato. En caso de incumplimiento, el comprador podrá resolver el contrato con devolución del doble de las arras entregadas."

COASTAL ZONE / LEY DE COSTAS:
→ ORANGE/RED alert. Request: certificado de no afección costas from Demarcación de Costas, deslinde maritime-terrestrial domain, confirmation of any concesión administrativa.
→ Clause: "El vendedor garantiza que la finca no se halla dentro del dominio público marítimo-terrestre ni de la servidumbre de protección de la Ley 22/1988 de Costas, aportando certificación de la Demarcación de Costas del Estado con carácter previo a la escritura pública."

URBAN INFRACTION / RÚSTICO LAND:
→ RED alert. Request: certificado de no expediente de infracción urbanística from ayuntamiento; certificado de antigüedad; check fuera de ordenación.
→ Clause: "El vendedor garantiza que la finca y todas las construcciones existentes no son objeto de expediente de infracción urbanística, disciplina urbanística o procedimiento de demolición, comprometiéndose a aportar certificado del Ayuntamiento acreditativo de dicha circunstancia antes de la escritura pública."

NON-RESIDENT SELLER (vendedor no residente en España):
→ RED alert. CRITICAL TAX RULE: When the SELLER is non-resident in Spain, the BUYER must withhold 3% of the purchase price and pay it to AEAT via Modelo 211 within 30 days of escritura (art. 25.2 LIRNR).
→ IMPORTANT: This rule applies to the SELLER being non-resident — NOT the buyer. If the buyer is non-resident but the seller IS resident, this rule does NOT apply.
→ Do NOT confuse buyer non-residency with seller non-residency. The 3% retention is ALWAYS about the seller's tax residency status.
→ Clause: "En cumplimiento del art. 25.2 LIRNR, el comprador retendrá el 3% del precio pactado ([importe] €) e ingresará dicho importe en la Agencia Tributaria mediante Modelo 211 en el plazo de un mes desde la escritura pública de compraventa, por ser el vendedor no residente fiscal en España."

PRICE BELOW VALOR DE REFERENCIA:
→ RED alert. AEAT taxes buyer on valor de referencia, not purchase price. Buyer will face unexpected tax demand.

ARRAS PENITENCIALES WITHOUT SYMMETRIC PENALTY:
→ RED alert. Seller must face equivalent deterrent. If seller penalty ≠ "doble de las arras", contract is asymmetric against buyer.

NO FINANCING CONDITION + BUYER NEEDS MORTGAGE:
→ RED alert. Buyer will lose deposit if bank refuses mortgage.
→ Clause: "La presente compraventa queda sujeta a la condición suspensiva de obtención de financiación hipotecaria por importe mínimo de [X] € en plazo de [N] días. De no obtenerse, el contrato quedará resuelto sin penalización, con devolución íntegra de las cantidades entregadas."

COMMUNITY DEBT CERTIFICATE MISSING:
→ ORANGE alert. Buyer may inherit unpaid community fees (debts of up to 1 year attach to the property by law — art. 9.1.e LPH).
→ Clause: "El vendedor aportará certificado de estar al corriente en el pago de las cuotas de la Comunidad de Propietarios, conforme al art. 9.1.e de la LPH, con anterioridad a la escritura pública."

IBI NOT UP TO DATE:
→ ORANGE alert. IBI debt of last 4 years attaches to property and follows the property on sale.
→ Documents: recibo IBI año en curso + certificado de no deudas municipales.

NO LICENCIA DE PRIMERA OCUPACIÓN (new build or unknown):
→ RED alert for new builds. Without LPO, water/electricity cannot be connected legally and buyer cannot legally inhabit.

SHORT DEADLINE TO ESCRITURA (< 30 days):
→ ORANGE alert. Insufficient time for searches, mortgage, obra nueva declaration, certificates.

EMPRESA AS SELLER:
→ ORANGE alert. Verify: autorización del órgano social competente, tax status, latent corporate taxes. Request: certificado de deudas con AEAT y Seguridad Social.

=== SCORING ===
Start 100. Deduct:
- 25 per RED alert (critical — do not sign until resolved)
- 12 per ORANGE alert (important — strongly recommended)
- 5 per YELLOW alert
Minimum 0.

CLASIFICACION FINAL:
- Score 80-100, no reds: "puede_firmarse"
- Score 50-79, or reds fixable by clause: "puede_firmarse_con_modificaciones"
- Score < 50, or unresolvable reds: "no_deberia_firmarse"

=== OUTPUT ===
FINAL REMINDER — LANGUAGE: {lang_reminder}

Respond ONLY with valid JSON (no markdown fences). Clause texts (alerts[].clause field only) always in Spanish. All other fields in the required language above.

{{
  "score": <0-100>,
  "risk_level": "<low|medium|high|critical>",
  "clasificacion_final": "<puede_firmarse|puede_firmarse_con_modificaciones|no_deberia_firmarse>",
  "summary": "<Executive summary: 3-4 sentences. State the biggest risk, the most critical missing document, and the final recommendation>",
  "alerts": [
    {{
      "level": "<red|orange|yellow|green>",
      "category": "<registral|catastral|urbanismo|comunidad|fiscal|contrato|posesion|licencias|costas|otro>",
      "title": "<concise title>",
      "body": "<detailed explanation of the risk and its practical consequences for the buyer>",
      "clause": "<recommended protective clause in Spanish legal language — required for all red and orange alerts, null otherwise>",
      "documents": ["<specific document name>", ...],
      "actuacion_previa": "<what must be done BEFORE signing, or null>",
      "quien_asume": "<vendedor|comprador|ambos|null>",
      "action": "<concrete next step for buyer>"
    }}
  ],
  "documentacion_aportada": ["<doc name>", ...],
  "documentacion_pendiente": ["<doc name — what has not been provided but is essential>", ...],
  "missing_clauses": ["<clause name>", ...],
  "dangerous_clauses": ["<description of problematic clause found in contract text>", ...],
  "actuaciones_previas_imprescindibles": ["<action that MUST happen before signing>", ...],
  "actuaciones_recomendadas": ["<recommended but not strictly mandatory action>", ...],
  "clausulas_adicionales_recomendadas": ["<clause name + one-line description>", ...],
  "recommended_actions": ["<prioritized concrete action for buyer>", ...],
  "documents_to_request": ["<document name>", ...],
  "checklist_antes_de_firmar": ["<item>", ...],
  "checklist_antes_de_escritura": ["<item>", ...],
  "preguntas_adicionales": ["<dynamic follow-up question the buyer should answer to complete the due diligence>", ...]
}}

Generate maximum 12 alerts. Focus RED alerts first. Be exhaustive in documentacion_pendiente — list everything that is missing that a diligent lawyer would require. Generate 5-8 preguntas_adicionales for any aspect that was unknown or not provided.
"""


# ── Endpoint ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "due-diligence-inmobiliaria",
        "version": "3.0.0",
        "api_key_set": bool(ANTHROPIC_KEY),
        "api_key_prefix": ANTHROPIC_KEY[:12] + "..." if ANTHROPIC_KEY else "NOT SET"
    }

@app.post("/analyze", response_model=DueDiligenceReport)
async def analyze_contract(req: ContractRequest):
    if not ANTHROPIC_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")

    prompt = build_prompt(req)

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 4096,
                "system": f"You are a Spanish real estate lawyer. {get_lang_sys(req.language)}",
                "messages": [{"role": "user", "content": prompt}]
            }
        )

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Claude API error: {response.status_code} — {response.text[:300]}")

    data = response.json()
    text = data["content"][0]["text"].strip()

    # Strip markdown fences
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:])
        if text.endswith("```"):
            text = text[:-3].strip()

    # Default empty lists for new fields
    new_fields = [
        "documentacion_aportada", "documentacion_pendiente", "missing_clauses",
        "dangerous_clauses", "actuaciones_previas_imprescindibles", "actuaciones_recomendadas",
        "clausulas_adicionales_recomendadas", "recommended_actions", "documents_to_request",
        "checklist_antes_de_firmar", "checklist_antes_de_escritura", "preguntas_adicionales"
    ]

    try:
        result = json.loads(text)
        for f in new_fields:
            if f not in result:
                result[f] = []
        if "clasificacion_final" not in result:
            s = result.get("score", 50)
            result["clasificacion_final"] = "puede_firmarse" if s >= 80 else "puede_firmarse_con_modificaciones" if s >= 50 else "no_deberia_firmarse"
        return DueDiligenceReport(**result)
    except json.JSONDecodeError:
        # Robust recovery
        try:
            import re
            score_m = re.search(r'"score":\s*(\d+)', text)
            risk_m = re.search(r'"risk_level":\s*"([^"]+)"', text)
            summary_m = re.search(r'"summary":\s*"([^"]+)"', text)
            clasif_m = re.search(r'"clasificacion_final":\s*"([^"]+)"', text)

            complete_alerts = []
            for m in re.finditer(r'\{[^{}]*"level"[^{}]*"title"[^{}]*"body"[^{}]*\}', text, re.S):
                try:
                    a = json.loads(m.group(0))
                    complete_alerts.append(a)
                except:
                    pass

            score = int(score_m.group(1)) if score_m else 40
            risk = risk_m.group(1) if risk_m else "high"
            summary = summary_m.group(1) if summary_m else "Análisis parcial completado — revise las alertas."
            clasif = clasif_m.group(1) if clasif_m else "no_deberia_firmarse"

            return DueDiligenceReport(
                score=score, risk_level=risk, clasificacion_final=clasif,
                summary=summary, alerts=complete_alerts[:8],
                **{f: [] for f in new_fields}
            )
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Parse error: {str(e2)}\nRaw: {text[:300]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ── PDF Generation Endpoint ────────────────────────────────────────────────

class PdfRequest(BaseModel):
    lang: str = "sv"
    property: Optional[dict] = None
    catastro: Optional[dict] = None
    registro: Optional[dict] = None
    urbanismo: Optional[dict] = None
    analysis: Optional[dict] = None   # Claude due diligence result

@app.post("/generate-pdf")
async def generate_pdf_endpoint(req: PdfRequest):
    """Generate a Due Diligence PDF and return it as a download."""
    try:
        from pdf_generator import generate_pdf
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"PDF generator not available: {e}")

    report_data = {
        "lang":      req.lang,
        "property":  req.property  or {},
        "catastro":  req.catastro  or {},
        "registro":  req.registro  or {},
        "urbanismo": req.urbanismo or {},
        "analysis":  req.analysis  or {},
    }

    # Build safe filename
    addr = (req.property or {}).get("direccion", "due-diligence")
    safe = "".join(c for c in addr if c.isalnum() or c in " -_")[:40].strip().replace(" ", "_")
    filename = f"DueDiligence_{safe}_ColasJurist.pdf"

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, filename)
        try:
            generate_pdf(report_data, out_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF generation error: {e}")

        with open(out_path, "rb") as f:
            pdf_bytes = f.read()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
