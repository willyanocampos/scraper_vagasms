import sys
import os
import json
import logging
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
try:
    import geopandas as gpd
    import pandas as pd
    from collections import defaultdict
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    logging.warning("GeoPandas não encontrado. Usando fallback para matplotlib básico.")
from enhanced_filters import EnhancedJobFilter
from accurate_ms_map_data import AccurateMSMapData
from interactive_map_widget import InteractiveMapWidget
if sys.platform.startswith('win'):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
class DataManager:
    def __init__(self):
        self.jobs_data: List[Dict] = []
        self.summary_data: Dict = {}
        self.last_update: Optional[datetime] = None
        self.data_callbacks: List = []
        self.current_source_file: Optional[str] = None
        self.enhanced_filter = EnhancedJobFilter()
        self.map_data = AccurateMSMapData()
    def add_callback(self, callback):
        self.data_callbacks.append(callback)
    def notify_callbacks(self):
        for callback in self.data_callbacks:
            try:
                import inspect
                sig = inspect.signature(callback)
                if len(sig.parameters) > 0:
                    callback(self.jobs_data)
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    def load_data(self) -> bool:
        try:
            output_dir = Path("output")
            logger.info(f"Looking for data files in: {output_dir.absolute()}")
            if not output_dir.exists():
                logger.warning("Output directory not found, creating it...")
                output_dir.mkdir(exist_ok=True)
            json_files = list(output_dir.glob("unified_ms_jobs_*.json")) + list(output_dir.glob("ms_jobs_*.json"))
            csv_files = list(output_dir.glob("unified_ms_jobs_*.csv")) + list(output_dir.glob("ms_jobs_*.csv"))
            logger.info(f"Found {len(json_files)} JSON files and {len(csv_files)} CSV files")
            if json_files:
                latest_json = max(json_files, key=lambda x: x.stat().st_mtime)
                logger.info(f"Using latest JSON file: {latest_json.name}")
                return self._load_from_json(latest_json)
            elif csv_files:
                latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
                logger.info(f"Using latest CSV file: {latest_csv.name}")
                return self._load_from_csv(latest_csv)
            else:
                logger.warning("No output files found, trying frontend data...")
                return self._load_from_frontend_data()
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.jobs_data = []
            self.summary_data = {}
            return False
    def _load_from_json(self, json_file: Path) -> bool:
        try:
            logger.info(f"Loading from JSON: {json_file.name}")
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'jobs' in data:
                self.jobs_data = data['jobs']
                if 'extraction_info' in data:
                    timestamp_str = data['extraction_info'].get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                        self.last_update = timestamp
                    except:
                        self.last_update = datetime.now()
                else:
                    self.last_update = datetime.fromtimestamp(json_file.stat().st_mtime)
            elif isinstance(data, list):
                self.jobs_data = data
                self.last_update = datetime.fromtimestamp(json_file.stat().st_mtime)
            else:
                logger.warning(f"Unexpected data format in {json_file.name}")
                self.jobs_data = []
                self.last_update = datetime.now()
            self.jobs_data = self._process_jobs_for_map_compatibility(self.jobs_data)
            self.enhanced_filter.set_jobs_data(self.jobs_data)
            self.summary_data = self._generate_summary()
            self.current_source_file = str(json_file)
            logger.info(f"Loaded {len(self.jobs_data)} jobs from JSON")
            self.notify_callbacks()
            return True
        except Exception as e:
            logger.error(f"Error loading JSON file: {e}")
            return False
    def _load_from_csv(self, csv_file: Path) -> bool:
        try:
            logger.info(f"Loading from CSV: {csv_file.name}")
            try:
                import pandas as pd
            except ImportError:
                logger.warning("pandas not available, trying manual CSV parsing")
                return self._load_csv_manual(csv_file)
            df = pd.read_csv(csv_file, encoding='utf-8')
            raw_jobs_data = df.to_dict('records')
            self.jobs_data = self._process_jobs_for_map_compatibility(raw_jobs_data)
            self.last_update = datetime.fromtimestamp(csv_file.stat().st_mtime)
            self.summary_data = self._generate_summary()
            self.current_source_file = str(csv_file)
            logger.info(f"Loaded {len(self.jobs_data)} jobs from CSV")
            self.notify_callbacks()
            return True
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            return False
    def _load_csv_manual(self, csv_file: Path) -> bool:
        try:
            import csv
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                raw_jobs_data = list(reader)
            self.jobs_data = self._process_jobs_for_map_compatibility(raw_jobs_data)
            self.last_update = datetime.fromtimestamp(csv_file.stat().st_mtime)
            self.summary_data = self._generate_summary()
            self.current_source_file = str(csv_file)
            logger.info(f"Loaded {len(self.jobs_data)} jobs from CSV (manual parsing)")
            self.notify_callbacks()
            return True
        except Exception as e:
            logger.error(f"Error with manual CSV parsing: {e}")
            return False
    def _load_from_frontend_data(self) -> bool:
        try:
            print("📄 Fallback: Loading from frontend/data/jobs.json")
            jobs_file = Path("frontend/data/jobs.json")
            if not jobs_file.exists():
                print("❌ No data files found")
                return False
            with open(jobs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                raw_jobs_data = data.get('jobs', [])
                self.jobs_data = self._process_jobs_for_map_compatibility(raw_jobs_data)
                self.last_update = datetime.fromisoformat(data.get('lastUpdate', datetime.now().isoformat()))
            self.summary_data = self._generate_summary()
            self.current_source_file = str(jobs_file)
            print(f"✅ Loaded {len(self.jobs_data)} jobs from frontend data")
            self.notify_callbacks()
            return True
        except Exception as e:
            print(f"❌ Error loading frontend data: {e}")
            return False
    def _process_jobs_for_map_compatibility(self, jobs_data: List[Dict]) -> List[Dict]:
        if not jobs_data:
            return jobs_data
        logger.info("Processing jobs for map compatibility...")
        city_mappings = {
            'campo grande': 'Campo Grande',
            'dourados': 'Dourados',
            'tres lagoas': 'Três Lagoas',
            'corumba': 'Corumbá',
            'ponta pora': 'Ponta Porã',
            'aquidauana': 'Aquidauana',
            'coxim': 'Coxim',
            'naviraí': 'Naviraí',
            'nova andradina': 'Nova Andradina',
            'paranaíba': 'Paranaíba'
        }
        city_coordinates = {
            'Campo Grande': {'latitude': -20.4697, 'longitude': -54.6201},
            'Dourados': {'latitude': -22.2211, 'longitude': -54.8056},
            'Três Lagoas': {'latitude': -20.7511, 'longitude': -51.6783},
            'Corumbá': {'latitude': -19.0078, 'longitude': -57.6547},
            'Ponta Porã': {'latitude': -22.5367, 'longitude': -55.7258},
            'Aquidauana': {'latitude': -20.4714, 'longitude': -55.7858},
            'Coxim': {'latitude': -18.5067, 'longitude': -54.7600},
            'Naviraí': {'latitude': -23.0650, 'longitude': -54.1892},
            'Nova Andradina': {'latitude': -22.2383, 'longitude': -53.3428},
            'Paranaíba': {'latitude': -19.6761, 'longitude': -51.1906}
        }
        processed_jobs = []
        fixed_count = 0
        for job in jobs_data:
            processed_job = job.copy()
            cidade = str(job.get('cidade', '')).strip()
            if not cidade or cidade.lower() in ['', 'n/a', 'nan', 'none', 'null']:
                localizacao = str(job.get('localizacao_completa', '')).strip()
                if localizacao:
                    for key, mapped_city in city_mappings.items():
                        if key in localizacao.lower():
                            processed_job['cidade'] = mapped_city
                            cidade = mapped_city
                            fixed_count += 1
                            break
                if not cidade or cidade.lower() in ['', 'n/a', 'nan', 'none', 'null']:
                    processed_job['cidade'] = 'Campo Grande'
                    cidade = 'Campo Grande'
                    fixed_count += 1
            else:
                cidade_lower = cidade.lower()
                if cidade_lower in city_mappings:
                    processed_job['cidade'] = city_mappings[cidade_lower]
                    cidade = city_mappings[cidade_lower]
            if not job.get('latitude') or not job.get('longitude'):
                if cidade in city_coordinates:
                    coords = city_coordinates[cidade]
                    processed_job['latitude'] = coords['latitude']
                    processed_job['longitude'] = coords['longitude']
                else:
                    processed_job['latitude'] = city_coordinates['Campo Grande']['latitude']
                    processed_job['longitude'] = city_coordinates['Campo Grande']['longitude']
            processed_jobs.append(processed_job)
        if fixed_count > 0:
            logger.info(f"Fixed {fixed_count} jobs with missing/invalid city data")
        return processed_jobs
    def _generate_summary(self) -> Dict:
        if not self.jobs_data:
            return {}
        cities = {}
        companies = {}
        sectors = {}
        for job in self.jobs_data:
            city = job.get('cidade', 'Unknown')
            company = job.get('empresa', 'Unknown')
            sector = job.get('setor', 'Unknown')
            cities[city] = cities.get(city, 0) + 1
            companies[company] = companies.get(company, 0) + 1
            sectors[sector] = sectors.get(sector, 0) + 1
        return {
            'totalJobs': len(self.jobs_data),
            'cities': cities,
            'companies': companies,
            'sectors': sectors,
            'lastUpdate': self.last_update.isoformat() if self.last_update else datetime.now().isoformat()
        }
    def get_filtered_jobs(self, filters: Dict) -> List[Dict]:
        self.enhanced_filter.set_jobs_data(self.jobs_data)
        return self.enhanced_filter.apply_filters(filters)
class MSJobsDesktop(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")
        self.data_manager = DataManager()
        self.data_manager.add_callback(self.on_data_updated)
        self.title("MS Jobs Desktop - Dashboard de Vagas")
        self.geometry("1200x800")
        self.minsize(800, 600)
        icon_path = Path("frontend/ms-jobs-dashboard/public/vite.svg")
        if icon_path.exists():
            try:
                icon = tk.PhotoImage(file=str(icon_path))
                self.iconphoto(True, icon)
            except:
                pass
        self.create_widgets()
        self.load_data()
    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.create_header()
        self.create_main_content()
        self.create_status_bar()
    def create_header(self):
        header_frame = ctk.CTkFrame(self, height=60)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(1, weight=1)
        title_label = ctk.CTkLabel(
            header_frame, 
            text="🏢 MS Jobs Desktop",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        controls_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=2, padx=20, pady=10, sticky="e")
        self.refresh_btn = ctk.CTkButton(
            controls_frame,
            text="🔄 Atualizar",
            command=self.load_data,
            width=100
        )
        self.refresh_btn.grid(row=0, column=0, padx=5)
        self.theme_btn = ctk.CTkButton(
            controls_frame,
            text="🌙 Tema",
            command=self.toggle_theme,
            width=80
        )
        self.theme_btn.grid(row=0, column=1, padx=5)
    def create_main_content(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.dashboard_tab = self.tabview.add("📊 Dashboard")
        self.jobs_tab = self.tabview.add("💼 Vagas")
        self.companies_tab = self.tabview.add("🏢 Empresas")
        self.map_tab = self.tabview.add("🗺️ Mapa")
        self.analytics_tab = self.tabview.add("📈 Analytics")
        self.settings_tab = self.tabview.add("⚙️ Configurações")
        self.create_dashboard_tab()
        self.create_jobs_tab()
        self.create_companies_tab()
        self.create_map_tab()
        self.create_analytics_tab()
        self.create_settings_tab()
    def create_dashboard_tab(self):
        self.dashboard_tab.grid_columnconfigure((0, 1), weight=1)
        self.dashboard_tab.grid_rowconfigure((1, 2), weight=1)
        stats_frame = ctk.CTkFrame(self.dashboard_tab)
        stats_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.total_jobs_card = self.create_stat_card(stats_frame, "💼", "Total de Vagas", "0", 0)
        self.cities_card = self.create_stat_card(stats_frame, "🏙️", "Cidades", "0", 1)
        self.companies_card = self.create_stat_card(stats_frame, "🏢", "Empresas", "0", 2)
        self.sectors_card = self.create_stat_card(stats_frame, "🏭", "Setores", "0", 3)
        charts_frame = ctk.CTkFrame(self.dashboard_tab)
        charts_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)
        chart_label = ctk.CTkLabel(charts_frame, text="📈 Distribuição por Cidade", 
                                 font=ctk.CTkFont(size=16, weight="bold"))
        chart_label.pack(pady=10)
        self.cities_scrollable = ctk.CTkScrollableFrame(charts_frame)
        self.cities_scrollable.pack(fill="both", expand=True, padx=10, pady=10)
        updates_frame = ctk.CTkFrame(self.dashboard_tab)
        updates_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)
        updates_label = ctk.CTkLabel(updates_frame, text="🕒 Última Atualização", 
                                   font=ctk.CTkFont(size=16, weight="bold"))
        updates_label.pack(pady=10)
        self.last_update_label = ctk.CTkLabel(updates_frame, text="Carregando...", 
                                            font=ctk.CTkFont(size=12))
        self.last_update_label.pack(pady=5)
        top_companies_label = ctk.CTkLabel(updates_frame, text="🏆 Top Empresas", 
                                         font=ctk.CTkFont(size=14, weight="bold"))
        top_companies_label.pack(pady=(20, 10))
        self.top_companies_frame = ctk.CTkScrollableFrame(updates_frame, height=200)
        self.top_companies_frame.pack(fill="x", padx=10, pady=10)
    def create_stat_card(self, parent, icon, title, value, column):
        card_frame = ctk.CTkFrame(parent)
        card_frame.grid(row=0, column=column, sticky="ew", padx=5, pady=10)
        icon_label = ctk.CTkLabel(card_frame, text=icon, font=ctk.CTkFont(size=24))
        icon_label.pack(pady=(10, 0))
        title_label = ctk.CTkLabel(card_frame, text=title, font=ctk.CTkFont(size=12))
        title_label.pack()
        value_label = ctk.CTkLabel(card_frame, text=value, font=ctk.CTkFont(size=20, weight="bold"))
        value_label.pack(pady=(0, 10))
        return value_label
    def create_jobs_tab(self):
        self.jobs_tab.grid_columnconfigure(0, weight=1)
        self.jobs_tab.grid_rowconfigure(1, weight=1)
        filters_frame = ctk.CTkFrame(self.jobs_tab, height=100)
        filters_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        filters_frame.grid_columnconfigure((1, 3, 5), weight=1)
        ctk.CTkLabel(filters_frame, text="🔍 Buscar:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.search_entry = ctk.CTkEntry(filters_frame, placeholder_text="Digite título, empresa ou cidade...")
        self.search_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_filter_change)
        ctk.CTkLabel(filters_frame, text="🏙️ Cidade:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        self.city_combo = ctk.CTkComboBox(filters_frame, values=["Todas"], command=self.on_filter_change)
        self.city_combo.grid(row=0, column=3, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(filters_frame, text="🏭 Setor:").grid(row=0, column=4, padx=10, pady=10, sticky="w")
        self.sector_combo = ctk.CTkComboBox(filters_frame, values=["Todos"], command=self.on_filter_change)
        self.sector_combo.grid(row=0, column=5, padx=10, pady=10, sticky="ew")
        self.remote_var = ctk.BooleanVar()
        self.remote_check = ctk.CTkCheckBox(filters_frame, text="💻 Apenas remoto", 
                                          variable=self.remote_var, command=self.on_filter_change)
        self.remote_check.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="w")
        self.jobs_scrollable = ctk.CTkScrollableFrame(self.jobs_tab)
        self.jobs_scrollable.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.jobs_scrollable.grid_columnconfigure(0, weight=1)
    def create_companies_tab(self):
        self.companies_tab.grid_columnconfigure(0, weight=1)
        self.companies_tab.grid_rowconfigure(1, weight=1)
        header_label = ctk.CTkLabel(self.companies_tab, text="🏢 Empresas Monitoradas", 
                                  font=ctk.CTkFont(size=20, weight="bold"))
        header_label.grid(row=0, column=0, pady=20)
        self.companies_scrollable = ctk.CTkScrollableFrame(self.companies_tab)
        self.companies_scrollable.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.companies_scrollable.grid_columnconfigure(0, weight=1)
    def create_settings_tab(self):
        self.settings_tab.grid_columnconfigure(0, weight=1)
        export_frame = ctk.CTkFrame(self.settings_tab)
        export_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        export_frame.grid_columnconfigure(1, weight=1)
        export_label = ctk.CTkLabel(export_frame, text="📤 Exportar Dados", 
                                  font=ctk.CTkFont(size=16, weight="bold"))
        export_label.grid(row=0, column=0, columnspan=2, pady=15)
        export_csv_btn = ctk.CTkButton(export_frame, text="📊 Exportar CSV", 
                                     command=self.export_csv, width=150)
        export_csv_btn.grid(row=1, column=0, padx=10, pady=10)
        export_excel_btn = ctk.CTkButton(export_frame, text="📈 Exportar Excel", 
                                       command=self.export_excel, width=150)
        export_excel_btn.grid(row=1, column=1, padx=10, pady=10)
        export_report_btn = ctk.CTkButton(export_frame, text="📄 Relatório PDF", 
                                        command=self.export_analytics_report, width=150)
        export_report_btn.grid(row=2, column=0, columnspan=2, padx=10, pady=10)
        info_frame = ctk.CTkFrame(self.settings_tab)
        info_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        info_label = ctk.CTkLabel(info_frame, text="ℹ️ Informações dos Dados", 
                                font=ctk.CTkFont(size=16, weight="bold"))
        info_label.grid(row=0, column=0, pady=15)
        self.data_info_text = ctk.CTkTextbox(info_frame, height=200)
        self.data_info_text.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.update_data_info()
        refresh_frame = ctk.CTkFrame(self.settings_tab)
        refresh_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        refresh_label = ctk.CTkLabel(refresh_frame, text="🔄 Atualização Manual", 
                                   font=ctk.CTkFont(size=16, weight="bold"))
        refresh_label.grid(row=0, column=0, pady=15)
        manual_refresh_btn = ctk.CTkButton(refresh_frame, 
                                         text="🔄 Atualizar Dados",
                                         command=self.load_data,
                                         width=200,
                                         height=36)
        manual_refresh_btn.grid(row=1, column=0, padx=10, pady=10)
    def create_map_tab(self):
        self.map_tab.grid_columnconfigure(0, weight=1)
        self.map_tab.grid_rowconfigure(1, weight=1)
        header_frame = ctk.CTkFrame(self.map_tab, height=60)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header_frame.grid_columnconfigure(1, weight=1)
        map_title = ctk.CTkLabel(header_frame, text="🗺️ Mapa de Vagas - Mato Grosso do Sul", 
                               font=ctk.CTkFont(size=18, weight="bold"))
        map_title.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        controls_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=1, padx=20, pady=10, sticky="e")
        self.map_refresh_btn = ctk.CTkButton(controls_frame, text="🔄 Atualizar Mapa", 
                                           command=self.update_map, width=120)
        self.map_refresh_btn.grid(row=0, column=0, padx=5)
        self.map_frame = ctk.CTkFrame(self.map_tab)
        self.map_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.create_ms_map()
    def create_analytics_tab(self):
        self.analytics_tab.grid_columnconfigure((0, 1), weight=1)
        self.analytics_tab.grid_rowconfigure((0, 1), weight=1)
        sector_frame = ctk.CTkFrame(self.analytics_tab)
        sector_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        sector_label = ctk.CTkLabel(sector_frame, text="📊 Distribuição por Setor", 
                                  font=ctk.CTkFont(size=16, weight="bold"))
        sector_label.pack(pady=10)
        contract_frame = ctk.CTkFrame(self.analytics_tab)
        contract_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        contract_label = ctk.CTkLabel(contract_frame, text="📄 Tipos de Contrato", 
                                    font=ctk.CTkFont(size=16, weight="bold"))
        contract_label.pack(pady=10)
        city_frame = ctk.CTkFrame(self.analytics_tab)
        city_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=10)
        city_label = ctk.CTkLabel(city_frame, text="🏙️ Top 10 Cidades", 
                                font=ctk.CTkFont(size=16, weight="bold"))
        city_label.pack(pady=10)
        remote_frame = ctk.CTkFrame(self.analytics_tab)
        remote_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=10)
        remote_label = ctk.CTkLabel(remote_frame, text="💻 Trabalho Remoto", 
                                  font=ctk.CTkFont(size=16, weight="bold"))
        remote_label.pack(pady=10)
        self.chart_frames = {
            'sector': sector_frame,
            'contract': contract_frame,
            'city': city_frame,
            'remote': remote_frame
        }
        self.create_analytics_charts()
    def create_status_bar(self):
        self.status_frame = ctk.CTkFrame(self, height=30)
        self.status_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        self.status_frame.grid_columnconfigure(1, weight=1)
        self.status_label = ctk.CTkLabel(self.status_frame, text="✅ Pronto", 
                                       font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.jobs_count_label = ctk.CTkLabel(self.status_frame, text="0 vagas carregadas", 
                                           font=ctk.CTkFont(size=12))
        self.jobs_count_label.grid(row=0, column=2, padx=10, pady=5, sticky="e")
    def load_data(self):
        def load():
            self.set_status("🔄 Carregando dados...")
            success = self.data_manager.load_data()
            if success:
                self.set_status("✅ Dados carregados com sucesso")
            else:
                self.set_status("❌ Erro ao carregar dados")
        threading.Thread(target=load, daemon=True).start()
    def on_data_updated(self):
        self.after(0, self.update_ui)
    def update_ui(self):
        try:
            self.update_dashboard()
            self.update_filters()
            self.update_jobs_list()
            self.update_companies_list()
            self.update_map()
            self.update_analytics_charts()
            self.update_data_info()
            self.jobs_count_label.configure(text=f"{len(self.data_manager.jobs_data)} vagas carregadas")
        except Exception as e:
            print(f"Error updating UI: {e}")
    def update_dashboard(self):
        summary = self.data_manager.summary_data
        self.total_jobs_card.configure(text=str(summary.get('totalJobs', 0)))
        self.cities_card.configure(text=str(len(summary.get('cities', {}))))
        self.companies_card.configure(text=str(len(summary.get('companies', {}))))
        self.sectors_card.configure(text=str(len(summary.get('sectors', {}))))
        if self.data_manager.last_update:
            update_text = self.data_manager.last_update.strftime("%d/%m/%Y às %H:%M")
            self.last_update_label.configure(text=update_text)
        try:
            for widget in self.cities_scrollable.winfo_children():
                widget.destroy()
        except Exception as e:
            print(f"Error clearing cities list: {e}")
        cities = summary.get('cities', {})
        for city, count in sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10]:
            city_frame = ctk.CTkFrame(self.cities_scrollable)
            city_frame.pack(fill="x", padx=5, pady=2)
            city_label = ctk.CTkLabel(city_frame, text=city, anchor="w")
            city_label.pack(side="left", padx=10, pady=5)
            count_label = ctk.CTkLabel(city_frame, text=str(count), 
                                     font=ctk.CTkFont(weight="bold"))
            count_label.pack(side="right", padx=10, pady=5)
        try:
            for widget in self.top_companies_frame.winfo_children():
                widget.destroy()
        except Exception as e:
            print(f"Error clearing companies list: {e}")
        companies = summary.get('companies', {})
        for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]:
            company_frame = ctk.CTkFrame(self.top_companies_frame)
            company_frame.pack(fill="x", padx=5, pady=2)
            company_label = ctk.CTkLabel(company_frame, text=company[:30] + "..." if len(company) > 30 else company, 
                                       anchor="w")
            company_label.pack(side="left", padx=10, pady=5)
            count_label = ctk.CTkLabel(company_frame, text=str(count), 
                                     font=ctk.CTkFont(weight="bold"))
            count_label.pack(side="right", padx=10, pady=5)
    def update_filters(self):
        try:
            self.data_manager.enhanced_filter.set_jobs_data(self.data_manager.jobs_data)
            filter_options = self.data_manager.enhanced_filter.get_filter_options()
            self.city_combo.configure(values=filter_options.get('cities', ['Todas']))
            self.sector_combo.configure(values=filter_options.get('sectors', ['Todos']))
        except Exception as e:
            print(f"Error updating filters: {e}")
            summary = self.data_manager.summary_data
            cities = ["Todas"] + sorted(summary.get('cities', {}).keys())
            sectors = ["Todos"] + sorted(summary.get('sectors', {}).keys())
            self.city_combo.configure(values=cities)
            self.sector_combo.configure(values=sectors)
    def update_jobs_list(self):
        try:
            for widget in self.jobs_scrollable.winfo_children():
                widget.destroy()
            filters = self.get_current_filters()
            jobs = self.data_manager.get_filtered_jobs(filters)
            if not jobs:
                no_jobs_label = ctk.CTkLabel(self.jobs_scrollable, 
                                           text="📭 Nenhuma vaga encontrada", 
                                           font=ctk.CTkFont(size=16))
                no_jobs_label.pack(pady=50)
                return
        except Exception as e:
            print(f"Error updating jobs list: {e}")
            return
        for i, job in enumerate(jobs[:50]):
            job_frame = ctk.CTkFrame(self.jobs_scrollable)
            job_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            job_frame.grid_columnconfigure(1, weight=1)
            title_label = ctk.CTkLabel(job_frame, text=job.get('titulo', 'N/A'), 
                                     font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
            title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 2))
            company_label = ctk.CTkLabel(job_frame, text=f"🏢 {job.get('empresa', 'N/A')}", 
                                       font=ctk.CTkFont(size=12), anchor="w")
            company_label.grid(row=1, column=0, sticky="w", padx=10, pady=2)
            location_text = f"📍 {job.get('cidade', 'N/A')}"
            if job.get('trabalho_remoto'):
                location_text += " (Remoto)"
            location_label = ctk.CTkLabel(job_frame, text=location_text, 
                                        font=ctk.CTkFont(size=12), anchor="w")
            location_label.grid(row=1, column=1, sticky="w", padx=10, pady=2)
            details_text = f"🏭 {job.get('setor', 'N/A')} • 📄 {job.get('tipo_contrato', 'N/A')}"
            details_label = ctk.CTkLabel(job_frame, text=details_text, 
                                       font=ctk.CTkFont(size=11), anchor="w")
            details_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 10))
            buttons_frame = ctk.CTkFrame(job_frame, fg_color="transparent")
            buttons_frame.grid(row=0, column=2, rowspan=3, padx=10, pady=5, sticky="ns")
            if job.get('link'):
                apply_btn = ctk.CTkButton(buttons_frame, text="🔗 Candidatar", 
                                        command=lambda url=job['link']: self.open_job_link(url),
                                        width=100, height=25)
                apply_btn.pack(pady=2)
            details_btn = ctk.CTkButton(buttons_frame, text="📝 Detalhes", 
                                      command=lambda j=job: self.show_job_details(j),
                                      width=100, height=25)
            details_btn.pack(pady=2)
    def update_companies_list(self):
        try:
            for widget in self.companies_scrollable.winfo_children():
                widget.destroy()
        except Exception as e:
            print(f"Error clearing companies scrollable: {e}")
        summary = self.data_manager.summary_data
        companies = summary.get('companies', {})
        for i, (company, count) in enumerate(sorted(companies.items(), key=lambda x: x[1], reverse=True)):
            company_frame = ctk.CTkFrame(self.companies_scrollable)
            company_frame.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            company_frame.grid_columnconfigure(1, weight=1)
            name_label = ctk.CTkLabel(company_frame, text=company, 
                                    font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
            name_label.grid(row=0, column=0, sticky="w", padx=15, pady=10)
            info_frame = ctk.CTkFrame(company_frame, fg_color="transparent")
            info_frame.grid(row=0, column=1, sticky="e", padx=15, pady=10)
            count_label = ctk.CTkLabel(info_frame, text=f"{count} vagas", 
                                     font=ctk.CTkFont(size=12))
            count_label.pack(side="left", padx=5)
            view_btn = ctk.CTkButton(info_frame, text="🔍 Ver", 
                                   command=lambda c=company: self.show_company_profile(c),
                                   width=60, height=25)
            view_btn.pack(side="right", padx=5)
    def get_current_filters(self) -> Dict:
        return {
            'search': self.search_entry.get(),
            'city': self.city_combo.get(),
            'sector': self.sector_combo.get(),
            'remote_only': self.remote_var.get()
        }
    def on_filter_change(self, event=None):
        self.update_jobs_list()
    def open_job_link(self, url: str):
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o link: {e}")
    def export_csv(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Exportar para CSV"
            )
            if filename:
                import pandas as pd
                df = pd.DataFrame(self.data_manager.jobs_data)
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                messagebox.showinfo("Sucesso", f"Dados exportados para: {filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar CSV: {e}")
    def export_excel(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Exportar para Excel"
            )
            if filename:
                import pandas as pd
                df = pd.DataFrame(self.data_manager.jobs_data)
                df.to_excel(filename, index=False, engine='openpyxl')
                messagebox.showinfo("Sucesso", f"Dados exportados para: {filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar Excel: {e}")
    def export_analytics_report(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                title="Exportar Relatório de Analytics"
            )
            if filename:
                from matplotlib.backends.backend_pdf import PdfPages
                with PdfPages(filename) as pdf:
                    if hasattr(self, 'map_fig'):
                        pdf.savefig(self.map_fig, bbox_inches='tight')
                    for chart_type, chart_data in self.analytics_charts.items():
                        if 'fig' in chart_data:
                            pdf.savefig(chart_data['fig'], bbox_inches='tight')
                messagebox.showinfo("Sucesso", f"Relatório exportado para: {filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar relatório: {e}")
    def update_data_info(self):
        try:
            if hasattr(self, 'data_info_text'):
                self.data_info_text.delete("1.0", "end")
                info_lines = []
                info_lines.append("📊 INFORMAÇÕES DOS DADOS CARREGADOS")
                info_lines.append("=" * 50)
                info_lines.append("")
                info_lines.append(f"📈 Total de vagas: {len(self.data_manager.jobs_data)}")
                info_lines.append(f"🏢 Empresas únicas: {len(self.data_manager.summary_data.get('companies', {}))}")
                info_lines.append(f"🏙️ Cidades: {len(self.data_manager.summary_data.get('cities', {}))}")
                info_lines.append(f"🏭 Setores: {len(self.data_manager.summary_data.get('sectors', {}))}")
                if self.data_manager.last_update:
                    update_str = self.data_manager.last_update.strftime("%d/%m/%Y às %H:%M:%S")
                    info_lines.append(f"🕒 Última atualização: {update_str}")
                info_lines.append("")
                info_lines.append("📂 FONTE DOS DADOS:")
                output_dir = Path("output")
                if output_dir.exists():
                    json_files = list(output_dir.glob("unified_ms_jobs_*.json")) + list(output_dir.glob("ms_jobs_*.json"))
                    csv_files = list(output_dir.glob("unified_ms_jobs_*.csv")) + list(output_dir.glob("ms_jobs_*.csv"))
                    if json_files:
                        latest_json = max(json_files, key=lambda x: x.stat().st_mtime)
                        info_lines.append(f"✅ JSON: {latest_json.name}")
                        mod_time = datetime.fromtimestamp(latest_json.stat().st_mtime)
                        info_lines.append(f"   📅 Criado: {mod_time.strftime('%d/%m/%Y às %H:%M:%S')}")
                    if csv_files:
                        latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
                        info_lines.append(f"📊 CSV: {latest_csv.name}")
                        mod_time = datetime.fromtimestamp(latest_csv.stat().st_mtime)
                        info_lines.append(f"   📅 Criado: {mod_time.strftime('%d/%m/%Y às %H:%M:%S')}")
                    if not json_files and not csv_files:
                        info_lines.append("⚠️ Nenhum arquivo encontrado em output/")
                        info_lines.append("💡 Execute scraper_gui.py ou run_scraper_windows.bat primeiro")
                else:
                    info_lines.append("❌ Diretório output/ não encontrado")
                info_lines.append("")
                info_lines.append("🔄 Para atualizar os dados:")
                info_lines.append("1. Execute scraper_gui.py (Interface Gráfica)")
                info_lines.append("2. Ou execute run_scraper_windows.bat")
                info_lines.append("3. Clique em 'Atualizar' no cabeçalho")
                self.data_info_text.insert("1.0", "\n".join(info_lines))
        except Exception as e:
            print(f"Error updating data info: {e}")
    def toggle_theme(self):
        current_mode = ctk.get_appearance_mode()
        new_mode = "Light" if current_mode == "Dark" else "Dark"
        ctk.set_appearance_mode(new_mode)
        icon = "☀️" if new_mode == "Light" else "🌙"
        self.theme_btn.configure(text=f"{icon} Tema")
    def set_status(self, message: str):
        try:
            self.after(0, lambda: self._update_status_label(message))
        except Exception as e:
            print(f"Error setting status: {e}")
    def _update_status_label(self, message: str):
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.configure(text=message)
        except Exception as e:
            print(f"Error updating status label: {e}")
    def create_ms_map(self):
        try:
            self.interactive_map = InteractiveMapWidget(self.map_frame)
            self.interactive_map.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
            self.map_frame.grid_columnconfigure(0, weight=1)
            self.map_frame.grid_rowconfigure(0, weight=1)
            self.data_manager.add_callback(self.on_data_updated_for_map)
            if self.data_manager.jobs_data:
                self.interactive_map.update_data(self.data_manager.jobs_data)
            print("✅ Mapa Interativo Folium criado com sucesso")
        except Exception as e:
            print(f"Error creating Interactive map: {e}")
            error_label = ctk.CTkLabel(
                self.map_frame, 
                text=f"⚠️ Erro ao carregar mapa interativo: {e}\nVerifique se o Folium está instalado.",
                font=ctk.CTkFont(size=14),
                wraplength=400
            )
            error_label.pack(expand=True)
    def on_data_updated_for_map(self, jobs_data=None):
        try:
            if hasattr(self, 'interactive_map'):
                if jobs_data is not None:
                    data_reference = jobs_data
                else:
                    data_reference = self.data_manager.jobs_data
                if (hasattr(self, '_last_map_data_size') and 
                    len(data_reference) == self._last_map_data_size):
                    print(f"📍 Mapa já atualizado com {len(data_reference)} vagas")
                    return
                self.after(0, lambda: self._update_map_data_optimized(data_reference))
                self._last_map_data_size = len(data_reference)
                print(f"📍 Mapa interativo preparado com {len(data_reference)} vagas")
        except Exception as e:
            print(f"Error scheduling interactive map update: {e}")
    def _update_map_data_optimized(self, jobs_data):
        try:
            if hasattr(self, 'interactive_map') and jobs_data:
                if hasattr(self.interactive_map, 'current_map_file') and self.interactive_map.current_map_file:
                    try:
                        import os
                        if os.path.exists(self.interactive_map.current_map_file):
                            pass
                    except:
                        pass
                self.interactive_map.update_data(jobs_data)
                print(f"📍 Dados do mapa interativo atualizados com {len(jobs_data)} vagas")
        except Exception as e:
            print(f"Error updating interactive map: {e}")
    def update_map(self):
        try:
            if hasattr(self, 'interactive_map') and self.data_manager.jobs_data:
                import time
                current_time = time.time()
                if (hasattr(self, '_last_manual_update') and 
                    current_time - self._last_manual_update < 2.0):
                    print(f"📍 Mapa update throttled - última atualização muito recente")
                    return
                self._last_manual_update = current_time
                self.on_data_updated_for_map(self.data_manager.jobs_data)
                print(f"📍 Mapa interativo atualizado manualmente com {len(self.data_manager.jobs_data)} vagas")
        except Exception as e:
            print(f"Error updating map: {e}")
    def generate_interactive_map(self):
        try:
            if not self.data_manager.jobs_data:
                messagebox.showinfo(
                    "Informação", 
                    "O mapa em tempo real será atualizado automaticamente quando os dados forem carregados."
                )
                return
            if hasattr(self, 'realtime_map'):
                self.realtime_map.update_data(self.data_manager.jobs_data)
                messagebox.showinfo(
                    "Sucesso",
                    "Mapa em tempo real atualizado com os dados atuais!"
                )
        except Exception as e:
            print(f"Error in legacy map generation: {e}")
            messagebox.showerror("Erro", f"Erro ao atualizar mapa:\n{e}")
    def open_map_in_browser(self):
        try:
            if not self.data_manager.jobs_data:
                messagebox.showwarning("Aviso", "Nenhuma vaga carregada para gerar mapa externo.")
                return
            map_path = self.data_manager.map_generator.generate_interactive_map(
                self.data_manager.jobs_data
            )
            self.data_manager.map_generator.open_map_in_browser(map_path)
        except Exception as e:
            print(f"Error opening external map: {e}")
            messagebox.showerror("Erro", f"Erro ao abrir mapa externo:\n{e}")
    def create_analytics_charts(self):
        self.analytics_charts = {}
        for chart_type, frame in self.chart_frames.items():
            try:
                fig = Figure(figsize=(5, 4), dpi=80, facecolor='white')
                ax = fig.add_subplot(111)
                self.analytics_charts[chart_type] = {'fig': fig, 'ax': ax}
                canvas = FigureCanvasTkAgg(fig, master=frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
                self.analytics_charts[chart_type]['canvas'] = canvas
            except Exception as e:
                print(f"Error creating {chart_type} chart: {e}")
                error_label = ctk.CTkLabel(frame, text=f"Gráfico {chart_type} indisponível")
                error_label.pack(expand=True)
    def update_analytics_charts(self):
        if not self.data_manager.jobs_data or not hasattr(self, 'analytics_charts'):
            return
        try:
            self.update_sector_chart()
            self.update_contract_chart()
            self.update_city_chart()
            self.update_remote_chart()
        except Exception as e:
            print(f"Error updating analytics charts: {e}")
    def update_sector_chart(self):
        if 'sector' not in self.analytics_charts:
            return
        ax = self.analytics_charts['sector']['ax']
        ax.clear()
        sectors = {}
        for job in self.data_manager.jobs_data:
            sector = job.get('setor', 'Não informado')
            sectors[sector] = sectors.get(sector, 0) + 1
        if sectors:
            top_sectors = dict(sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:8])
            colors = plt.cm.Set3(np.linspace(0, 1, len(top_sectors)))
            wedges, texts, autotexts = ax.pie(top_sectors.values(), labels=top_sectors.keys(), 
                                            autopct='%1.1f%%', colors=colors, startangle=90)
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(8)
                autotext.set_weight('bold')
            for text in texts:
                text.set_fontsize(8)
        ax.set_title('Distribuição por Setor', fontsize=10, fontweight='bold')
        self.analytics_charts['sector']['canvas'].draw()
    def update_contract_chart(self):
        if 'contract' not in self.analytics_charts:
            return
        ax = self.analytics_charts['contract']['ax']
        ax.clear()
        contracts = {}
        for job in self.data_manager.jobs_data:
            contract = job.get('tipo_contrato', 'Não informado')
            contracts[contract] = contracts.get(contract, 0) + 1
        if contracts:
            contract_types = list(contracts.keys())
            counts = list(contracts.values())
            bars = ax.bar(range(len(contract_types)), counts, 
                         color=['#2E8B57', '#4169E1', '#FF6347', '#32CD32', '#FF1493'][:len(contract_types)])
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                       f'{count}', ha='center', va='bottom', fontsize=8)
            ax.set_xticks(range(len(contract_types)))
            ax.set_xticklabels([ct[:10] + '...' if len(ct) > 10 else ct for ct in contract_types], 
                              rotation=45, ha='right', fontsize=8)
            ax.set_ylabel('Número de Vagas', fontsize=8)
        ax.set_title('Tipos de Contrato', fontsize=10, fontweight='bold')
        ax.tick_params(axis='both', which='major', labelsize=8)
        self.analytics_charts['contract']['fig'].tight_layout()
        self.analytics_charts['contract']['canvas'].draw()
    def update_city_chart(self):
        if 'city' not in self.analytics_charts:
            return
        ax = self.analytics_charts['city']['ax']
        ax.clear()
        cities = {}
        for job in self.data_manager.jobs_data:
            city = job.get('cidade', 'Não informado')
            cities[city] = cities.get(city, 0) + 1
        if cities:
            top_cities = dict(sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10])
            city_names = list(top_cities.keys())
            counts = list(top_cities.values())
            bars = ax.barh(range(len(city_names)), counts, 
                          color='#4169E1', alpha=0.7)
            for bar, count in zip(bars, counts):
                width = bar.get_width()
                ax.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                       f'{count}', ha='left', va='center', fontsize=8)
            ax.set_yticks(range(len(city_names)))
            ax.set_yticklabels([city[:15] + '...' if len(city) > 15 else city for city in city_names], 
                              fontsize=8)
            ax.set_xlabel('Número de Vagas', fontsize=8)
        ax.set_title('Top 10 Cidades', fontsize=10, fontweight='bold')
        ax.tick_params(axis='both', which='major', labelsize=8)
        self.analytics_charts['city']['fig'].tight_layout()
        self.analytics_charts['city']['canvas'].draw()
    def update_remote_chart(self):
        if 'remote' not in self.analytics_charts:
            return
        ax = self.analytics_charts['remote']['ax']
        ax.clear()
        remote_count = 0
        on_site_count = 0
        for job in self.data_manager.jobs_data:
            if job.get('trabalho_remoto', False):
                remote_count += 1
            else:
                on_site_count += 1
        if remote_count + on_site_count > 0:
            sizes = [remote_count, on_site_count]
            labels = [f'Remoto\n({remote_count})', f'Presencial\n({on_site_count})']
            colors = ['#32CD32', '#FF6347']
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                            colors=colors, startangle=90,
                                            wedgeprops=dict(width=0.5))
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(10)
                autotext.set_weight('bold')
            for text in texts:
                text.set_fontsize(9)
                text.set_weight('bold')
        ax.set_title('Trabalho Remoto vs Presencial', fontsize=10, fontweight='bold')
        self.analytics_charts['remote']['canvas'].draw()
    def show_job_details(self, job):
        details_window = ctk.CTkToplevel(self)
        details_window.title(f"Detalhes da Vaga - {job.get('titulo', 'N/A')}")
        details_window.geometry("600x500")
        details_window.transient(self)
        details_window.grab_set()
        details_window.grid_columnconfigure(0, weight=1)
        details_window.grid_rowconfigure(1, weight=1)
        header_frame = ctk.CTkFrame(details_window)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        title_label = ctk.CTkLabel(header_frame, text=job.get('titulo', 'N/A'),
                                 font=ctk.CTkFont(size=18, weight="bold"))
        title_label.pack(pady=10)
        company_label = ctk.CTkLabel(header_frame, text=f"🏢 {job.get('empresa', 'N/A')}",
                                   font=ctk.CTkFont(size=14))
        company_label.pack()
        content_frame = ctk.CTkScrollableFrame(details_window)
        content_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        details_info = [
            ("📍 Cidade", job.get('cidade', 'N/A')),
            ("🏭 Setor", job.get('setor', 'N/A')),
            ("📄 Tipo de Contrato", job.get('tipo_contrato', 'N/A')),
            ("💻 Trabalho Remoto", "Sim" if job.get('trabalho_remoto', False) else "Não"),
            ("📅 Data de Publicação", job.get('data_publicacao', 'N/A')),
            ("🔗 Link Original", job.get('link', 'N/A')),
        ]
        for label, value in details_info:
            info_frame = ctk.CTkFrame(content_frame)
            info_frame.pack(fill="x", padx=5, pady=2)
            info_frame.grid_columnconfigure(1, weight=1)
            label_widget = ctk.CTkLabel(info_frame, text=label, font=ctk.CTkFont(weight="bold"),
                                      anchor="w", width=150)
            label_widget.grid(row=0, column=0, padx=10, pady=5, sticky="w")
            value_widget = ctk.CTkLabel(info_frame, text=str(value), anchor="w")
            value_widget.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        if job.get('descricao'):
            desc_label = ctk.CTkLabel(content_frame, text="📝 Descrição da Vaga",
                                    font=ctk.CTkFont(size=14, weight="bold"))
            desc_label.pack(anchor="w", padx=5, pady=(10, 5))
            desc_text = ctk.CTkTextbox(content_frame, height=150)
            desc_text.pack(fill="x", padx=5, pady=5)
            desc_text.insert("1.0", job.get('descricao', ''))
            desc_text.configure(state="disabled")
        buttons_frame = ctk.CTkFrame(details_window)
        buttons_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        buttons_frame.grid_columnconfigure((0, 1), weight=1)
        if job.get('link'):
            apply_btn = ctk.CTkButton(buttons_frame, text="🔗 Candidatar-se",
                                    command=lambda: self.open_job_link(job['link']))
            apply_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        close_btn = ctk.CTkButton(buttons_frame, text="❌ Fechar",
                                command=details_window.destroy)
        close_btn.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
    def show_company_profile(self, company_name):
        profile_window = ctk.CTkToplevel(self)
        profile_window.title(f"Perfil da Empresa - {company_name}")
        profile_window.geometry("800x600")
        profile_window.transient(self)
        profile_window.grab_set()
        profile_window.grid_columnconfigure(0, weight=1)
        profile_window.grid_rowconfigure(1, weight=1)
        header_frame = ctk.CTkFrame(profile_window)
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        company_label = ctk.CTkLabel(header_frame, text=f"🏢 {company_name}",
                                   font=ctk.CTkFont(size=20, weight="bold"))
        company_label.pack(pady=15)
        company_jobs = [job for job in self.data_manager.jobs_data 
                       if job.get('empresa') == company_name]
        stats_frame = ctk.CTkFrame(profile_window)
        stats_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        total_jobs = len(company_jobs)
        cities = len(set(job.get('cidade', 'N/A') for job in company_jobs))
        sectors = len(set(job.get('setor', 'N/A') for job in company_jobs))
        remote_jobs = len([job for job in company_jobs if job.get('trabalho_remoto', False)])
        stats = [
            ("💼", "Total de Vagas", str(total_jobs)),
            ("🏙️", "Cidades", str(cities)),
            ("🏭", "Setores", str(sectors)),
            ("💻", "Vagas Remotas", str(remote_jobs))
        ]
        for i, (icon, title, value) in enumerate(stats):
            stat_frame = ctk.CTkFrame(stats_frame)
            stat_frame.grid(row=0, column=i, padx=5, pady=10, sticky="ew")
            icon_label = ctk.CTkLabel(stat_frame, text=icon, font=ctk.CTkFont(size=20))
            icon_label.pack(pady=(10, 0))
            title_label = ctk.CTkLabel(stat_frame, text=title, font=ctk.CTkFont(size=10))
            title_label.pack()
            value_label = ctk.CTkLabel(stat_frame, text=value, 
                                     font=ctk.CTkFont(size=16, weight="bold"))
            value_label.pack(pady=(0, 10))
        jobs_frame = ctk.CTkScrollableFrame(profile_window)
        jobs_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        jobs_frame.grid_columnconfigure(0, weight=1)
        jobs_title = ctk.CTkLabel(jobs_frame, text="📋 Vagas Disponíveis",
                                font=ctk.CTkFont(size=16, weight="bold"))
        jobs_title.pack(pady=10)
        for i, job in enumerate(company_jobs):
            job_frame = ctk.CTkFrame(jobs_frame)
            job_frame.pack(fill="x", padx=5, pady=2)
            job_frame.grid_columnconfigure(1, weight=1)
            title_label = ctk.CTkLabel(job_frame, text=job.get('titulo', 'N/A'),
                                     font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
            title_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 2))
            details_text = f"📍 {job.get('cidade', 'N/A')} • 🏭 {job.get('setor', 'N/A')}"
            if job.get('trabalho_remoto'):
                details_text += " • 💻 Remoto"
            details_label = ctk.CTkLabel(job_frame, text=details_text,
                                       font=ctk.CTkFont(size=10), anchor="w")
            details_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))
            buttons_frame = ctk.CTkFrame(job_frame, fg_color="transparent")
            buttons_frame.grid(row=0, column=2, rowspan=2, padx=10, pady=5, sticky="ns")
            details_btn = ctk.CTkButton(buttons_frame, text="📝 Ver",
                                      command=lambda j=job: self.show_job_details(j),
                                      width=60, height=25)
            details_btn.pack(pady=1)
            if job.get('link'):
                apply_btn = ctk.CTkButton(buttons_frame, text="🔗 Ir",
                                        command=lambda url=job['link']: self.open_job_link(url),
                                        width=60, height=25)
                apply_btn.pack(pady=1)
        close_frame = ctk.CTkFrame(profile_window)
        close_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        close_btn = ctk.CTkButton(close_frame, text="❌ Fechar",
                                command=profile_window.destroy)
        close_btn.pack(pady=10)
def main():
    try:
        app = MSJobsDesktop()
        app.mainloop()
    except KeyboardInterrupt:
        print("\n👋 Aplicação encerrada pelo usuário")
    except Exception as e:
        print(f"❌ Erro na aplicação: {e}")
        messagebox.showerror("Erro Fatal", f"Erro na aplicação: {e}")
if __name__ == "__main__":
    main()