import os
import json
import tempfile
import webbrowser
import threading
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox, filedialog
from accurate_ms_map_data import AccurateMSMapData
logger = logging.getLogger(__name__)
class InteractiveMapWidget(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.map_data = AccurateMSMapData()
        self.jobs_data = []
        self.current_map_file = None
        self.is_generating = False
        self.companies = {}
        self.default_company_templates = {
            'aegea': {
                'name': 'AEGEA',
                'color': '#1f77b4',
                'description': 'Empresa de saneamento',
                'icon': '💧'
            },
            'grupo_pereira': {
                'name': 'GRUPO PEREIRA',
                'color': '#ff7f0e', 
                'description': 'Grupo empresarial diversificado',
                'icon': '🏢'
            },
            'jbs': {
                'name': 'JBS',
                'color': '#2ca02c',
                'description': 'Indústria alimentícia',
                'icon': '🥩'
            },
            'sicredi': {
                'name': 'SICREDI',
                'color': '#d62728',
                'description': 'Cooperativa financeira',
                'icon': '🏦'
            },
            'suzano': {
                'name': 'SUZANO',
                'color': '#9467bd',
                'description': 'Indústria de papel e celulose',
                'icon': '🌲'
            }
        }
        self.color_palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#393b79', '#637939', '#8c6d31', '#843c39', '#7b4173',
            '#5254a3', '#8ca252', '#bd9e39', '#ad494a', '#a55194',
            '#6b6ecf', '#b5cf6b', '#e7ba52', '#d6616b', '#ce6dbd',
            '#9c9ede', '#cedb9c', '#e7cb94', '#e7969c', '#de9ed6',
            '#3182bd', '#6baed6', '#9ecae1', '#c6dbef', '#756bb1',
            '#9e9ac8', '#bcbddc', '#dadaeb', '#54278f', '#6a51a3',
            '#807dba', '#9e9ac8', '#31a354', '#74c476', '#a1d99b',
            '#c7e9c0', '#636363', '#969696', '#bdbdbd', '#d9d9d9'
        ]
        self.icon_palette = [
            '🏢', '🏭', '🏪', '🏬', '🏦', '🏛️', '🏗️', '⚙️', '🔧', '🔨',
            '💼', '📊', '📈', '📋', '💻', '🔌', '⚡', '🌐', '📱', '🎯',
            '🚀', '⭐', '🔥', '💡', '🛠️', '🏆', '🎖️', '🌟', '💎', '🎨',
            '🏀', '⚽', '🎾', '🏐', '🎮', '🎲', '🎯', '🎪', '🎭', '🎬',
            '🎵', '🎸', '🎹', '🎤', '🎧', '📻', '📺', '📽️', '📷', '📸',
            '🔬', '🧪', '⚗️', '🧬', '💊', '🏥', '🚑', '⚕️', '🩺', '🔍',
            '🌍', '🌎', '🌏', '🌐', '🗺️', '🧭', '⛰️', '🏔️', '🗻', '🏞️',
            '🌊', '🏖️', '🏝️', '🚢', '⛵', '🛥️', '🚤', '✈️', '🛩️', '🚁',
            '🚗', '🚙', '🚐', '🚛', '🚚', '🚜', '🏎️', '🚓', '🚑', '🚒',
            '🚲', '🛴', '🛵', '🏍️', '🚠', '🚡', '🚟', '🚃', '🚋', '🚞'
        ]
        self.processed_jobs = {}
        self.clustered_locations = {}
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.formatted_date = datetime.now().strftime('%d/%m/%Y')
        self.full_datetime = datetime.now().strftime('%d/%m/%Y às %H:%M')
        logger.info("InteractiveMapWidget initialized following bi_mapa_vagas_ms_v2.py structure")
        self.demonstrate_themed_emojis()
        self.setup_ui()
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header_frame = ctk.CTkFrame(self, height=80)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_columnconfigure(1, weight=1)
        title_label = ctk.CTkLabel(
            header_frame, 
            text="🎯 BI Vagas - Mato Grosso do Sul",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        controls_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=1, padx=20, pady=10, sticky="e")
        self.generate_btn = ctk.CTkButton(
            controls_frame,
            text="🚀 Gerar Mapa BI",
            command=self.generate_interactive_map,
            width=140,
            height=36,
            corner_radius=8
        )
        self.generate_btn.grid(row=0, column=0, padx=5)
        export_btn = ctk.CTkButton(
            controls_frame,
            text="💾 Exportar",
            command=self.export_map,
            width=100,
            height=36,
            corner_radius=8
        )
        export_btn.grid(row=0, column=1, padx=5)
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_rowconfigure(1, weight=1)
        self.status_label = ctk.CTkLabel(
            info_frame,
            text="✅ Pronto para gerar mapa interativo BI",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.grid(row=0, column=0, pady=10)
        self.info_text = ctk.CTkTextbox(info_frame, height=200)
        self.info_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.update_info_display()
    def update_data(self, jobs_data: List[Dict]):
        self.jobs_data = jobs_data
        logger.info(f"Updating data with {len(jobs_data)} jobs")
        self.detect_all_companies()
        self.update_info_display()
    def detect_all_companies(self):
        if not self.jobs_data:
            return
        logger.info("Detecting all companies from jobs data...")
        companies_found = set()
        for job in self.jobs_data:
            company_name = str(job.get('empresa', '')).strip()
            if company_name and company_name.upper() not in ['', 'N/A', 'NAN', 'NONE', 'NULL']:
                companies_found.add(company_name.upper())
        logger.info(f"Found {len(companies_found)} unique companies for themed emoji assignment")
        if len(companies_found) <= 10:
            logger.info(f"Companies: {sorted(list(companies_found))}")
        else:
            logger.info(f"Companies: {sorted(list(companies_found))[:10]}... (+{len(companies_found)-10} more)")
        self.companies = {}
        for idx, company_name in enumerate(sorted(companies_found)):
            company_key = self.generate_company_key(company_name)
            template = self.find_company_template(company_name)
            if template:
                self.companies[company_key] = {
                    'name': company_name,
                    'color': template['color'],
                    'description': template['description'],
                    'icon': template['icon']
                }
            else:
                color = self.color_palette[idx % len(self.color_palette)]
                themed_icon = self.get_themed_emoji_for_company(company_name)
                description = self.generate_company_description(company_name)
                self.companies[company_key] = {
                    'name': company_name,
                    'color': color,
                    'description': description,
                    'icon': themed_icon
                }
        self.log_themed_emoji_assignments()
        logger.info(f"Successfully configured {len(self.companies)} companies for the map with themed emojis")
        return len(self.companies)
    def generate_company_key(self, company_name: str) -> str:
        import re
        key = re.sub(r'[^a-zA-Z0-9\s]', '', company_name.lower())
        key = re.sub(r'\s+', '_', key.strip())
        return key[:50]
    def find_company_template(self, company_name: str) -> Optional[Dict]:
        company_upper = company_name.upper()
        for template_key, template in self.default_company_templates.items():
            template_name = template['name'].upper()
            if (template_name in company_upper or 
                company_upper in template_name or
                any(word in company_upper for word in template_name.split() if len(word) > 2)):
                return template
        return None
    def get_themed_emoji_for_company(self, company_name: str) -> str:
        company_upper = company_name.upper()
        category_emojis = {
            'SANEAMENTO': '💧',
            'AGUA': '💧', 
            'AEGEA': '💧',
            'SABESP': '💧',
            'BANK': '🏦',
            'BANCO': '🏦',
            'CREDIT': '💳',
            'SICREDI': '🏦',
            'BRADESCO': '🏦',
            'ITAU': '🏦',
            'SANTANDER': '🏦',
            'BB': '🏦',
            'CAIXA': '🏦',
            'ALIMENTICIA': '🍗',
            'FOOD': '🍽️',
            'JBS': '🥩',
            'FRIGORIFICO': '🥩',
            'MARFRIG': '🥩',
            'BRF': '🍗',
            'SEARA': '🍗',
            'PAPEL': '🌳',
            'CELULOSE': '🌳',
            'SUZANO': '🌲',
            'KLABIN': '🌳',
            'FIBRIA': '🌳',
            'TECH': '💻',
            'TECNOLOGIA': '💻',
            'SOFTWARE': '💻',
            'MICROSOFT': '💻',
            'GOOGLE': '💻',
            'IBM': '💻',
            'ORACLE': '💻',
            'HOSPITAL': '🏥',
            'SAUDE': '⚕️',
            'CLINICA': '🏥',
            'MEDICO': '👨‍⚕️',
            'FARMACIA': '💊',
            'EDUCAÇÃO': '🎓',
            'ENSINO': '🎓',
            'UNIVERSIDADE': '🎓',
            'ESCOLA': '🏫',
            'FACULDADE': '🎓',
            'CONSTRUÇÃO': '🏗️',
            'CONSTRUTORA': '🏗️',
            'ENGENHARIA': '🛠️',
            'OBRAS': '🏗️',
            'TRANSPORTE': '🚚',
            'LOGISTICA': '📦',
            'CORREIOS': '📫',
            'FEDEX': '🚚',
            'DHL': '📦',
            'VAREJO': '🛍️',
            'COMERCIO': '🏢',
            'MAGAZINE': '🛍️',
            'LOJAS': '🏪',
            'MERCADO': '🏢',
            'INDUSTRIA': '🏭',
            'FABRICA': '🏭',
            'MANUFATURA': '⚙️',
            'PRODUCAO': '🏭',
            'MINERAÇÃO': '⛏️',
            'MINERADORA': '⛏️',
            'VALE': '⛏️',
            'ENERGIA': '⚡',
            'ELETRICA': '⚡',
            'ENERGISA': '⚡',
            'CEMIG': '⚡',
            'COPEL': '⚡',
            'PETROLEO': '⛽',
            'GAS': '⛽',
            'PETROBRAS': '⛽',
            'SHELL': '⛽',
            'AGRO': '🌾',
            'AGRICULTURA': '🌾',
            'FAZENDA': '🐄',
            'RURAL': '🌾',
            'TELECOM': '📶',
            'TELEFONIA': '📱',
            'VIVO': '📱',
            'TIM': '📱',
            'CLARO': '📱',
            'OI': '📱',
            'SEGURO': '🛡️',
            'SEGUROS': '🛡️',
            'SEGURADORA': '🛡️',
            'CONSULTORIA': '📊',
            'CONSULTING': '📊',
            'PREFEITURA': '🏢',
            'GOVERNO': '🏢',
            'ESTADO': '🏢',
            'PUBLICO': '🏢',
            'COCA': '🥤',
            'PEPSI': '🥤', 
            'AMBEV': '🍺',
            'HEINEKEN': '🍺',
            'NESTLE': '🍫',
            'FORD': '🚗',
            'GM': '🚗',
            'VOLKSWAGEN': '🚗',
            'FIAT': '🚗',
            'TOYOTA': '🚗',
            'UNILEVER': '🧼',
            'PROCTER': '🧼',
            'AVON': '💄',
            'NATURA': '🌿',
            'GLOBO': '📺',
            'SBT': '📺',
            'RECORD': '📺',
            'BRASKEM': '⚗️',
            'BAYER': '💊',
            'ROCHE': '💊',
            'PFIZER': '💊'
        }
        for keyword, emoji in category_emojis.items():
            if keyword in company_upper:
                return emoji
        return '🏢'
    def generate_company_description(self, company_name: str) -> str:
        company_upper = company_name.upper()
        industry_keywords = {
            'SANEAMENTO': 'Empresa de saneamento e tratamento de água',
            'AGUA': 'Empresa de saneamento e tratamento de água',
            'BANK': 'Instituição financeira',
            'BANCO': 'Instituição financeira',
            'CREDIT': 'Cooperativa de crédito',
            'SICREDI': 'Cooperativa financeira',
            'ALIMENTICIA': 'Indústria alimentícia',
            'FOOD': 'Indústria alimentícia',
            'JBS': 'Indústria alimentícia',
            'TECH': 'Empresa de tecnologia',
            'TECNOLOGIA': 'Empresa de tecnologia',
            'SOFTWARE': 'Empresa de software',
            'HOSPITAL': 'Instituição de saúde',
            'SAUDE': 'Instituição de saúde',
            'EDUCAÇÃO': 'Instituição de ensino',
            'ENSINO': 'Instituição de ensino',
            'CONSTRUÇÃO': 'Empresa de construção civil',
            'CONSTRUTORA': 'Empresa de construção civil',
            'TRANSPORTE': 'Empresa de transporte e logística',
            'LOGISTICA': 'Empresa de transporte e logística',
            'VAREJO': 'Empresa de varejo',
            'COMERCIO': 'Empresa comercial',
            'INDUSTRIA': 'Empresa industrial',
            'PAPELÃO': 'Indústria de papel e celulose',
            'PAPEL': 'Indústria de papel e celulose',
            'SUZANO': 'Indústria de papel e celulose',
            'MINERAÇÃO': 'Empresa de mineração',
            'ENERGIA': 'Empresa do setor energético',
            'ELETRICA': 'Empresa do setor elétrico'
        }
        for keyword, description in industry_keywords.items():
            if keyword in company_upper:
                return description
        return 'Empresa'
    def log_themed_emoji_assignments(self):
        logger.info("🎨 EMOJI TEMÁTICOS ATRIBUÍDOS:")
        emoji_groups = {}
        for company_id, company_info in self.companies.items():
            emoji = company_info['icon']
            if emoji not in emoji_groups:
                emoji_groups[emoji] = []
            emoji_groups[emoji].append(company_info['name'])
        for emoji, companies in emoji_groups.items():
            category = self.get_emoji_category(emoji)
            logger.info(f"  {emoji} {category}: {', '.join(companies)}")
    def get_emoji_category(self, emoji: str) -> str:
        emoji_categories = {
            '💧': 'Saneamento',
            '🏦': 'Financeiro', 
            '🥩': 'Frigorífico',
            '🌲': 'Papel/Celulose',
            '🌳': 'Papel/Celulose',
            '💻': 'Tecnologia',
            '🏥': 'Saúde',
            '⚕️': 'Saúde',
            '🎓': 'Educação',
            '🏗️': 'Construção',
            '🚚': 'Transporte',
            '📦': 'Logística',
            '🏢': 'Empresa',
            '⛏️': 'Mineração',
            '⚡': 'Energia',
            '⛽': 'Petróleo/Gás',
            '🌾': 'Agronegócio',
            '📱': 'Telecom'
        }
        return emoji_categories.get(emoji, 'Outra')
    def demonstrate_themed_emojis(self):
        logger.info("🎨 DEMONSTRAÇÃO DO SISTEMA DE EMOJIS TEMÁTICOS:")
        logger.info("=" * 60)
        test_companies = [
            'SUZANO PAPEL E CELULOSE',
            'JBS FRIGORÍFICO',
            'BANCO DO BRASIL',
            'AEGEA SANEAMENTO',
            'MICROSOFT TECNOLOGIA',
            'HOSPITAL SÃO LUCAS',
            'UNIVERSIDADE FEDERAL',
            'CONSTRUTORA ABC',
            'TRANSPORTES RODONÓVIA',
            'VALE MINERAÇÃO',
            'ENERGISA ELÉTRICA',
            'PETROBRAS',
            'FAZENDA SANTA CLARA',
            'VIVO TELECOM',
            'COCA COLA',
            'FORD MOTORS',
            'NATURA COSMÉTICOS',
            'EMPRESA DESCONHECIDA'
        ]
        for company in test_companies:
            emoji = self.get_themed_emoji_for_company(company)
            category = self.get_emoji_category(emoji)
            logger.info(f"  {emoji} {company:<25} → {category}")
        logger.info("=" * 60)
        logger.info("✅ Sistema de emojis temáticos configurado com sucesso!")
    def process_jobs_data(self):
        if not self.jobs_data:
            return
        logger.info("Processing jobs data...")
        self.processed_jobs = {}
        if not self.companies:
            self.detect_all_companies()
        for company_id, company_info in self.companies.items():
            company_jobs = []
            company_name = company_info['name']
            for job in self.jobs_data:
                job_company = str(job.get('empresa', '')).strip().upper()
                if (company_name.upper() == job_company or 
                    company_name.upper() in job_company or 
                    job_company in company_name.upper()):
                    processed_job = self.process_single_job(job, company_id, company_info)
                    if processed_job:
                        company_jobs.append(processed_job)
            if company_jobs:
                self.processed_jobs[company_id] = company_jobs
                logger.info(f"{company_name}: {len(company_jobs)} jobs processed")
        logger.info(f"Total companies with jobs: {len(self.processed_jobs)}")
        self.create_location_clusters()
    def process_single_job(self, job: Dict, company_id: str, company_info: Dict) -> Optional[Dict]:
        try:
            location_text = str(job.get('localizacao') or job.get('cidade') or job.get('location') or 'Campo Grande')
            coords = self.get_precise_coordinates(location_text, company_id)
            processed_job = {
                'id': f"{company_id}_{len(self.processed_jobs.get(company_id, []))}",
                'titulo': str(job.get('titulo', 'Título não informado')),
                'localizacao': location_text,
                'empresa': company_info['name'],
                'tipo_contrato': str(job.get('tipo_contrato', 'Não informado')),
                'modalidade': str(job.get('modalidade', 'Presencial')),
                'salario': str(job.get('salario', 'A combinar')),
                'lat': coords['lat'],
                'lng': coords['lng'],
                'color': company_info['color'],
                'icon': company_info['icon'],
                'description': company_info['description'],
                'address': coords.get('address', ''),
                'atribuicoes': self.format_bullet_points(str(job.get('atribuicoes', ''))),
                'requisitos': self.format_bullet_points(str(job.get('requisitos', ''))),
                'link': str(job.get('link', '')) if job.get('link') and str(job.get('link')).startswith('http') else ''
            }
            return processed_job
        except Exception as e:
            logger.warning(f"Error processing job: {e}")
            return None
    def get_precise_coordinates(self, location_text: str, company_id: str) -> Dict:
        if not location_text or str(location_text).lower() in ['sem informações', 'nan', 'none', '']:
            location_text = 'Campo Grande'
        location_text = str(location_text).strip()
        company_info = self.companies.get(company_id, {})
        company_locations = company_info.get('locations', {})
        for city, coords in company_locations.items():
            if city.upper() in location_text.upper():
                return coords
        try:
            coords_tuple = self.map_data.get_city_coordinates(location_text)
            if coords_tuple:
                return {
                    'lat': coords_tuple[0], 
                    'lng': coords_tuple[1], 
                    'address': location_text.title()
                }
        except Exception as e:
            logger.warning(f"Error getting coordinates for {location_text}: {e}")
        logger.warning(f"Location not found: '{location_text}' - using Campo Grande")
        return {'lat': -20.4697, 'lng': -54.6201, 'address': 'Campo Grande'}
    def format_bullet_points(self, text: str) -> str:
        if not text or str(text).lower() in ['sem informações', 'nan', 'none', '', 'não informado']:
            return ''
        text = str(text).strip()
        text = text.replace('•', '•').replace('⚫', '•').replace('◦', '•')
        text = text.replace('\n', ' ').replace('\r', ' ')
        if '•' in text:
            parts = text.split('•')
            formatted_parts = []
            for part in parts:
                part = part.strip()
                if part:
                    part = part.lstrip('.-• ')
                    if part:
                        formatted_parts.append(f"• {part}")
            return '<br>'.join(formatted_parts) if formatted_parts else ''
        else:
            return text
    def create_location_clusters(self):
        logger.info("Creating location clusters...")
        self.clustered_locations = {}
        for company_id, jobs in self.processed_jobs.items():
            for job in jobs:
                lat, lng = job['lat'], job['lng']
                location_key = f"{lat:.4f},{lng:.4f}"
                if location_key not in self.clustered_locations:
                    self.clustered_locations[location_key] = {
                        'lat': lat,
                        'lng': lng,
                        'location_name': job['localizacao'],
                        'companies': {},
                        'total_jobs': 0
                    }
                company_name = job['empresa']
                if company_name not in self.clustered_locations[location_key]['companies']:
                    self.clustered_locations[location_key]['companies'][company_name] = {
                        'color': job['color'],
                        'icon': job['icon'],
                        'jobs': []
                    }
                self.clustered_locations[location_key]['companies'][company_name]['jobs'].append(job)
                self.clustered_locations[location_key]['total_jobs'] += 1
        logger.info(f"Created {len(self.clustered_locations)} location clusters")
    def generate_interactive_map(self):
        if not self.jobs_data:
            messagebox.showinfo(
                "Dados Necessários",
                "Carregue dados de vagas primeiro para gerar o mapa BI."
            )
            return
        try:
            self.status_label.configure(text="🔄 Gerando mapa interativo BI...")
            self.process_jobs_data()
            html_content = self.create_enhanced_interactive_map_html()
            temp_dir = Path(tempfile.gettempdir())
            filename = f"bi_mapa_vagas_ms_{self.timestamp}.html"
            self.current_map_file = temp_dir / filename
            with open(self.current_map_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            total_jobs = sum(len(jobs) for jobs in self.processed_jobs.values())
            total_companies = len([jobs for jobs in self.processed_jobs.values() if jobs])
            total_locations = len(self.clustered_locations)
            result = messagebox.askyesno(
                "Mapa BI Gerado!",
                f"Mapa BI gerado com sucesso!\n"
                f"Arquivo: {filename}\n\n"
                f"📊 {total_jobs} vagas processadas\n"
                f"🏢 {total_companies} empresas\n"
                f"📍 {total_locations} localizações\n\n"
                f"Deseja abrir no navegador?"
            )
            if result:
                webbrowser.open(f"file://{self.current_map_file.absolute()}")
            self.status_label.configure(text="✅ Mapa BI gerado com sucesso!")
            self.update_info_display()
        except Exception as e:
            logger.error(f"Error generating BI map: {e}")
            messagebox.showerror("Erro", f"Erro ao gerar mapa BI: {e}")
            self.status_label.configure(text="❌ Erro ao gerar mapa")
    def create_enhanced_interactive_map_html(self) -> str:
        clustered_data_json = json.dumps(self.clustered_locations, ensure_ascii=False, indent=2)
        html_template = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BI Vagas MS - Mapa Interativo</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <style>
        body { 
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        } 
        .header { 
            background: rgba(255,255,255,0.95);
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        } 
        .header h1 { 
            margin: 0;
            color: #2c3e50;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        } 
        .header p { 
            margin: 10px 0 0 0;
            color: #7f8c8d;
            font-size: 1.2em;
        } 
        .container { 
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 20px;
        } 
        .stats-panel { 
            background: rgba(255,255,255,0.95);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        } 
        .stats-grid { 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        } 
        .stat-card { 
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 3px 10px rgba(0,0,0,0.2);
        } 
        .stat-number { 
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        } 
        .stat-label { 
            font-size: 1.1em;
            opacity: 0.9;
        } 
        .companies-container { 
            max-height: 400px;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid rgba(0,0,0,0.1);
            border-radius: 10px;
            background: rgba(255,255,255,0.5);
        } 
        .companies-legend { 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-top: 10px;
        } 
        .company-item { 
            display: flex;
            align-items: center;
            background: rgba(255,255,255,0.9);
            padding: 8px 12px;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
        } 
        .company-item:hover { 
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        } 
        .company-icon { 
            width: 18px;
            height: 18px;
            border-radius: 50%;
            margin-right: 8px;
            flex-shrink: 0;
        } 
        .company-info { 
            flex: 1;
        } 
        .company-name { 
            font-weight: bold;
            color: #2c3e50;
            font-size: 0.9em;
            line-height: 1.2;
        } 
        .company-desc { 
            font-size: 0.75em;
            color: #7f8c8d;
            line-height: 1.1;
            margin-top: 2px;
        } 
        #map { 
            height: 600px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            border: 3px solid rgba(255,255,255,0.3);
        } 
        .leaflet-popup-content { 
            max-width: 500px;
            max-height: 600px;
            overflow-y: auto;
        } 
        .cluster-popup { 
            font-family: 'Segoe UI', sans-serif;
        } 
        .location-title { 
            font-size: 1.4em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
            text-align: center;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
        } 
        .company-section { 
            margin-bottom: 20px;
            border-left: 4px solid;
            padding-left: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 5px;
            padding: 10px;
        } 
        .company-header { 
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
        } 
        .job-item { 
            background: rgba(255,255,255,0.8);
            margin: 8px 0;
            padding: 12px;
            border-radius: 8px;
            border-left: 3px solid;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        } 
        .job-title { 
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
            font-size: 1.1em;
        } 
        .job-details { 
            font-size: 0.9em;
            color: #555;
        } 
        .job-link-button { 
            display: inline-block;
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            text-decoration: none;
            font-size: 0.85em;
            font-weight: bold;
            margin-top: 10px;
            transition: all 0.3s ease;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        } 
        .job-link-button:hover { 
            background: linear-gradient(135deg, #2980b9, #1f5f99);
            transform: translateY(-1px);
            box-shadow: 0 3px 8px rgba(0,0,0,0.3);
        } 
        .footer { 
            background: rgba(255,255,255,0.95);
            text-align: center;
            padding: 20px;
            margin-top: 20px;
            color: #7f8c8d;
        } 
        @media (max-width: 768px) { 
            .header h1 { 
                font-size: 2em;
            } 
            .stats-grid { 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            } 
            .companies-legend { 
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 8px;
            } 
            .companies-container { 
                max-height: 300px;
            } 
            #map { 
                height: 400px;
            } 
        } 
    </style>
</head>
<body>
    <div class="header">
        <h1>BI Vagas - Mato Grosso do Sul</h1>
        <p>Mapa Interativo - {self.formatted_date}</p>
    </div>
    <div class="container">
        <div class="stats-panel">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-jobs">0</div>
                    <div class="stat-label">Total de Vagas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-companies">0</div>
                    <div class="stat-label">Empresas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-locations">0</div>
                    <div class="stat-label">Localizações</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{self.formatted_date}</div>
                    <div class="stat-label">Última Atualização</div>
                </div>
            </div>
            <h3 style="color: #2c3e50; margin-top: 30px; margin-bottom: 15px;">🏢 Empresas Monitoradas</h3>
            <div class="companies-container">
                <div class="companies-legend" id="companies-legend">
                    <!-- Companies will be inserted dynamically -->
                </div>
            </div>
        </div>
        <div id="map"></div>
    </div>
    <div class="footer">
        <p>Sistema de BI - Extração de Vagas MS | Atualizado em {self.full_datetime}</p>
        <p>📍 Clique nos marcadores para ver vagas agrupadas por localização</p>
        <p>🏢 Dados reais extraídos dos sistemas das empresas</p>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
    <script>
        const clusteredData = {clustered_data_json};
        // Configuração do mapa
        const map = L.map('map').setView([-20.4697, -54.6201], 7);
        // Adiciona camada do mapa
        L.tileLayer('https://{ s} .tile.openstreetmap.org/{ z} /{ x} /{ y} .png', { 
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        } ).addTo(map);
        // Cria grupo de marcadores com clustering
        const markers = L.markerClusterGroup({ 
            iconCreateFunction: function(cluster) { 
                const count = cluster.getChildCount();
                let size = 'small';
                if (count >= 10) size = 'large';
                else if (count >= 5) size = 'medium';
                return L.divIcon({ 
                    html: '<div style="background: rgba(52, 152, 219, 0.8); border: 3px solid white; border-radius: 50%; color: white; font-weight: bold; text-align: center; display: flex; align-items: center; justify-content: center; box-shadow: 0 3px 10px rgba(0,0,0,0.3);">' + count + '</div>',
                    className: 'marker-cluster marker-cluster-' + size,
                    iconSize: [40, 40]
                } );
            } ,
            maxClusterRadius: 50
        } );
        // Estatísticas
        let totalJobs = 0;
        let totalLocations = Object.keys(clusteredData).length;
        // Função para criar popup de localização
        function createLocationPopup(location) { 
            let popupContent = '<div class="cluster-popup">';
            popupContent += '<div class="location-title">' + location.location_name + '</div>';
            Object.keys(location.companies).forEach(companyName => { 
                const company = location.companies[companyName];
                popupContent += '<div class="company-section" style="border-left-color: ' + company.color + ';">';
                popupContent += '<div class="company-header" style="color: ' + company.color + ';">';
                popupContent += company.icon + ' ' + companyName + ' (' + company.jobs.length + ' vagas)';
                popupContent += '</div>';
                company.jobs.forEach(job => { 
                    popupContent += '<div class="job-item" style="border-left-color: ' + company.color + ';">';
                    popupContent += '<div class="job-title">' + job.titulo + '</div>';
                    popupContent += '<div class="job-details">';
                    popupContent += '📍 ' + job.localizacao + '<br>';
                    if (job.tipo_contrato) popupContent += '📄 ' + job.tipo_contrato + '<br>';
                    if (job.salario) popupContent += '💰 ' + job.salario;
                    popupContent += '</div>';
                    if (job.link) { 
                        popupContent += '<a href="' + job.link + '" target="_blank" class="job-link-button">🔗 Ver Vaga</a>';
                    } 
                    popupContent += '</div>';
                } );
                popupContent += '</div>';
            } );
            popupContent += '</div>';
            return popupContent;
        } 
        // Processa cada localização
        Object.keys(clusteredData).forEach(locationKey => { 
            const location = clusteredData[locationKey];
            totalJobs += location.total_jobs;
            // Cria popup com informações detalhadas
            const popupContent = createLocationPopup(location);
            // Determina ícone principal baseado na empresa com mais vagas
            let mainCompany = null;
            let maxJobs = 0;
            Object.keys(location.companies).forEach(companyName => { 
                const companyJobs = location.companies[companyName].jobs.length;
                if (companyJobs > maxJobs) { 
                    maxJobs = companyJobs;
                    mainCompany = location.companies[companyName];
                } 
            } );
            // Cria marcador principal
            const mainIcon = L.divIcon({ 
                html: '<div style="background: ' + mainCompany.color + '; border: 3px solid white; border-radius: 50%; color: white; font-weight: bold; text-align: center; display: flex; align-items: center; justify-content: center; box-shadow: 0 3px 10px rgba(0,0,0,0.3); font-size: 18px; width: 35px; height: 35px;">' + mainCompany.icon + '</div>',
                className: 'company-marker',
                iconSize: [35, 35],
                iconAnchor: [17, 35]
            } );
            const marker = L.marker([location.lat, location.lng], {  icon: mainIcon } );
            marker.bindPopup(popupContent, { 
                maxWidth: 500,
                maxHeight: 600
            } );
            markers.addLayer(marker);
        } );
        // Adiciona grupo de marcadores ao mapa
        map.addLayer(markers);
        // Atualiza estatísticas
        document.getElementById('total-jobs').textContent = totalJobs;
        document.getElementById('total-companies').textContent = Object.values(clusteredData).reduce((acc, location) => { 
            return acc + Object.keys(location.companies).length;
        } , 0);
        document.getElementById('total-locations').textContent = totalLocations;
        // Gera legenda de empresas
        const companiesLegend = document.getElementById('companies-legend');
        const allCompanies = { } ;
        Object.values(clusteredData).forEach(location => { 
            Object.keys(location.companies).forEach(companyName => { 
                const company = location.companies[companyName];
                if (!allCompanies[companyName]) { 
                    allCompanies[companyName] = { 
                        color: company.color,
                        icon: company.icon,
                        description: company.description || 'Empresa parceira',
                        totalJobs: 0
                    } ;
                } 
                allCompanies[companyName].totalJobs += company.jobs.length;
            } );
        } );
        Object.keys(allCompanies).sort().forEach(companyName => { 
            const company = allCompanies[companyName];
            const companyElement = document.createElement('div');
            companyElement.className = 'company-item';
            companyElement.innerHTML = `
                <div class="company-icon" style="background: ${ company.color} ;"></div>
                <div class="company-info">
                    <div class="company-name">${ company.icon}  ${ companyName}  (${ company.totalJobs} )</div>
                    <div class="company-desc">${ company.description} </div>
                </div>
            `;
            companiesLegend.appendChild(companyElement);
        } );
        console.log('BI Mapa MS carregado com sucesso!');
        console.log('Total de vagas:', totalJobs);
        console.log('Total de localizações:', totalLocations);
    </script>
</body>
</html>'''
        return html_template
    def export_map(self):
        if not self.current_map_file or not self.current_map_file.exists():
            messagebox.showwarning("Aviso", "Gere o mapa primeiro antes de exportar.")
            return
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".html",
                filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
                title="Exportar Mapa BI"
            )
            if filename:
                import shutil
                shutil.copy2(self.current_map_file, filename)
                messagebox.showinfo("Sucesso", f"Mapa exportado para: {filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar: {e}")
    def update_info_display(self):
        try:
            info_lines = []
            info_lines.append("🎯 BI VAGAS MS - STATUS DO SISTEMA")
            info_lines.append("=" * 50)
            info_lines.append("")
            if self.jobs_data:
                total_jobs = len(self.jobs_data)
                cities = set(job.get('cidade', 'N/A') for job in self.jobs_data)
                companies = set(job.get('empresa', 'N/A') for job in self.jobs_data)
                info_lines.append(f"📊 Total de vagas carregadas: {total_jobs}")
                info_lines.append(f"🏢 Empresas encontradas: {len(companies)}")
                info_lines.append(f"🏙️ Cidades: {len(cities)}")
                info_lines.append("")
                if self.processed_jobs:
                    processed_total = sum(len(jobs) for jobs in self.processed_jobs.values())
                    info_lines.append(f"✅ Vagas processadas: {processed_total}")
                    info_lines.append(f"📍 Clusters de localização: {len(self.clustered_locations)}")
                    info_lines.append("")
            else:
                info_lines.append("📭 Nenhuma vaga carregada")
                info_lines.append("")
            info_lines.append(f"🕒 Data de atualização: {self.formatted_date}")
            info_lines.append(f"⏰ Horário: {self.full_datetime}")
            info_lines.append("")
            info_lines.append("🚀 Clique em 'Gerar Mapa BI' para criar o mapa interativo")
            self.info_text.delete("1.0", "end")
            self.info_text.insert("1.0", "\n".join(info_lines))
        except Exception as e:
            logger.error(f"Error updating info display: {e}")
    def open_map_in_browser(self):
        if self.current_map_file and self.current_map_file.exists():
            webbrowser.open(f"file://{self.current_map_file.absolute()}")
        else:
            messagebox.showwarning("Aviso", "Gere o mapa primeiro.")