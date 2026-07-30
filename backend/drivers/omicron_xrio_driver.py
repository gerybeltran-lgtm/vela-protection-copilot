from backend.schemas.protection_schema import ProtectionSettingsSchema

class OmicronXRIODriver:
    """Generador de Plantillas de Pruebas OMICRON Test Universe / RelaySimTest (.XRIO)."""

    def generate_xrio_template(self, settings: ProtectionSettingsSchema) -> str:
        s = settings
        ct = s.ct_ratio
        p51 = s.ansi_51_phase
        g51 = s.ansi_51n_ground
        
        pickup_51_sec = p51.pickup_secondary_a if (p51 and p51.pickup_secondary_a) else 1.0
        tdm_51 = p51.time_dial if (p51 and p51.time_dial) else 0.5
        
        pickup_51n_sec = g51.pickup_secondary_a if (g51 and g51.pickup_secondary_a) else 0.1
        tdm_51n = g51.time_dial if (g51 and g51.time_dial) else 0.5

        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<XRIO version="3.10">
  <Header>
    <DeviceName>{s.feeder_id}</DeviceName>
    <Substation>{s.substation_name}</Substation>
    <RelayBrand>{s.relay_brand}</RelayBrand>
    <RelayModel>{s.relay_model}</RelayModel>
    <Manufacturer>OMICRON Test Universe Export by Vela Protection Copilot</Manufacturer>
  </Header>
  <DeviceParameters>
    <Parameter ID="CT_Primary" Value="{ct.primary_a}" Unit="A" />
    <Parameter ID="CT_Secondary" Value="{ct.secondary_a}" Unit="A" />
  </DeviceParameters>
  <ProtectionFunctions>
    <Function ID="ANSI_51_Phase">
      <Enabled>{'true' if p51 and p51.enabled else 'false'}</Enabled>
      <PickupSecondary Unit="A">{pickup_51_sec}</PickupSecondary>
      <TimeDial>{tdm_51}</TimeDial>
      <CurveType>{p51.curve.value if (p51 and p51.curve) else 'IEEE_VERY_INVERSE'}</CurveType>
    </Function>
    <Function ID="ANSI_51N_Ground">
      <Enabled>{'true' if g51 and g51.enabled else 'false'}</Enabled>
      <PickupSecondary Unit="A">{pickup_51n_sec}</PickupSecondary>
      <TimeDial>{tdm_51n}</TimeDial>
      <CurveType>{g51.curve.value if (g51 and g51.curve) else 'IEEE_VERY_INVERSE'}</CurveType>
    </Function>
  </ProtectionFunctions>
</XRIO>
"""
        return xml_content
