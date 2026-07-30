import os
import json
import re
import base64
from typing import Optional, List
import google.generativeai as genai
from backend.schemas.protection_schema import ProtectionSettingsSchema

# ═══════════════════════════════════════════════════════════════════════
# AGENTE 1: Extractor Numérico — Solo extrae tablas de ajustes del ECAP
# ═══════════════════════════════════════════════════════════════════════
EXTRACTION_PROMPT = """
Eres un Agente Extractor de Datos de relés de protección eléctrica. Tu ÚNICA tarea es extraer
las tablas de ajustes numéricos del documento PDF adjunto (Estudio de Coordinación y Ajuste de 
Protecciones - ECAP).

Extrae TODOS los relés/paños del documento. Para cada uno:

Devuelve una LISTA JSON con este formato exacto:
[
  {
    "substation_name": "Nombre de la Subestación",
    "feeder_id": "Identificador del Paño o Alimentador",
    "relay_brand": "Marca del relé (ej. GE Multilin, SEL, Siemens)",
    "relay_model": "Modelo (ej. 850, SEL-751, SIPROTEC 5)",
    "ct_ratio": {"primary_a": float, "secondary_a": float},
    "vt_ratio": {"primary_v": float, "secondary_v": float},
    "ansi_51_phase": {
       "enabled": true/false,
       "pickup_primary_a": float,
       "pickup_secondary_a": float,
       "curve": "IEEE_VERY_INVERSE",
       "time_dial": float
    },
    "ansi_51n_ground": {
       "enabled": true/false,
       "pickup_primary_a": float,
       "pickup_secondary_a": float,
       "curve": "IEEE_VERY_INVERSE",
       "time_dial": float
    },
    "raw_notes": ["Observaciones del proyectista encontradas en el documento"]
  }
]

REGLAS:
- Extrae SOLO datos numéricos y técnicos de las tablas del documento.
- NO inventes datos. Si un valor no aparece en el documento, usa null.
- Devuelve ÚNICAMENTE el JSON válido, sin texto adicional.
"""

# ═══════════════════════════════════════════════════════════════════════
# AGENTE 2: Auditor Regulatorio — Solo evalúa cumplimiento normativo
# ═══════════════════════════════════════════════════════════════════════
REGULATORY_PROMPT = """
Eres un Agente Auditor Regulatorio Senior especialista en normativa eléctrica chilena (CEN) e 
internacional (IEEE/IEC). Tu ÚNICA tarea es auditar el TEXTO del documento PDF para detectar
problemas regulatorios, observaciones de la ITO y cumplimiento de reglas del proyecto.

EVALÚA ESTRICTAMENTE:

1. REGLA CEN 110 kV:
   - ¿El informe menciona un sistema de 110 kV?
   - ¿El estudio OMITE, EXCLUYE o NO CONTEMPLA la coordinación con la barra de 110 kV?
   - ¿Se menciona el Estudio de Protecciones del Sistema Principal (PSP)?
   - ¿Se menciona al Coordinador Eléctrico Nacional (CEN)?
   - Si el alcance está limitado y no incluye 110 kV: missing_system_110kv DEBE ser true.

2. OBSERVACIONES ITO:
   - ¿Hay comentarios, observaciones o acuerdos pendientes de la Inspección Técnica de Obra (ITO)?
   - Extrae las citas textuales exactas del documento.
   - NO inventes observaciones de la ITO si no existen en el documento.

3. REGLAS PERSONALIZADAS DEL INGENIERO:
   >>> {CUSTOM_RULES_TEXT} <<<
   Evalúa el cumplimiento estricto de estas reglas contra el contenido del documento.

Devuelve UN SOLO objeto JSON con este formato exacto:
{
  "has_ito_comments": true/false,
  "ito_comments_list": ["Cita textual 1 de observación ITO del documento", "Cita 2..."],
  "missing_system_110kv": true/false,
  "missing_psp_study": true/false,
  "cen_regulatory_warning": "Explicación detallada de por qué se omite 110 kV (dejar null si no aplica)",
  "custom_rules_findings": ["Hallazgo 1 de incumplimiento de regla personalizada", "Hallazgo 2..."]
}

REGLAS CRÍTICAS:
- Si el documento dice EXPLÍCITAMENTE que no contempla, omite o excluye el sistema de 110 kV → missing_system_110kv = true
- Si el alcance del estudio se limita a un nivel de tensión inferior (ej. 23kV, 33kV, 44kV) y existe un sistema de 110 kV mencionado pero no analizado → missing_system_110kv = true
- has_ito_comments = true SOLO si el documento cita explícitamente observaciones de la ITO. NO inventes comentarios.
- Devuelve ÚNICAMENTE el JSON válido, sin texto adicional.
"""


class ECAPGeminiParser:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def _get_model_name(self) -> str:
        """Determina el mejor modelo Gemini disponible."""
        preferred_models = [
            "gemini-2.5-flash",
            "gemini-2.0-flash", 
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]
        try:
            available = {m.name.split("/")[-1] for m in genai.list_models()}
            for model in preferred_models:
                if model in available:
                    print(f"[Agente Parser] Usando modelo: {model}")
                    return model
        except Exception as e:
            print(f"[Agente Parser] Error listando modelos: {e}")
        
        # Fallback seguro
        print("[Agente Parser] Fallback a gemini-2.0-flash")
        return "gemini-2.0-flash"

    def _parse_with_groq(self, pdf_path: str, custom_rules: str, groq_key: str) -> str:
        from groq import Groq
        client = Groq(api_key=groq_key)
        
        with open(pdf_path, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode('utf-8')

        custom_text = custom_rules.strip() if custom_rules.strip() else "Ninguna regla personalizada adicional especificada."
        
        # Para Groq, combinamos ambos prompts en uno (limitación del modelo)
        combined_prompt = EXTRACTION_PROMPT + "\n\nAdemás, incluye un campo 'doc_metadata' en cada relé con la evaluación regulatoria:\n" + REGULATORY_PROMPT.replace("{CUSTOM_RULES_TEXT}", custom_text)

        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres un experto auditor de ECAPs. Responde solo con el JSON solicitado."},
                {"role": "user", "content": f"Audita este archivo PDF (codificado en base64): {pdf_b64[:100]}... [omitido b64 largo]. Prompt de auditoría: {combined_prompt}"}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1
        )
        return response.choices[0].message.content

    def _call_gemini_agent(self, contents_list: list, model_name: str) -> str:
        """Llama a un agente Gemini con los contenidos y retorna el texto de respuesta."""
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            contents_list,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        return response.text.strip()

    def parse_pdf_to_schema_list(self, pdf_path: str, custom_rules: str = "", extra_pdf_paths: List[str] = None) -> List[ProtectionSettingsSchema]:
        raw_text = ""
        regulatory_json = None
        extra_pdf_paths = extra_pdf_paths or []
        
        if self.api_key:
            try:
                model_name = self._get_model_name()

                # 1. Subir archivo ECAP Principal
                main_uploaded = genai.upload_file(pdf_path, mime_type="application/pdf")
                
                # 2. Subir PDFs de Contexto
                extra_uploaded_files = []
                for extra_path in extra_pdf_paths:
                    try:
                        extra_uploaded = genai.upload_file(extra_path, mime_type="application/pdf")
                        extra_uploaded_files.append(extra_uploaded)
                        print(f"[Agente Parser] Subido PDF de contexto: {extra_path}")
                    except Exception as e_up:
                        print(f"[Agente Parser] Advertencia subiendo contexto {extra_path}: {e_up}")

                # ═══════════════════════════════════════════════
                # AGENTE 1: Extracción numérica de tablas
                # ═══════════════════════════════════════════════
                print("[Agente Extractor] Extrayendo tablas numéricas del ECAP...")
                extraction_contents = [main_uploaded] + extra_uploaded_files + [EXTRACTION_PROMPT]
                raw_text = self._call_gemini_agent(extraction_contents, model_name)
                print(f"[Agente Extractor] Extracción completada ({len(raw_text)} chars)")

                # ═══════════════════════════════════════════════
                # AGENTE 2: Auditoría regulatoria independiente
                # ═══════════════════════════════════════════════
                print("[Agente Regulatorio] Evaluando cumplimiento normativo CEN/ITO...")
                custom_text = custom_rules.strip() if custom_rules.strip() else "Ninguna regla personalizada adicional especificada."
                regulatory_prompt = REGULATORY_PROMPT.replace("{CUSTOM_RULES_TEXT}", custom_text)
                regulatory_contents = [main_uploaded] + extra_uploaded_files + [regulatory_prompt]
                
                try:
                    regulatory_raw = self._call_gemini_agent(regulatory_contents, model_name)
                    regulatory_json = json.loads(regulatory_raw)
                    print(f"[Agente Regulatorio] Resultado: missing_110kv={regulatory_json.get('missing_system_110kv')}, "
                          f"has_ito={regulatory_json.get('has_ito_comments')}, "
                          f"custom_findings={len(regulatory_json.get('custom_rules_findings', []))}")
                except Exception as e_reg:
                    print(f"[Agente Regulatorio] Error en auditoría regulatoria: {e_reg}")
                    regulatory_json = None

            except Exception as gemini_err:
                print(f"Advertencia Gemini API ({gemini_err}). Activando Fallback a Groq AI (Llama 3.3 70B)...")
                groq_key = os.getenv("GROQ_API_KEY")
                if not groq_key:
                    raise Exception(f"Error con la clave de Gemini y no hay GROQ_API_KEY configurada. Detalle: {gemini_err}")
                
                raw_text = self._parse_with_groq(pdf_path, custom_rules, groq_key)
        else:
            groq_key = os.getenv("GROQ_API_KEY")
            if not groq_key:
                raise Exception("GEMINI_API_KEY no encontrada y no hay GROQ_API_KEY configurada.")
            raw_text = self._parse_with_groq(pdf_path, custom_rules, groq_key)

        # ═══════════════════════════════════════════════
        # Parseo del JSON de extracción
        # ═══════════════════════════════════════════════
        parsed = []
        try:
            json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
            else:
                try:
                    parsed = json.loads(raw_text)
                except Exception:
                    dict_matches = re.findall(r'\{\s*"substation_name".*?\}', raw_text, re.DOTALL)
                    parsed = [json.loads(d) for d in dict_matches]
        except Exception as e:
            print(f"Error parseando JSON devuelto por IA: {e}")
            raise Exception(f"No se pudo extraer la matriz de relés del informe. Respuesta de la IA: {raw_text[:200]}")

        if isinstance(parsed, dict):
            parsed = [parsed]

        # ═══════════════════════════════════════════════
        # Merge: Inyectar resultado del Agente Regulatorio
        # en el doc_metadata de cada relé extraído
        # ═══════════════════════════════════════════════
        results = []
        for item in parsed:
            # Si el Agente Regulatorio dio resultados, inyectarlos
            if regulatory_json:
                existing_meta = item.get("doc_metadata", {}) or {}
                # El Agente Regulatorio tiene prioridad sobre lo que haya extraído el Extractor
                merged_meta = {
                    "has_ito_comments": regulatory_json.get("has_ito_comments", existing_meta.get("has_ito_comments", False)),
                    "ito_comments_list": regulatory_json.get("ito_comments_list", existing_meta.get("ito_comments_list", [])),
                    "missing_system_110kv": regulatory_json.get("missing_system_110kv", existing_meta.get("missing_system_110kv", False)),
                    "missing_psp_study": regulatory_json.get("missing_psp_study", existing_meta.get("missing_psp_study", False)),
                    "cen_regulatory_warning": regulatory_json.get("cen_regulatory_warning", existing_meta.get("cen_regulatory_warning")),
                    "custom_rules_findings": regulatory_json.get("custom_rules_findings", existing_meta.get("custom_rules_findings", [])),
                }
                item["doc_metadata"] = merged_meta
            
            results.append(ProtectionSettingsSchema(**item))
        
        return results
