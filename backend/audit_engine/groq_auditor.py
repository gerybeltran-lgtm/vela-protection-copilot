import os
import json
import requests
from typing import List, Dict, Any
from backend.audit_engine.auditor import AuditFinding, Severity

GROQ_SYSTEM_PROMPT = """
Eres un Agente Especialista Senior en Protecciones Eléctricas e Ingeniería de Subestaciones Alta Tensión (IEEE/IEC/CEN Chile).
Tu función es realizar un ANÁLISIS DURO Y DEEP REASONING (Chain-of-Thought) sobre los ajustes de protecciones extraídos de un informe ECAP.

Evalúa estrictamente:
1. Descalce primario/secundario de corriente según la razón RTC ($I_{sec} = I_{prim} / RTC$).
2. Sensibilidad de protecciones de tierra (ANSI 51N) ante fallas monofásicas.
3. Coordinación de curvas de tiempo (TDM IEEE vs TMS IEC).
4. Rangos de hardware de los relés.

Si detectas alguna inconsistencia grave de ingeniería, emite una alerta CRITICAL o WARNING.

Devuelve únicamente un JSON válido con este formato:
[
  {
    "code": "GROQ_HARD_AUDIT_WARNING",
    "severity": "CRITICAL" | "WARNING",
    "title": "Título corto de la observación",
    "description": "Explicación matemática y técnica detallada del hallazgo",
    "affected_setting": "ansi_51_phase / ansi_51n_ground / ct_ratio",
    "recommendation": "Acción correctiva para la ITO/Proyectista"
  }
]
"""

class GroqHardAuditor:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")

    def audit_with_groq(self, settings_dict: Dict[str, Any]) -> List[AuditFinding]:
        if not self.api_key:
            return []

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        user_payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": GROQ_SYSTEM_PROMPT},
                {"role": "user", "content": f"Realiza análisis duro de protecciones sobre estos ajustes:\n{json.dumps(settings_dict, indent=2)}"}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        try:
            res = requests.post(url, headers=headers, json=user_payload, timeout=20)
            if res.status_code != 200:
                print(f"Advertencia Groq API status ({res.status_code}): {res.text}")
                return []

            res_json = res.json()
            content = res_json["choices"][0]["message"]["content"]
            
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "findings" in parsed:
                parsed = parsed["findings"]
            elif isinstance(parsed, dict):
                parsed = list(parsed.values())[0] if isinstance(list(parsed.values())[0], list) else []

            findings = []
            for item in parsed:
                if isinstance(item, dict):
                    sev = Severity.CRITICAL if item.get("severity") == "CRITICAL" else Severity.WARNING
                    findings.append(AuditFinding(
                        code=item.get("code", "GROQ_HARD_AUDIT"),
                        severity=sev,
                        title=item.get("title", "Observación de Análisis Duro (Groq AI)"),
                        description=item.get("description", ""),
                        affected_setting=item.get("affected_setting", "general"),
                        recommendation=item.get("recommendation", "")
                    ))
            return findings

        except Exception as e:
            print(f"Error en auditoría Groq Cloud: {e}")
            return []
