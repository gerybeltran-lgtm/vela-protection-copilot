import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.parser.ecap_parser import ECAPGeminiParser
from backend.audit_engine.auditor import ProtectionAuditor
from backend.drivers.ge_multilin_driver import GEMultilinDriver

def test_parse_sample():
    ecap_dir = Path(r"g:\Mi unidad\Antigravity\Vela Electric\Ejemplos ECAP")
    pdf_files = list(ecap_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("[ERROR] No se encontraron archivos PDF en Ejemplos ECAP.")
        return

    sample_pdf = [f for f in pdf_files if "DTP" in f.name][0]
    print(f"[+] Analizando informe ECAP real: {sample_pdf.name}...")
    
    parser = ECAPGeminiParser()
    try:
        settings_list = parser.parse_pdf_to_schema_list(str(sample_pdf))
        print(f"\n[OK] GEMINI EXTRAJO EXITOSAMENTE {len(settings_list)} RELE(S) / PAÑO(S) DEL ECAP:")
        
        for idx, settings in enumerate(settings_list, 1):
            print(f"\n==================== RELE #{idx} ====================")
            print(f"  - Subestacion: {settings.substation_name}")
            print(f"  - Pano/Alimentador: {settings.feeder_id}")
            print(f"  - Marca/Modelo: {settings.relay_brand} {settings.relay_model}")
            print(f"  - RTC: {settings.ct_ratio.primary_a}/{settings.ct_ratio.secondary_a}")
            
            if settings.ansi_51_phase and settings.ansi_51_phase.enabled:
                p = settings.ansi_51_phase
                curve_str = p.curve.value if p.curve else "DEFINITE_TIME"
                print(f"  - ANSI 51 (Fase): Pickup Prim={p.pickup_primary_a}A | Sec={p.pickup_secondary_a}A | Curva={curve_str} | Dial={p.time_dial}")
                
            if settings.ansi_51n_ground and settings.ansi_51n_ground.enabled:
                g = settings.ansi_51n_ground
                curve_str = g.curve.value if g.curve else "DEFINITE_TIME"
                print(f"  - ANSI 51N (Tierra): Pickup Prim={g.pickup_primary_a}A | Sec={g.pickup_secondary_a}A | Curva={curve_str} | Dial={g.time_dial}")

            # Ejecutar Auditoría para este relé
            print("\n  [AUDITORIA]")
            auditor = ProtectionAuditor(settings)
            findings = auditor.audit_all()
            if not findings:
                print("    [OK] 100% Consistente. Sin incoherencias.")
            else:
                for f in findings:
                    print(f"    [{f.severity.value}] {f.title}: {f.description}")

            # Generar CSV EnerVista para el relé
            driver = GEMultilinDriver()
            csv_out = driver.generate_enervista_csv(settings)
            print("\n  [EXPORT ENERVISTA CSV - Vista Previa]")
            print("  " + csv_out.replace("\n", "\n  ")[:180] + "\n  ...")

    except Exception as e:
        print(f"[ERROR] Error durante el parsing: {e}")

if __name__ == "__main__":
    test_parse_sample()
