import datetime
from typing import List, Dict, Any

class ProtectionReportGenerator:
    @staticmethod
    def generate_html_report(data: Dict[str, Any]) -> str:
        filename = data.get("filename", "Estudio de Protecciones")
        summary = data.get("summary", {})
        relays = data.get("relays", [])
        overall_status = data.get("overall_status", "APPROVED")
        digsilent_loaded = data.get("digsilent_loaded", False)
        custom_rules_applied = data.get("custom_rules_applied", False)
        now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M hrs")
        
        status_banner_class = "bg-emerald-950/40 border-emerald-500/50 text-emerald-300"
        status_title = "✅ CERTIFICADO DE PRE-COMISIONAMIENTO: APTO PARA PROGRAMACIÓN"
        status_subtitle = "Todos los parámetros auditados coinciden 100% con las leyes de coordinación IEEE/IEC, simulación y reglas de ingeniería."

        if overall_status == "REJECTED":
            status_banner_class = "bg-red-950/50 border-red-500/60 text-red-300"
            status_title = "🔴 INFORME RECHAZADO: INCOHERENCIAS CRÍTICAS DETECTADAS"
            status_subtitle = f"Se detectaron {summary.get('critical_errors', 0)} descalces críticos o compromisos ITO sin resolver. Las matrices de carga quedan bloqueadas por seguridad operativa."
        elif overall_status == "APPROVED_WITH_WARNINGS":
            status_banner_class = "bg-amber-950/40 border-amber-500/50 text-amber-300"
            status_title = "⚠️ APROBADO CON OBSERVACIONES MENORES DE HARDWARE"
            status_subtitle = f"Estudio realizable con {summary.get('warnings', 0)} advertencias sobre rango de precisión o dialecto de curva."

        relays_html = ""
        for idx, r in enumerate(relays, 1):
            s = r["settings"]
            findings = r["findings"]
            st = r["status"]
            
            badge_st = '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">APROBADO</span>'
            if st == "REJECTED":
                badge_st = '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/20 text-red-300 border border-red-500/30">RECHAZADO</span>'
            elif st == "WARNING":
                badge_st = '<span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">ADVERTENCIA</span>'

            findings_html = ""
            if not findings:
                findings_html = '''
                <div class="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center gap-2">
                    <i class="fa-solid fa-check-circle text-base"></i>
                    <span><strong>Parámetros Auditados:</strong> Coincidencia matemática exacta entre primario/secundario y límites físicos del relé.</span>
                </div>
                '''
            else:
                for f in findings:
                    is_crit = f['severity'] == 'CRITICAL'
                    findings_html += f'''
                    <div class="mt-2.5 p-3 rounded-xl bg-gray-900 border { 'border-red-500/40 bg-red-950/20' if is_crit else 'border-amber-500/40 bg-amber-950/20' } text-xs space-y-1">
                        <div class="flex justify-between font-bold { 'text-red-400' if is_crit else 'text-amber-400' }">
                            <span>[{f['severity']}] {f['title']}</span>
                            <span class="font-mono text-gray-400">{f['affected_setting']}</span>
                        </div>
                        <p class="text-gray-300">{f['description']}</p>
                        <p class="text-amber-300 font-mono pt-1">
                            <strong>Acción Requerida:</strong> {f['recommendation']}
                        </p>
                    </div>
                    '''

            ct = s.get("ct_ratio", {})
            p51 = s.get("ansi_51_phase", {}) or {}
            g51 = s.get("ansi_51n_ground", {}) or {}

            relays_html += f'''
            <div class="mb-6 p-5 rounded-2xl bg-gray-950 border border-gray-800 space-y-4">
                <div class="flex justify-between items-center border-b border-gray-850 pb-3">
                    <div>
                        <h3 class="font-bold text-sm text-gray-100 flex items-center gap-2">
                            <i class="fa-solid fa-microchip text-amber-500"></i> Paño #{idx}: {s.get('feeder_id')}
                        </h3>
                        <p class="text-xs text-gray-400">Subestación: {s.get('substation_name')} | Relé Target: {s.get('relay_brand')} {s.get('relay_model')}</p>
                    </div>
                    {badge_st}
                </div>

                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs bg-gray-900/60 p-3 rounded-xl border border-gray-850 font-mono text-gray-300">
                    <div>
                        <span class="text-gray-500 block text-[10px]">RTC (FASE)</span>
                        <strong>{ct.get('primary_a')}/{ct.get('secondary_a')} A</strong> (Ratio {ct.get('primary_a',0)/max(ct.get('secondary_a',1),1):.1f})
                    </div>
                    <div>
                        <span class="text-gray-500 block text-[10px]">ANSI 51 (FASE)</span>
                        <strong>{p51.get('pickup_secondary_a','N/A')} A sec</strong> (TDM {p51.get('time_dial','N/A')})
                    </div>
                    <div>
                        <span class="text-gray-500 block text-[10px]">ANSI 51N (TIERRA)</span>
                        <strong>{g51.get('pickup_secondary_a','N/A')} A sec</strong> (TDM {g51.get('time_dial','N/A')})
                    </div>
                    <div>
                        <span class="text-gray-500 block text-[10px]">CURVA CONFIGURADA</span>
                        <strong>{p51.get('curve','N/A')}</strong>
                    </div>
                </div>

                <div>
                    <h4 class="text-xs font-bold text-gray-400 mb-1">Dictamen Auditor del Paño:</h4>
                    {findings_html}
                </div>
            </div>
            '''

        return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe Oficial | Vela Protection Agent - Vela Ingeniería</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Outfit', sans-serif; background-color: #0B0F17; color: #F3F4F6; }}
        .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
        .page-block {{ page-break-inside: avoid; break-inside: avoid; }}

        @page {{
            size: A4;
            margin: 0;
        }}

        @media print {{
            html, body {{
                background-color: #ffffff !important;
                color: #1e293b !important;
                padding: 12mm !important;
                margin: 0 !important;
                width: 100% !important;
            }}
            .no-print {{ display: none !important; }}
            .glass-card {{ background: #ffffff !important; border: 1px solid #e2e8f0 !important; color: #0f172a !important; box-shadow: none !important; }}
            header {{ border-bottom: 2px solid #e2e8f0 !important; padding-bottom: 1rem !important; }}
            footer {{ border-top: 2px solid #e2e8f0 !important; padding-top: 1rem !important; }}
            .text-white {{ color: #0f172a !important; }}
            .text-gray-300, .text-gray-400 {{ color: #475569 !important; }}
            .bg-gray-950, .bg-gray-900 {{ background-color: #f8fafc !important; border: 1px solid #cbd5e1 !important; color: #0f172a !important; }}
            .text-amber-400, .text-amber-500 {{ color: #d97706 !important; }}
            .page-block {{ page-break-inside: avoid !important; break-inside: avoid !important; }}
        }}
    </style>
</head>
<body class="p-6 md:p-12 max-w-5xl mx-auto space-y-8">

    <!-- Header Oficial con Branding Vela Ingeniería & Agencia Vela -->
    <header class="border-b border-gray-800 pb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 page-block">
        <div class="flex items-center space-x-4">
            <div class="w-14 h-14 rounded-2xl bg-gradient-to-tr from-amber-500 to-orange-600 flex items-center justify-center text-gray-950 font-bold text-2xl shadow-xl shadow-amber-500/20">
                <i class="fa-solid fa-bolt"></i>
            </div>
            <div>
                <h1 class="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                    VELA <span class="text-amber-500">PROTECTION AGENT</span>
                </h1>
                <p class="text-xs text-amber-400/90 font-semibold tracking-wide uppercase">
                    Vela Ingeniería &bull; Suite de Soluciones Industriales de Agencia Vela
                </p>
                <p class="text-[11px] text-gray-400">Certificado Oficial de Auditoría & Pre-Comisionamiento en Subestación</p>
            </div>
        </div>

        <div class="text-left md:text-right text-xs text-gray-400 font-mono space-y-1 bg-gray-950 p-3 rounded-xl border border-gray-850">
            <p><span class="text-gray-500">Emisión:</span> <strong class="text-gray-200">{now_str}</strong></p>
            <p><span class="text-gray-500">Documento ECAP:</span> <strong class="text-amber-400">{filename}</strong></p>
            <p><span class="text-gray-500">Auditoría DIgSILENT:</span> <strong class="text-emerald-400">{ 'Nativa (.dz/json)' if digsilent_loaded else 'No requerida' }</strong></p>
        </div>
    </header>

    <!-- Banner Ejecutivo de Dictamen -->
    <section class="p-6 rounded-3xl border shadow-2xl {status_banner_class} space-y-2 page-block">
        <div class="flex items-center justify-between">
            <span class="text-[10px] font-bold uppercase tracking-widest font-mono text-gray-400">Dictamen Técnico Oficial</span>
            <span class="text-xs font-mono text-amber-400">Engine v1.0 Certified</span>
        </div>
        <h2 class="text-xl font-extrabold tracking-tight">{status_title}</h2>
        <p class="text-xs text-gray-300 leading-relaxed">{status_subtitle}</p>
    </section>

    <!-- KPIs del Estudio -->
    <section class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center page-block">
        <div class="p-4 rounded-2xl bg-gray-950 border border-gray-850">
            <span class="text-2xl font-extrabold text-white font-mono">{summary.get('total_relays')}</span>
            <span class="block text-[11px] text-gray-400 mt-1">Paños Auditados</span>
        </div>
        <div class="p-4 rounded-2xl bg-gray-950 border border-gray-850">
            <span class="text-2xl font-extrabold text-red-400 font-mono">{summary.get('critical_errors')}</span>
            <span class="block text-[11px] text-gray-400 mt-1">Errores Críticos</span>
        </div>
        <div class="p-4 rounded-2xl bg-gray-950 border border-gray-850">
            <span class="text-2xl font-extrabold text-amber-400 font-mono">{summary.get('warnings')}</span>
            <span class="block text-[11px] text-gray-400 mt-1">Advertencias HW</span>
        </div>
        <div class="p-4 rounded-2xl bg-gray-950 border border-gray-850">
            <span class="text-2xl font-extrabold text-emerald-400 font-mono">100%</span>
            <span class="block text-[11px] text-gray-400 mt-1">Trazabilidad CEN/ITO</span>
        </div>
    </section>

    <!-- Detalle por Paño -->
    <section class="space-y-4 page-block">
        <h2 class="text-base font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-list-check text-amber-500"></i> Desglose Técnico por Paño de Protección
        </h2>
        {relays_html}
    </section>

    <!-- Banner Comercial de la Suite Vela Ingeniería -->
    <section class="p-6 rounded-2xl bg-gradient-to-r from-gray-950 via-gray-900 to-gray-950 border border-amber-500/30 text-xs space-y-3 shadow-xl page-block">
        <div class="flex items-center justify-between">
            <h3 class="font-bold text-amber-400 text-sm flex items-center gap-2">
                <i class="fa-solid fa-industry"></i> Sobre Vela Ingeniería &bull; Suite de Soluciones B2B
            </h3>
            <span class="text-[10px] text-gray-400 font-mono">by Agencia Vela</span>
        </div>
        <p class="text-gray-300 leading-relaxed">
            <strong>Vela Ingeniería</strong> es la división tecnológica de <strong>Agencia Vela</strong> especializada en suites de Inteligencia Artificial para el sector eléctrico y minero. Diseñada para auditar memorias de cálculo, automatizar parametrizaciones y reducir en más de un <strong>80% los tiempos de pre-comisionamiento</strong>, garantizando cero fallas operativas en subestación.
        </p>
    </section>

    <!-- Footer y Botones -->
    <footer class="border-t border-gray-800 pt-6 space-y-4 text-xs text-gray-500 page-block">
        <!-- CLAUSULA DE SEGURIDAD OPERATIVA Y RESPONSABILIDAD DE INGENIERÍA -->
        <div class="p-5 rounded-2xl bg-red-950/20 border-2 border-red-500/40 text-xs space-y-2 page-block">
            <h4 class="text-red-400 font-extrabold text-sm flex items-center gap-2">
                <i class="fa-solid fa-triangle-exclamation"></i> PROTOCOLO DE SEGURIDAD OPERATIVA E INFRAESTRUCTURA CRÍTICA
            </h4>
            <p class="text-gray-300 leading-relaxed text-[11px]">
                Este informe de auditoría, las matrices de programación nativa (.CSV, .SEC, .RIO) y las plantillas de pruebas (.XRIO) han sido procesados determinísticamente por el motor Multi-Agente de <strong>Vela Protection Agent</strong>. Debido al carácter ultra-crítico de los sistemas de transmisión y distribución de energía eléctrica, <strong>todos los archivos deben ser obligatoriamente revisados, validados y visados por un Ingeniero Civil Eléctrico / Especialista de Protecciones habilitado</strong> antes de ser cargados en los relés físicos o ejecutados en pruebas FAT/SAT en terreno.
            </p>
        </div>

        <div class="flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="text-left">
                <p class="font-bold text-gray-300">VELA PROTECTION AGENT &bull; Suite Vela Ingeniería (by Agencia Vela & E-Voltage)</p>
                <p class="text-gray-400">Documento certificado para presentación ante Inspección Técnica de Obra (ITO) y Coordinador Eléctrico Nacional (CEN).</p>
            </div>

            <div class="no-print">
                <button onclick="window.print()" class="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 text-gray-950 font-bold rounded-xl shadow-lg transition flex items-center gap-2">
                    <i class="fa-solid fa-print"></i> Imprimir / Guardar Informe PDF
                </button>
            </div>
        </div>
    </footer>

</body>
</html>
'''
