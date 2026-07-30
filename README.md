# Vela Protection Copilot (E-Voltage & Vela Agency)

**Vela Protection Copilot** es una plataforma de **Auditoría de ECAP (Estudios de Coordinación y Ajustes de Protecciones)** y **Generador de Archivos de Carga para Relés** (GE EnerVista, SEL AcSELerator, OMICRON Test Universe/XRIO).

Designed for **E-Voltage Ingeniería** and commercialized as a B2B SaaS platform by **Vela Agency**.

---

## 🚀 Módulos Implementados en la FASE 1

1. **Schema Unificado de Protecciones (`backend/schemas/protection_schema.py`)**:
   - Representación estándar en Pydantic de transformadores de medida (RTC / RTT), funciones ANSI 50/51 (Fase), ANSI 50N/51N (Tierra), curvas de tiempo (IEEE / IEC) y multiplicadores (TDM/TMS).

2. **Motor de Auditoría & Verificación Cruzada (`backend/audit_engine/auditor.py`)**:
   - Auditoría matemática de consistencia Primario vs. Secundario vs. RTC (Tolerancia < 1.5%).
   - Auditoría de rangos dinámicos y precisión física de hardware en TCs de entrada.
   - Auditoría de dialectos de tiempo (Alerta sobre descalces TDM vs TMS).

3. **Driver GE Multilin - Exporter EnerVista (`backend/drivers/ge_multilin_driver.py`)**:
   - Conversión de parámetros unificados a archivo nativo `.csv` listo para importación en **EnerVista Setup Software**.

4. **API Backend FastAPI (`backend/main.py`)**:
   - Endpoint `/api/audit`: Ejecuta la auditoría y devuelve hallazgos RFI categorizados por gravedad (`CRITICAL`, `WARNING`, `INFO`).
   - Endpoint `/api/export/ge-enervista`: Genera y descarga el archivo `.csv`.

5. **Interfaz de Usuario / DashBoard (`frontend/index.html`)**:
   - Interfaz web con tema oscuro industrial, tablero de parámetros, semáforo de hallazgos RFI y vista previa / descarga del archivo EnerVista.

---

## 🛠️ Instrucciones de Ejecución

### 1. Iniciar el Backend API (FastAPI)
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
El servidor estará accesible en: `http://localhost:8000` (Docs interactivos Swagger en `http://localhost:8000/docs`).

### 2. Abrir la Interfaz de Usuario
Simplemente abre `frontend/index.html` en cualquier navegador web o bien sírvelo con un servidor HTTP local.

---

## 📑 Próximos Sprints (Roadmap)
- **Sprint 2**: Integración de Parser OCR/LLM con la API de Gemini para la extracción automática desde PDFs de ECAPs subidos por los clientes.
- **Sprint 3**: Adición del Driver SEL (AcSELerator / SELogic) y Driver OMICRON (`.xrio` / `.rio` para Test Universe).
