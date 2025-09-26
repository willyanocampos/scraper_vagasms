import os
import sys
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_file, redirect, url_for
from werkzeug.serving import make_server
import webbrowser
import subprocess
from unified_ms_job_scraper import (
    InfoJobsIndependentScraper,
    SimpleGupyScraper,
    load_gupy_companies_from_json,
    save_jobs_to_json,
    logger
)
app = Flask(__name__)
scraper_status = {
    'is_running': False,
    'progress': 0,
    'current_step': '',
    'total_jobs': 0,
    'infojobs_jobs': 0,
    'gupy_jobs': 0,
    'errors': [],
    'last_update': '',
    'output_file': ''
}
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 MS Jobs Scraper - Interface Web</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            text-align: center;
            padding: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        .content {
            padding: 40px;
        }
        .config-section {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 30px;
            border-left: 5px solid #4facfe;
        }
        .config-section h3 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.3em;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
        }
        .form-control {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-control:focus {
            outline: none;
            border-color: #4facfe;
            box-shadow: 0 0 0 3px rgba(79, 172, 254, 0.1);
        }
        select.form-control {
            cursor: pointer;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .checkbox-group input[type="checkbox"] {
            width: 20px;
            height: 20px;
            accent-color: #4facfe;
        }
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-right: 10px;
            margin-bottom: 10px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
        }
        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(79, 172, 254, 0.3);
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-secondary:hover:not(:disabled) {
            background: #545b62;
        }
        .btn-success {
            background: #28a745;
            color: white;
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none !important;
        }
        .progress-section {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 10px;
            padding: 25px;
            margin-top: 30px;
            display: none;
        }
        .progress-section.active {
            display: block;
        }
        .progress-bar-container {
            background: #e9ecef;
            border-radius: 10px;
            height: 25px;
            margin: 15px 0;
            overflow: hidden;
        }
        .progress-bar {
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            height: 100%;
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }
        .status-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .status-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .status-card h4 {
            color: #4facfe;
            margin-bottom: 10px;
        }
        .status-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .results-section {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 10px;
            padding: 25px;
            margin-top: 30px;
            display: none;
        }
        .results-section.active {
            display: block;
        }
        .error-section {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            display: none;
        }
        .error-section.active {
            display: block;
        }
        .log-container {
            background: #2d3748;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            max-height: 300px;
            overflow-y: auto;
            margin-top: 20px;
        }
        .log-line {
            margin-bottom: 5px;
            padding: 2px 0;
        }
        .log-info { color: #63b3ed; }
        .log-warning { color: #f6e05e; }
        .log-error { color: #fc8181; }
        .log-success { color: #68d391; }
        @media (max-width: 768px) {
            .content {
                padding: 20px;
            }
            .header h1 {
                font-size: 2em;
            }
            .status-info {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 MS Jobs Scraper</h1>
            <p>Interface Web para Extração de Vagas do Mato Grosso do Sul</p>
        </div>
        <div class="content">
            <!-- Configuration Section -->
            <div class="config-section">
                <h3>⚙️ Configurações de Extração</h3>
                <div class="form-group">
                    <label for="execution_mode">🎯 Modo de Execução</label>
                    <select id="execution_mode" class="form-control">
                        <option value="test">🧪 Teste (5 páginas por fonte)</option>
                        <option value="partial">📊 Parcial (20 páginas por fonte)</option>
                        <option value="full">🚀 Completo (Todas as páginas)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="infojobs_pages">📄 InfoJobs - Número de Páginas</label>
                    <input type="number" id="infojobs_pages" class="form-control" value="5" min="1" max="999">
                </div>
                <div class="form-group">
                    <div class="checkbox-group">
                        <input type="checkbox" id="enable_infojobs" checked>
                        <label for="enable_infojobs">🔍 Habilitar InfoJobs</label>
                    </div>
                </div>
                <div class="form-group">
                    <div class="checkbox-group">
                        <input type="checkbox" id="enable_gupy" checked>
                        <label for="enable_gupy">🏢 Habilitar Gupy</label>
                    </div>
                </div>
                <div class="form-group">
                    <label for="output_format">💾 Formato de Saída</label>
                    <select id="output_format" class="form-control">
                        <option value="json">📋 JSON (Padrão)</option>
                        <option value="both">📊 JSON + CSV</option>
                    </select>
                </div>
            </div>
            <!-- Control Buttons -->
            <div style="text-align: center; margin: 30px 0;">
                <button id="start_scraper" class="btn btn-primary">
                    🚀 Iniciar Extração
                </button>
                <button id="stop_scraper" class="btn btn-secondary" disabled>
                    ⏹️ Parar Extração
                </button>
                <button id="open_desktop" class="btn btn-success">
                    🖥️ Abrir Desktop App
                </button>
            </div>
            <!-- Progress Section -->
            <div id="progress_section" class="progress-section">
                <h3>📊 Progresso da Extração</h3>
                <div id="current_step">Preparando...</div>
                <div class="progress-bar-container">
                    <div id="progress_bar" class="progress-bar">0%</div>
                </div>
                <div class="status-info">
                    <div class="status-card">
                        <h4>📋 Total de Vagas</h4>
                        <div id="total_jobs" class="value">0</div>
                    </div>
                    <div class="status-card">
                        <h4>🔍 InfoJobs</h4>
                        <div id="infojobs_jobs" class="value">0</div>
                    </div>
                    <div class="status-card">
                        <h4>🏢 Gupy</h4>
                        <div id="gupy_jobs" class="value">0</div>
                    </div>
                    <div class="status-card">
                        <h4>⏱️ Última Atualização</h4>
                        <div id="last_update" class="value" style="font-size: 1em;">-</div>
                    </div>
                </div>
                <div class="log-container" id="log_container">
                    <div class="log-line log-info">🔧 Sistema pronto para extração...</div>
                </div>
            </div>
            <!-- Results Section -->
            <div id="results_section" class="results-section">
                <h3>✅ Extração Concluída!</h3>
                <p id="results_summary">Resultados serão exibidos aqui...</p>
                <div style="margin-top: 20px;">
                    <button id="download_json" class="btn btn-primary">
                        📥 Download JSON
                    </button>
                    <button id="download_csv" class="btn btn-secondary" style="display: none;">
                        📊 Download CSV
                    </button>
                    <button id="view_data" class="btn btn-success">
                        👁️ Visualizar Dados
                    </button>
                </div>
            </div>
            <!-- Error Section -->
            <div id="error_section" class="error-section">
                <h3>❌ Erros Encontrados</h3>
                <div id="error_list"></div>
            </div>
        </div>
    </div>
    <script>
        let statusInterval;
        // Update execution mode parameters
        document.getElementById('execution_mode').addEventListener('change', function() {
            const mode = this.value;
            const pagesInput = document.getElementById('infojobs_pages');
            switch(mode) {
                case 'test':
                    pagesInput.value = 5;
                    break;
                case 'partial':
                    pagesInput.value = 20;
                    break;
                case 'full':
                    pagesInput.value = 999;
                    break;
            }
        });
        // Start scraper
        document.getElementById('start_scraper').addEventListener('click', function() {
            const config = {
                execution_mode: document.getElementById('execution_mode').value,
                infojobs_pages: parseInt(document.getElementById('infojobs_pages').value),
                enable_infojobs: document.getElementById('enable_infojobs').checked,
                enable_gupy: document.getElementById('enable_gupy').checked,
                output_format: document.getElementById('output_format').value
            };
            fetch('/start_scraper', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('start_scraper').disabled = true;
                    document.getElementById('stop_scraper').disabled = false;
                    document.getElementById('progress_section').classList.add('active');
                    document.getElementById('results_section').classList.remove('active');
                    document.getElementById('error_section').classList.remove('active');
                    // Start status polling
                    statusInterval = setInterval(updateStatus, 2000);
                } else {
                    alert('Erro ao iniciar: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Erro de conexão: ' + error);
            });
        });
        // Stop scraper
        document.getElementById('stop_scraper').addEventListener('click', function() {
            fetch('/stop_scraper', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    clearInterval(statusInterval);
                    document.getElementById('start_scraper').disabled = false;
                    document.getElementById('stop_scraper').disabled = true;
                    addLogLine('⏹️ Extração interrompida pelo usuário', 'warning');
                }
            });
        });
        // Open desktop app
        document.getElementById('open_desktop').addEventListener('click', function() {
            fetch('/open_desktop', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addLogLine('🖥️ Desktop app iniciado', 'success');
                } else {
                    alert('Erro ao abrir desktop app: ' + data.message);
                }
            });
        });
        // Update status
        function updateStatus() {
            fetch('/status')
            .then(response => response.json())
            .then(data => {
                // Update progress bar
                document.getElementById('progress_bar').style.width = data.progress + '%';
                document.getElementById('progress_bar').textContent = data.progress + '%';
                // Update current step
                document.getElementById('current_step').textContent = data.current_step;
                // Update counters
                document.getElementById('total_jobs').textContent = data.total_jobs;
                document.getElementById('infojobs_jobs').textContent = data.infojobs_jobs;
                document.getElementById('gupy_jobs').textContent = data.gupy_jobs;
                document.getElementById('last_update').textContent = data.last_update;
                // Add new log entries
                if (data.current_step && data.current_step !== window.lastStep) {
                    addLogLine('📝 ' + data.current_step, 'info');
                    window.lastStep = data.current_step;
                }
                // Check if completed
                if (!data.is_running && data.progress > 0) {
                    clearInterval(statusInterval);
                    document.getElementById('start_scraper').disabled = false;
                    document.getElementById('stop_scraper').disabled = true;
                    if (data.total_jobs > 0) {
                        showResults(data);
                    }
                    if (data.errors.length > 0) {
                        showErrors(data.errors);
                    }
                }
            })
            .catch(error => {
                console.error('Status update error:', error);
            });
        }
        // Add log line
        function addLogLine(message, type = 'info') {
            const logContainer = document.getElementById('log_container');
            const logLine = document.createElement('div');
            logLine.className = `log-line log-${type}`;
            logLine.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
            logContainer.appendChild(logLine);
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        // Show results
        function showResults(data) {
            document.getElementById('results_section').classList.add('active');
            document.getElementById('results_summary').innerHTML = `
                <strong>Extração concluída com sucesso!</strong><br>
                📊 Total de vagas coletadas: <strong>${data.total_jobs}</strong><br>
                🔍 InfoJobs: <strong>${data.infojobs_jobs}</strong> vagas<br>
                🏢 Gupy: <strong>${data.gupy_jobs}</strong> vagas<br>
                📁 Arquivo salvo: <code>${data.output_file}</code>
            `;
            // Show CSV download if format includes it
            if (data.output_file && data.output_file.includes('csv')) {
                document.getElementById('download_csv').style.display = 'inline-flex';
            }
            addLogLine('✅ Extração concluída com sucesso!', 'success');
        }
        // Show errors
        function showErrors(errors) {
            document.getElementById('error_section').classList.add('active');
            const errorList = document.getElementById('error_list');
            errorList.innerHTML = errors.map(error => `<div>❌ ${error}</div>`).join('');
        }
        // Download handlers
        document.getElementById('download_json').addEventListener('click', function() {
            window.open('/download/json', '_blank');
        });
        document.getElementById('download_csv').addEventListener('click', function() {
            window.open('/download/csv', '_blank');
        });
        document.getElementById('view_data').addEventListener('click', function() {
            window.open('/view_data', '_blank');
        });
        // Initial log
        addLogLine('🚀 Interface web carregada e pronta para uso', 'success');
    </script>
</body>
</html>
"""
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)
@app.route('/start_scraper', methods=['POST'])
def start_scraper():
    global scraper_status
    if scraper_status['is_running']:
        return jsonify({'success': False, 'message': 'Scraper já está em execução'})
    try:
        config = request.get_json()
        scraper_status.update({
            'is_running': True,
            'progress': 0,
            'current_step': 'Iniciando extração...',
            'total_jobs': 0,
            'infojobs_jobs': 0,
            'gupy_jobs': 0,
            'errors': [],
            'last_update': datetime.now().strftime('%H:%M:%S'),
            'output_file': ''
        })
        scraper_thread = threading.Thread(
            target=run_scraper_with_config,
            args=(config,),
            daemon=True
        )
        scraper_thread.start()
        return jsonify({'success': True, 'message': 'Scraper iniciado com sucesso'})
    except Exception as e:
        logger.error(f"Erro ao iniciar scraper: {e}")
        return jsonify({'success': False, 'message': str(e)})
@app.route('/stop_scraper', methods=['POST'])
def stop_scraper():
    global scraper_status
    scraper_status['is_running'] = False
    return jsonify({'success': True, 'message': 'Scraper interrompido'})
@app.route('/status')
def get_status():
    return jsonify(scraper_status)
@app.route('/open_desktop', methods=['POST'])
def open_desktop():
    try:
        desktop_script = Path('ms_jobs_desktop.py')
        if desktop_script.exists():
            subprocess.Popen([sys.executable, str(desktop_script)], cwd=Path.cwd())
            return jsonify({'success': True, 'message': 'Desktop app iniciado'})
        else:
            return jsonify({'success': False, 'message': 'Desktop app não encontrado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
@app.route('/download/<file_type>')
def download_file(file_type):
    try:
        output_dir = Path('output')
        if file_type == 'json':
            files = list(output_dir.glob('unified_ms_jobs_*.json'))
        elif file_type == 'csv':
            files = list(output_dir.glob('unified_ms_jobs_*.csv'))
        else:
            return "Tipo de arquivo inválido", 400
        if not files:
            return "Arquivo não encontrado", 404
        latest_file = max(files, key=lambda x: x.stat().st_mtime)
        return send_file(latest_file, as_attachment=True)
    except Exception as e:
        return f"Erro ao baixar arquivo: {e}", 500
@app.route('/view_data')
def view_data():
    try:
        output_dir = Path('output')
        json_files = list(output_dir.glob('unified_ms_jobs_*.json'))
        if not json_files:
            return "Nenhum arquivo de dados encontrado", 404
        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dados Extraídos - MS Jobs</title>
            <style>
                body {  font-family: Arial, sans-serif; margin: 20px; } 
                .job {  border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; } 
                .job-title {  font-weight: bold; color: #333; margin-bottom: 5px; } 
                .job-company {  color: #666; margin-bottom: 5px; } 
                .job-location {  color: #999; font-size: 0.9em; } 
                .summary {  background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; } 
            </style>
        </head>
        <body>
            <h1>📊 Dados Extraídos - MS Jobs</h1>
            <div class="summary">
                <h3>Resumo da Extração</h3>
                <p><strong>Total de vagas:</strong> {len(data.get('jobs', []))}</p>
                <p><strong>Arquivo:</strong> {latest_file.name}</p>
                <p><strong>Data de extração:</strong> {data.get('extraction_info', {}).get('extraction_date', 'N/A')}</p>
            </div>
            <h3>📋 Vagas Encontradas</h3>
        """
        for job in data.get('jobs', [])[:50]:  
            html += f"""
            <div class="job">
                <div class="job-title">💼 {job.get('titulo', 'N/A')}</div>
                <div class="job-company">🏢 {job.get('empresa', 'N/A')}</div>
                <div class="job-location">📍 {job.get('cidade', 'N/A')} - {job.get('estado', 'N/A')}</div>
                <div class="job-location">🔗 <a href="{job.get('link', '#')}" target="_blank">Ver vaga original</a></div>
            </div>
            """
        if len(data.get('jobs', [])) > 50:
            html += f"<p><em>... e mais {len(data.get('jobs', [])) - 50} vagas</em></p>"
        html += "</body></html>"
        return html
    except Exception as e:
        return f"Erro ao visualizar dados: {e}", 500
def run_scraper_with_config(config):
    global scraper_status
    try:
        scraper_status['current_step'] = 'Preparando configurações...'
        scraper_status['progress'] = 5
        scraper_status['last_update'] = datetime.now().strftime('%H:%M:%S')
        all_jobs = []
        if config.get('enable_infojobs', True):
            scraper_status['current_step'] = 'Extraindo vagas do InfoJobs...'
            scraper_status['progress'] = 10
            scraper_status['last_update'] = datetime.now().strftime('%H:%M:%S')
            try:
                infojobs_scraper = InfoJobsIndependentScraper()
                infojobs_jobs = infojobs_scraper.scrape_jobs(max_pages=config.get('infojobs_pages', 5))
                if infojobs_jobs:
                    all_jobs.extend(infojobs_jobs)
                    scraper_status['infojobs_jobs'] = len(infojobs_jobs)
                    scraper_status['total_jobs'] = len(all_jobs)
                scraper_status['progress'] = 50
                scraper_status['last_update'] = datetime.now().strftime('%H:%M:%S')
            except Exception as e:
                error_msg = f"Erro no InfoJobs: {str(e)}"
                scraper_status['errors'].append(error_msg)
                logger.error(error_msg)
        if config.get('enable_gupy', True):
            scraper_status['current_step'] = 'Extraindo vagas da Gupy...'
            scraper_status['progress'] = 60
            scraper_status['last_update'] = datetime.now().strftime('%H:%M:%S')
            try:
                gupy_companies = load_gupy_companies_from_json("data/json_portais_carreiras_ms.json")
                if gupy_companies:
                    for i, company in enumerate(gupy_companies):
                        if not scraper_status['is_running']:
                            break
                        scraper_status['current_step'] = f'Processando {company.nome}...'
                        progress = 60 + (30 * (i + 1) / len(gupy_companies))
                        scraper_status['progress'] = int(progress)
                        scraper_status['last_update'] = datetime.now().strftime('%H:%M:%S')
                        try:
                            gupy_scraper = SimpleGupyScraper(company)
                            gupy_jobs = gupy_scraper.scrape_all_jobs()
                            if gupy_jobs:
                                all_jobs.extend(gupy_jobs)
                                scraper_status['gupy_jobs'] = len([j for j in all_jobs if j.get('portal_origem') == 'Gupy'])
                                scraper_status['total_jobs'] = len(all_jobs)
                        except Exception as e:
                            logger.error(f"Erro na empresa {company.nome}: {e}")
            except Exception as e:
                error_msg = f"Erro na Gupy: {str(e)}"
                scraper_status['errors'].append(error_msg)
                logger.error(error_msg)
        if all_jobs and scraper_status['is_running']:
            scraper_status['current_step'] = 'Salvando resultados...'
            scraper_status['progress'] = 95
            scraper_status['last_update'] = datetime.now().strftime('%H:%M:%S')
            seen = set()
            unique_jobs = []
            for job in all_jobs:
                job_key = (job.get('titulo'), job.get('empresa'), job.get('cidade'))
                if job_key not in seen:
                    seen.add(job_key)
                    unique_jobs.append(job)
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_file = f"output/unified_ms_jobs_{timestamp}.json"
            save_jobs_to_json(unique_jobs, json_file)
            scraper_status['output_file'] = json_file
            if config.get('output_format') == 'both':
                try:
                    import pandas as pd
                    csv_file = f"output/unified_ms_jobs_{timestamp}.csv"
                    df = pd.DataFrame(unique_jobs)
                    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                except ImportError:
                    scraper_status['errors'].append("Pandas não disponível para exportar CSV")
            scraper_status['total_jobs'] = len(unique_jobs)
            scraper_status['progress'] = 100
            scraper_status['current_step'] = f'✅ Concluído! {len(unique_jobs)} vagas extraídas'
        elif not all_jobs:
            scraper_status['current_step'] = '⚠️ Nenhuma vaga foi encontrada'
            scraper_status['progress'] = 100
        scraper_status['is_running'] = False
        scraper_status['last_update'] = datetime.now().strftime('%H:%M:%S')
    except Exception as e:
        scraper_status['is_running'] = False
        scraper_status['errors'].append(f"Erro geral: {str(e)}")
        scraper_status['current_step'] = f'❌ Erro: {str(e)}'
        scraper_status['progress'] = 0
        logger.error(f"Erro na execução do scraper: {e}")
def main():
    print("\n🚀 MS Jobs Scraper - Interface Web")
    print("=" * 50)
    port = 5000
    try:
        server = make_server('127.0.0.1', port, app, threaded=True)
        print(f"🌐 Servidor iniciado em: http://localhost:{port}")
        print("📝 Abrindo navegador automaticamente...")
        print("⏹️  Pressione Ctrl+C para parar o servidor")
        print("-" * 50)
        def open_browser():
            time.sleep(1.5)  
            webbrowser.open(f'http://localhost:{port}')
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Servidor encerrado pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao iniciar servidor: {e}")
if __name__ == "__main__":
    main()