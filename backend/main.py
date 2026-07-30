import os
import shutil
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Response, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.schemas.protection_schema import ProtectionSettingsSchema
from backend.audit_engine.auditor import ProtectionAuditor, AuditFinding, Severity
from backend.audit_engine.groq_auditor import GroqHardAuditor
from backend.drivers.ge_multilin_driver import GEMultilinDriver
from backend.drivers.omicron_xrio_driver import OmicronXRIODriver
from backend.parser.ecap_parser import ECAPGeminiParser
from backend.parser.digsilent_parser import DIgSILENTParser
from backend.parser.pdf_text_extractor import PDFTextExtractor
from backend.reports.report_generator import ProtectionReportGenerator
from backend.security.sanitizer import CIPSanitizer

app = FastAPI(
    title="Vela Protection Agent API",
    description="Motor de Auditoría Multi-Agente de ECAP y Parametrización para Relés de Protecciones",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Resolución de ruta absoluta para la carpeta frontend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend"))
os.makedirs(FRONTEND_DIR, exist_ok=True)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Vela Protection Agent Engine v2.0"}

@app.post("/api/upload-ecap")
async def upload_and_process_ecap(
    file: UploadFile = File(...),
    digsilent_file: Optional[UploadFile] = File(None),
    rule_files: List[UploadFile] = File(default=[]),
    custom_rules: Optional[str] = Form(None),
    rule_links: Optional[str] = Form(None)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo principal debe ser en formato PDF.")

    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ═══════════════════════════════════════════════════════════
    # PASO 0: Extracción de texto bruto con PyMuPDF (determinista)
    # ═══════════════════════════════════════════════════════════
    print("[Pipeline] Paso 0: Extrayendo texto bruto del PDF con PyMuPDF...")
    raw_pdf_text = PDFTextExtractor.extract_full_text(file_location)
    pdf_page_count = len(PDFTextExtractor.extract_pages(file_location))
    print(f"[Pipeline] Texto bruto extraído: {len(raw_pdf_text)} caracteres, {pdf_page_count} páginas")

    digsilent_relays = []
    if digsilent_file and digsilent_file.filename:
        digsilent_path = os.path.join(UPLOAD_DIR, f"digsilent_{digsilent_file.filename}")
        with open(digsilent_path, "wb") as buf:
            shutil.copyfileobj(digsilent_file.file, buf)
        try:
            d_parser = DIgSILENTParser()
            digsilent_relays = d_parser.parse_digsilent_export(digsilent_path)
        except Exception as e:
            print(f"Advertencia procesando archivo DIgSILENT: {e}")

    rule_file_paths = []
    if rule_files:
        for rf in rule_files:
            if rf.filename:
                rf_path = os.path.join(UPLOAD_DIR, f"rule_{rf.filename}")
                with open(rf_path, "wb") as buf:
                    shutil.copyfileobj(rf.file, buf)
                rule_file_paths.append(rf_path)

    combined_rules = custom_rules or ""
    if rule_links:
        combined_rules += f"\n[LINKS REGULATORIOS ADJUNTOS]: {rule_links}"
    if digsilent_relays:
        combined_rules += f"\n[SIMULACIÓN DIGSILENT DETECTADA]: Proyecto cargado con {len(digsilent_relays)} modelos ElmRelay en PowerFactory."

    try:
        # ═══════════════════════════════════════════════════════════
        # PASO 1: Parsing Multi-Agente (Extractor + Regulatorio)
        # ═══════════════════════════════════════════════════════════
        print("[Pipeline] Paso 1: Parsing multi-agente con Gemini...")
        parser = ECAPGeminiParser()
        settings_list = parser.parse_pdf_to_schema_list(file_location, custom_rules=combined_rules, extra_pdf_paths=rule_file_paths)
        
        # ═══════════════════════════════════════════════════════════
        # PASO 2: Auditoría (Determinista + Groq Deep Reasoning)
        # ═══════════════════════════════════════════════════════════
        print("[Pipeline] Paso 2: Auditoría determinista + Groq Deep Reasoning...")
        audited_relays = []
        critical_total = 0
        warning_total = 0

        digsilent_discrepancies = []
        if digsilent_relays:
            d_parser = DIgSILENTParser()
            digsilent_discrepancies = d_parser.compare_digsilent_vs_ecap(digsilent_relays, settings_list)

        groq_auditor = GroqHardAuditor()

        for settings in settings_list:
            # Auditor determinista con texto bruto del PDF
            auditor = ProtectionAuditor(settings, raw_pdf_text=raw_pdf_text)
            findings = auditor.audit_all()

            # Ensamble con Groq AI (Análisis duro Deep Reasoning)
            groq_findings = groq_auditor.audit_with_groq(settings.dict())
            findings.extend(groq_findings)

            for disc in digsilent_discrepancies:
                if disc["feeder_id"] == settings.feeder_id:
                    findings.append(AuditFinding(
                        code="CRITICAL_DIGSILENT_PDF_DISCREPANCY",
                        severity=Severity.CRITICAL,
                        title=disc["title"],
                        description=disc["description"],
                        affected_setting="digsilent_vs_pdf_pickup",
                        recommendation="Revisar el archivo nativo .pfd de PowerFactory y corregir la memoria PDF para asegurar consistencia con la simulación."
                    ))
            
            c_count = sum(1 for f in findings if f.severity == "CRITICAL")
            w_count = sum(1 for f in findings if f.severity == "WARNING")
            critical_total += c_count
            warning_total += w_count

            audited_relays.append({
                "settings": settings.dict(),
                "findings": [f.dict() for f in findings],
                "status": "REJECTED" if c_count > 0 else ("WARNING" if w_count > 0 else "APPROVED")
            })

        # ═══════════════════════════════════════════════════════════
        # PASO 3: Validación de sanidad post-auditoría
        # ═══════════════════════════════════════════════════════════
        if critical_total == 0 and warning_total == 0 and pdf_page_count > 10:
            print(f"[Pipeline] ADVERTENCIA: 0 hallazgos en un PDF de {pdf_page_count} páginas. Posible auditoría incompleta.")
            # Agregar warning a todos los relés
            for relay_data in audited_relays:
                relay_data["findings"].append(AuditFinding(
                    code="WARN_AUDIT_POTENTIALLY_INCOMPLETE",
                    severity=Severity.WARNING,
                    title="Auditoría Potencialmente Incompleta",
                    description=f"El documento tiene {pdf_page_count} páginas pero no se encontraron observaciones. "
                                f"Esto puede indicar que el análisis de IA no evaluó correctamente el contenido completo del documento.",
                    affected_setting="general",
                    recommendation="Se recomienda una revisión manual del documento para confirmar que todos los aspectos regulatorios fueron evaluados."
                ).dict())
                relay_data["status"] = "WARNING" if relay_data["status"] == "APPROVED" else relay_data["status"]
            warning_total += len(audited_relays)

        overall_status = "REJECTED" if critical_total > 0 else ("APPROVED_WITH_WARNINGS" if warning_total > 0 else "APPROVED")
        print(f"[Pipeline] Dictamen final: {overall_status} ({critical_total} CRITICAL, {warning_total} WARNING)")

        return {
            "filename": file.filename,
            "overall_status": overall_status,
            "digsilent_loaded": bool(digsilent_relays),
            "custom_rules_applied": bool(combined_rules),
            "pdf_pages": pdf_page_count,
            "summary": {
                "total_relays": len(audited_relays),
                "critical_errors": critical_total,
                "warnings": warning_total
            },
            "relays": audited_relays
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analizando el ECAP: {str(e)}")

@app.post("/api/report/html")
def generate_html_report_endpoint(data: Dict[str, Any]):
    html_content = ProtectionReportGenerator.generate_html_report(data)
    return Response(content=html_content, media_type="text/html")

@app.post("/api/audit")
def audit_protection_settings(settings: ProtectionSettingsSchema):
    auditor = ProtectionAuditor(settings)
    findings = auditor.audit_all()
    
    critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
    warning_count = sum(1 for f in findings if f.severity == "WARNING")
    
    status = "APPROVED_WITH_WARNINGS" if warning_count > 0 else "APPROVED"
    if critical_count > 0:
        status = "REJECTED_HAS_CRITICAL_ERRORS"
        
    return {
        "status": status,
        "summary": {
            "critical_errors": critical_count,
            "warnings": warning_count,
            "total_findings": len(findings)
        },
        "findings": [f.dict() for f in findings],
        "settings": settings.dict()
    }

@app.post("/api/export/ge-enervista")
def export_ge_enervista(settings: ProtectionSettingsSchema):
    driver = GEMultilinDriver()
    csv_content = driver.generate_enervista_csv(settings)
    
    filename = f"EnerVista_{settings.substation_name}_{settings.feeder_id}.csv".replace(" ", "_")
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/api/export/omicron-xrio")
def export_omicron_xrio(settings: ProtectionSettingsSchema):
    driver = OmicronXRIODriver()
    xrio_content = driver.generate_xrio_template(settings)
    
    filename = f"Omicron_{settings.substation_name}_{settings.feeder_id}.xrio".replace(" ", "_")
    return Response(
        content=xrio_content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
