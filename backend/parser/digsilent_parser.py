import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.schemas.protection_schema import ProtectionSettingsSchema, CTRatio, ANSI5051Phase, ANSI5051NGround, CurveType

class DIgSILENTRelayModel(BaseModel):
    relay_name: str
    element_id: str
    substation: str
    ct_primary: float
    ct_secondary: float
    pickup_phase_sec: Optional[float] = None
    pickup_ground_sec: Optional[float] = None
    curve_shape: Optional[str] = None
    time_dial: Optional[float] = None

class DIgSILENTParser:
    """Parser de proyectos DIgSILENT PowerFactory (Formatos DGS, JSON, XML o exportaciones DGS/PFC)."""

    def parse_digsilent_export(self, file_path: str) -> List[DIgSILENTRelayModel]:
        """Lee un archivo de simulación exportado de DIgSILENT PowerFactory y extrae los objetos ElmRelay."""
        relays = []
        
        # 1. Intento de lectura formato JSON DGS export
        if file_path.endswith(".json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Extraer tabla ElmRelay de PowerFactory DGS
            elements = data.get("ElmRelay", []) or data.get("elements", [])
            for el in elements:
                relays.append(DIgSILENTRelayModel(
                    relay_name=el.get("loc_name", "ElmRelay"),
                    element_id=el.get("id", "1"),
                    substation=el.get("substation", "DIgSILENT Substation"),
                    ct_primary=float(el.get("ct_pri", 600)),
                    ct_secondary=float(el.get("ct_sec", 5)),
                    pickup_phase_sec=float(el.get("Isec_51", 2.0)) if el.get("Isec_51") else None,
                    pickup_ground_sec=float(el.get("Isec_51N", 0.2)) if el.get("Isec_51N") else None,
                    time_dial=float(el.get("tdm", 0.5)) if el.get("tdm") else None
                ))

        # 2. Intento de lectura XML / DGS estándar
        elif file_path.endswith(".xml") or file_path.endswith(".dgs"):
            tree = ET.parse(file_path)
            root = tree.getroot()
            for elem in root.findall(".//ElmRelay"):
                relays.append(DIgSILENTRelayModel(
                    relay_name=elem.attrib.get("loc_name", "ElmRelay"),
                    element_id=elem.attrib.get("id", "1"),
                    substation=elem.attrib.get("substation", "DIgSILENT Substation"),
                    ct_primary=float(elem.attrib.get("ct_pri", 600)),
                    ct_secondary=float(elem.attrib.get("ct_sec", 5)),
                    pickup_phase_sec=float(elem.attrib.get("Isec_51", 2.0)) if "Isec_51" in elem.attrib else None
                ))
                
        return relays

    def compare_digsilent_vs_ecap(self, digsilent_relays: List[DIgSILENTRelayModel], ecap_relays: List[ProtectionSettingsSchema]) -> List[Dict[str, Any]]:
        """Compara la simulación nativa de DIgSILENT contra lo que el proyectista escribió en el PDF del ECAP."""
        discrepancies = []
        
        for d_relay in digsilent_relays:
            # Buscar relé correspondiente en el ECAP por nombre o paño
            match = next((e for e in ecap_relays if d_relay.relay_name.lower() in e.feeder_id.lower() or e.feeder_id.lower() in d_relay.relay_name.lower()), None)
            if match and match.ansi_51_phase and d_relay.pickup_phase_sec:
                pdf_sec = match.ansi_51_phase.pickup_secondary_a
                if pdf_sec and abs(pdf_sec - d_relay.pickup_phase_sec) > 0.05:
                    discrepancies.append({
                        "relay_name": d_relay.relay_name,
                        "feeder_id": match.feeder_id,
                        "title": "Discrepancia entre Simulación DIgSILENT y Memoria PDF",
                        "digsilent_value": d_relay.pickup_phase_sec,
                        "pdf_value": pdf_sec,
                        "description": f"En el modelo de DIgSILENT PowerFactory el pickup fue simulado en {d_relay.pickup_phase_sec} A sec, pero en el PDF del ECAP se escribió {pdf_sec} A sec."
                    })
                    
        return discrepancies
