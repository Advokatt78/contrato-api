"""
Due Diligence PDF Generator — Colás Jurist
Estructura profesional: portada, 6 secciones, tabla de riesgos, firma
"""
import sys, json, os, requests, datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import Flowable

# ── Brand colors ────────────────────────────────────────────────────────────
NAVY      = HexColor('#1C2B3A')
GOLD      = HexColor('#B8975A')
CRIMSON   = HexColor('#9B2335')
CREAM     = HexColor('#F7F4EF')
LIGHT_BG  = HexColor('#F8F7F4')
BORDER    = HexColor('#D4D1CA')
TEXT      = HexColor('#28251D')
MUTED     = HexColor('#6B7280')
RED_RISK  = HexColor('#DC2626')
RED_BG    = HexColor('#FEF2F2')
ORG_RISK  = HexColor('#EA580C')
ORG_BG    = HexColor('#FFF7ED')
YEL_RISK  = HexColor('#D97706')
YEL_BG    = HexColor('#FFFBEB')
GRN_RISK  = HexColor('#16A34A')
GRN_BG    = HexColor('#F0FDF4')
BLUE_BG   = HexColor('#EFF6FF')
BLUE_RISK = HexColor('#1D4ED8')

# ── Multilingual labels ──────────────────────────────────────────────────────
def T(lang, key):
    """Get translated label."""
    LABELS = {
        'report_title':        {'sv': 'RAPPORT FASTIGHETS-DUE DILIGENCE', 'es': 'INFORME DE DUE DILIGENCE INMOBILIARIA', 'en': 'REAL ESTATE DUE DILIGENCE REPORT'},
        'ai_notice':           {'sv': 'Genererad med artificiell intelligens', 'es': 'Generado con inteligencia artificial', 'en': 'Generated with artificial intelligence'},
        'elaborado':           {'sv': 'Colás Jurist AI Due Diligence', 'es': 'Colás Jurist AI Due Diligence', 'en': 'Colás Jurist AI Due Diligence'},
        'alcance':             {'sv': 'Juridisk och urbanistisk due diligence (AI-genererad)', 'es': 'Due diligence jurídica y urbanística (generada por IA)', 'en': 'Legal and urban planning due diligence (AI-generated)'},
        'disclaimer_cover':    {
            'sv': 'VIKTIGT: Denna rapport har genererats automatiskt med artificiell intelligens baserat på den information som användaren tillhandahållit. Den utgör INTE juridisk rådgivning, är INTE bindande och kan innehålla fel eller ofullständiga uppgifter. Rapporten måste granskas av en kvalificerad jurist innan den används som beslutsunderlag. Colás Jurist ansvarar inte för beslut fattade enbart på grundval av detta dokument.',
            'es': 'AVISO IMPORTANTE: Este informe ha sido generado automáticamente mediante inteligencia artificial a partir de la información aportada por el usuario. NO constituye asesoramiento jurídico vinculante, NO garantiza la exactitud de los datos y PUEDE contener errores u omisiones. El informe debe ser revisado por un abogado cualificado antes de ser utilizado como base para cualquier decisión. Colás Jurist no se responsabiliza de las decisiones adoptadas exclusivamente en base a este documento.',
            'en': 'IMPORTANT NOTICE: This report has been automatically generated using artificial intelligence based on the information provided by the user. It does NOT constitute legal advice, is NOT legally binding and MAY contain errors or omissions. This report must be reviewed by a qualified lawyer before being used as a basis for any decision. Colás Jurist accepts no responsibility for decisions made solely on the basis of this document.',
        },
        's01':                 {'sv': 'FASTIGHETENS IDENTIFIERING', 'es': 'IDENTIFICACIÓN DEL INMUEBLE', 'en': 'PROPERTY IDENTIFICATION'},
        's02':                 {'sv': 'REGISTERUPPGIFTER', 'es': 'SITUACIÓN REGISTRAL', 'en': 'LAND REGISTRY STATUS'},
        's02_1':               {'sv': 'Registerdata', 'es': 'Datos registrales', 'en': 'Registry data'},
        's02_2':               {'sv': 'Belastningar och gravamen', 'es': 'Cargas y gravámenes', 'en': 'Charges and encumbrances'},
        's02_nota':            {'sv': 'Innehåll i nota simple:', 'es': 'Contenido de la nota simple:', 'en': 'Nota simple content:'},
        's03':                 {'sv': 'KATASTRALSITUATION', 'es': 'SITUACIÓN CATASTRAL', 'en': 'CADASTRAL STATUS'},
        's04':                 {'sv': 'URBANISTISK SITUATION', 'es': 'SITUACIÓN URBANÍSTICA', 'en': 'URBAN PLANNING STATUS'},
        's04_cedula':          {'sv': 'Innehåll i cédula urbanística:', 'es': 'Contenido de la cédula urbanística:', 'en': 'Cédula urbanística content:'},
        's05':                 {'sv': 'RISKKARTA', 'es': 'MAPA DE RIESGOS', 'en': 'RISK MAP'},
        's06':                 {'sv': 'SLUTSATSER OCH REKOMMENDATIONER', 'es': 'CONCLUSIÓN Y RECOMENDACIONES', 'en': 'CONCLUSIONS AND RECOMMENDATIONS'},
        'risk_area':           {'sv': 'Riskområde', 'es': 'Área de riesgo', 'en': 'Risk area'},
        'risk_level':          {'sv': 'Nivå', 'es': 'Nivel', 'en': 'Level'},
        'risk_desc':           {'sv': 'Beskrivning', 'es': 'Descripción', 'en': 'Description'},
        'clasif_label': {
            'sv': {'puede_firmarse': 'KAN UNDERTECKNAS', 'puede_firmarse_con_modificaciones': 'KAN UNDERTECKNAS MED ÄNDRINGAR', 'no_deberia_firmarse': 'BÖR INTE UNDERTECKNAS'},
            'es': {'puede_firmarse': 'PUEDE FIRMARSE', 'puede_firmarse_con_modificaciones': 'PUEDE FIRMARSE CON MODIFICACIONES', 'no_deberia_firmarse': 'NO DEBERÍA FIRMARSE'},
            'en': {'puede_firmarse': 'CAN BE SIGNED', 'puede_firmarse_con_modificaciones': 'CAN BE SIGNED WITH AMENDMENTS', 'no_deberia_firmarse': 'SHOULD NOT BE SIGNED'},
        },
        'indice':              {'sv': 'Juridiskt index', 'es': 'Índice jurídico', 'en': 'Legal index'},
        'critico':             {'sv': 'kritisk(a)', 'es': 'crítico(s)', 'en': 'critical'},
        'importante':          {'sv': 'viktig(a)', 'es': 'importante(s)', 'en': 'important'},
        'moderado':            {'sv': 'måttlig(a)', 'es': 'moderado(s)', 'en': 'moderate'},
        'problemas_criticos':  {'sv': 'Kritiska problem — måste lösas före undertecknande', 'es': 'Problemas críticos — deben resolverse antes de firmar', 'en': 'Critical issues — must be resolved before signing'},
        'advertencias':        {'sv': 'Viktiga varningar', 'es': 'Advertencias importantes', 'en': 'Important warnings'},
        'puntos_atencion':     {'sv': 'Informationspunkter', 'es': 'Puntos de atención', 'en': 'Notes'},
        'aspectos_orden':      {'sv': 'Punkter i ordning', 'es': 'Aspectos en orden', 'en': 'Points in order'},
        'clausulas_missing':   {'sv': 'Kontraktsklausuler att lägga till', 'es': 'Cláusulas contractuales a incorporar', 'en': 'Contract clauses to be added'},
        'chk_firmar':          {'sv': 'Checklista före undertecknande', 'es': 'Checklist antes de firmar el contrato', 'en': 'Checklist before signing the contract'},
        'chk_escritura':       {'sv': 'Checklista inför notariemötet', 'es': 'Checklist antes del otorgamiento de escritura', 'en': 'Checklist before the notarial deed'},
        'actuaciones':         {'sv': 'Ofrånkomliga åtgärder', 'es': 'Actuaciones previas imprescindibles', 'en': 'Mandatory prior actions'},
        'preguntas':           {'sv': 'Aspekter som kräver verifiering', 'es': 'Aspectos pendientes de verificar', 'en': 'Aspects requiring verification'},
        'accion':              {'sv': 'Åtgärd', 'es': 'Acción', 'en': 'Action'},
        'actuacion':           {'sv': 'Åtgärd', 'es': 'Actuación', 'en': 'Action'},
        'docs_solicitar':      {'sv': 'Dokument att begära:', 'es': 'Documentos a solicitar:', 'en': 'Documents to request:'},
        'clausula_recom':      {'sv': 'Rekommenderad klausul:', 'es': 'Cláusula recomendada:', 'en': 'Recommended clause:'},
        'cargas_ninguna':      {'sv': 'Inga registrerade belastningar eller gravamen pa fastigheten.', 'es': 'No constan cargas registrales ni gravamenes sobre la finca.', 'en': 'No registered charges or encumbrances on the property.'},
        'cargas_hipoteca':     {'sv': 'Fastigheten är belastad med inteckning. Se riskanalys.', 'es': 'La finca esta gravada con hipoteca. Ver analisis de riesgos.', 'en': 'The property is subject to a mortgage. See risk analysis.'},
        'cargas_embargo':      {'sv': 'Fastigheten har en utmätningsanteckning. Se riskanalys.', 'es': 'La finca presenta anotacion de embargo. Ver analisis de riesgos.', 'en': 'The property has an embargo annotation. See risk analysis.'},
        'cargas_unknown':      {'sv': 'Ingen nota simple har tillhandahållits. Brådskande registerkontroll rekommenderas.', 'es': 'No se ha facilitado la nota simple. Consulta urgente del Registro recomendada.', 'en': 'No nota simple has been provided. Urgent land registry check is recommended.'},
        'disc_alert':          {'sv': 'AVVIKELSE REGISTER / KATASTRAL', 'es': 'DISCREPANCIA REGISTRAL / CATASTRAL', 'en': 'REGISTRY / CADASTRAL DISCREPANCY'},
        'disc_diff':           {'sv': 'Skillnad', 'es': 'Diferencia', 'en': 'Difference'},
        'disc_body': {
            'sv': lambda reg, cat, diff: f"Det finns en avvikelse på {diff:.0f} m² mellan den inskrivna ytan i Registret ({reg} m²) och den i Catastro redovisade ({cat} m²). Ytterligare konstruktioner kan saknas i Registret, vilket kräver en deklaration om obra nueva före notarieakten.",
            'es': lambda reg, cat, diff: f"Existe una divergencia de {diff:.0f} m² entre la superficie inscrita en el Registro ({reg} m²) y la reflejada en el Catastro ({cat} m²). Las construcciones adicionales pueden no constar inscritas registralmente, lo que requiere declaración de obra nueva antes de la escritura.",
            'en': lambda reg, cat, diff: f"There is a discrepancy of {diff:.0f} m² between the area registered in the Land Registry ({reg} m²) and that shown in the Cadastre ({cat} m²). Additional constructions may not be registered, requiring an obra nueva declaration before the deed.",
        },
        'footer_author':       {'sv': 'Colás Jurist · AI Due Diligence · colasjurist.se', 'es': 'Colás Jurist · AI Due Diligence · colasjurist.se', 'en': 'Colás Jurist · AI Due Diligence · colasjurist.se'},
        'footer_pagina':       {'sv': 'Sida', 'es': 'Página', 'en': 'Page'},
        'sig_title':           {'sv': 'Colás Jurist AI Due Diligence', 'es': 'Colás Jurist AI Due Diligence', 'en': 'Colás Jurist AI Due Diligence'},
        'sig_sub':             {'sv': 'Automatisk juridisk analys · Granskas av Hugo Gutiérrez Colás, Abogado nr 6.539 ICALI', 'es': 'Análisis jurídico automático · Para revisión por Hugo Gutiérrez Colás, Abogado nr 6.539 ICALI', 'en': 'Automated legal analysis · For review by Hugo Gutiérrez Colás, Abogado nr 6.539 ICALI'},
        'sig_addr':            {'sv': 'Calle Mozart 9 · 03581 Alfaz del Pi (Alicante) · Spanien', 'es': 'Calle Mozart 9 · 03581 Alfaz del Pi (Alicante) · España', 'en': 'Calle Mozart 9 · 03581 Alfaz del Pi (Alicante) · Spain'},
        'sig_disclaimer':      {
            'sv': 'OBS: Denna rapport är automatiskt genererad med AI och utgör inte bindande juridisk rådgivning. Granska alltid med en kvalificerad jurist.',
            'es': 'AVISO: Este informe es generado automáticamente por IA y no constituye asesoramiento jurídico vinculante. Revise siempre con un abogado cualificado.',
            'en': 'NOTICE: This report is automatically generated by AI and does not constitute binding legal advice. Always review with a qualified lawyer.',
        },
        'risk_critico':   {'sv': 'KRITISK', 'es': 'CRÍTICO', 'en': 'CRITICAL'},
        'risk_importante': {'sv': 'VIKTIG', 'es': 'IMPORTANTE', 'en': 'IMPORTANT'},
        'risk_moderado':  {'sv': 'MÅTTLIG', 'es': 'MODERADO', 'en': 'MODERATE'},
        'risk_ok':        {'sv': 'OK', 'es': 'OK', 'en': 'OK'},
        'header_conf':    {'sv': 'RAPPORT FASTIGHETS-DUE DILIGENCE · AI-GENERERAD', 'es': 'INFORME DE DUE DILIGENCE INMOBILIARIA · GENERADO POR IA', 'en': 'REAL ESTATE DUE DILIGENCE REPORT · AI-GENERATED'},
        'header_right':   {'sv': 'Colás Jurist · colasjurist.se', 'es': 'Colás Jurist · colasjurist.se', 'en': 'Colás Jurist · colasjurist.se'},
        'fecha_informe':  {'sv': 'Rapportdatum', 'es': 'Fecha del informe', 'en': 'Report date'},
        'ref_exp':        {'sv': 'AI Due Diligence · colasjurist.se', 'es': 'AI Due Diligence · colasjurist.se', 'en': 'AI Due Diligence · colasjurist.se'},
        'conf_line1':     {'sv': 'Denna rapport har genererats automatiskt med AI och är INTE juridiskt bindande rådgivning.', 'es': 'Este informe ha sido generado automáticamente por IA y NO constituye asesoramiento jurídico vinculante.', 'en': 'This report has been automatically generated by AI and does NOT constitute legally binding advice.'},
        'conf_line2':     {'sv': 'Innehållet är konfidentiellt. Måste granskas av en kvalificerad jurist.', 'es': 'El contenido es confidencial. Debe ser revisado por un abogado cualificado.', 'en': 'The content is confidential. Must be reviewed by a qualified lawyer.'},
        'lbl_direccion':   {'sv': 'Adress', 'es': 'Dirección', 'en': 'Address'},
        'lbl_ref_cat':     {'sv': 'Katastralbeteckning', 'es': 'Referencia catastral', 'en': 'Cadastral reference'},
        'lbl_registro':    {'sv': 'Fastighetsregister', 'es': 'Registro de la Propiedad', 'en': 'Land Registry'},
        'lbl_tipo':        {'sv': 'Fastighetstyp', 'es': 'Tipo de inmueble', 'en': 'Property type'},
        'lbl_municipio':   {'sv': 'Kommun', 'es': 'Municipio', 'en': 'Municipality'},
        'lbl_anno':        {'sv': 'Byggnadsår', 'es': 'Año de construcción', 'en': 'Year built'},
        'lbl_precio':      {'sv': 'Köpesumma', 'es': 'Precio de compraventa', 'en': 'Purchase price'},
        'lbl_vendedor':    {'sv': 'Säljare', 'es': 'Vendedor', 'en': 'Seller'},
        'lbl_estado':      {'sv': 'Nuvarande status', 'es': 'Estado actual', 'en': 'Current status'},
        'lbl_finca':       {'sv': 'Fastighetsnummer', 'es': 'N.º de finca', 'en': 'Property no.'},
        'lbl_sup_constr':  {'sv': 'Byggd yta (inskriven)', 'es': 'Superficie inscrita (construida)', 'en': 'Built area (registered)'},
        'lbl_sup_parcela': {'sv': 'Tomtyta (inskriven)', 'es': 'Superficie inscrita (parcela)', 'en': 'Plot area (registered)'},
        'lbl_titularidad': {'sv': 'Ägarskap', 'es': 'Titularidad', 'en': 'Ownership'},
        'lbl_coord_cat':   {'sv': 'Koordinering med Catastro', 'es': 'Coordinación con Catastro', 'en': 'Coordination with Cadastre'},
        'lbl_sup_cat':     {'sv': 'Byggd yta (Catastro)', 'es': 'Superficie construida', 'en': 'Built area (Cadastre)'},
        'lbl_sup_parc_cat':{'sv': 'Tomtyta (Catastro)', 'es': 'Superficie de parcela', 'en': 'Plot area (Cadastre)'},
        'lbl_anno_cat':    {'sv': 'Byggnadsår (Catastro)', 'es': 'Año de construcción', 'en': 'Year built (Cadastre)'},
        'lbl_val_cat':     {'sv': 'Katastralt värde', 'es': 'Valor catastral', 'en': 'Cadastral value'},
        'lbl_val_ref':     {'sv': 'Referensvärde (AEAT)', 'es': 'Valor de referencia (AEAT)', 'en': 'Reference value (AEAT)'},
        'lbl_piscina':     {'sv': 'Pool i Catastro', 'es': 'Piscina en Catastro', 'en': 'Pool in Cadastre'},
        'lbl_garaje':      {'sv': 'Garage i Catastro', 'es': 'Garaje en Catastro', 'en': 'Garage in Cadastre'},
        'lbl_clasificacion':{'sv': 'Markklass', 'es': 'Clasificación del suelo', 'en': 'Land classification'},
        'lbl_costas':      {'sv': 'Kustzon (Ley de Costas)', 'es': 'Zona costera (Ley de Costas)', 'en': 'Coastal zone (Ley de Costas)'},
        'lbl_lpo':         {'sv': 'Första uthyrningslicens', 'es': 'Licencia de primera ocupación', 'en': 'First occupation licence'},
        'lbl_expediente':  {'sv': 'Urbanistiskt ärende', 'es': 'Expediente urbanístico', 'en': 'Urban planning case'},
        'lbl_elaborado':   {'sv': 'Sammanställd av', 'es': 'Elaborado por', 'en': 'Prepared by'},
        'lbl_alcance':     {'sv': 'Omfattning', 'es': 'Alcance', 'en': 'Scope'},
        'lbl_fecha':       {'sv': 'Rapportdatum', 'es': 'Fecha del informe', 'en': 'Report date'},
        'lbl_ref_exp':     {'sv': 'Katastralbeteckning', 'es': 'Referencia catastral', 'en': 'Cadastral reference'},
        'val_si':          {'sv': 'Ja — granska deslinde', 'es': 'Sí — revisar deslinde', 'en': 'Yes — check deslinde'},
        'val_no':          {'sv': 'Nej', 'es': 'No', 'en': 'No'},
        'val_segunda':     {'sv': 'Andrahandsmarknad (begagnad)', 'es': 'Segunda mano', 'en': 'Resale (second-hand)'},
        'val_nueva':       {'sv': 'Nyproduktion', 'es': 'Obra nueva', 'en': 'New build'},
        'val_rustico':     {'sv': 'Lantlig fastighet', 'es': 'Rústico', 'en': 'Rural property'},
        'val_no_urb':      {'sv': 'Icke-urbaniserbar mark', 'es': 'No urbanizable', 'en': 'Non-developable land'},
        'val_urbano':      {'sv': 'Stadsmark', 'es': 'Urbano', 'en': 'Urban land'},
        'val_unknown':     {'sv': 'Okänd', 'es': 'Desconocido', 'en': 'Unknown'},
        'txt_full_exp':    {'sv': '[Fullständig text tillgänglig i ärendet]', 'es': '[Texto completo disponible en el expediente]', 'en': '[Full text available in the file]'},
        'disc_body_sv':    {'sv': lambda r, ca, d: f"Det finns en avvikelse på {d:.0f} m² mellan den inskrivna ytan i Registret ({r} m²) och den i Catastro ({ca} m²). Ytterligare konstruktioner saknas i Registret — declaración de obra nueva krävs.", 'es': lambda r, ca, d: f"Existe una divergencia de {d:.0f} m² entre la superficie inscrita en el Registro ({r} m²) y la reflejada en el Catastro ({ca} m²). Se requiere declaración de obra nueva.", 'en': lambda r, ca, d: f"There is a discrepancy of {d:.0f} m² between the Land Registry ({r} m²) and the Cadastre ({ca} m²). An obra nueva declaration is required."},
    }
    return LABELS.get(key, {}).get(lang, LABELS.get(key, {}).get('en', key))


# ── Download & register fonts ────────────────────────────────────────────────
FONT_DIR = '/tmp/pdf_fonts'
os.makedirs(FONT_DIR, exist_ok=True)

def dl_font(name, url):
    path = f'{FONT_DIR}/{name}.ttf'
    if not os.path.exists(path):
        r = requests.get(url, timeout=30)
        with open(path, 'wb') as f:
            f.write(r.content)
    return path

# DM Sans (body) + DM Serif Display (headings)
fonts = {
    'DMSans':       'https://github.com/google/fonts/raw/main/ofl/dmsans/DMSans%5Bopsz%2Cwght%5D.ttf',
    'DMSans-Bold':  'https://github.com/google/fonts/raw/main/ofl/dmsans/DMSans%5Bopsz%2Cwght%5D.ttf',
    'DMSerif':      'https://github.com/google/fonts/raw/main/ofl/dmseriftext/DMSerifText-Regular.ttf',
}

try:
    p1 = dl_font('DMSans', fonts['DMSans'])
    p2 = dl_font('DMSerif', fonts['DMSerif'])
    pdfmetrics.registerFont(TTFont('DMSans', p1))
    pdfmetrics.registerFont(TTFont('DMSans-Bold', p1))
    pdfmetrics.registerFont(TTFont('DMSerif', p2))
    BODY_FONT  = 'DMSans'
    BOLD_FONT  = 'DMSans-Bold'
    SERIF_FONT = 'DMSerif'
except Exception as e:
    print(f"Font download failed ({e}), using Helvetica")
    BODY_FONT  = 'Helvetica'
    BOLD_FONT  = 'Helvetica-Bold'
    SERIF_FONT = 'Helvetica-Bold'

W, H = A4
ML = 2.2*cm; MR = 2.2*cm; MT = 2*cm; MB = 2.5*cm

# ── Style helpers ────────────────────────────────────────────────────────────
def style(name, **kw):
    base = getSampleStyleSheet()['Normal']
    s = ParagraphStyle(name, parent=base, **kw)
    return s

S_BODY      = style('body',      fontName=BODY_FONT,  fontSize=9.5,  leading=15,   textColor=TEXT,  alignment=TA_JUSTIFY)
S_BODY_L    = style('bodyL',     fontName=BODY_FONT,  fontSize=9.5,  leading=15,   textColor=TEXT,  alignment=TA_LEFT)
S_SMALL     = style('small',     fontName=BODY_FONT,  fontSize=8,    leading=11,   textColor=MUTED)
S_CAPTION   = style('caption',   fontName=BOLD_FONT,  fontSize=8,    leading=11,   textColor=MUTED, spaceAfter=2)
S_CELL      = style('cell',      fontName=BODY_FONT,  fontSize=9,    leading=13,   textColor=TEXT)
S_CELL_B    = style('cellB',     fontName=BOLD_FONT,  fontSize=9,    leading=13,   textColor=TEXT)
S_CELL_MUT  = style('cellM',     fontName=BODY_FONT,  fontSize=8.5,  leading=12,   textColor=MUTED)
S_RISK_LBL  = style('riskL',     fontName=BOLD_FONT,  fontSize=8,    leading=11,   alignment=TA_CENTER)
S_SECTION   = style('section',   fontName=BOLD_FONT,  fontSize=13,   leading=18,   textColor=NAVY,  spaceBefore=18, spaceAfter=8)
S_SUBSEC    = style('subsec',    fontName=BOLD_FONT,  fontSize=10.5, leading=15,   textColor=NAVY,  spaceBefore=12, spaceAfter=5)
S_ALERT_T   = style('alertT',    fontName=BOLD_FONT,  fontSize=9.5,  leading=13,   textColor=TEXT)
S_ALERT_B   = style('alertB',    fontName=BODY_FONT,  fontSize=9,    leading=13,   textColor=TEXT)
S_CLAUSE    = style('clause',    fontName=BODY_FONT,  fontSize=8.5,  leading=13,   textColor=TEXT,  leftIndent=8, rightIndent=8, italics=True)
S_BULLET    = style('bullet',    fontName=BODY_FONT,  fontSize=9.5,  leading=14,   textColor=TEXT,  leftIndent=12, bulletIndent=0)
S_COVER_T   = style('covT',      fontName=SERIF_FONT, fontSize=26,   leading=32,   textColor=white, alignment=TA_LEFT)
S_COVER_SUB = style('covSub',    fontName=BODY_FONT,  fontSize=11,   leading=17,   textColor=HexColor('#B8C8D8'), alignment=TA_LEFT)
S_COVER_META= style('covMeta',   fontName=BODY_FONT,  fontSize=9,    leading=14,   textColor=HexColor('#8CA0B4'), alignment=TA_LEFT)
S_COVER_CONF= style('covConf',   fontName=BODY_FONT,  fontSize=7.5,  leading=12,   textColor=HexColor('#607080'), alignment=TA_LEFT)

# ── Custom flowables ─────────────────────────────────────────────────────────
class NavyBar(Flowable):
    """Left accent bar for section headings."""
    def __init__(self, w=3, h=18, color=GOLD):
        self.bar_w = w; self.bar_h = h; self.bar_color = color
    def wrap(self, *args): return (self.bar_w + 8, self.bar_h)
    def draw(self):
        self.canv.setFillColor(self.bar_color)
        self.canv.rect(0, 0, self.bar_w, self.bar_h, stroke=0, fill=1)

class CoverPage(Flowable):
    def __init__(self, data):
        self.data = data
        Flowable.__init__(self)

    def wrap(self, w, h): return (w, h)

    def draw(self):
        c = self.canv
        d = self.data
        pw = self.canv._pagesize[0]
        ph = self.canv._pagesize[1]

        # Full navy background
        c.setFillColor(NAVY)
        c.rect(0, 0, pw, ph, stroke=0, fill=1)

        # Gold left stripe
        c.setFillColor(GOLD)
        c.rect(0, 0, 6, ph, stroke=0, fill=1)

        # Crimson accent bar bottom
        c.setFillColor(CRIMSON)
        c.rect(0, 0, pw, 0.8*cm, stroke=0, fill=1)

        # Logo area top right
        c.setFillColor(CRIMSON)
        c.rect(pw - 5.5*cm, ph - 3.2*cm, 5.5*cm, 3.2*cm, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(pw - 5.5*cm, ph - 3.2*cm, 5.5*cm, 0.3, stroke=0, fill=1)
        c.setFont(BOLD_FONT, 11)
        c.setFillColor(white)
        c.drawString(pw - 5.2*cm, ph - 1.5*cm, "COLÁS JURIST")
        c.setFont(BODY_FONT, 7.5)
        c.setFillColor(HexColor('#B8975A'))
        c.drawString(pw - 5.2*cm, ph - 1.9*cm, "Spansk jurist · Costa Blanca")

        # INFORME heading
        c.setFont(BODY_FONT, 9)
        c.setFillColor(GOLD)
        c.drawString(ML + 0.3*cm, ph - 3.5*cm, T(d.get("lang","sv"), "report_title"))

        # Property title
        addr = d.get('direccion', d.get('municipio', 'Propiedad'))
        title_lines = [addr[i:i+40] for i in range(0, min(len(addr), 80), 40)]
        y = ph - 5*cm
        c.setFont(SERIF_FONT, 26)
        c.setFillColor(white)
        for line in title_lines[:2]:
            c.drawString(ML + 0.3*cm, y, line)
            y -= 3.2*cm

        # Metadata block
        y -= 0.5*cm
        lg = d.get('lang', 'sv')
        meta = [
            (T(lg,'lbl_ref_cat'),    d.get('ref_catastral', '—')),
            (T(lg,'lbl_registro'),   d.get('registro', '—')),
            (T(lg,'lbl_municipio'),  d.get('municipio', '—')),
            (T(lg,'lbl_fecha'),      d.get('fecha', datetime.date.today().strftime('%d %B %Y'))),
            (T(lg,'lbl_elaborado'),  T(lg, 'elaborado')),
            (T(lg,'lbl_alcance'),    T(lg, 'alcance')),
        ]
        for label, val in meta:
            c.setFont(BOLD_FONT, 8)
            c.setFillColor(GOLD)
            c.drawString(ML + 0.3*cm, y, label.upper())
            c.setFont(BODY_FONT, 9)
            c.setFillColor(HexColor('#C8D8E8'))
            c.drawString(ML + 0.3*cm + 5*cm, y, val)
            y -= 0.55*cm

        # Confidentiality notice
        y -= 0.8*cm
        c.setFont(BODY_FONT, 7.5)
        c.setFillColor(HexColor('#607080'))
        notice = T(d.get("lang","sv"), "conf_line1")
        c.drawString(ML + 0.3*cm, y, notice)
        y -= 0.4*cm
        c.drawString(ML + 0.3*cm, y, T(d.get("lang","sv"), "conf_line2"))

        # Ref number bottom
        c.setFont(BODY_FONT, 8)
        c.setFillColor(GOLD)
        c.drawString(ML + 0.3*cm, 1.5*cm, f"colasjurist.se · info@colas-abogados.com · +34 629 549 430")

def section_heading(num, title):
    """Returns a table with number badge + title."""
    num_cell = Table([[Paragraph(str(num), style('sn', fontName=BOLD_FONT, fontSize=10, textColor=white, alignment=TA_CENTER))]],
                     colWidths=[0.8*cm], rowHeights=[0.7*cm])
    num_cell.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [3,3,3,3]),
    ]))
    title_para = Paragraph(title, style('sh', fontName=BOLD_FONT, fontSize=13, textColor=NAVY, leading=17))
    t = Table([[num_cell, title_para]], colWidths=[1.1*cm, 14*cm])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LINEBEFORE', (1,0), (1,-1), 0.5, GOLD),
    ]))
    return [Spacer(1, 0.5*cm), t, HRFlowable(width='100%', thickness=1, color=BORDER, spaceAfter=10)]

def info_table(rows, col_widths=None):
    """Two-column label/value table."""
    if not col_widths:
        col_widths = [5*cm, 10.5*cm]
    data = []
    for label, val in rows:
        data.append([
            Paragraph(label, S_CELL_MUT),
            Paragraph(str(val) if val else '—', S_CELL_B)
        ])
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), LIGHT_BG),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [white, LIGHT_BG]),
    ]))
    return t

def risk_badge(level):
    """Colored risk level badge."""
    cfg = {
        'red':    ('CRÍTICO',     RED_RISK,  RED_BG),
        'orange': ('IMPORTANTE',  ORG_RISK,  ORG_BG),
        'yellow': ('MODERADO',    YEL_RISK,  YEL_BG),
        'green':  ('OK',          GRN_RISK,  GRN_BG),
        'resuelto': ('RESUELTO',  GRN_RISK,  GRN_BG),
        'bajo':   ('BAJO',        YEL_RISK,  YEL_BG),
        'medio':  ('MEDIO',       ORG_RISK,  ORG_BG),
        'alto':   ('ALTO',        RED_RISK,  RED_BG),
    }
    label, fg, bg = cfg.get(level.lower(), ('—', MUTED, LIGHT_BG))
    fg_hex = '#%02x%02x%02x' % (int(fg.red*255), int(fg.green*255), int(fg.blue*255))
    p = Paragraph(f'<font color="{fg_hex}"><b>{label}</b></font>', S_RISK_LBL)
    t = Table([[p]], colWidths=[2.5*cm], rowHeights=[0.55*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg),
        ('BOX', (0,0), (-1,-1), 0.5, fg),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    return t

def alert_block(alert, lang='sv'):
    """Full alert card with title, body, clause, documents."""
    level = alert.get('level', 'yellow')
    cfg = {
        'red':    (RED_RISK,  RED_BG),
        'orange': (ORG_RISK,  ORG_BG),
        'yellow': (YEL_RISK,  YEL_BG),
        'green':  (GRN_RISK,  GRN_BG),
    }
    fg, bg = cfg.get(level, (MUTED, LIGHT_BG))

    rows = []
    # Title row
    title = alert.get('title', '')
    badge = risk_badge(level)
    title_row = Table([[badge, Paragraph(title, S_ALERT_T)]],
                      colWidths=[2.7*cm, 12.8*cm])
    title_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    rows.append(title_row)

    # Body
    body = alert.get('body', '')
    if body:
        rows.append(Spacer(1, 3))
        rows.append(Paragraph(body, S_ALERT_B))

    # Action
    action = alert.get('action', '')
    if action:
        rows.append(Spacer(1, 3))
        rows.append(Paragraph(f'<b>→ {action}</b>',
            style('act', fontName=BOLD_FONT, fontSize=9, textColor=fg, leading=13)))

    # Documents
    docs = alert.get('documents', [])
    if docs:
        rows.append(Spacer(1, 4))
        rows.append(Paragraph(f'<b>{T(lang, "docs_solicitar")}</b>',
            style('dh', fontName=BOLD_FONT, fontSize=8.5, textColor=NAVY, leading=12)))
        for doc in docs:
            rows.append(Paragraph(f'• {doc}', S_BULLET))

    # Clause
    clause = alert.get('clause', '')
    if clause and clause != 'null':
        rows.append(Spacer(1, 5))
        rows.append(Paragraph(f'<b>{T(lang, "clausula_recom")}</b>',
            style('ch', fontName=BOLD_FONT, fontSize=8.5, textColor=NAVY, leading=12)))
        rows.append(Paragraph(f'"{clause}"', S_CLAUSE))

    inner = Table([[r] for r in rows], colWidths=[15.5*cm])
    inner.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('BACKGROUND', (0,0), (-1,-1), bg),
        ('LINEBEFORE', (0,0), (0,-1), 3, fg),
    ]))
    return KeepTogether([inner, Spacer(1, 6)])

def risk_table(alerts, lang='sv'):
    """Summary risk table: Area | Level | Description."""
    S_WHITE_BOLD = style('whB', fontName=BOLD_FONT, fontSize=9, leading=13, textColor=white)
    headers = [
        Paragraph(f'<b>{T(lang, "risk_area")}</b>', S_WHITE_BOLD),
        Paragraph(f'<b>{T(lang, "risk_level")}</b>', S_WHITE_BOLD),
        Paragraph(f'<b>{T(lang, "risk_desc")}</b>', S_WHITE_BOLD),
    ]
    rows = [headers]
    for a in alerts:
        badge = risk_badge(a.get('level', 'yellow'))
        rows.append([
            Paragraph(a.get('category', '').capitalize(), S_CELL),
            badge,
            Paragraph(a.get('title', ''), S_CELL),
        ])
    t = Table(rows, colWidths=[3.5*cm, 2.8*cm, 9.2*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, LIGHT_BG]),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
    ]))
    return t

def checklist_table(items, title, lang='sv'):
    """Numbered action checklist table."""
    if not items: return Spacer(1, 0)
    S_WH = style('wh', fontName=BOLD_FONT, fontSize=9, leading=13, textColor=white)
    headers = [
        Paragraph('<b>#</b>', S_WH),
        Paragraph(f'<b>{title}</b>', S_WH),
    ]
    rows = [headers]
    for i, item in enumerate(items, 1):
        rows.append([
            Paragraph(str(i), S_CELL),
            Paragraph(item, S_CELL),
        ])
    t = Table(rows, colWidths=[0.8*cm, 14.7*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('TEXTCOLOR', (0,0), (-1,0), white),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, LIGHT_BG]),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    return t

_PDF_LANG = 'sv'  # set before build

def page_header_footer(canvas, doc):
    """Recurring header/footer."""
    canvas.saveState()
    w, h = A4
    lg = _PDF_LANG

    # Header line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(ML, h - 1.5*cm, w - MR, h - 1.5*cm)
    canvas.setFont(BODY_FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(ML, h - 1.2*cm, T(lg, "header_conf"))
    canvas.drawRightString(w - MR, h - 1.2*cm, T(lg, "header_right"))

    # Footer line
    canvas.line(ML, 1.8*cm, w - MR, 1.8*cm)
    canvas.setFont(BODY_FONT, 7.5)
    canvas.drawString(ML, 1.3*cm, T(lg, "footer_author"))
    canvas.drawRightString(w - MR, 1.3*cm, f'{T(lg, "footer_pagina")} {doc.page}')

    canvas.restoreState()

# ── Main generator ───────────────────────────────────────────────────────────
def generate_pdf(report_data: dict, output_path: str):
    """
    report_data keys:
      property:   dict with direccion, ref_catastral, registro, municipio, etc.
      catastro:   dict with surface, year, elements, valor_catastral, etc.
      registro:   dict with cargas, superficie_registro, etc.
      urbanismo:  dict with clasificacion, documentos, alertas, etc.
      analysis:   dict from Claude (score, risk_level, clasificacion_final, alerts, etc.)
      lang:       'sv' | 'es' | 'en'
    """
    global _PDF_LANG
    _PDF_LANG = report_data.get('lang', 'sv')

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=2.2*cm, bottomMargin=2.5*cm,
        title=f"Due Diligence — {report_data.get('property', {}).get('direccion', 'Propiedad')}",
        author="Perplexity Computer"
    )

    prop    = report_data.get('property', {})
    cat     = report_data.get('catastro', {})
    reg     = report_data.get('registro', {})
    urb     = report_data.get('urbanismo', {})
    ai      = report_data.get('analysis', {})
    lang    = report_data.get('lang', 'sv')
    _date_fmts = {'sv': '%-d %B %Y', 'es': '%-d de %B de %Y', 'en': '%B %-d, %Y'}
    today   = datetime.date.today().strftime(_date_fmts.get(lang, '%-d %B %Y'))
    prop['fecha'] = prop.get('fecha', today)

    alerts  = ai.get('alerts', [])
    red_a   = [a for a in alerts if a.get('level') == 'red']
    org_a   = [a for a in alerts if a.get('level') == 'orange']
    yel_a   = [a for a in alerts if a.get('level') == 'yellow']
    grn_a   = [a for a in alerts if a.get('level') == 'green']

    score   = ai.get('score', 0)
    clasif  = ai.get('clasificacion_final', 'no_deberia_firmarse')
    summary = ai.get('summary', '')

    clasif_labels = {
        'puede_firmarse':                  ('KAN UNDERTECKNAS', GRN_RISK),
        'puede_firmarse_con_modificaciones': ('KAN UNDERTECKNAS MED ÄNDRINGAR', YEL_RISK),
        'no_deberia_firmarse':             ('BÖR INTE UNDERTECKNAS', RED_RISK),
    }
    if lang == 'es':
        clasif_labels = {
            'puede_firmarse':                  ('PUEDE FIRMARSE', GRN_RISK),
            'puede_firmarse_con_modificaciones': ('PUEDE FIRMARSE CON MODIFICACIONES', YEL_RISK),
            'no_deberia_firmarse':             ('NO DEBERÍA FIRMARSE', RED_RISK),
        }
    clasif_label, clasif_color = clasif_labels.get(clasif, ('—', MUTED))

    story = []

    # ── COVER ────────────────────────────────────────────────────────────────
    story.append(CoverPage(prop))
    story.append(PageBreak())

    # ── S01 IDENTIFICACIÓN ───────────────────────────────────────────────────
    story.extend(section_heading('01', T(lang, 's01')))
    rows_id = [
        (T(lang,'lbl_direccion'), prop.get('direccion','—')),
        (T(lang,'lbl_ref_cat'), prop.get('ref_catastral','—')),
        (T(lang,'lbl_tipo'), prop.get('tipo','—')),
        (T(lang,'lbl_municipio'), prop.get('municipio','—')),
        (T(lang,'lbl_anno'), prop.get('anno_construccion','—')),
        (T(lang,'lbl_precio'), prop.get('precio','—')),
        (T(lang,'lbl_vendedor'), prop.get('vendedor','—')),
        (T(lang,'lbl_estado'), prop.get('estado','—')),
    ]
    story.append(info_table([(k, v) for k, v in rows_id if v and v != '—']))
    story.append(Spacer(1, 0.3*cm))

    # ── S02 SITUACIÓN REGISTRAL ──────────────────────────────────────────────
    story.extend(section_heading('02', T(lang, 's02')))
    story.append(Paragraph('2.1 ' + T(lang, 's02_1'), S_SUBSEC))
    rows_reg = [
        (T(lang,'lbl_registro'), reg.get('registro', prop.get('registro','—'))),
        (T(lang,'lbl_finca'), reg.get('finca','—')),
        (T(lang,'lbl_sup_constr'), f"{reg.get('superficie_registro','—')} m²" if reg.get('superficie_registro') else '—'),
        (T(lang,'lbl_sup_parcela'), f"{reg.get('superficie_parcela_registro','—')} m²" if reg.get('superficie_parcela_registro') else '—'),
        (T(lang,'lbl_titularidad'), reg.get('titularidad','—')),
        (T(lang,'lbl_coord_cat'), reg.get('coordinacion_catastro','—')),
    ]
    story.append(info_table([(k, v) for k, v in rows_reg if v and v != '—']))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph('2.2 ' + T(lang, 's02_2'), S_SUBSEC))
    cargas = reg.get('cargas', prop.get('cargas', 'ninguna'))
    cargas_text = {
        'ninguna':   T(lang, 'cargas_ninguna'),
        'hipoteca':  T(lang, 'cargas_hipoteca'),
        'embargo':   T(lang, 'cargas_embargo'),
        'usufructo': {'sv': 'Fastigheten är belastad med nyttjanderätt. Se riskanalys.', 'es': 'La finca está sujeta a derecho de usufructo. Ver análisis de riesgos.', 'en': 'The property is subject to a usufruct right. See risk analysis.'}.get(lang, ''),
        'unknown':   T(lang, 'cargas_unknown'),
    }.get(str(cargas).lower(), str(cargas))
    story.append(Paragraph(cargas_text, S_BODY))
    story.append(Spacer(1, 0.2*cm))

    nota_text = reg.get('nota_simple_text', '')
    if nota_text:
        story.append(Paragraph(f'<b>{T(lang, "s02_nota")}</b>', S_SUBSEC))
        story.append(Paragraph(nota_text[:1500], S_BODY))
        if len(nota_text) > 1500:
            story.append(Paragraph(T(lang,'txt_full_exp'), S_SMALL))

    # ── S03 SITUACIÓN CATASTRAL ──────────────────────────────────────────────
    story.extend(section_heading('03', T(lang, 's03')))
    rows_cat = [
        ('Referencia catastral', cat.get('ref_catastral', prop.get('ref_catastral', '—'))),
        ('Clase / Uso', cat.get('uso', '—')),
        (T(lang,'lbl_sup_cat'), f"{cat.get('superficie_catastro','—')} m²" if cat.get('superficie_catastro') else '—'),
        (T(lang,'lbl_sup_parc_cat'), f"{cat.get('superficie_parcela_catastro','—')} m²" if cat.get('superficie_parcela_catastro') else '—'),
        (T(lang,'lbl_anno_cat'), cat.get('anno_construccion_catastro','—')),
        (T(lang,'lbl_val_cat'), f"{cat.get('valor_catastral','—')} €" if cat.get('valor_catastral') else '—'),
        (T(lang,'lbl_val_ref'), f"{cat.get('valor_referencia','—')} €" if cat.get('valor_referencia') else '—'),
        (T(lang,'lbl_piscina'), T(lang,'val_si') if cat.get('piscina_catastro') else (T(lang,'val_no') if cat.get('piscina_catastro') is False else '—')),
        (T(lang,'lbl_garaje'), T(lang,'val_si') if cat.get('garaje_catastro') else (T(lang,'val_no') if cat.get('garaje_catastro') is False else '—')),
    ]
    story.append(info_table([(k, v) for k, v in rows_cat if v and v != '—']))

    # Discrepancy alert
    sup_cat = cat.get('superficie_catastro', 0)
    sup_reg = reg.get('superficie_registro', 0)
    if sup_cat and sup_reg and abs(float(sup_cat) - float(sup_reg)) > 5:
        diff = abs(float(sup_cat) - float(sup_reg))
        story.append(Spacer(1, 0.3*cm))
        disc = Table([[
            Paragraph(T(lang, 'disc_alert'), style('dh', fontName=BOLD_FONT, fontSize=9.5, textColor=ORG_RISK, leading=13)),
            Paragraph(f'Diferencia: {diff:.0f} m²', style('dd', fontName=BOLD_FONT, fontSize=9.5, textColor=ORG_RISK, leading=13, alignment=TA_RIGHT))
        ]], colWidths=[10*cm, 5.5*cm])
        disc.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), ORG_BG),
            ('BOX', (0,0), (-1,-1), 1, ORG_RISK),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(disc)
        story.append(Spacer(1, 4))
        _disc_texts = {'sv': f'Det finns en avvikelse pa {diff:.0f} m2 mellan den inskrivna ytan i Registret ({sup_reg} m2) och Catastro ({sup_cat} m2). Deklaration av obra nueva kravs fore notarieakten.', 'es': f'Existe una divergencia de {diff:.0f} m2 entre la superficie inscrita en el Registro ({sup_reg} m2) y la reflejada en el Catastro ({sup_cat} m2). Se requiere declaracion de obra nueva antes de la escritura.', 'en': f'There is a discrepancy of {diff:.0f} m2 between the Land Registry ({sup_reg} m2) and the Cadastre ({sup_cat} m2). An obra nueva declaration is required before the deed.'}
        story.append(Paragraph(_disc_texts.get(lang, _disc_texts['en']), S_BODY))

    # ── S04 SITUACIÓN URBANÍSTICA ────────────────────────────────────────────
    story.extend(section_heading('04', T(lang, 's04')))
    rows_urb = [
        (T(lang,'lbl_clasificacion'), urb.get('tipo_suelo', prop.get('tipo_suelo','—'))),
        (T(lang,'lbl_costas'), T(lang,'val_si') if prop.get('zona_costera') else T(lang,'val_no')),
        (T(lang,'lbl_lpo'), prop.get('tiene_licencia_primera_ocupacion','—')),
        (T(lang,'lbl_expediente'), prop.get('expediente_urbanistico','—')),
    ]
    story.append(info_table([(k, v) for k, v in rows_urb if v and v not in ('—', 'None')]))

    cedula_text = urb.get('cedula_text', '')
    if cedula_text:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f'<b>{T(lang, "s04_cedula")}</b>', S_SUBSEC))
        story.append(Paragraph(cedula_text[:1200], S_BODY))
        if len(cedula_text) > 1200:
            story.append(Paragraph('[Texto completo disponible en el expediente]', S_SMALL))

    # ── S05 MAPA DE RIESGOS ──────────────────────────────────────────────────
    story.extend(section_heading('05', T(lang, 's05')))

    # Score + classification banner
    score_color = GRN_RISK if score >= 80 else (YEL_RISK if score >= 60 else (ORG_RISK if score >= 40 else RED_RISK))
    S_CL = style('cl', fontName=BOLD_FONT, fontSize=9.5, textColor=clasif_color, leading=13)
    S_CS = style('cs', fontName=BODY_FONT, fontSize=8.5, textColor=MUTED, leading=12)
    score_table = Table([
        [
            Paragraph(f'<b>{score}</b>',
                      style('sc', fontName=BOLD_FONT, fontSize=26, textColor=score_color, leading=30, alignment=TA_CENTER)),
            Paragraph(clasif_label, S_CL),
            Paragraph(f'{len(red_a)} critico(s) · {len(org_a)} importante(s) · {len(yel_a)} moderado(s)', S_CS),
        ]
    ], colWidths=[2.2*cm, 8*cm, 5.3*cm])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1.5, clasif_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.4*cm))
    if summary:
        story.append(Paragraph(summary, S_BODY))
        story.append(Spacer(1, 0.3*cm))

    # Risk table
    if alerts:
        story.append(risk_table(alerts, lang))
        story.append(Spacer(1, 0.5*cm))

    # Detailed alerts
    if red_a:
        story.append(Paragraph(T(lang, 'problemas_criticos'), S_SUBSEC))
        for a in red_a: story.append(alert_block(a, lang))
    if org_a:
        story.append(Paragraph(T(lang, 'advertencias'), S_SUBSEC))
        for a in org_a: story.append(alert_block(a, lang))
    if yel_a:
        story.append(Paragraph(T(lang, 'puntos_atencion'), S_SUBSEC))
        for a in yel_a: story.append(alert_block(a, lang))
    if grn_a:
        story.append(Paragraph(T(lang, 'aspectos_orden'), S_SUBSEC))
        for a in grn_a: story.append(alert_block(a, lang))

    # ── S06 CONCLUSIÓN Y RECOMENDACIONES ────────────────────────────────────
    story.extend(section_heading('06', T(lang, 's06')))

    # Missing clauses
    missing = ai.get('missing_clauses', [])
    if missing:
        story.append(Paragraph(T(lang, 'clausulas_missing'), S_SUBSEC))
        for m in missing:
            story.append(Paragraph(f'• {m}', S_BULLET))
        story.append(Spacer(1, 0.3*cm))

    # Checklist firmar
    chk_firmar = ai.get('checklist_antes_de_firmar', [])
    if chk_firmar:
        story.append(Paragraph(T(lang, 'chk_firmar'), S_SUBSEC))
        story.append(checklist_table(chk_firmar, T(lang, 'accion')))
        story.append(Spacer(1, 0.3*cm))

    # Checklist escritura
    chk_escritura = ai.get('checklist_antes_de_escritura', [])
    if chk_escritura:
        story.append(Paragraph(T(lang, 'chk_escritura'), S_SUBSEC))
        story.append(checklist_table(chk_escritura, T(lang, 'accion')))
        story.append(Spacer(1, 0.3*cm))

    # Actuaciones previas
    acts = ai.get('actuaciones_previas_imprescindibles', [])
    if acts:
        story.append(Paragraph(T(lang, 'actuaciones'), S_SUBSEC))
        story.append(checklist_table(acts, T(lang, 'actuacion')))
        story.append(Spacer(1, 0.3*cm))

    # Follow-up questions
    preguntas = ai.get('preguntas_adicionales', [])
    if preguntas:
        story.append(Paragraph(T(lang, 'preguntas'), S_SUBSEC))
        for q in preguntas:
            story.append(Paragraph(f'• {q}', S_BULLET))
        story.append(Spacer(1, 0.3*cm))

    # Signature block
    story.append(Spacer(1, 0.5*cm))
    # AI Disclaimer block
    disc_text = T(lang, 'disclaimer_cover')
    disc_block = Table([[
        Paragraph('AI', style('di', fontName=BOLD_FONT, fontSize=9, textColor=YEL_RISK, alignment=TA_CENTER, leading=11)),
        Paragraph(disc_text, style('db', fontName=BODY_FONT, fontSize=8, textColor=TEXT, leading=12)),
    ]], colWidths=[1*cm, 14.5*cm])
    disc_block.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), YEL_BG),
        ('BOX', (0,0), (-1,-1), 1, YEL_RISK),
        ('LINEBEFORE', (0,0), (0,-1), 3, YEL_RISK),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(disc_block)
    story.append(Spacer(1, 1*cm))
    sig = Table([[
        Table([[
            Paragraph(f'<b>{T(lang, "sig_title")}</b>', style('sn', fontName=BOLD_FONT, fontSize=10, textColor=NAVY, leading=14)),
            Paragraph(T(lang, 'sig_sub'), style('st', fontName=BODY_FONT, fontSize=8.5, textColor=MUTED, leading=12)),
            Paragraph(T(lang, 'sig_addr'), style('sa', fontName=BODY_FONT, fontSize=8, textColor=MUTED, leading=11)),
            Paragraph(f'<a href="https://colasjurist.se" color="blue">colasjurist.se</a> · info@colas-abogados.com · +34 629 549 430', style('sw', fontName=BODY_FONT, fontSize=8, textColor=MUTED, leading=11)),
            Paragraph(T(lang, 'sig_disclaimer'), style('sd', fontName=BODY_FONT, fontSize=7.5, textColor=YEL_RISK, leading=11)),
            Paragraph(f'Informe generado: {today}', S_SMALL),
        ]])
    ]], colWidths=[15.5*cm])
    sig.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CREAM),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER),
        ('LINEBEFORE', (0,0), (0,-1), 3, GOLD),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(sig)

    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=page_header_footer)
    print(f"PDF generated: {output_path}")
    return output_path


# ── CLI / test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Test with sample data
    sample = {
        "lang": "sv",
        "property": {
            "direccion": "Calle Serra del Cid 16, L'Alfàs del Pi",
            "ref_catastral": "2648109YH5724N0001FB",
            "registro": "Callosa d'en Sarrià",
            "municipio": "L'Alfàs del Pi (Alicante)",
            "tipo": "Vivienda unifamiliar aislada",
            "anno_construccion": "1970",
            "precio": "443.000 €",
            "vendedor": "Particular",
        },
        "catastro": {
            "superficie_catastro": 209,
            "superficie_parcela_catastro": 540,
            "anno_construccion_catastro": 1970,
            "valor_catastral": 52667.85,
            "valor_referencia": 260222.26,
            "piscina_catastro": False,
            "garaje_catastro": True,
        },
        "registro": {
            "superficie_registro": 103,
            "superficie_parcela_registro": 540,
            "cargas": "hipoteca",
            "titularidad": "1 propietario",
        },
        "urbanismo": {
            "tipo_suelo": "Suelo Urbanizable No Programado (S.U.N.P.) n.º 6",
            "cedula_text": "Departamento: Urbanismo. La vivienda está emplazada en Suelo Urbanizable No Programado (S.U.N.P.) 6 Serra del Cid y tiene una antigüedad superior a quince años.",
        },
        "analysis": {
            "score": 28,
            "risk_level": "critical",
            "clasificacion_final": "no_deberia_firmarse",
            "summary": "Operació d'alt risc amb tres deficiències crítiques: (1) hipoteca registrada de 150.000 € sense mecanisme de retenció; (2) discrepància catastral greu — registre mostra 103 m² però catastro indica 209 m²; (3) termini extremadament curt. No s'hauria de signar sense resoldre els punts crítics.",
            "alerts": [
                {
                    "level": "red",
                    "category": "hipoteca",
                    "title": "Hipoteca registrada sin cláusula de cancelación",
                    "body": "La finca está gravada con hipoteca a favor de CaixaBank de 150.000 €. El contrato no especifica mecanismo de retención ni garantía de cancelación registral simultánea a la escritura.",
                    "action": "Solicitar certificado de deuda pendiente a CaixaBank e incorporar cláusula de retención al contrato.",
                    "documents": ["Certificado de deuda pendiente (CaixaBank)", "Escritura de cancelación hipotecaria"],
                    "clause": "El comprador retendrá de la cantidad a entregar en escritura el importe necesario para la cancelación registral de la hipoteca, cuyo saldo será acreditado mediante certificado de deuda emitido por la entidad acreedora con una antelación máxima de 10 días hábiles a la fecha de la escritura pública de compraventa."
                },
                {
                    "level": "red",
                    "category": "catastral",
                    "title": "Discrepancia grave Catastro-Registro (106 m²)",
                    "body": "Existe una divergencia de 106 m² entre la superficie inscrita en el Registro (103 m²) y la reflejada en el Catastro (209 m²). Las construcciones adicionales no constan inscritas registralmente.",
                    "action": "Exigir declaración de obra nueva antes de la escritura o retención del precio para cubrir el coste.",
                    "documents": ["Nota simple actualizada", "Consulta descriptiva y gráfica del Catastro"],
                    "clause": "El vendedor se obliga a declarar ante Notario la obra nueva correspondiente a las construcciones existentes antes de la firma de la escritura pública de compraventa, siendo dicho trámite condición esencial del presente contrato."
                },
                {
                    "level": "orange",
                    "category": "urbanismo",
                    "title": "Suelo Urbanizable No Programado — régimen especial",
                    "body": "La finca se ubica en S.U.N.P. n.º 6. La antigüedad superior a 15 años ampara las edificaciones bajo DT 26.ª TRLOTUP, pero conviene confirmar verbalmente con el Arquitecto Municipal.",
                    "action": "Solicitar certificado de no infracción urbanística al Ayuntamiento.",
                    "documents": ["Certificado de no infracción urbanística", "Cédula urbanística"],
                    "clause": "El vendedor garantiza que la finca no es objeto de expediente de infracción urbanística, comprometiéndose a aportar certificado del Ayuntamiento antes de la escritura pública."
                },
            ],
            "missing_clauses": [
                "Condición suspensiva de financiación hipotecaria",
                "Cláusula de libre de cargas y gravámenes",
                "Cláusula de libre de ocupantes",
                "Regularización urbanística de construcciones",
            ],
            "checklist_antes_de_firmar": [
                "Obtener nota simple actualizada del Registro de la Propiedad",
                "Solicitar certificado de deuda pendiente a CaixaBank",
                "Verificar situación urbanística con el Ayuntamiento de L'Alfàs del Pi",
                "Revisar actas de la comunidad de propietarios (últimas 3)",
                "Confirmar que el energicertifikat está vigente",
            ],
            "checklist_antes_de_escritura": [
                "Certificado de cancelación económica de hipoteca CaixaBank",
                "Declaración de obra nueva otorgada ante Notario",
                "Certificado de no deuda de la comunidad de propietarios",
                "Recibo IBI del año en curso",
                "Liquidación de ITP en los 30 días siguientes",
            ],
            "actuaciones_previas_imprescindibles": [
                "Incorporar cláusula de retención hipotecaria al contrato privado",
                "Exigir declaración de obra nueva como condición suspensiva",
                "Solicitar certificado de no infracción urbanística al Ayuntamiento",
            ],
            "preguntas_adicionales": [
                "¿Existe certificado de eficiencia energética vigente?",
                "¿La comunidad de propietarios tiene derramas pendientes?",
                "¿El vendedor es residente fiscal en España?",
            ],
            "documents_to_request": [
                "Nota simple actualizada del Registro de la Propiedad",
                "Certificado de deuda pendiente (CaixaBank)",
                "Certificado de no infracción urbanística",
                "Certificado de no deuda de la comunidad",
                "Recibo IBI año en curso",
                "Certificado de eficiencia energética vigente",
            ]
        }
    }

    out = '/home/user/workspace/due_diligence_test.pdf'
    generate_pdf(sample, out)
