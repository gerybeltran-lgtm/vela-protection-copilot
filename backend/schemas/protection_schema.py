from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class CurveType(str, Enum):
    IEEE_MODERATELY_INVERSE = "IEEE_MODERATELY_INVERSE"
    IEEE_VERY_INVERSE = "IEEE_VERY_INVERSE"
    IEEE_EXTREMELY_INVERSE = "IEEE_EXTREMELY_INVERSE"
    ANSI_MODERATELY_INVERSE = "ANSI_MODERATELY_INVERSE"
    ANSI_VERY_INVERSE = "ANSI_VERY_INVERSE"
    ANSI_EXTREMELY_INVERSE = "ANSI_EXTREMELY_INVERSE"
    ANSI_NORMAL_INVERSE = "ANSI_NORMAL_INVERSE"
    IEC_STANDARD_INVERSE = "IEC_STANDARD_INVERSE"
    IEC_VERY_INVERSE = "IEC_VERY_INVERSE"
    IEC_EXTREMELY_INVERSE = "IEC_EXTREMELY_INVERSE"
    DEFINITE_TIME = "DEFINITE_TIME"

class ANSI5051Phase(BaseModel):
    enabled: bool = True
    pickup_primary_a: Optional[float] = Field(None, description="Corriente de disparo en Amperes primarios")
    pickup_secondary_a: Optional[float] = Field(None, description="Corriente de disparo en Amperes secundarios")
    curve: Optional[CurveType] = CurveType.IEEE_VERY_INVERSE
    time_dial: Optional[float] = Field(None, description="TDM (IEEE) o TMS (IEC)")
    delay_time_s: Optional[float] = Field(0.0, description="Tiempo de retardo adicional en segundos")

    @field_validator('curve', mode='before')
    def normalize_curve(cls, v):
        if not v or str(v).upper() in ["NONE", "N/A", "DISABLED", "DESHABILITADO", "OFF", "NULL"]:
            return None
        if isinstance(v, str):
            v_upper = v.upper()
            if "EXTREMELY" in v_upper:
                return CurveType.IEEE_EXTREMELY_INVERSE
            if "VERY" in v_upper:
                return CurveType.IEEE_VERY_INVERSE
            if "MODERATELY" in v_upper or "NORMAL" in v_upper or "STANDARD" in v_upper:
                return CurveType.IEEE_MODERATELY_INVERSE
            if "DEFINITE" in v_upper:
                return CurveType.DEFINITE_TIME
        return v

class ANSI5051NGround(BaseModel):
    enabled: bool = True
    pickup_primary_a: Optional[float] = Field(None, description="Corriente de disparo de tierra en A primarios")
    pickup_secondary_a: Optional[float] = Field(None, description="Corriente de disparo de tierra en A secundarios")
    curve: Optional[CurveType] = CurveType.IEEE_VERY_INVERSE
    time_dial: Optional[float] = Field(None, description="TDM (IEEE) o TMS (IEC)")
    delay_time_s: Optional[float] = Field(0.0, description="Tiempo de retardo adicional en segundos")

    @field_validator('curve', mode='before')
    def normalize_curve(cls, v):
        if not v or str(v).upper() in ["NONE", "N/A", "DISABLED", "DESHABILITADO", "OFF", "NULL"]:
            return None
        if isinstance(v, str):
            v_upper = v.upper()
            if "EXTREMELY" in v_upper:
                return CurveType.IEEE_EXTREMELY_INVERSE
            if "VERY" in v_upper:
                return CurveType.IEEE_VERY_INVERSE
            if "MODERATELY" in v_upper or "NORMAL" in v_upper or "STANDARD" in v_upper:
                return CurveType.IEEE_MODERATELY_INVERSE
            if "DEFINITE" in v_upper:
                return CurveType.DEFINITE_TIME
        return v

class CTRatio(BaseModel):
    primary_a: float = Field(..., description="Corriente primaria nominal del TC, ej. 1200")
    secondary_a: float = Field(..., description="Corriente secundaria nominal del TC, ej. 5")
    
    @property
    def ratio(self) -> float:
        return self.primary_a / self.secondary_a

class VTRatio(BaseModel):
    primary_v: float = Field(..., description="Tensión primaria nominal del TT, ej. 13800")
    secondary_v: float = Field(..., description="Tensión secundaria nominal del TT, ej. 115")

    @property
    def ratio(self) -> float:
        return self.primary_v / self.secondary_v

class DocumentMetadata(BaseModel):
    has_ito_comments: bool = False
    ito_comments_list: Optional[List[str]] = []
    missing_system_110kv: bool = False
    missing_psp_study: bool = False
    cen_regulatory_warning: Optional[str] = None
    custom_rules_findings: Optional[List[str]] = []

class ProtectionSettingsSchema(BaseModel):
    substation_name: str
    feeder_id: str
    relay_brand: str = "GE Multilin"
    relay_model: str = "850"
    firmware_version: Optional[str] = "7.00"
    
    ct_ratio: CTRatio
    vt_ratio: Optional[VTRatio] = None
    
    ansi_51_phase: Optional[ANSI5051Phase] = None
    ansi_51n_ground: Optional[ANSI5051NGround] = None
    
    doc_metadata: Optional[DocumentMetadata] = None
    raw_notes: Optional[List[str]] = []
