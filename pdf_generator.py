"""
Due Diligence PDF Generator — Colás Jurist
Portada profesional, 6 secciones, resúmenes de documentos, mapa de riesgos, firma.
Rediseñado desde cero: badges de sección de una sola línea, resúmenes IA de
nota simple / cédula urbanística (nunca texto crudo), traducción de valores,
fechas localizadas y una portada mucho más rica visualmente.
"""
import os
import re
import datetime
import requests

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import Flowable

# ── Brand colors ─────────────────────────────────────────────────────────────
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
NAVY_MUTE = HexColor('#4A5A6C')


# ── Multilingual labels ──────────────────────────────────────────────────────
def T(lang, key):
    """Get translated label."""
    LABELS = {
        'report_title':        {'sv': 'RAPPORT FASTIGHETS-DUE DILIGENCE', 'es': 'INFORME DE DUE DILIGENCE INMOBILIARIA', 'en': 'REAL ESTATE DUE DILIGENCE REPORT'},
        'ai_notice':           {'sv': 'Genererad med artificiell intelligens', 'es': 'Generado con inteligencia artificial', 'en': 'Generated with artificial intelligence'},
        'ai_label':            {'sv': 'AI DUE DILIGENCE', 'es': 'AI DUE DILIGENCE', 'en': 'AI DUE DILIGENCE'},
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
        's02_nota':            {'sv': 'Nota simple analyserad — nyckelresultat:', 'es': 'Nota simple analizada — hallazgos clave:', 'en': 'Nota simple analysed — key findings:'},
        's03':                 {'sv': 'KATASTRALSITUATION', 'es': 'SITUACIÓN CATASTRAL', 'en': 'CADASTRAL STATUS'},
        's04':                 {'sv': 'URBANISTISK SITUATION', 'es': 'SITUACIÓN URBANÍSTICA', 'en': 'URBAN PLANNING STATUS'},
        's04_cedula':          {'sv': 'Cédula urbanística analyserad — nyckelresultat:', 'es': 'Cédula urbanística analizada — hallazgos clave:', 'en': 'Cédula urbanística analysed — key findings:'},
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
        'cargas_ninguna':      {'sv': 'Inga registrerade belastningar eller gravamen på fastigheten.', 'es': 'No constan cargas registrales ni gravámenes sobre la finca.', 'en': 'No registered charges or encumbrances on the property.'},
        'cargas_hipoteca':     {'sv': 'Fastigheten är belastad med inteckning. Se riskanalys.', 'es': 'La finca está gravada con hipoteca. Ver análisis de riesgos.', 'en': 'The property is subject to a mortgage. See risk analysis.'},
        'cargas_embargo':      {'sv': 'Fastigheten har en utmätningsanteckning. Se riskanalys.', 'es': 'La finca presenta anotación de embargo. Ver análisis de riesgos.', 'en': 'The property has an embargo annotation. See risk analysis.'},
        'cargas_usufructo':    {'sv': 'Fastigheten är belastad med nyttjanderätt. Se riskanalys.', 'es': 'La finca está sujeta a derecho de usufructo. Ver análisis de riesgos.', 'en': 'The property is subject to a usufruct right. See risk analysis.'},
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
        'risk_critico':    {'sv': 'KRITISK', 'es': 'CRÍTICO', 'en': 'CRITICAL'},
        'risk_importante': {'sv': 'VIKTIG', 'es': 'IMPORTANTE', 'en': 'IMPORTANT'},
        'risk_moderado':   {'sv': 'MÅTTLIG', 'es': 'MODERADO', 'en': 'MODERATE'},
        'risk_ok':         {'sv': 'OK', 'es': 'OK', 'en': 'OK'},
        'header_conf':     {'sv': 'RAPPORT FASTIGHETS-DUE DILIGENCE · AI-GENERERAD', 'es': 'INFORME DE DUE DILIGENCE INMOBILIARIA · GENERADO POR IA', 'en': 'REAL ESTATE DUE DILIGENCE REPORT · AI-GENERATED'},
        'header_right':    {'sv': 'Colás Jurist · colasjurist.se', 'es': 'Colás Jurist · colasjurist.se', 'en': 'Colás Jurist · colasjurist.se'},
        'fecha_informe':   {'sv': 'Rapportdatum', 'es': 'Fecha del informe', 'en': 'Report date'},
        'ref_exp':         {'sv': 'AI Due Diligence · colasjurist.se', 'es': 'AI Due Diligence · colasjurist.se', 'en': 'AI Due Diligence · colasjurist.se'},
        'conf_line1':      {'sv': 'Denna rapport har genererats automatiskt med AI och är INTE juridiskt bindande rådgivning.', 'es': 'Este informe ha sido generado automáticamente por IA y NO constituye asesoramiento jurídico vinculante.', 'en': 'This report has been automatically generated by AI and does NOT constitute legally binding advice.'},
        'conf_line2':      {'sv': 'Innehållet är konfidentiellt. Måste granskas av en kvalificerad jurist.', 'es': 'El contenido es confidencial. Debe ser revisado por un abogado cualificado.', 'en': 'The content is confidential. Must be reviewed by a qualified lawyer.'},
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
        'txt_full_exp':    {'sv': '[Fullständig text tillgänglig i ärendet]', 'es': '[Texto completo disponible en el expediente]', 'en': '[Full text available in the file]'},
        # Nota simple / cédula extraction labels
        'ns_owner':        {'sv': 'Ägare', 'es': 'Titular', 'en': 'Owner'},
        'ns_description':  {'sv': 'Fastighetsbeskrivning', 'es': 'Descripción de la finca', 'en': 'Property description'},
        'ns_area':         {'sv': 'Inskriven yta', 'es': 'Superficie inscrita', 'en': 'Registered area'},
        'ns_charges':      {'sv': 'Belastningar', 'es': 'Cargas', 'en': 'Charges'},
        'ns_finca':        {'sv': 'Fastighetsnummer (finca)', 'es': 'N.º de finca', 'en': 'Property (finca) number'},
        'ns_coord':        {'sv': 'Koordinering med Catastro', 'es': 'Coordinación con Catastro', 'en': 'Coordination with Cadastre'},
        'ns_no_charges':   {'sv': 'Inga belastningar identifierade', 'es': 'No se identificaron cargas', 'en': 'No charges identified'},
        'ns_not_found':    {'sv': 'Ej identifierat i dokumentet', 'es': 'No identificado en el documento', 'en': 'Not identified in the document'},
        'cd_classification': {'sv': 'Markklassificering', 'es': 'Clasificación del suelo', 'en': 'Land classification'},
        'cd_status':       {'sv': 'Planstatus', 'es': 'Situación urbanística', 'en': 'Planning status'},
        'cd_restrictions': {'sv': 'Restriktioner', 'es': 'Restricciones', 'en': 'Restrictions'},
        'cd_reference':    {'sv': 'Kommunal referens', 'es': 'Referencia municipal', 'en': 'Municipal reference'},
        # Cover metadata
        'cov_katastral':   {'sv': 'Katastralbeteckning', 'es': 'Referencia catastral', 'en': 'Cadastral reference'},
        'cov_registro':    {'sv': 'Fastighetsregister', 'es': 'Registro de la Propiedad', 'en': 'Land Registry'},
        'cov_kommun':      {'sv': 'Kommun', 'es': 'Municipio', 'en': 'Municipality'},
        'cov_datum':       {'sv': 'Rapportdatum', 'es': 'Fecha del informe', 'en': 'Report date'},
        'cov_sammanstalld':{'sv': 'Sammanställd av', 'es': 'Elaborado por', 'en': 'Prepared by'},
        'cov_omfattning':  {'sv': 'Omfattning', 'es': 'Alcance', 'en': 'Scope'},
    }
    return LABELS.get(key, {}).get(lang, LABELS.get(key, {}).get('en', key))


# ── Value translations (for raw Spanish codes/values) ────────────────────────
def translate_value(lang, value):
    """Translate common Spanish property-related values into the target language."""
    if value is None:
        return None
    key = str(value).strip().lower()
    key = key.replace('_', '-')

    MAP = {
        'segunda-mano':    {'sv': 'Begagnad bostad',        'es': 'Segunda mano',        'en': 'Resale property'},
        'segunda mano':    {'sv': 'Begagnad bostad',        'es': 'Segunda mano',        'en': 'Resale property'},
        'obra-nueva':      {'sv': 'Nyproduktion',           'es': 'Obra nueva',          'en': 'New build'},
        'obra nueva':      {'sv': 'Nyproduktion',           'es': 'Obra nueva',          'en': 'New build'},
        'rustico':         {'sv': 'Lantlig fastighet',      'es': 'Rústico',             'en': 'Rural property'},
        'rústico':         {'sv': 'Lantlig fastighet',      'es': 'Rústico',             'en': 'Rural property'},
        'no-urbanizable':  {'sv': 'Icke-urbaniserbar mark', 'es': 'No urbanizable',      'en': 'Non-developable land'},
        'no urbanizable':  {'sv': 'Icke-urbaniserbar mark', 'es': 'No urbanizable',      'en': 'Non-developable land'},
        'urbano':          {'sv': 'Stadsmark',              'es': 'Urbano',              'en': 'Urban land'},
        'urbanizable':     {'sv': 'Urbaniserbar mark',      'es': 'Urbanizable',         'en': 'Developable land'},
        'particular':      {'sv': 'Privatperson',           'es': 'Particular',          'en': 'Private individual'},
        'empresa':         {'sv': 'Företag',                'es': 'Empresa',             'en': 'Company'},
        'banco':           {'sv': 'Bank/kreditinstitut',    'es': 'Entidad bancaria',    'en': 'Bank/lender'},
        'promotor':        {'sv': 'Byggherre',              'es': 'Promotor',            'en': 'Property developer'},
        'hipoteca':        {'sv': 'Inteckning (kvarstår)',  'es': 'Hipoteca',            'en': 'Mortgage (outstanding)'},
        'embargo':         {'sv': 'Utmätning',              'es': 'Embargo',             'en': 'Embargo/attachment'},
        'ninguna':         {'sv': 'Inga belastningar',      'es': 'Ninguna',             'en': 'No charges'},
        'unknown':         {'sv': 'Ej kontrollerat',        'es': 'Desconocido',         'en': 'Unknown'},
    }
    if key in MAP:
        return MAP[key].get(lang, MAP[key].get('en', value))
    return value


# ── Date formatting (locale-free, dict lookup) ────────────────────────────────
_MONTHS = {
    'sv': ['januari', 'februari', 'mars', 'april', 'maj', 'juni', 'juli', 'augusti', 'september', 'oktober', 'november', 'december'],
    'es': ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'],
    'en': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
}


def format_date(lang, dt=None):
    """Locale-aware date formatting without relying on the `locale` module."""
    if dt is None:
        dt = datetime.date.today()
    months = _MONTHS.get(lang, _MONTHS['en'])
    month_name = months[dt.month - 1]
    if lang == 'sv':
        return f"{dt.day} {month_name} {dt.year}"
    if lang == 'es':
        return f"{dt.day} de {month_name} de {dt.year}"
    return f"{month_name} {dt.day}, {dt.year}"


# ── Document summary extraction (nota simple / cédula) ────────────────────────
def extract_nota_simple_summary(lang, nota_text, structured=None):
    """
    Build a list of (label, value) bullet-worthy findings from a nota simple.
    Prefers structured data if provided; otherwise parses the raw Spanish text
    with regex heuristics. The raw text is NEVER returned or displayed.
    """
    structured = structured or {}
    findings = {}

    findings['owner'] = structured.get('titular') or structured.get('owner')
    findings['description'] = structured.get('descripcion') or structured.get('description')
    findings['area'] = structured.get('superficie') or structured.get('area')
    findings['charges'] = structured.get('cargas_detalle') or structured.get('charges')
    findings['finca'] = structured.get('finca') or structured.get('finca_number')
    findings['coordination'] = structured.get('coordinacion_catastro') or structured.get('coordination')

    text = nota_text or ''

    if not findings['owner']:
        m = re.search(r'(?:TITULAR(?:ES)?|Titular(?:es)?)[:\s]+([^\n\.]{3,80})', text)
        if m:
            findings['owner'] = m.group(1).strip(' .,:;')

    if not findings['description']:
        m = re.search(r'(?:DESCRIPCI[ÓO]N|Descripci[óo]n)[:\s]+([^\n]{5,300}?)(?=\s*(?:CARGAS|Cargas|TITULAR|Titular|FINCA|Finca|$))', text)
        if m:
            desc = m.group(1).strip(' .,:;')
            if len(desc) > 220:
                desc = desc[:217].rsplit(' ', 1)[0] + '…'
            findings['description'] = desc

    if not findings['area']:
        m = re.search(r'(\d{1,3}(?:[.,]\d{1,2})?)\s*m(?:²|2|ts2|etros cuadrados)', text, re.IGNORECASE)
        if m:
            findings['area'] = f"{m.group(1)} m²"

    if not findings['finca']:
        m = re.search(r'(?:FINCA|Finca)\s*(?:N[ÚÜUúu]MERO|N[º°.]?)?\s*[:\s]*([\d\.]{2,12})', text)
        if m:
            findings['finca'] = m.group(1).strip(' .,:;')

    if not findings['coordination']:
        # Check negative phrasing first ("no consta coordinada...") since it
        # would otherwise also match the generic positive pattern below.
        if re.search(r'no\s+consta\s+coordinad', text, re.IGNORECASE) or re.search(r'no\s+(?:est[áa]\s+)?coordinad[ao]', text, re.IGNORECASE):
            findings['coordination'] = 'no_coordinada'
        elif re.search(r'coordinad[ao]\s+gr[áa]ficamente\s+con\s+(?:el\s+)?catastro', text, re.IGNORECASE):
            findings['coordination'] = 'coordinada'

    if not findings['charges']:
        charges_list = []
        m = re.search(r'(?:CARGAS|Cargas)[:\s]+([^\n]{3,400})', text)
        if m:
            block = m.group(1)
            if re.search(r'no\s+figuran|libre\s+de\s+cargas|sin\s+cargas', block, re.IGNORECASE):
                charges_list = []
            else:
                for chunk in re.split(r'[;\n]|(?<=\.)\s+(?=[A-ZÁÉÍÓÚ])', block):
                    chunk = chunk.strip(' .,:;')
                    if chunk and len(chunk) > 3:
                        charges_list.append(chunk)
        if re.search(r'hipoteca', text, re.IGNORECASE) and not charges_list:
            hm = re.search(r'([^\n]{0,50}hipoteca[^\n]{0,150})', text, re.IGNORECASE)
            if hm:
                charges_list.append(hm.group(1).strip(' .,:;'))
        if re.search(r'embargo', text, re.IGNORECASE):
            em = re.search(r'([^\n]{0,50}embargo[^\n]{0,150})', text, re.IGNORECASE)
            if em:
                charges_list.append(em.group(1).strip(' .,:;'))
        findings['charges'] = charges_list if charges_list else None

    na = T(lang, 'ns_not_found')
    bullets = []
    bullets.append(f"{T(lang,'ns_owner')}: {findings['owner'] or na}")
    bullets.append(f"{T(lang,'ns_description')}: {findings['description'] or na}")
    bullets.append(f"{T(lang,'ns_area')}: {findings['area'] or na}")

    charges = findings['charges']
    if charges:
        if isinstance(charges, list):
            bullets.append(f"{T(lang,'ns_charges')}:")
            for c in charges[:6]:
                bullets.append(f"  – {c}")
        else:
            bullets.append(f"{T(lang,'ns_charges')}: {charges}")
    else:
        bullets.append(f"{T(lang,'ns_charges')}: {T(lang,'ns_no_charges')}")

    bullets.append(f"{T(lang,'ns_finca')}: {findings['finca'] or na}")

    coord = findings['coordination']
    if coord:
        coord_map = {
            'coordinada':    {'sv': 'Ja, koordinerad med Catastro', 'es': 'Sí, coordinada con Catastro', 'en': 'Yes, coordinated with Cadastre'},
            'no_coordinada': {'sv': 'Nej, ej koordinerad med Catastro', 'es': 'No, no coordinada con Catastro', 'en': 'No, not coordinated with Cadastre'},
        }
        coord_val = coord_map.get(coord, {}).get(lang, coord)
    else:
        coord_val = na
    bullets.append(f"{T(lang,'ns_coord')}: {coord_val}")

    return bullets


def extract_cedula_summary(lang, cedula_text, structured=None):
    """
    Build a list of bullet-point findings from a cédula urbanística.
    Prefers structured data if provided; otherwise parses raw text.
    The raw text is NEVER returned or displayed.
    """
    structured = structured or {}
    findings = {}
    findings['classification'] = structured.get('clasificacion') or structured.get('classification')
    findings['status'] = structured.get('situacion') or structured.get('status')
    findings['restrictions'] = structured.get('restricciones') or structured.get('restrictions')
    findings['reference'] = structured.get('referencia_municipal') or structured.get('reference')

    text = cedula_text or ''

    if not findings['classification']:
        m = re.search(r'[Ss]uelo\s+(urbano|urbanizable(?:\s+no\s+programado)?|no\s+urbanizable|r[úu]stico)[^\n\.]{0,80}', text)
        if m:
            findings['classification'] = m.group(0).strip(' .,:;')

    if not findings['status']:
        m = re.search(r'(?:SITUACI[ÓO]N|Situaci[óo]n)[:\s]+([^\n]{5,260}?)(?=\s*(?:RESTRICCIONES|Restricciones|Expediente|EXPEDIENTE|$))', text)
        if m:
            status = m.group(1).strip(' .,:;')
            if len(status) > 200:
                status = status[:197].rsplit(' ', 1)[0] + '…'
            findings['status'] = status

    if not findings['restrictions']:
        restr_list = []
        covered_spans = []
        for kw in [r'servidumbre[^\n\.]{0,120}', r'zona de polic[íi]a[^\n\.]{0,120}', r'protecci[óo]n[^\n\.]{0,120}', r'afecci[óo]n[^\n\.]{0,120}', r'dominio p[úu]blico[^\n\.]{0,120}', r'retranqueo[^\n\.]{0,120}']:
            for m in re.finditer(kw, text, re.IGNORECASE):
                start, end = m.span()
                # Skip if this span overlaps with an already-captured one
                if any(not (end <= s or start >= e) for s, e in covered_spans):
                    continue
                snippet = m.group(0).strip(' .,:;')
                if snippet and snippet not in restr_list:
                    restr_list.append(snippet)
                    covered_spans.append((start, end))
        findings['restrictions'] = restr_list if restr_list else None

    if not findings['reference']:
        m = re.search(r'(?:Expediente|EXPEDIENTE|Referencia)[:\s]+([A-Za-z0-9/\-\.]{3,30})', text)
        if m:
            findings['reference'] = m.group(1).strip(' .,:;')

    na = T(lang, 'ns_not_found')
    bullets = []
    bullets.append(f"{T(lang,'cd_classification')}: {findings['classification'] or na}")
    bullets.append(f"{T(lang,'cd_status')}: {findings['status'] or na}")

    restrictions = findings['restrictions']
    if restrictions:
        bullets.append(f"{T(lang,'cd_restrictions')}:")
        for r in restrictions[:6]:
            bullets.append(f"  – {r}")
    else:
        bullets.append(f"{T(lang,'cd_restrictions')}: {T(lang,'val_no')}")

    bullets.append(f"{T(lang,'cd_reference')}: {findings['reference'] or na}")
    return bullets


# ── Download & register fonts ────────────────────────────────────────────────
FONT_DIR = '/tmp/pdf_fonts'
os.makedirs(FONT_DIR, exist_ok=True)


def dl_font(name, url):
    path = f'{FONT_DIR}/{name}.ttf'
    if not os.path.exists(path):
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(path, 'wb') as f:
            f.write(r.content)
    return path


FONT_URLS = {
    'DMSans':  'https://github.com/google/fonts/raw/main/ofl/dmsans/DMSans%5Bopsz%2Cwght%5D.ttf',
    'DMSerif': 'https://github.com/google/fonts/raw/main/ofl/dmseriftext/DMSerifText-Regular.ttf',
}

try:
    p1 = dl_font('DMSans', FONT_URLS['DMSans'])
    p2 = dl_font('DMSerif', FONT_URLS['DMSerif'])
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
ML = 2.2 * cm
MR = 2.2 * cm
MT = 2 * cm
MB = 2.5 * cm


# ── Style helpers ─────────────────────────────────────────────────────────────
def style(name, **kw):
    base = getSampleStyleSheet()['Normal']
    return ParagraphStyle(name, parent=base, **kw)


S_BODY       = style('body',    fontName=BODY_FONT, fontSize=9.5, leading=15, textColor=TEXT, alignment=TA_JUSTIFY)
S_BODY_L     = style('bodyL',   fontName=BODY_FONT, fontSize=9.5, leading=15, textColor=TEXT, alignment=TA_LEFT)
S_SMALL      = style('small',   fontName=BODY_FONT, fontSize=8,   leading=11, textColor=MUTED)
S_CAPTION    = style('caption', fontName=BOLD_FONT, fontSize=8,   leading=11, textColor=MUTED, spaceAfter=2)
S_CELL       = style('cell',    fontName=BODY_FONT, fontSize=9,   leading=13, textColor=TEXT)
S_CELL_B     = style('cellB',   fontName=BOLD_FONT, fontSize=9,   leading=13, textColor=TEXT)
S_CELL_MUT   = style('cellM',   fontName=BODY_FONT, fontSize=8.5, leading=12, textColor=MUTED)
S_RISK_LBL   = style('riskL',   fontName=BOLD_FONT, fontSize=8,   leading=11, alignment=TA_CENTER)
S_SUBSEC     = style('subsec',  fontName=BOLD_FONT, fontSize=10.5, leading=15, textColor=NAVY, spaceBefore=12, spaceAfter=5)
S_ALERT_T    = style('alertT',  fontName=BOLD_FONT, fontSize=9.5, leading=13, textColor=TEXT)
S_ALERT_B    = style('alertB',  fontName=BODY_FONT, fontSize=9,   leading=13, textColor=TEXT)
S_CLAUSE     = style('clause',  fontName=BODY_FONT, fontSize=8.5, leading=13, textColor=TEXT, leftIndent=8, rightIndent=8)
S_BULLET     = style('bullet',  fontName=BODY_FONT, fontSize=9.5, leading=14, textColor=TEXT, leftIndent=12, bulletIndent=0)
S_FINDING    = style('finding', fontName=BODY_FONT, fontSize=9,   leading=13.5, textColor=TEXT, leftIndent=10)


# ── Custom flowables ──────────────────────────────────────────────────────────
class SectionBadge(Flowable):
    """Section number badge + title, drawn directly on canvas to avoid line
    breaks inside the number (e.g. '02' must never wrap to '0\\n2')."""

    def __init__(self, num_str, title, lang='sv'):
        Flowable.__init__(self)
        self.num_str = num_str
        self.title = title
        self.lang = lang

    def wrap(self, availWidth, availHeight):
        self._avail_w = availWidth
        return (availWidth, 1.2 * cm)

    def draw(self):
        c = self.canv
        # Navy badge
        c.setFillColor(NAVY)
        c.roundRect(0, 0.15 * cm, 0.9 * cm, 0.9 * cm, 3, stroke=0, fill=1)
        # Number, single string, centred — never split across lines
        c.setFillColor(GOLD)
        c.setFont(BOLD_FONT, 11)
        c.drawCentredString(0.45 * cm, 0.42 * cm, self.num_str)
        # Title
        c.setFillColor(NAVY)
        c.setFont(BOLD_FONT, 13.5)
        c.drawString(1.25 * cm, 0.42 * cm, self.title)
        # Gold underline spanning the available width
        avail_w = getattr(self, '_avail_w', W - ML - MR)
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.5)
        c.line(0, 0.05 * cm, avail_w, 0.05 * cm)


def section_heading(num, title, lang='sv'):
    """Section header block, wrapped in KeepTogether to avoid page splits."""
    badge = SectionBadge(num, title, lang)
    return [KeepTogether([Spacer(1, 0.55 * cm), badge, Spacer(1, 0.35 * cm)])]


class CoverPage(Flowable):
    def __init__(self, prop, lang='sv'):
        Flowable.__init__(self)
        self.prop = prop
        self.lang = lang

    def wrap(self, w, h):
        return (w, h)

    def draw(self):
        c = self.canv
        d = self.prop
        lg = self.lang
        pw = self.canv._pagesize[0]
        ph = self.canv._pagesize[1]

        # Full navy background
        c.setFillColor(NAVY)
        c.rect(0, 0, pw, ph, stroke=0, fill=1)

        # Subtle secondary panel for depth
        c.setFillColor(HexColor('#223347'))
        c.rect(0, ph * 0.42, pw, ph * 0.58, stroke=0, fill=1)
        c.setFillColor(NAVY)
        c.rect(0, 0, pw, ph * 0.42, stroke=0, fill=1)

        # Gold left stripe (full height)
        c.setFillColor(GOLD)
        c.rect(0, 0, 6, ph, stroke=0, fill=1)

        # Crimson bottom bar
        c.setFillColor(CRIMSON)
        c.rect(0, 0, pw, 1 * cm, stroke=0, fill=1)

        # Crimson logo box top-right
        box_w, box_h = 5.6 * cm, 3.2 * cm
        c.setFillColor(CRIMSON)
        c.rect(pw - box_w, ph - box_h, box_w, box_h, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(pw - box_w, ph - box_h, box_w, 0.08 * cm, stroke=0, fill=1)
        c.setFont(BOLD_FONT, 13)
        c.setFillColor(white)
        c.drawString(pw - box_w + 0.35 * cm, ph - 1.55 * cm, "COLÁS JURIST")
        c.setFont(BODY_FONT, 8)
        c.setFillColor(HexColor('#F0D9B0'))
        c.drawString(pw - box_w + 0.35 * cm, ph - 1.95 * cm, "Spansk jurist · Costa Blanca")

        # Decorative thin gold rule under logo box
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.6)
        c.line(pw - box_w, ph - box_h - 0.15 * cm, pw, ph - box_h - 0.15 * cm)

        # AI DUE DILIGENCE small-caps label
        c.setFont(BOLD_FONT, 10)
        c.setFillColor(GOLD)
        c.drawString(ML + 0.3 * cm, ph - 2.1 * cm, T(lg, 'ai_label'))
        c.setStrokeColor(GOLD)
        c.setLineWidth(1)
        c.line(ML + 0.3 * cm, ph - 2.3 * cm, ML + 3.2 * cm, ph - 2.3 * cm)

        # Report title kicker
        c.setFont(BODY_FONT, 9.5)
        c.setFillColor(HexColor('#9FB4C8'))
        c.drawString(ML + 0.3 * cm, ph - 3.5 * cm, T(lg, 'report_title'))

        # Property title (large serif)
        addr = d.get('direccion') or d.get('municipio') or 'Propiedad'
        # simple wrap into lines of ~34 chars, max 3 lines
        words = addr.split()
        lines, cur = [], ''
        for w_ in words:
            trial = (cur + ' ' + w_).strip()
            if len(trial) > 30 and cur:
                lines.append(cur)
                cur = w_
            else:
                cur = trial
        if cur:
            lines.append(cur)
        lines = lines[:3]

        y = ph - 4.4 * cm
        c.setFont(SERIF_FONT, 27)
        c.setFillColor(white)
        for line in lines:
            c.drawString(ML + 0.3 * cm, y, line)
            y -= 1.15 * cm

        # Reference number, muted cream
        ref = d.get('ref_catastral', '—')
        y -= 0.25 * cm
        c.setFont(BODY_FONT, 10.5)
        c.setFillColor(HexColor('#C9AF7E'))
        c.drawString(ML + 0.3 * cm, y, f"{T(lg,'lbl_ref_cat')}: {ref}")

        # Divider
        y -= 0.55 * cm
        c.setStrokeColor(HexColor('#3A4A5C'))
        c.setLineWidth(0.75)
        c.line(ML + 0.3 * cm, y, pw - MR, y)

        # Metadata block (6 rows)
        y -= 0.85 * cm
        meta = [
            (T(lg, 'cov_katastral'),    d.get('ref_catastral', '—')),
            (T(lg, 'cov_registro'),     d.get('registro', '—')),
            (T(lg, 'cov_kommun'),       d.get('municipio', '—')),
            (T(lg, 'cov_datum'),        d.get('fecha', format_date(lg))),
            (T(lg, 'cov_sammanstalld'), T(lg, 'elaborado')),
            (T(lg, 'cov_omfattning'),   T(lg, 'alcance')),
        ]
        for label, val in meta:
            c.setFont(BOLD_FONT, 8)
            c.setFillColor(GOLD)
            c.drawString(ML + 0.3 * cm, y, label.upper())
            c.setFont(BODY_FONT, 9.3)
            c.setFillColor(HexColor('#D7E2EC'))
            # Wrap long values
            val_str = str(val)
            max_chars = 58
            if len(val_str) > max_chars:
                val_str = val_str[:max_chars - 1] + '…'
            c.drawString(ML + 5.3 * cm, y, val_str)
            y -= 0.62 * cm

        # AI disclaimer box (amber)
        disc_y_bottom = 2.15 * cm
        disc_h = 2.55 * cm
        disc_y_top = disc_y_bottom + disc_h
        c.setFillColor(HexColor('#3A2E10'))
        c.rect(ML, disc_y_bottom, pw - ML - MR, disc_h, stroke=0, fill=1)
        c.setStrokeColor(YEL_RISK)
        c.setLineWidth(1.2)
        c.rect(ML, disc_y_bottom, pw - ML - MR, disc_h, stroke=1, fill=0)
        c.setFillColor(YEL_RISK)
        c.rect(ML, disc_y_bottom, 0.12 * cm, disc_h, stroke=0, fill=1)

        c.setFont(BOLD_FONT, 8.5)
        c.setFillColor(HexColor('#FCD34D'))
        c.drawString(ML + 0.4 * cm, disc_y_top - 0.45 * cm, {
            'sv': '** AI-GENERERAT INNEHALL - EJ JURIDISK RADGIVNING **',
            'es': '** CONTENIDO GENERADO POR IA - NO ES ASESORAMIENTO JURIDICO **',
            'en': '** AI-GENERATED CONTENT - NOT LEGAL ADVICE **',
        }.get(lg, '** AI-GENERATED CONTENT - NOT LEGAL ADVICE **'))

        c.setFont(BODY_FONT, 7.6)
        c.setFillColor(HexColor('#F3E3B8'))
        disclaimer = T(lg, 'disclaimer_cover')
        # wrap disclaimer text manually to fit width
        max_chars_line = 108
        words = disclaimer.split()
        dl_lines, cur = [], ''
        for w_ in words:
            trial = (cur + ' ' + w_).strip()
            if len(trial) > max_chars_line and cur:
                dl_lines.append(cur)
                cur = w_
            else:
                cur = trial
        if cur:
            dl_lines.append(cur)
        ty = disc_y_top - 0.85 * cm
        for line in dl_lines[:5]:
            c.drawString(ML + 0.4 * cm, ty, line)
            ty -= 0.32 * cm

        # Bottom contact line (gold), above crimson bar
        c.setFont(BODY_FONT, 8.5)
        c.setFillColor(GOLD)
        c.drawString(ML + 0.3 * cm, 1.35 * cm, "colasjurist.se  ·  info@colas-abogados.com  ·  +34 629 549 430")


def info_table(rows, col_widths=None):
    """Two-column label/value table."""
    if not col_widths:
        col_widths = [5.2 * cm, 10.3 * cm]
    data = []
    for label, val in rows:
        data.append([
            Paragraph(label, S_CELL_MUT),
            Paragraph(str(val) if val not in (None, '') else '—', S_CELL_B)
        ])
    if not data:
        data = [[Paragraph('—', S_CELL_MUT), Paragraph('—', S_CELL_B)]]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [white, LIGHT_BG]),
    ]))
    return t


def findings_block(bullets):
    """Render a list of finding strings (some prefixed with '  – ' for
    sub-items) as Paragraph flowables."""
    flows = []
    for b in bullets:
        if b.startswith('  – '):
            flows.append(Paragraph('• ' + b.strip()[2:], S_FINDING))
        else:
            flows.append(Paragraph(f'<b>{b.split(":")[0]}:</b>{b.split(":",1)[1] if ":" in b else ""}', S_FINDING))
    return flows


def risk_badge(level, lang='sv'):
    """Colored risk level badge — language aware."""
    _lbl = {
        'red':      T(lang,'risk_critico'),
        'orange':   T(lang,'risk_importante'),
        'yellow':   T(lang,'risk_moderado'),
        'green':    T(lang,'risk_ok'),
        'resuelto': T(lang,'risk_ok'),
        'bajo':     T(lang,'risk_moderado'),
        'medio':    T(lang,'risk_importante'),
        'alto':     T(lang,'risk_critico'),
    }
    _col = {
        'red': (RED_RISK, RED_BG), 'orange': (ORG_RISK, ORG_BG),
        'yellow': (YEL_RISK, YEL_BG), 'green': (GRN_RISK, GRN_BG),
        'resuelto': (GRN_RISK, GRN_BG), 'bajo': (YEL_RISK, YEL_BG),
        'medio': (ORG_RISK, ORG_BG), 'alto': (RED_RISK, RED_BG),
    }
    label = _lbl.get(str(level).lower(), '—')
    fg, bg = _col.get(str(level).lower(), (MUTED, LIGHT_BG))
    fg_hex = '#%02x%02x%02x' % (int(fg.red * 255), int(fg.green * 255), int(fg.blue * 255))
    p = Paragraph(f'<font color="{fg_hex}"><b>{label}</b></font>', S_RISK_LBL)
    t = Table([[p]], colWidths=[2.5 * cm], rowHeights=[0.55 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('BOX', (0, 0), (-1, -1), 0.5, fg),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return t


def alert_block(alert, lang='sv'):
    """Full alert card with title, body, action, clause, documents."""
    level = alert.get('level', 'yellow')
    cfg = {
        'red':    (RED_RISK, RED_BG),
        'orange': (ORG_RISK, ORG_BG),
        'yellow': (YEL_RISK, YEL_BG),
        'green':  (GRN_RISK, GRN_BG),
    }
    fg, bg = cfg.get(level, (MUTED, LIGHT_BG))

    rows = []
    title = alert.get('title', '')
    badge = risk_badge(level)
    title_row = Table([[badge, Paragraph(title, S_ALERT_T)]], colWidths=[2.7 * cm, 12.8 * cm])
    title_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    rows.append(title_row)

    body = alert.get('body', '')
    if body:
        rows.append(Spacer(1, 3))
        rows.append(Paragraph(body, S_ALERT_B))

    action = alert.get('action', '')
    if action:
        rows.append(Spacer(1, 3))
        rows.append(Paragraph(f'<b>→ {action}</b>', style('act', fontName=BOLD_FONT, fontSize=9, textColor=fg, leading=13)))

    docs = alert.get('documents', [])
    if docs:
        rows.append(Spacer(1, 4))
        rows.append(Paragraph(f'<b>{T(lang, "docs_solicitar")}</b>', style('dh', fontName=BOLD_FONT, fontSize=8.5, textColor=NAVY, leading=12)))
        for doc in docs:
            rows.append(Paragraph(f'• {doc}', S_BULLET))

    clause = alert.get('clause', '')
    if clause and clause != 'null':
        rows.append(Spacer(1, 5))
        rows.append(Paragraph(f'<b>{T(lang, "clausula_recom")}</b>', style('ch', fontName=BOLD_FONT, fontSize=8.5, textColor=NAVY, leading=12)))
        rows.append(Paragraph(f'"{clause}"', S_CLAUSE))

    inner = Table([[r] for r in rows], colWidths=[15.5 * cm])
    inner.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('LINEBEFORE', (0, 0), (0, -1), 3, fg),
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
        badge = risk_badge(a.get('level', 'yellow'), lang)
        rows.append([
            Paragraph(str(a.get('category', '')).capitalize(), S_CELL),
            badge,
            Paragraph(a.get('title', ''), S_CELL),
        ])
    t = Table(rows, colWidths=[3.5 * cm, 2.8 * cm, 9.2 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    return t


def checklist_table(items, title, lang='sv'):
    """Numbered action checklist table."""
    if not items:
        return Spacer(1, 0)
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
    t = Table(rows, colWidths=[0.8 * cm, 14.7 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return t


_PDF_LANG = 'sv'  # set before build, used by header/footer callback


def page_header_footer(canvas, doc):
    """Recurring header/footer for interior pages."""
    canvas.saveState()
    w, h = A4
    lg = _PDF_LANG

    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(ML, h - 1.5 * cm, w - MR, h - 1.5 * cm)
    canvas.setFont(BODY_FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(ML, h - 1.2 * cm, T(lg, "header_conf"))
    canvas.drawRightString(w - MR, h - 1.2 * cm, T(lg, "header_right"))

    canvas.line(ML, 1.8 * cm, w - MR, 1.8 * cm)
    canvas.setFont(BODY_FONT, 7.5)
    canvas.drawString(ML, 1.3 * cm, T(lg, "footer_author"))
    canvas.drawRightString(w - MR, 1.3 * cm, f'{T(lg, "footer_pagina")} {doc.page}')

    canvas.restoreState()


# ── Main generator ────────────────────────────────────────────────────────────
def generate_pdf(report_data: dict, output_path: str) -> str:
    """
    report_data keys:
      lang:       'sv' | 'es' | 'en'
      property:   dict with direccion, ref_catastral, registro, municipio, etc.
      catastro:   dict with surface, year, elements, valor_catastral, etc.
      registro:   dict with cargas, superficie_registro, nota_simple_text, etc.
      urbanismo:  dict with clasificacion, cedula_text, alertas, etc.
      analysis:   dict from AI analysis (score, risk_level, clasificacion_final, alerts, etc.)
    """
    try:
        global _PDF_LANG
        report_data = report_data or {}
        lang = report_data.get('lang', 'sv')
        _PDF_LANG = lang

        prop = report_data.get('property', {}) or {}
        cat  = report_data.get('catastro', {}) or {}
        reg  = report_data.get('registro', {}) or {}
        urb  = report_data.get('urbanismo', {}) or {}
        ai   = report_data.get('analysis', {}) or {}

        today = format_date(lang)
        prop['fecha'] = prop.get('fecha') or today

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=ML, rightMargin=MR,
            topMargin=2.2 * cm, bottomMargin=2.5 * cm,
            title=f"Due Diligence — {prop.get('direccion', 'Propiedad')}",
            author="Colás Jurist AI Due Diligence",
        )

        alerts = ai.get('alerts', []) or []
        red_a  = [a for a in alerts if a.get('level') == 'red']
        org_a  = [a for a in alerts if a.get('level') == 'orange']
        yel_a  = [a for a in alerts if a.get('level') == 'yellow']
        grn_a  = [a for a in alerts if a.get('level') == 'green']

        score   = ai.get('score', 0) or 0
        clasif  = ai.get('clasificacion_final', 'no_deberia_firmarse')
        summary = ai.get('summary', '') or ''

        clasif_map = T(lang, 'clasif_label') if isinstance(T(lang, 'clasif_label'), dict) else {}
        # T() with dict values needs special handling since LABELS['clasif_label'][lang] is itself a dict
        clasif_dict = {
            'sv': {'puede_firmarse': 'KAN UNDERTECKNAS', 'puede_firmarse_con_modificaciones': 'KAN UNDERTECKNAS MED ÄNDRINGAR', 'no_deberia_firmarse': 'BÖR INTE UNDERTECKNAS'},
            'es': {'puede_firmarse': 'PUEDE FIRMARSE', 'puede_firmarse_con_modificaciones': 'PUEDE FIRMARSE CON MODIFICACIONES', 'no_deberia_firmarse': 'NO DEBERÍA FIRMARSE'},
            'en': {'puede_firmarse': 'CAN BE SIGNED', 'puede_firmarse_con_modificaciones': 'CAN BE SIGNED WITH AMENDMENTS', 'no_deberia_firmarse': 'SHOULD NOT BE SIGNED'},
        }.get(lang, {})
        clasif_colors = {'puede_firmarse': GRN_RISK, 'puede_firmarse_con_modificaciones': YEL_RISK, 'no_deberia_firmarse': RED_RISK}
        clasif_label = clasif_dict.get(clasif, '—')
        clasif_color = clasif_colors.get(clasif, MUTED)

        story = []

        # ── COVER ────────────────────────────────────────────────────────────
        story.append(CoverPage(prop, lang))
        story.append(PageBreak())

        # ── S01 IDENTIFICACIÓN ───────────────────────────────────────────────
        story.extend(section_heading('01', T(lang, 's01'), lang))
        rows_id = [
            (T(lang, 'lbl_direccion'), prop.get('direccion', '—')),
            (T(lang, 'lbl_ref_cat'),   prop.get('ref_catastral', '—')),
            (T(lang, 'lbl_tipo'),      translate_value(lang, prop.get('tipo', '—'))),
            (T(lang, 'lbl_municipio'), prop.get('municipio', '—')),
            (T(lang, 'lbl_anno'),      prop.get('anno_construccion', '—')),
            (T(lang, 'lbl_precio'),    prop.get('precio', '—')),
            (T(lang, 'lbl_vendedor'),  translate_value(lang, prop.get('vendedor', '—'))),
            (T(lang, 'lbl_estado'),    translate_value(lang, prop.get('estado', '—'))),
        ]
        story.append(info_table([(k, v) for k, v in rows_id if v and v != '—']))
        story.append(Spacer(1, 0.3 * cm))

        # ── S02 SITUACIÓN REGISTRAL ──────────────────────────────────────────
        story.extend(section_heading('02', T(lang, 's02'), lang))
        story.append(Paragraph('2.1 ' + T(lang, 's02_1'), S_SUBSEC))
        rows_reg = [
            (T(lang, 'lbl_registro'),    reg.get('registro', prop.get('registro', '—'))),
            (T(lang, 'lbl_finca'),       reg.get('finca', '—')),
            (T(lang, 'lbl_sup_constr'),  f"{reg.get('superficie_registro','—')} m²" if reg.get('superficie_registro') else '—'),
            (T(lang, 'lbl_sup_parcela'), f"{reg.get('superficie_parcela_registro','—')} m²" if reg.get('superficie_parcela_registro') else '—'),
            (T(lang, 'lbl_titularidad'), translate_value(lang, reg.get('titularidad', '—'))),
            (T(lang, 'lbl_coord_cat'),   reg.get('coordinacion_catastro', '—')),
        ]
        story.append(info_table([(k, v) for k, v in rows_reg if v and v != '—']))
        story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph('2.2 ' + T(lang, 's02_2'), S_SUBSEC))
        cargas = reg.get('cargas', prop.get('cargas', 'ninguna'))
        cargas_key = str(cargas).lower()
        cargas_text_map = {
            'ninguna':   T(lang, 'cargas_ninguna'),
            'hipoteca':  T(lang, 'cargas_hipoteca'),
            'embargo':   T(lang, 'cargas_embargo'),
            'usufructo': T(lang, 'cargas_usufructo'),
            'unknown':   T(lang, 'cargas_unknown'),
        }
        cargas_text = cargas_text_map.get(cargas_key, translate_value(lang, cargas))
        story.append(Paragraph(cargas_text, S_BODY))
        story.append(Spacer(1, 0.2 * cm))

        nota_text = reg.get('nota_simple_text', '')
        nota_structured = reg.get('nota_simple_data') or {}
        if nota_text or nota_structured:
            story.append(Paragraph(f'<b>{T(lang, "s02_nota")}</b>', S_SUBSEC))
            bullets = extract_nota_simple_summary(lang, nota_text, nota_structured)
            findings_flows = findings_block(bullets)
            story.append(KeepTogether(findings_flows[:2]) if len(findings_flows) >= 2 else findings_flows[0])
            for f in findings_flows[2:]:
                story.append(f)

        # ── S03 SITUACIÓN CATASTRAL ──────────────────────────────────────────
        story.extend(section_heading('03', T(lang, 's03'), lang))
        rows_cat = [
            (T(lang, 'lbl_ref_cat'),      cat.get('ref_catastral', prop.get('ref_catastral', '—'))),
            (T(lang, 'lbl_tipo'),         translate_value(lang, cat.get('uso', '—'))),
            (T(lang, 'lbl_sup_cat'),      f"{cat.get('superficie_catastro','—')} m²" if cat.get('superficie_catastro') else '—'),
            (T(lang, 'lbl_sup_parc_cat'), f"{cat.get('superficie_parcela_catastro','—')} m²" if cat.get('superficie_parcela_catastro') else '—'),
            (T(lang, 'lbl_anno_cat'),     cat.get('anno_construccion_catastro', '—')),
            (T(lang, 'lbl_val_cat'),      f"{cat.get('valor_catastral','—')} €" if cat.get('valor_catastral') else '—'),
            (T(lang, 'lbl_val_ref'),      f"{cat.get('valor_referencia','—')} €" if cat.get('valor_referencia') else '—'),
            (T(lang, 'lbl_piscina'),      T(lang, 'val_si') if cat.get('piscina_catastro') else (T(lang, 'val_no') if cat.get('piscina_catastro') is False else '—')),
            (T(lang, 'lbl_garaje'),       T(lang, 'val_si') if cat.get('garaje_catastro') else (T(lang, 'val_no') if cat.get('garaje_catastro') is False else '—')),
        ]
        story.append(info_table([(k, v) for k, v in rows_cat if v and v != '—']))

        # Discrepancy alert
        try:
            sup_cat = float(cat.get('superficie_catastro', 0) or 0)
            sup_reg = float(reg.get('superficie_registro', 0) or 0)
        except (TypeError, ValueError):
            sup_cat, sup_reg = 0, 0
        if sup_cat and sup_reg and abs(sup_cat - sup_reg) > 5:
            diff = abs(sup_cat - sup_reg)
            story.append(Spacer(1, 0.3 * cm))
            disc = Table([[
                Paragraph(T(lang, 'disc_alert'), style('dh', fontName=BOLD_FONT, fontSize=9.5, textColor=ORG_RISK, leading=13)),
                Paragraph(f'{T(lang,"disc_diff")}: {diff:.0f} m²', style('dd', fontName=BOLD_FONT, fontSize=9.5, textColor=ORG_RISK, leading=13, alignment=TA_RIGHT)),
            ]], colWidths=[10 * cm, 5.5 * cm])
            disc.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), ORG_BG),
                ('BOX', (0, 0), (-1, -1), 1, ORG_RISK),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(disc)
            story.append(Spacer(1, 4))
            body_fn = {
                'sv': lambda r, ca, di: f"Det finns en avvikelse på {di:.0f} m² mellan den inskrivna ytan i Registret ({r:.0f} m²) och Catastro ({ca:.0f} m²). Deklaration av obra nueva krävs före notarieakten.",
                'es': lambda r, ca, di: f"Existe una divergencia de {di:.0f} m² entre la superficie inscrita en el Registro ({r:.0f} m²) y la reflejada en el Catastro ({ca:.0f} m²). Se requiere declaración de obra nueva antes de la escritura.",
                'en': lambda r, ca, di: f"There is a discrepancy of {di:.0f} m² between the Land Registry ({r:.0f} m²) and the Cadastre ({ca:.0f} m²). An obra nueva declaration is required before the deed.",
            }.get(lang, None)
            if body_fn:
                story.append(Paragraph(body_fn(sup_reg, sup_cat, diff), S_BODY))

        # ── S04 SITUACIÓN URBANÍSTICA ─────────────────────────────────────────
        story.extend(section_heading('04', T(lang, 's04'), lang))
        rows_urb = [
            (T(lang, 'lbl_clasificacion'), translate_value(lang, urb.get('tipo_suelo', prop.get('tipo_suelo', '—')))),
            (T(lang, 'lbl_costas'),        T(lang, 'val_si') if prop.get('zona_costera') else T(lang, 'val_no')),
            (T(lang, 'lbl_lpo'),           prop.get('tiene_licencia_primera_ocupacion', '—')),
            (T(lang, 'lbl_expediente'),    prop.get('expediente_urbanistico', '—')),
        ]
        story.append(info_table([(k, v) for k, v in rows_urb if v and v not in ('—', 'None')]))

        cedula_text = urb.get('cedula_text', '')
        cedula_structured = urb.get('cedula_data') or {}
        if cedula_text or cedula_structured:
            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(f'<b>{T(lang, "s04_cedula")}</b>', S_SUBSEC))
            bullets = extract_cedula_summary(lang, cedula_text, cedula_structured)
            for f in findings_block(bullets):
                story.append(f)

        # ── S05 MAPA DE RIESGOS ────────────────────────────────────────────────
        story.extend(section_heading('05', T(lang, 's05'), lang))

        score_color = GRN_RISK if score >= 80 else (YEL_RISK if score >= 60 else (ORG_RISK if score >= 40 else RED_RISK))
        S_CL = style('cl', fontName=BOLD_FONT, fontSize=9.5, textColor=clasif_color, leading=13)
        S_CS = style('cs', fontName=BODY_FONT, fontSize=8.5, textColor=MUTED, leading=12)
        counts_text = f'{len(red_a)} {T(lang,"critico")} · {len(org_a)} {T(lang,"importante")} · {len(yel_a)} {T(lang,"moderado")}'
        score_table = Table([
            [
                Paragraph(f'<b>{score}</b>', style('sc', fontName=BOLD_FONT, fontSize=26, textColor=score_color, leading=30, alignment=TA_CENTER)),
                Paragraph(clasif_label, S_CL),
                Paragraph(counts_text, S_CS),
            ]
        ], colWidths=[2.2 * cm, 8 * cm, 5.3 * cm])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
            ('BOX', (0, 0), (-1, -1), 1.5, clasif_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 0.4 * cm))
        if summary:
            story.append(Paragraph(summary, S_BODY))
            story.append(Spacer(1, 0.3 * cm))

        if alerts:
            story.append(risk_table(alerts, lang))
            story.append(Spacer(1, 0.5 * cm))

        if red_a:
            story.append(Paragraph(T(lang, 'problemas_criticos'), S_SUBSEC))
            for a in red_a:
                story.append(alert_block(a, lang))
        if org_a:
            story.append(Paragraph(T(lang, 'advertencias'), S_SUBSEC))
            for a in org_a:
                story.append(alert_block(a, lang))
        if yel_a:
            story.append(Paragraph(T(lang, 'puntos_atencion'), S_SUBSEC))
            for a in yel_a:
                story.append(alert_block(a, lang))
        if grn_a:
            story.append(Paragraph(T(lang, 'aspectos_orden'), S_SUBSEC))
            for a in grn_a:
                story.append(alert_block(a, lang))

        # ── S06 CONCLUSIÓN Y RECOMENDACIONES ────────────────────────────────
        story.extend(section_heading('06', T(lang, 's06'), lang))

        missing = ai.get('missing_clauses', []) or []
        if missing:
            story.append(Paragraph(T(lang, 'clausulas_missing'), S_SUBSEC))
            for m in missing:
                story.append(Paragraph(f'• {m}', S_BULLET))
            story.append(Spacer(1, 0.3 * cm))

        chk_firmar = ai.get('checklist_antes_de_firmar', []) or []
        if chk_firmar:
            story.append(Paragraph(T(lang, 'chk_firmar'), S_SUBSEC))
            story.append(checklist_table(chk_firmar, T(lang, 'accion'), lang))
            story.append(Spacer(1, 0.3 * cm))

        chk_escritura = ai.get('checklist_antes_de_escritura', []) or []
        if chk_escritura:
            story.append(Paragraph(T(lang, 'chk_escritura'), S_SUBSEC))
            story.append(checklist_table(chk_escritura, T(lang, 'accion'), lang))
            story.append(Spacer(1, 0.3 * cm))

        acts = ai.get('actuaciones_previas_imprescindibles', []) or []
        if acts:
            story.append(Paragraph(T(lang, 'actuaciones'), S_SUBSEC))
            story.append(checklist_table(acts, T(lang, 'actuacion'), lang))
            story.append(Spacer(1, 0.3 * cm))

        preguntas = ai.get('preguntas_adicionales', []) or []
        if preguntas:
            story.append(Paragraph(T(lang, 'preguntas'), S_SUBSEC))
            for q in preguntas:
                story.append(Paragraph(f'• {q}', S_BULLET))
            story.append(Spacer(1, 0.3 * cm))

        # AI Disclaimer block
        story.append(Spacer(1, 0.5 * cm))
        disc_text = T(lang, 'disclaimer_cover')
        disc_block = Table([[
            Paragraph('AI', style('di', fontName=BOLD_FONT, fontSize=9, textColor=YEL_RISK, alignment=TA_CENTER, leading=11)),
            Paragraph(disc_text, style('db', fontName=BODY_FONT, fontSize=8, textColor=TEXT, leading=12)),
        ]], colWidths=[1 * cm, 14.5 * cm])
        disc_block.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), YEL_BG),
            ('BOX', (0, 0), (-1, -1), 1, YEL_RISK),
            ('LINEBEFORE', (0, 0), (0, -1), 3, YEL_RISK),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(disc_block)
        story.append(Spacer(1, 1 * cm))

        sig_rows = [
            [Paragraph(f'<b>{T(lang, "sig_title")}</b>', style('sn', fontName=BOLD_FONT, fontSize=10, textColor=NAVY, leading=14))],
            [Paragraph(T(lang, 'sig_sub'), style('st', fontName=BODY_FONT, fontSize=8.5, textColor=MUTED, leading=12))],
            [Paragraph(T(lang, 'sig_addr'), style('sa', fontName=BODY_FONT, fontSize=8, textColor=MUTED, leading=11))],
            [Paragraph('<a href="https://colasjurist.se" color="blue">colasjurist.se</a> · info@colas-abogados.com · +34 629 549 430',
                       style('sw', fontName=BODY_FONT, fontSize=8, textColor=MUTED, leading=11))],
            [Paragraph(T(lang, 'sig_disclaimer'), style('sd', fontName=BODY_FONT, fontSize=7.5, textColor=YEL_RISK, leading=11))],
            [Paragraph(f'{T(lang,"fecha_informe")}: {today}', S_SMALL)],
        ]
        sig = Table(sig_rows, colWidths=[15.5 * cm])
        sig.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CREAM),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
            ('LINEBEFORE', (0, 0), (0, -1), 3, GOLD),
            ('LEFTPADDING', (0, 0), (-1, -1), 14),
            ('RIGHTPADDING', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
        ]))
        story.append(sig)

        doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=page_header_footer)
        print(f"PDF generated: {output_path}")
        return output_path

    except Exception as e:
        raise RuntimeError(f"Failed to generate Due Diligence PDF: {e}") from e


# ── CLI / test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    sample = {
        "lang": "sv",
        "property": {
            "direccion": "Calle Serra del Cid 16, L'Alfàs del Pi",
            "ref_catastral": "2648109YH5724N0001FB",
            "registro": "Callosa d'en Sarrià",
            "municipio": "L'Alfàs del Pi (Alicante)",
            "tipo": "segunda-mano",
            "anno_construccion": "1970",
            "precio": "443.000 €",
            "vendedor": "particular",
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
            "nota_simple_text": (
                "REGISTRO DE LA PROPIEDAD DE CALLOSA D'EN SARRIÀ. NOTA SIMPLE INFORMATIVA.\n"
                "FINCA NÚMERO: 4521. TITULAR: Juan García Martínez, con DNI 12345678A, por título de compraventa. "
                "DESCRIPCIÓN: Vivienda unifamiliar aislada sita en Calle Serra del Cid 16, con una superficie construida "
                "de 103 m² y parcela de 540 m². CARGAS: Hipoteca a favor de CaixaBank S.A. constituida en escritura de "
                "fecha 12 de marzo de 2015 por importe de 150.000 euros de principal; Nota marginal de afección fiscal. "
                "La finca no consta coordinada gráficamente con el Catastro."
            ),
        },
        "urbanismo": {
            "tipo_suelo": "no-urbanizable",
            "cedula_text": (
                "AYUNTAMIENTO DE L'ALFÀS DEL PI. DEPARTAMENTO DE URBANISMO. CÉDULA URBANÍSTICA.\n"
                "SITUACIÓN: La vivienda está emplazada en Suelo Urbanizable No Programado (S.U.N.P.) 6 Serra del Cid "
                "y tiene una antigüedad superior a quince años, por lo que resulta de aplicación la Disposición "
                "Transitoria 26ª de la LOTUP. RESTRICCIONES: Zona de policía de cauces a menos de 100 metros; "
                "servidumbre de paso registrada a favor de la finca colindante. Expediente: URB-2023-00456."
            ),
        },
        "analysis": {
            "score": 28,
            "risk_level": "critical",
            "clasificacion_final": "no_deberia_firmarse",
            "summary": "Operation med hög risk med tre kritiska brister: (1) registrerad inteckning om 150 000 € utan mekanism för innehållande; (2) allvarlig katastral avvikelse — registret visar 103 m² men Catastro anger 209 m²; (3) extremt kort tidsfrist. Bör inte undertecknas utan att de kritiska punkterna åtgärdas.",
            "alerts": [
                {
                    "level": "red",
                    "category": "hipoteca",
                    "title": "Registrerad inteckning utan avregistreringsklausul",
                    "body": "Fastigheten är belastad med en inteckning till förmån för CaixaBank om 150 000 €. Kontraktet anger inte någon mekanism för innehållande eller garanti för samtidig avregistrering vid undertecknandet av köpebrevet.",
                    "action": "Begär skuldsaldointyg från CaixaBank och inför en innehållandeklausul i avtalet.",
                    "documents": ["Skuldsaldointyg (CaixaBank)", "Avregistreringshandling för inteckningen"],
                    "clause": "Köparen ska från den summa som ska betalas vid undertecknandet innehålla det belopp som krävs för att avregistrera inteckningen i registret, vars saldo ska styrkas genom ett skuldintyg utfärdat av den fordringsägande institutionen senast 10 arbetsdagar före datumet för den officiella köpehandlingen."
                },
                {
                    "level": "red",
                    "category": "catastral",
                    "title": "Allvarlig avvikelse Catastro–Register (106 m²)",
                    "body": "Det finns en skillnad på 106 m² mellan den registrerade ytan (103 m²) och den som anges i Catastro (209 m²). Ytterligare konstruktioner är inte registrerade.",
                    "action": "Kräv en deklaration om obra nueva före undertecknandet eller innehållande av köpeskillingen för att täcka kostnaden.",
                    "documents": ["Uppdaterad nota simple", "Beskrivande och grafisk uppgift från Catastro"],
                    "clause": "Säljaren förbinder sig att inför notarie deklarera den obra nueva som motsvarar befintliga konstruktioner innan undertecknandet av den officiella köpehandlingen, vilket utgör ett väsentligt villkor för detta avtal."
                },
                {
                    "level": "orange",
                    "category": "urbanismo",
                    "title": "Icke-programmerad urbaniserbar mark — särskilt regelverk",
                    "body": "Fastigheten ligger i S.U.N.P. nr 6. Åldern över 15 år skyddar byggnaderna enligt DT 26 TRLOTUP, men det bör bekräftas muntligen med kommunens stadsarkitekt.",
                    "action": "Begär intyg om att ingen urbanistisk överträdelse föreligger från kommunen.",
                    "documents": ["Intyg om ingen urbanistisk överträdelse", "Cédula urbanística"],
                    "clause": "Säljaren garanterar att fastigheten inte är föremål för något ärende om urbanistisk överträdelse och åtar sig att inhämta intyg från kommunen innan undertecknandet av köpehandlingen."
                },
            ],
            "missing_clauses": [
                "Uppskjutande villkor om lånefinansiering",
                "Klausul om frihet från belastningar och gravamen",
                "Klausul om frihet från nyttjanderätter",
                "Reglering av byggnadernas urbanistiska status",
            ],
            "checklist_antes_de_firmar": [
                "Hämta uppdaterad nota simple från fastighetsregistret",
                "Begär skuldsaldointyg från CaixaBank",
                "Verifiera den urbanistiska statusen hos kommunen i L'Alfàs del Pi",
                "Granska de senaste 3 protokollen från samfällighetsföreningen",
                "Bekräfta att energideklarationen är giltig",
            ],
            "checklist_antes_de_escritura": [
                "Intyg om ekonomisk avregistrering av inteckningen hos CaixaBank",
                "Deklaration om obra nueva utfärdad inför notarie",
                "Intyg om att inga skulder finns till samfällighetsföreningen",
                "Kvitto för innevarande års fastighetsskatt (IBI)",
                "Reglering av överlåtelseskatt inom 30 dagar",
            ],
            "actuaciones_previas_imprescindibles": [
                "Inför en klausul om innehållande för inteckningen i det privata avtalet",
                "Kräv deklaration om obra nueva som ett uppskjutande villkor",
                "Begär intyg om att ingen urbanistisk överträdelse föreligger från kommunen",
            ],
            "preguntas_adicionales": [
                "Finns det en giltig energideklaration?",
                "Har samfällighetsföreningen några utestående extra avgifter?",
                "Är säljaren skatterättsligt bosatt i Spanien?",
            ],
            "documents_to_request": [
                "Uppdaterad nota simple från fastighetsregistret",
                "Skuldsaldointyg (CaixaBank)",
                "Intyg om ingen urbanistisk överträdelse",
                "Intyg om ingen skuld till samfällighetsföreningen",
                "Kvitto för innevarande års IBI",
                "Giltig energideklaration",
            ]
        }
    }

    out = '/home/user/workspace/due_diligence_redesigned.pdf'
    generate_pdf(sample, out)
