"""
PDF Text Extractor — Módulo de extracción de texto bruto de PDFs.

Utiliza PyMuPDF (fitz) para extraer texto plano de cada página del PDF,
independientemente de la IA, para alimentar verificaciones deterministas
del motor de auditoría regulatoria (CEN 110 kV, ITO, alcance, etc.).
"""

import re
from typing import List, Dict, Optional

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


class PDFTextExtractor:
    """Extrae texto plano de un PDF para verificación determinista."""

    @staticmethod
    def extract_full_text(pdf_path: str) -> str:
        """Extrae todo el texto del PDF como un string concatenado."""
        if not HAS_PYMUPDF:
            print("ADVERTENCIA: PyMuPDF no instalado. Extracción de texto bruto deshabilitada.")
            return ""
        
        try:
            doc = fitz.open(pdf_path)
            full_text = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                if text:
                    full_text.append(text)
            doc.close()
            return "\n".join(full_text)
        except Exception as e:
            print(f"Error extrayendo texto del PDF con PyMuPDF: {e}")
            return ""

    @staticmethod
    def extract_pages(pdf_path: str) -> List[Dict[str, any]]:
        """Extrae texto por página del PDF."""
        if not HAS_PYMUPDF:
            return []
        
        try:
            doc = fitz.open(pdf_path)
            pages = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                pages.append({
                    "page": page_num + 1,
                    "text": text or ""
                })
            doc.close()
            return pages
        except Exception as e:
            print(f"Error extrayendo páginas del PDF: {e}")
            return []


class DeterministicRegulatoryAuditor:
    """
    Auditor regulatorio 100% determinista basado en texto bruto del PDF.
    No depende de ninguna IA — analiza directamente el texto extraído con PyMuPDF.
    """

    # Patrones regex para detección de 110 kV / sistema de transmisión CEN
    PATTERNS_110KV = [
        r"110\s*kV",
        r"110\s*kv",
        r"barra\s+de\s+110",
        r"sistema\s+de\s+110",
        r"nivel\s+de\s+tensi[oó]n\s+110",
        r"transmisi[oó]n\s+110",
        r"l[ií]nea\s+de\s+110",
    ]

    PATTERNS_OMISSION = [
        r"no\s+(?:se\s+)?(?:considera|contempla|incluye|analiza)",
        r"(?:fuera|excluido|excluy[eó])\s+del\s+alcance",
        r"(?:omite|omisi[oó]n|omitido)",
        r"no\s+(?:fue|es|ser[aá])\s+(?:parte|incluido|contemplado)",
        r"sin\s+(?:considerar|contemplar|incluir)",
        r"(?:queda|deja)\s+(?:fuera|pendiente|excluido)",
        r"alcance\s+(?:limitado|restringido|parcial)",
        r"s[oó]lo\s+(?:se\s+)?(?:analiz[aó]|consider[aó]|contempl[aó])",
    ]

    PATTERNS_PSP = [
        r"(?:estudio|an[aá]lisis)\s+(?:de\s+)?(?:protecciones?\s+)?(?:del\s+)?sistema\s+principal",
        r"PSP",
        r"sistema\s+(?:de\s+)?transmisi[oó]n\s+(?:principal|troncal|nacional)",
        r"coordinador\s+el[eé]ctrico\s+nacional",
        r"CEN",
        r"norma\s+t[eé]cnica\s+de\s+seguridad",
        r"NTSyCS",
    ]

    PATTERNS_ITO = [
        r"inspecci[oó]n\s+t[eé]cnica\s+de\s+obra",
        r"\bITO\b",
        r"observaci[oó]n(?:es)?\s+(?:de\s+la\s+)?(?:ITO|inspecci[oó]n)",
        r"comentario(?:s)?\s+(?:de\s+la\s+)?(?:ITO|inspecci[oó]n)",
        r"acuerdo(?:s)?\s+(?:de\s+la\s+)?(?:ITO|inspecci[oó]n)",
        r"pendiente(?:s)?\s+(?:de\s+la\s+)?(?:ITO|inspecci[oó]n)",
    ]

    @classmethod
    def audit_raw_text(cls, raw_text: str) -> Dict[str, any]:
        """
        Analiza el texto bruto del PDF y retorna hallazgos regulatorios deterministas.
        
        Returns:
            Dict con claves:
                - has_110kv_mention: bool — El documento menciona 110 kV
                - has_omission_language: bool — Hay lenguaje de omisión/exclusión
                - has_psp_mention: bool — Se menciona PSP/CEN/NTSyCS
                - has_ito_mention: bool — Se mencionan observaciones de ITO
                - is_110kv_omitted: bool — CONCLUSIÓN: El sistema 110 kV fue omitido
                - omission_evidence: list — Frases del documento que evidencian la omisión
                - ito_evidence: list — Frases del documento que mencionan ITO
                - confidence: str — "HIGH", "MEDIUM", "LOW"
        """
        if not raw_text or len(raw_text.strip()) < 50:
            return {
                "has_110kv_mention": False,
                "has_omission_language": False,
                "has_psp_mention": False,
                "has_ito_mention": False,
                "is_110kv_omitted": False,
                "omission_evidence": [],
                "ito_evidence": [],
                "confidence": "LOW"
            }

        text_lower = raw_text.lower()
        lines = raw_text.split("\n")

        # 1. Detectar menciones de 110 kV
        has_110kv = any(re.search(p, raw_text, re.IGNORECASE) for p in cls.PATTERNS_110KV)

        # 2. Detectar lenguaje de omisión cerca de menciones de 110 kV
        omission_evidence = []
        has_omission = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if not line_lower:
                continue
            
            # Buscar patrones de 110 kV en esta línea y las vecinas
            context_window = " ".join([
                lines[max(0, i-2)],
                line,
                lines[min(len(lines)-1, i+1)] if i+1 < len(lines) else "",
                lines[min(len(lines)-1, i+2)] if i+2 < len(lines) else ""
            ]).lower()

            has_110_in_context = any(re.search(p, context_window, re.IGNORECASE) for p in cls.PATTERNS_110KV)
            has_omission_in_context = any(re.search(p, context_window, re.IGNORECASE) for p in cls.PATTERNS_OMISSION)

            if has_110_in_context and has_omission_in_context:
                has_omission = True
                evidence_text = line.strip()
                if len(evidence_text) > 10 and evidence_text not in omission_evidence:
                    omission_evidence.append(evidence_text[:200])

        # 3. Detectar alcance limitado a un solo nivel de tensión
        # (indica que 110 kV probablemente fue excluido aunque no lo diga explícitamente)
        scope_patterns = [
            r"alcance\s*(?:del\s+)?(?:estudio|informe|an[aá]lisis)",
            r"el\s+presente\s+(?:estudio|informe|documento)",
        ]
        
        tension_levels_found = set()
        for match in re.finditer(r"(\d{2,3})\s*kV", raw_text, re.IGNORECASE):
            kv_val = int(match.group(1))
            if kv_val in [23, 33, 44, 66, 110, 154, 220, 500]:
                tension_levels_found.add(kv_val)

        # Si el documento menciona 110 kV pero tiene lenguaje de omisión
        is_110kv_omitted = has_110kv and has_omission

        # Si el documento NO menciona 110 kV pero menciona otros niveles
        # y tiene referencia al CEN/PSP, la omisión es implícita
        has_psp = any(re.search(p, raw_text, re.IGNORECASE) for p in cls.PATTERNS_PSP)
        
        if not has_110kv and has_psp and len(tension_levels_found) > 0 and 110 not in tension_levels_found:
            # El documento habla del CEN pero no analiza 110 kV — omisión implícita
            is_110kv_omitted = True
            omission_evidence.append(
                f"El documento referencia al CEN/sistema principal pero solo analiza niveles de tensión: "
                f"{', '.join(str(v) + ' kV' for v in sorted(tension_levels_found))}. "
                f"No se incluye análisis del sistema de 110 kV."
            )

        # 4. Detectar menciones de ITO
        ito_evidence = []
        has_ito = False
        for i, line in enumerate(lines):
            for p in cls.PATTERNS_ITO:
                if re.search(p, line, re.IGNORECASE):
                    has_ito = True
                    evidence = line.strip()
                    if len(evidence) > 10 and evidence not in ito_evidence:
                        ito_evidence.append(evidence[:200])
                    break

        # Determinar confianza
        confidence = "LOW"
        if is_110kv_omitted and len(omission_evidence) >= 2:
            confidence = "HIGH"
        elif is_110kv_omitted and len(omission_evidence) >= 1:
            confidence = "MEDIUM"
        elif has_110kv:
            confidence = "MEDIUM"

        return {
            "has_110kv_mention": has_110kv,
            "has_omission_language": has_omission,
            "has_psp_mention": has_psp,
            "has_ito_mention": has_ito,
            "is_110kv_omitted": is_110kv_omitted,
            "omission_evidence": omission_evidence[:5],  # Max 5 evidencias
            "ito_evidence": ito_evidence[:5],
            "confidence": confidence,
            "tension_levels_found": sorted(list(tension_levels_found))
        }
