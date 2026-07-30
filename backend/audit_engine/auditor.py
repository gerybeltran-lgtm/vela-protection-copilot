from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
from backend.schemas.protection_schema import ProtectionSettingsSchema
from backend.parser.pdf_text_extractor import DeterministicRegulatoryAuditor

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

class AuditFinding(BaseModel):
    code: str
    severity: Severity
    title: str
    description: str
    affected_setting: str
    recommendation: str

class ProtectionAuditor:
    def __init__(self, settings: ProtectionSettingsSchema, raw_pdf_text: str = ""):
        self.settings = settings
        self.findings: List[AuditFinding] = []
        self.raw_pdf_text = raw_pdf_text  # Texto bruto extraído con PyMuPDF

    def audit_all(self) -> List[AuditFinding]:
        self.findings.clear()
        self._audit_post_ia_sanity()
        self._audit_document_metadata_and_ito()
        self._audit_deterministic_regulatory()
        self._audit_custom_user_rules()
        self._audit_ct_calculations()
        self._audit_pickup_hardware_limits()
        self._audit_time_dialects()
        return self.findings

    # ═══════════════════════════════════════════════════════════════
    # NUEVO: Validación Post-IA — detecta si la IA no auditó nada
    # ═══════════════════════════════════════════════════════════════
    def _audit_post_ia_sanity(self):
        """Verifica que la IA haya poblado los campos regulatorios correctamente."""
        meta = self.settings.doc_metadata

        if not meta:
            self.findings.append(AuditFinding(
                code="WARN_MISSING_DOC_METADATA",
                severity=Severity.WARNING,
                title="Metadatos de Documento No Disponibles",
                description="El agente de IA no generó metadatos del documento (doc_metadata). "
                            "La auditoría regulatoria (CEN, ITO) podría estar incompleta. "
                            "Se procederá con la verificación determinista basada en el texto bruto del PDF.",
                affected_setting="doc_metadata",
                recommendation="Reenviar el documento para un segundo análisis o verificar manualmente el alcance regulatorio."
            ))

    # ═══════════════════════════════════════════════════════════════
    # NUEVO: Auditoría 100% Determinista desde texto bruto del PDF
    # (No depende de ninguna IA — usa PyMuPDF + Regex)
    # ═══════════════════════════════════════════════════════════════
    def _audit_deterministic_regulatory(self):
        """
        Auditoría regulatoria determinista basada en el texto bruto del PDF.
        Esta verificación es INDEPENDIENTE de lo que haya dicho la IA.
        Si la IA dijo que no hay omisión pero el texto dice lo contrario,
        esta función SOBRESCRIBE el resultado de la IA.
        """
        if not self.raw_pdf_text or len(self.raw_pdf_text.strip()) < 100:
            return

        det_result = DeterministicRegulatoryAuditor.audit_raw_text(self.raw_pdf_text)
        meta = self.settings.doc_metadata

        # ── Verificación de 110 kV ──
        if det_result["is_110kv_omitted"]:
            # Verificar si la IA ya detectó esto
            ia_detected = meta and (meta.missing_system_110kv or meta.missing_psp_study)
            
            # Verificar si ya existe un finding CEN de la verificación de metadatos
            already_has_cen_finding = any(f.code == "CRITICAL_CEN_SCOPE_MISSING" for f in self.findings)

            if not already_has_cen_finding:
                evidence_text = " | ".join(det_result["omission_evidence"][:3]) if det_result["omission_evidence"] else ""
                desc = (
                    f"DETECCIÓN DETERMINISTA (PyMuPDF): El análisis del texto bruto del PDF detectó que el "
                    f"sistema de 110 kV fue omitido del alcance del estudio. "
                    f"Confianza: {det_result['confidence']}. "
                    f"Niveles de tensión encontrados: {', '.join(str(v) + ' kV' for v in det_result.get('tension_levels_found', []))}."
                )
                if evidence_text:
                    desc += f" Evidencia del documento: '{evidence_text}'"
                if not ia_detected:
                    desc += " NOTA: El agente de IA NO detectó esta omisión — fue capturada exclusivamente por el verificador determinista."

                self.findings.append(AuditFinding(
                    code="CRITICAL_CEN_SCOPE_MISSING",
                    severity=Severity.CRITICAL,
                    title="Observación Regulatoria CEN: Omisión de Sistema 110 kV / Estudio PSP",
                    description=desc,
                    affected_setting="doc_metadata.cen_scope",
                    recommendation="Verificar el alcance del informe según la exigencia de la Norma Técnica de Seguridad y "
                                   "Calidad de Servicio del Coordinador Eléctrico Nacional (CEN). El estudio debe incluir "
                                   "la coordinación con la barra de 110 kV del sistema de transmisión."
                ))

        # ── Verificación de ITO desde texto bruto ──
        if det_result["has_ito_mention"] and det_result["ito_evidence"]:
            ia_detected_ito = meta and meta.has_ito_comments and meta.ito_comments_list
            already_has_ito_finding = any(f.code == "CRITICAL_ITO_PENDING_COMMENTS" for f in self.findings)

            if not already_has_ito_finding and not ia_detected_ito:
                evidence_str = " | ".join(det_result["ito_evidence"][:3])
                self.findings.append(AuditFinding(
                    code="WARN_ITO_MENTIONS_DETECTED",
                    severity=Severity.WARNING,
                    title="Posibles Observaciones de ITO Detectadas en Texto",
                    description=f"DETECCIÓN DETERMINISTA (PyMuPDF): Se encontraron menciones de la ITO en el texto "
                                f"del PDF que no fueron capturadas por el agente de IA: '{evidence_str}'",
                    affected_setting="doc_metadata.ito_comments",
                    recommendation="Revisar manualmente si existen observaciones pendientes de la ITO en el documento."
                ))

    def _audit_custom_user_rules(self):
        """Audita el cumplimiento de reglas específicas agregadas por los ingenieros."""
        meta = self.settings.doc_metadata
        if not meta or not meta.custom_rules_findings:
            return

        for idx, finding_text in enumerate(meta.custom_rules_findings, 1):
            self.findings.append(AuditFinding(
                code=f"CRITICAL_CUSTOM_USER_RULE_{idx}",
                severity=Severity.CRITICAL,
                title="Incumplimiento de Regla Personalizada del Ingeniero",
                description=f"Se detectó una violación a las reglas particulares del proyecto especificadas por el usuario: '{finding_text}'",
                affected_setting="doc_metadata.custom_rules",
                recommendation="Ajustar los parámetros según los criterios particulares exigidos por la ingeniería del cliente antes de autorizar el comisionamiento."
            ))

    def _audit_document_metadata_and_ito(self):
        meta = self.settings.doc_metadata
        if not meta:
            return

        if meta.has_ito_comments and meta.ito_comments_list:
            clean_comments = [c for c in meta.ito_comments_list if isinstance(c, str) and len(c.strip()) > 5]
            
            # Evitar falsos positivos / alucinaciones repetitivas de la IA
            generic_phrases = [
                "revisar ajustes de protección para el sistema de 110 kv",
                "verificar compatibilidad con los relés",
                "se recomienda verificar",
                "se sugiere revisar",
            ]
            real_ito_comments = [
                c for c in clean_comments 
                if not any(gp in c.lower() for gp in generic_phrases)
            ]

            if real_ito_comments:
                comments_str = " | ".join(real_ito_comments)
                self.findings.append(AuditFinding(
                    code="CRITICAL_ITO_PENDING_COMMENTS",
                    severity=Severity.CRITICAL,
                    title="Comentarios / Acuerdos de la ITO Pendientes de Resolver",
                    description=f"El informe ECAP contiene compromisos u observaciones pendientes de la Inspección Técnica (ITO): '{comments_str}'.",
                    affected_setting="doc_metadata.ito_comments",
                    recommendation="Revisar y actualizar la información de resistencias de puesta a tierra, ajustes de generadores o extremos de red antes de autorizar comisionamiento."
                ))

        # Verificación basada en metadatos de la IA (complementaria a la determinista)
        if meta.missing_system_110kv or meta.missing_psp_study:
            already_has = any(f.code == "CRITICAL_CEN_SCOPE_MISSING" for f in self.findings)
            if not already_has:
                desc = meta.cen_regulatory_warning or "El estudio fue realizado omitiendo la coordinación con la barra de 110 kV del Coordinador Eléctrico Nacional (CEN)."
                self.findings.append(AuditFinding(
                    code="CRITICAL_CEN_SCOPE_MISSING",
                    severity=Severity.CRITICAL,
                    title="Observación Regulatoria CEN: Omisión de Sistema 110 kV / Estudio PSP",
                    description=f"DETECCIÓN POR AGENTE IA: {desc}",
                    affected_setting="doc_metadata.cen_scope",
                    recommendation="Verificar el alcance del informe según la exigencia de la Norma Técnica de Seguridad y Calidad de Servicio del Coordinador Eléctrico Nacional (CEN)."
                ))

    def _audit_ct_calculations(self):
        ct = self.settings.ct_ratio
        
        if self.settings.ansi_51_phase and self.settings.ansi_51_phase.enabled:
            phase = self.settings.ansi_51_phase
            if phase.pickup_primary_a is not None and phase.pickup_secondary_a is not None:
                expected_sec = phase.pickup_primary_a / ct.ratio
                diff = abs(expected_sec - phase.pickup_secondary_a)
                if diff > (expected_sec * 0.015):
                    self.findings.append(AuditFinding(
                        code="ERR_RTC_MISMATCH_51",
                        severity=Severity.CRITICAL,
                        title="Inconsistencia Primario/Secundario (ANSI 51)",
                        description=f"El ECAP indica Pickup Primario = {phase.pickup_primary_a} A y Secundario = {phase.pickup_secondary_a} A. Con la RTC {ct.primary_a}/{ct.secondary_a} (Ratio = {ct.ratio}), el secundario exacto debe ser {expected_sec:.3f} A.",
                        affected_setting="ansi_51_phase.pickup_secondary_a",
                        recommendation=f"Corregir el valor secundario en el relé a {expected_sec:.3f} A para evitar descalce de trip."
                    ))

        if self.settings.ansi_51n_ground and self.settings.ansi_51n_ground.enabled:
            ground = self.settings.ansi_51n_ground
            if ground.pickup_primary_a is not None and ground.pickup_secondary_a is not None:
                expected_sec = ground.pickup_primary_a / ct.ratio
                diff = abs(expected_sec - ground.pickup_secondary_a)
                if diff > (expected_sec * 0.015):
                    self.findings.append(AuditFinding(
                        code="ERR_RTC_MISMATCH_51N",
                        severity=Severity.CRITICAL,
                        title="Inconsistencia Primario/Secundario (ANSI 51N)",
                        description=f"El ECAP indica Pickup Neutro Primario = {ground.pickup_primary_a} A y Secundario = {ground.pickup_secondary_a} A. Con la RTC {ct.primary_a}/{ct.secondary_a}, el valor exacto debe ser {expected_sec:.4f} A.",
                        affected_setting="ansi_51n_ground.pickup_secondary_a",
                        recommendation=f"Ajustar el valor secundario de tierra a {expected_sec:.4f} A."
                    ))

    def _audit_pickup_hardware_limits(self):
        if self.settings.ansi_51n_ground and self.settings.ansi_51n_ground.enabled:
            ground = self.settings.ansi_51n_ground
            if ground.pickup_secondary_a is not None and ground.pickup_secondary_a < 0.05:
                self.findings.append(AuditFinding(
                    code="WARN_HW_LOW_PICKUP_51N",
                    severity=Severity.CRITICAL,
                    title="Pickup de Tierra bajo Límite de Precisión del Relé",
                    description=f"El valor de pickup secundario de tierra ({ground.pickup_secondary_a:.4f} A) está por debajo del rango de precisión garantizada del TC de entrada (0.05 A sec).",
                    affected_setting="ansi_51n_ground.pickup_secondary_a",
                    recommendation="Revisar si se requiere un TC de secuencia cero (Core Balance CT) o ajustar la relación de transformación."
                ))

    def _audit_time_dialects(self):
        if self.settings.ansi_51_phase and self.settings.ansi_51_phase.enabled:
            phase = self.settings.ansi_51_phase
            if phase.curve and "IEC" in phase.curve.value and phase.time_dial and phase.time_dial > 2.0:
                self.findings.append(AuditFinding(
                    code="WARN_DIALECT_TMS_TDM",
                    severity=Severity.WARNING,
                    title="Posible confusión de Dialecto TDM / TMS",
                    description=f"Se especificó curva IEC ({phase.curve.value}) pero con un multiplicador de {phase.time_dial}, inusualmente alto para TMS (estándar IEC).",
                    affected_setting="ansi_51_phase.time_dial",
                    recommendation="Confirmar si el proyectista del ECAP especificó TDM (IEEE) en lugar de TMS (IEC) para evitar retardos excesivos en la eliminación de la falla."
                ))
