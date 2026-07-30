import re
from typing import Dict, Any

class CIPSanitizer:
    """Módulo de Anonimización de Información Crítica de Infraestructura (CIP & PII Sanitizer)."""

    @staticmethod
    def sanitize_text(text: str) -> str:
        if not text:
            return ""

        # 1. Anonimizar RUTs / Cédulas de Identidad Chilenas (ej. 12.345.678-9)
        sanitized = re.sub(r'\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b', '[RUT_ANONIMIZADO]', text)

        # 2. Anonimizar Correos Electrónicos Personales/Corporativos
        sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_ANONIMIZADO]', sanitized)

        # 3. Anonimizar Coordenadas GPS (Latitud/Longitud)
        sanitized = re.sub(r'[-+]?\d{1,2}\.\d+,\s*[-+]?\d{1,3}\.\d+', '[COORDENADAS_GPS_ANONIMIZADAS]', sanitized)

        return sanitized

    @staticmethod
    def sanitize_settings_dict(settings_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Anonimiza campos sensibles de un diccionario de ajustes antes de enviarlo a auditoría de IA."""
        sanitized_dict = settings_dict.copy()
        
        # Ocultar o tokenizar datos sensibles de la subestación
        if "raw_notes" in sanitized_dict and isinstance(sanitized_dict["raw_notes"], list):
            sanitized_dict["raw_notes"] = [CIPSanitizer.sanitize_text(note) for note in sanitized_dict["raw_notes"]]
            
        return sanitized_dict
