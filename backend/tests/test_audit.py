from backend.schemas.protection_schema import ProtectionSettingsSchema, CTRatio, ANSI5051Phase, ANSI5051NGround, CurveType
from backend.audit_engine.auditor import ProtectionAuditor
from backend.drivers.ge_multilin_driver import GEMultilinDriver

def test_audit_detects_rtc_mismatch():
    settings = ProtectionSettingsSchema(
        substation_name="SE San Pedro",
        feeder_id="F-01",
        ct_ratio=CTRatio(primary_a=1000, secondary_a=5),
        ansi_51_phase=ANSI5051Phase(
            enabled=True,
            pickup_primary_a=500,
            pickup_secondary_a=2.00, # Incorrecto: 500 / 200 = 2.50 A
            curve=CurveType.IEEE_VERY_INVERSE,
            time_dial=0.5
        )
    )
    auditor = ProtectionAuditor(settings)
    findings = auditor.audit_all()
    
    assert len(findings) >= 1
    assert any(f.code == "ERR_RTC_MISMATCH_51" for f in findings)

def test_enervista_csv_generation():
    settings = ProtectionSettingsSchema(
        substation_name="SE Don Bosco",
        feeder_id="F-02",
        ct_ratio=CTRatio(primary_a=800, secondary_a=5),
        ansi_51_phase=ANSI5051Phase(
            enabled=True,
            pickup_primary_a=400,
            pickup_secondary_a=2.50,
            curve=CurveType.IEEE_VERY_INVERSE,
            time_dial=0.4
        )
    )
    driver = GEMultilinDriver()
    csv_str = driver.generate_enervista_csv(settings)
    
    assert "SYSTEM_CT_PRIMARY,800" in csv_str
    assert "POC1_PICKUP,2.500" in csv_str
    assert "IEEE Very Inverse" in csv_str
