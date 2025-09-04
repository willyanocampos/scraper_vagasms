import time
import sys
import os
from urllib.parse import urljoin
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import random
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue
import csv
import argparse
import psutil
from urllib.parse import urlparse, urljoin, urlunparse
import asyncio
import aiohttp
import base64
from urllib.parse import parse_qs

if sys.platform.startswith('win'):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class ScrapingConfiguration:
    def __init__(self):
        self.max_companies = None
        self.max_pages_per_company = 200
        self.max_workers = self.detect_optimal_workers()
        self.max_career_urls_per_company = 10
        self.enable_full_power = False
        self.enable_enhanced_url_extraction = True
        self.enable_url_validation = True
        self.timeout_multiplier = 1.0
        
    def detect_optimal_workers(self):
        try:
            cpu_count = psutil.cpu_count(logical=True)
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            optimal_workers = min(cpu_count * 2, 16)
            
            memory_limited_workers = int(memory_gb * 2)
            
            return min(optimal_workers, memory_limited_workers, 16)
        except:
            return 6
    
    def enable_full_power_mode(self):
        self.enable_full_power = True
        self.max_companies = None
        self.max_pages_per_company = 500
        self.max_workers = min(self.detect_optimal_workers() * 2, 20)
        self.max_career_urls_per_company = 20
        self.timeout_multiplier = 1.5
        return self

CONFIG = ScrapingConfiguration()

MAX_COMPANIES_FOR_TESTING = None

MS_CITIES = [
    'Campo Grande', 'Dourados', 'Três Lagoas', 'Corumbá', 'Ponta Porã',
    'Naviraí', 'Nova Andradina', 'Maracaju', 'Sidrolândia', 'Caarapó',
    'Aquidauana', 'Paranaíba', 'Chapadão do Sul', 'Coxim', 'Miranda',
    'Bonito', 'Jardim', 'Iguatemi', 'Itaquiraí', 'Água Clara',
    'Ribas do Rio Pardo', 'São Gabriel do Oeste', 'Costa Rica',
    'Anastácio', 'Terenos', 'Inocência', 'Cassilândia', 'Aparecida do Taboado'
]

MS_KEYWORDS = [
    'ms', 'mato grosso do sul', 'campo grande', 'dourados', 'três lagoas',
    'corumbá', 'ponta porã', 'naviraí', 'nova andradina', 'maracaju',
    'sidrolândia', 'caarapó', 'aquidauana', 'paranaíba', 'chapadão do sul'
]

JOB_KEYWORDS = [
    'vaga', 'job', 'emprego', 'carreira', 'oportunidade', 'posição',
    'analista', 'técnico', 'assistente', 'coordenador', 'gerente',
    'operador', 'auxiliar', 'especialista', 'supervisor', 'engenheiro',
    'desenvolvedor', 'programador', 'consultor', 'diretor', 'trainee',
    'estágio', 'jovem aprendiz', 'trabalhe conosco'
]

@dataclass
class Company:
    id: int
    nome: str
    cidade: str
    setor: str
    portal_principal: str
    portal_alternativo: Optional[str] = None
    portal_site: Optional[str] = None
    portal_brasil: Optional[str] = None
    portal_pandape: Optional[str] = None
    portal_global: Optional[str] = None
    observacoes: str = ""
    
    @property
    def is_gupy(self) -> bool:
        return "gupy.io" in self.portal_principal.lower()
    
    @property
    def is_proprietary(self) -> bool:
        return not self.is_gupy and self.portal_principal and "[LINKEDIN_ONLY]" not in self.observacoes

@dataclass
class MSJob:
    id: str
    titulo: str
    empresa: str
    empresa_id: int
    setor: str
    cidade: str
    estado: str = "MS"
    localizacao_completa: str = ""
    tipo_contrato: str = ""
    trabalho_remoto: bool = False
    link: str = ""
    data_coleta: str = ""
    ms_verified: bool = False
    extraction_method: str = ""
    responsabilidades: str = ""
    requisitos: str = ""
    beneficios: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'titulo': self.titulo,
            'empresa': self.empresa,
            'empresa_id': self.empresa_id,
            'setor': self.setor,
            'cidade': self.cidade,
            'estado': self.estado,
            'localizacao_completa': self.localizacao_completa,
            'tipo_contrato': self.tipo_contrato,
            'trabalho_remoto': self.trabalho_remoto,
            'link': self.link,
            'data_coleta': self.data_coleta,
            'ms_verified': self.ms_verified,
            'extraction_method': self.extraction_method,
            'responsabilidades': self.responsabilidades,
            'requisitos': self.requisitos,
            'beneficios': self.beneficios
        }

class MSLocationValidator:
    @staticmethod
    def is_ms_location(text: str) -> tuple[bool, str, str]:
        if not text:
            return False, "", ""
        
        text_lower = text.lower().strip()
        
        if any(keyword in text_lower for keyword in MS_KEYWORDS):
            for city in MS_CITIES:
                if city.lower() in text_lower:
                    return True, city, text.strip()
            return True, "Mato Grosso do Sul", text.strip()
        
        state_patterns = [
            r'\b(ms)\b',
            r'mato\s+grosso\s+do\s+sul',
            r'estado\s+de\s+ms',
            r'localização.*ms'
        ]
        
        for pattern in state_patterns:
            if re.search(pattern, text_lower):
                return True, "Mato Grosso do Sul", text.strip()
        
        remote_indicators = ['remoto', 'remote', 'home office', 'híbrido', 'hybrid', 'distância']
        if any(indicator in text_lower for indicator in remote_indicators):
            return True, "Remoto", text.strip()
        
        return False, "", text.strip()
    
    @staticmethod
    def extract_job_info_from_text(text: str) -> tuple[str, str, str]:
        if not text:
            return "", "", ""
        
        lines = text.split('\n')
        title = ""
        location = ""
        contract_type = ""
        
        for line in lines:
            line = line.strip()
            if len(line) > 5 and any(keyword in line.lower() for keyword in JOB_KEYWORDS):
                if not title and len(line) < 100:
                    title = line
                break
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in MS_KEYWORDS + ['localização', 'cidade', 'local']):
                location = line
                break
        
        contract_keywords = ['efetivo', 'estágio', 'temporário', 'clt', 'pj', 'trainee', 'jovem aprendiz']
        full_text_lower = text.lower()
        for contract in contract_keywords:
            if contract in full_text_lower:
                contract_type = contract.title()
                break
        
        return title, location, contract_type

class EnhancedURLExtractor:
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.validated_urls_cache = set()
        self.invalid_urls_cache = set()
        self.session = requests.Session()
        self.session.timeout = 10
        
    def extract_and_validate_job_link(self, soup, element, driver=None):
        link = self._extract_link_from_soup(soup)
        if link:
            normalized_link = self._normalize_url(link)
            if self._is_valid_job_url(normalized_link):
                return normalized_link
        
        if driver and element:
            link = self._extract_link_from_selenium(element)
            if link:
                normalized_link = self._normalize_url(link)
                if self._is_valid_job_url(normalized_link):
                    return normalized_link
        
        if soup:
            link = self._extract_link_advanced_patterns(soup)
            if link:
                normalized_link = self._normalize_url(link)
                if self._is_valid_job_url(normalized_link):
                    return normalized_link
        
        return ""
    
    def _extract_link_from_soup(self, soup):
        link_selectors = [
            'a[href*="job"]',
            'a[href*="vaga"]', 
            'a[href*="career"]',
            'a[href*="position"]',
            'a[href*="oportunidade"]',
            'a[data-testid*="job"]',
            'a[class*="job"]',
            'a[class*="vaga"]',
            'a'
        ]
        
        for selector in link_selectors:
            try:
                link_element = soup.select_one(selector)
                if link_element and link_element.get('href'):
                    href = link_element.get('href')
                    if href and href not in ['#', 'javascript:void(0)', 'javascript:;']:
                        return href
            except:
                continue
        
        return None
    
    def _extract_link_from_selenium(self, element):
        try:
            approaches = [
                lambda: element.find_element(By.TAG_NAME, 'a').get_attribute('href'),
                lambda: element.get_attribute('href'),
                lambda: element.find_element(By.CSS_SELECTOR, 'a[href]').get_attribute('href'),
                lambda: element.find_element(By.XPATH, './/a[@href]').get_attribute('href')
            ]
            
            for approach in approaches:
                try:
                    href = approach()
                    if href and href not in ['#', 'javascript:void(0)', 'javascript:;']:
                        return href
                except:
                    continue
                    
        except:
            pass
        
        return None
    
    def _extract_link_advanced_patterns(self, soup):
        try:
            elements_with_data = soup.find_all(attrs={'data-url': True})
            for elem in elements_with_data:
                url = elem.get('data-url')
                if url:
                    return url
            
            onclick_elements = soup.find_all(attrs={'onclick': True})
            for elem in onclick_elements:
                onclick = elem.get('onclick', '')
                url_match = re.search(r'["\'](.*?/(?:job|vaga|career|position).*?)["\']', onclick)
                if url_match:
                    return url_match.group(1)
            
            forms = soup.find_all('form', action=True)
            for form in forms:
                action = form.get('action')
                if action and any(keyword in action.lower() for keyword in ['job', 'vaga', 'career', 'position']):
                    return action
                    
        except:
            pass
        
        return None
    
    def _normalize_url(self, url):
        if not url:
            return ""
        
        url = url.strip()
        
        if url in ['#', 'javascript:void(0)', 'javascript:;'] or url.startswith(('javascript:', 'mailto:', 'tel:')):
            return ""
        
        if url.startswith('//'):
            parsed_base = urlparse(self.base_url)
            return f"{parsed_base.scheme}:{url}"
        
        if url.startswith('/'):
            parsed_base = urlparse(self.base_url)
            return f"{parsed_base.scheme}://{parsed_base.netloc}{url}"
        
        if not url.startswith(('http://', 'https://')):
            return urljoin(self.base_url, url)
        
        return url
    
    def _is_valid_job_url(self, url):
        if not url or url in self.invalid_urls_cache:
            return False
        
        if url in self.validated_urls_cache:
            return True
        
        if not self._passes_pattern_validation(url):
            self.invalid_urls_cache.add(url)
            return False
        
        if CONFIG.enable_url_validation:
            if self._validate_url_exists(url):
                self.validated_urls_cache.add(url)
                return True
            else:
                self.invalid_urls_cache.add(url)
                return False
        
        self.validated_urls_cache.add(url)
        return True
    
    def _passes_pattern_validation(self, url):
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            job_patterns = [
                'job', 'vaga', 'career', 'position', 'oportunidade',
                'trabalhe', 'emprego', 'hiring', 'vacancy', 'opportunities'
            ]
            
            if any(pattern in path for pattern in job_patterns):
                return True
            
            query = parsed.query.lower()
            if any(pattern in query for pattern in job_patterns):
                return True
            
            non_job_patterns = [
                'about', 'contact', 'news', 'blog', 'home', 'index',
                'login', 'register', 'privacy', 'terms', 'help'
            ]
            
            if any(pattern in path for pattern in non_job_patterns):
                return False
            
            if len(path.strip('/')) == 0:
                return False
            
            return True
            
        except:
            return False
    
    def _validate_url_exists(self, url):
        try:
            response = self.session.head(url, timeout=5, allow_redirects=True)
            return response.status_code < 400
        except:
            return False

class GrupoPereiraScraper:
    
    def __init__(self, company: Company):
        self.company = company
        self.base_url = company.portal_principal
        self.jobs_data = []
        self.driver = None
        self.url_extractor = EnhancedURLExtractor(self.base_url)
        self.setup_driver()
    
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            print(f"❌ Error setting up driver for {self.company.nome}: {e}")
            raise
    
    def click_load_more_button(self):
        try:
            time.sleep(3)
            
            load_more_selectors = [
                "#btLoadMore",
                "button#btLoadMore",
                "//button[@id='btLoadMore']",
                "//button[contains(text(), 'Mostrar') and contains(text(), 'vagas')]",
                "//button[contains(text(), 'Mostrar 20 vagas mais')]"
            ]
            
            for selector in load_more_selectors:
                try:
                    if selector.startswith('//'):
                        element = self.driver.find_element(By.XPATH, selector)
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if element and element.is_displayed() and element.is_enabled():
                        loading_elements = self.driver.find_elements(By.CSS_SELECTOR, ".preloader, .sk-three-bounce")
                        is_loading = any(el.is_displayed() for el in loading_elements)
                        
                        if not is_loading:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(1)
                            self.driver.execute_script("arguments[0].click();", element)
                            time.sleep(5)
                            
                            try:
                                WebDriverWait(self.driver, 10).until_not(
                                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".preloader"))
                                )
                            except:
                                pass
                            
                            return True
                        else:
                            time.sleep(3)
                            return False
                    
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def extract_enhanced_job_fields(self, soup, element):
        fields = {}
        
        modalidade_div = soup.find('i', class_='icon-buildings')
        if modalidade_div:
            parent = modalidade_div.find_parent('div')
            if parent:
                fields['modalidade'] = parent.get_text(strip=True)
        
        periodo_div = soup.find('i', class_='icon-clock')
        if periodo_div:
            parent = periodo_div.find_parent('div')
            if parent:
                fields['periodo'] = parent.get_text(strip=True)
        
        posicoes_div = soup.find('i', class_='icon-candidates')
        if posicoes_div:
            parent = posicoes_div.find_parent('div')
            if parent:
                fields['posicoes'] = parent.get_text(strip=True)
        
        salary_div = soup.find('i', class_='icon-wallet')
        if salary_div:
            parent = salary_div.find_parent('div')
            if parent:
                fields['salario'] = parent.get_text(strip=True)
        
        date_div = soup.find('div', class_='vacancy-date')
        if date_div:
            fields['data_publicacao'] = date_div.get_text(strip=True)
        
        return fields
    
    def scrape_all_jobs(self):
        try:
            print(f"🚀 Iniciando scraping Grupo Pereira: {self.company.nome}")
            print(f"🌐 URL: {self.base_url}")
            
            self.driver.get(self.base_url)
            time.sleep(10)
            
            self.wait_for_element(By.TAG_NAME, "body", timeout=20)
            time.sleep(5)
            
            current_load = 1
            consecutive_failed_loads = 0
            max_failed_loads = 3
            max_loads = 50
            
            print("📥 FASE 1: Carregando todas as vagas...")
            
            while current_load <= max_loads:
                if not self.check_if_more_jobs_available():
                    print("🏁 Não há mais vagas para carregar")
                    break
                
                load_success = self.click_load_more_button()
                
                if load_success:
                    current_load += 1
                    consecutive_failed_loads = 0
                else:
                    consecutive_failed_loads += 1
                    if consecutive_failed_loads >= max_failed_loads:
                        break
                    time.sleep(3)
            
            print("📤 FASE 2: Extraindo vagas de MS...")
            jobs_added = self.extract_job_listings()
            
            print(f"✅ Total de vagas MS coletadas: {jobs_added}")
            return self.jobs_data
            
        except Exception as e:
            print(f"❌ Erro no scraping {self.company.nome}: {e}")
            return []
    
    def extract_job_listings(self):
        try:
            time.sleep(3)
            
            job_selectors = [
                "a.card-vacancy",
                "a.card.card-vacancy", 
                ".card-vacancy"
            ]
            
            job_items = []
            for selector in job_selectors:
                try:
                    items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if items:
                        job_items = items
                        break
                except:
                    continue
            
            if not job_items:
                xpath_selectors = [
                    "//a[contains(@class, 'card-vacancy')]",
                    "//a[contains(@href, '/Detail/')]",
                    "//div[@id='VacancyList']//a"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        items = self.driver.find_elements(By.XPATH, xpath)
                        if items:
                            job_items = items
                            break
                    except:
                        continue
            
            jobs_added = 0
            existing_jobs = {(job['titulo'], job['localizacao_completa']) for job in self.jobs_data}
            
            for item in job_items:
                try:
                    html = item.get_attribute('outerHTML')
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    title = self.extract_job_title(soup, item)
                    location = self.extract_job_location(soup, item)
                    
                    is_ms, city, cleaned_location = MSLocationValidator.is_ms_location(f"{title} {location}")
                    if not is_ms:
                        continue
                    
                    enhanced_fields = self.extract_enhanced_job_fields(soup, item)
                    
                    job_link = self.url_extractor.extract_and_validate_job_link(soup, item, self.driver)
                    
                    job_key = (title, location)
                    if (title != "Título não encontrado" or job_link) and job_key not in existing_jobs:
                        job_id = f"grupo-pereira-{self.company.id}-{len(self.jobs_data)+1:03d}-{int(time.time()) % 1000}"
                        
                        job = MSJob(
                            id=job_id,
                            titulo=title,
                            empresa=self.company.nome,
                            empresa_id=self.company.id,
                            setor=self.company.setor,
                            cidade=city,
                            estado="MS",
                            localizacao_completa=cleaned_location,
                            tipo_contrato=enhanced_fields.get('tipo_contrato', 'Não informado'),
                            trabalho_remoto="remoto" in location.lower(),
                            link=job_link,
                            data_coleta=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            ms_verified=True,
                            extraction_method="grupo_pereira_ajax",
                            responsabilidades="Extraído via detalhes",
                            requisitos="Extraído via detalhes",
                            beneficios="Extraído via detalhes"
                        )
                        
                        job_dict = job.to_dict()
                        job_dict.update(enhanced_fields)
                        
                        self.jobs_data.append(job_dict)
                        existing_jobs.add(job_key)
                        jobs_added += 1
                
                except Exception:
                    continue
            
            return jobs_added
            
        except Exception:
            return 0
    
    def extract_job_title(self, soup, element):
        title_element = soup.find('h3', {'title': True})
        if title_element:
            title = title_element.get('title') or title_element.get_text(strip=True)
            if title:
                return title
        
        h3_element = soup.find('h3')
        if h3_element:
            title = h3_element.get_text(strip=True)
            if title:
                return title
        
        return "Título não encontrado"
    
    def extract_job_location(self, soup, element):
        location_div = soup.find('div', class_='align-middle mr-20 mb-10')
        if location_div:
            icon = location_div.find('i', class_='icon-location-pin-1')
            if icon:
                text = location_div.get_text(strip=True)
                return text
        
        text_elements = soup.find_all(text=True)
        for text in text_elements:
            if 'Campo Grande' in text or ' - MS' in text:
                return text.strip()
        
        return "Mato Grosso do Sul - MS"
    
    def check_if_more_jobs_available(self):
        try:
            load_more_button = None
            try:
                load_more_button = self.driver.find_element(By.ID, "btLoadMore")
            except:
                try:
                    load_more_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Mostrar')]")
                except:
                    pass
            
            if load_more_button:
                if load_more_button.is_displayed() and load_more_button.is_enabled():
                    loading_elements = self.driver.find_elements(By.CSS_SELECTOR, ".preloader, .sk-three-bounce")
                    is_loading = any(el.is_displayed() for el in loading_elements)
                    return not is_loading
                else:
                    return False
            else:
                return False
        except:
            return False
    
    def wait_for_element(self, by, value, timeout=15):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            return None
    
    def close(self):
        if self.driver:
            self.driver.quit()

class DetailedJobExtractor:
    
    def __init__(self, max_workers=6):
        self.vagas_detalhadas = []
        self.max_workers = max_workers
        self.progress_lock = threading.Lock()
        self.results_lock = threading.Lock()
        self.total_processed = 0
        self.total_success = 0
    
    def create_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except:
            return None
    
    def worker_thread(self, vagas_batch, thread_id, total_vagas):
        driver = None
        batch_results = []
        
        try:
            driver = self.create_driver()
            if not driver:
                return []
            
            for i, vaga in enumerate(vagas_batch):
                try:
                    if i > 0:
                        time.sleep(0.5)
                    
                    with self.progress_lock:
                        self.total_processed += 1
                        current_progress = self.total_processed
                    
                    detalhes = self.extract_job_details_with_driver(driver, vaga['link'])
                    
                    if detalhes:
                        vaga_completa = {**vaga, **detalhes}
                        batch_results.append(vaga_completa)
                        
                        with self.progress_lock:
                            self.total_success += 1
                    else:
                        vaga_completa = vaga.copy()
                        vaga_completa.update({
                            'requisitos_qualificacoes': 'Não foi possível extrair',
                            'experiencia_valorizada': 'Não foi possível extrair',
                            'beneficios': 'Não foi possível extrair',
                            'dados_gerais': {},
                            'data_extracao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })
                        batch_results.append(vaga_completa)
                
                except Exception:
                    vaga_erro = vaga.copy()
                    vaga_erro.update({
                        'requisitos_qualificacoes': 'Erro na extração',
                        'experiencia_valorizada': 'Erro na extração',
                        'beneficios': 'Erro na extração',
                        'dados_gerais': {},
                        'data_extracao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    batch_results.append(vaga_erro)
                    continue
            
            return batch_results
            
        except Exception:
            return batch_results
        
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def extract_job_details_with_driver(self, driver, job_url):
        try:
            driver.get(job_url)
            time.sleep(3)
            
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                return None
            
            requisitos = self.extract_requisitos_with_driver(driver)
            experiencia_valorizada = self.extract_experiencia_valorizada_with_driver(driver)
            beneficios = self.extract_beneficios_with_driver(driver)
            dados_gerais = self.extract_dados_gerais_with_driver(driver)
            
            return {
                'requisitos_qualificacoes': requisitos,
                'experiencia_valorizada': experiencia_valorizada,
                'beneficios': beneficios,
                'dados_gerais': dados_gerais,
                'url_extraida': job_url,
                'data_extracao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception:
            return None
    
    def extract_requisitos_with_driver(self, driver):
        try:
            try:
                requirements_div = driver.find_element(By.ID, "Requirements")
                requisitos = self.extract_tags_from_element_with_driver(driver, requirements_div, "requisitos")
                if requisitos and requisitos != "Informação não encontrada":
                    return requisitos
            except NoSuchElementException:
                pass
            
            requisitos_sections = []
            xpath_targets = [
                "//h3[contains(text(), 'Requisitos')]/following-sibling::*",
                "//h5[contains(text(), 'Estudos')]/following-sibling::*",
                "//*[contains(text(), 'Requisitos')]/../following-sibling::*"
            ]
            
            for xpath in xpath_targets:
                try:
                    elementos = driver.find_elements(By.XPATH, xpath)
                    for elemento in elementos:
                        secao = self.extract_tags_from_element_with_driver(driver, elemento, "requisitos")
                        if secao and secao != "Informação não encontrada":
                            requisitos_sections.append(secao)
                except:
                    continue
            
            if requisitos_sections:
                return self.clean_and_join_sections(requisitos_sections)
            
            return "Informação não encontrada"
            
        except Exception:
            return "Erro na extração"
    
    def extract_experiencia_valorizada_with_driver(self, driver):
        try:
            try:
                valued_div = driver.find_element(By.ID, "Valued")
                experiencia = self.extract_tags_from_element_with_driver(driver, valued_div, "experiencia")
                if experiencia and experiencia != "Informação não encontrada":
                    return experiencia
            except NoSuchElementException:
                pass
            
            experiencia_sections = []
            xpath_targets = [
                "//h3[contains(text(), 'Valorizado')]/following-sibling::*",
                "//h5[contains(text(), 'Experiência profissional')]/following-sibling::*",
                "//*[contains(text(), 'Valorizado')]/../following-sibling::*"
            ]
            
            for xpath in xpath_targets:
                try:
                    elementos = driver.find_elements(By.XPATH, xpath)
                    for elemento in elementos:
                        secao = self.extract_tags_from_element_with_driver(driver, elemento, "experiencia")
                        if secao and secao != "Informação não encontrada":
                            experiencia_sections.append(secao)
                except:
                    continue
            
            if experiencia_sections:
                return self.clean_and_join_sections(experiencia_sections)
            
            return "Informação não encontrada"
            
        except Exception:
            return "Erro na extração"
    
    def extract_beneficios_with_driver(self, driver):
        try:
            try:
                benefits_div = driver.find_element(By.ID, "Benefits")
                beneficios = self.extract_tags_from_element_with_driver(driver, benefits_div, "beneficios")
                if beneficios and beneficios != "Informação não encontrada":
                    return beneficios
            except NoSuchElementException:
                pass
            
            beneficios_sections = []
            xpath_targets = [
                "//h3[contains(text(), 'Benefícios')]/following-sibling::*",
                "//*[contains(text(), 'Benefícios')]/../following-sibling::*"
            ]
            
            for xpath in xpath_targets:
                try:
                    elementos = driver.find_elements(By.XPATH, xpath)
                    for elemento in elementos:
                        secao = self.extract_tags_from_element_with_driver(driver, elemento, "beneficios")
                        if secao and secao != "Informação não encontrada":
                            beneficios_sections.append(secao)
                except:
                    continue
            
            if beneficios_sections:
                return self.clean_and_join_sections(beneficios_sections)
            
            return "Informação não encontrada"
            
        except Exception:
            return "Erro na extração"
    
    def extract_tags_from_element_with_driver(self, driver, elemento, tipo):
        try:
            tags = elemento.find_elements(By.CSS_SELECTOR, ".custom-tag .js_tagText")
            
            if tags:
                itens_extraidos = []
                for tag in tags:
                    texto_tag = tag.text.strip()
                    if texto_tag and len(texto_tag) > 1:
                        itens_extraidos.append(f"• {texto_tag}")
                
                if itens_extraidos:
                    return '\n'.join(itens_extraidos)
            
            try:
                texto_elemento = elemento.text.strip()
                if texto_elemento and len(texto_elemento) > 20:
                    if self.text_seems_relevant(texto_elemento, tipo):
                        return self.format_text_as_list(texto_elemento)
            except:
                pass
            
            return "Informação não encontrada"
            
        except Exception:
            return "Informação não encontrada"
    
    def extract_dados_gerais_with_driver(self, driver):
        try:
            dados = {}
            
            try:
                location_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Campo Grande') or contains(text(), 'MS')]")
                if location_elements:
                    dados['localizacao_detalhada'] = location_elements[0].text.strip()
                
                page_text = driver.page_source
                patterns = {
                    'codigo_vaga': r'(?:ID|Código|Code):\s*([A-Za-z0-9]+)',
                    'area': r'(?:Área|Department|Setor):\s*([^<\n]+)',
                    'nivel': r'(?:Nível|Level):\s*([^<\n]+)'
                }
                
                for key, pattern in patterns.items():
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        dados[key] = match.group(1).strip()
                
            except Exception:
                pass
            
            return dados
            
        except Exception:
            return {}
    
    def text_seems_relevant(self, text, tipo):
        text_lower = text.lower()
        
        if tipo == "requisitos":
            keywords = ['ensino', 'graduação', 'curso', 'formação', 'escolaridade', 'diploma', 'certificado', 'conhecimento', 'técnico', 'superior', 'médio', 'fundamental']
        elif tipo == "experiencia":
            keywords = ['experiência', 'anos', 'meses', 'prática', 'vivência', 'atuação', 'trabalho', 'sem experiência', 'iniciante', 'júnior', 'sênior', 'pleno']
        else:
            keywords = ['vale', 'plano', 'seguro', 'auxílio', 'assistência', 'convênio', 'desconto', 'refeitório', 'transporte', 'alimentação', 'saúde', 'dental', 'odontológico', 'vida', 'carreira']
        
        keyword_count = sum(1 for keyword in keywords if keyword in text_lower)
        return keyword_count >= 1
    
    def format_text_as_list(self, text):
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if any(line.startswith(('•', '-', '*')) for line in lines):
            return text
        
        if len(lines) > 1:
            formatted_lines = [f"• {line}" for line in lines if len(line) > 3]
            return '\n'.join(formatted_lines)
        
        return text
    
    def clean_and_join_sections(self, sections):
        all_items = []
        seen_items = set()
        
        for section in sections:
            lines = section.split('\n')
            for line in lines:
                line = line.strip()
                if line and line not in seen_items:
                    if not line.startswith('•'):
                        line = f"• {line}"
                    all_items.append(line)
                    seen_items.add(line)
        
        return '\n'.join(all_items) if all_items else "Informação não encontrada"

class SimpleGupyScraper:
    
    def __init__(self, company: Company):
        self.company = company
        self.base_url = company.portal_principal
        self.jobs_data = []
        self.driver = None
        self.url_extractor = EnhancedURLExtractor(self.base_url)
        self.setup_driver()
    
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            print(f"❌ Error setting up driver for {self.company.nome}: {e}")
            raise
    
    def wait_for_element(self, by, value, timeout=15):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            return None
    
    def wait_for_clickable(self, by, value, timeout=15):
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            return element
        except TimeoutException:
            return None
    
    def apply_filters(self):
        try:
            print("🔧 Aplicando filtros...")
            
            time.sleep(5)
            
            print("   📍 Configurando filtro de Estado para MS...")
            success_state = self.apply_state_filter()
            
            if success_state:
                print("   ✅ Filtro de Estado aplicado com sucesso")
                time.sleep(3)
            else:
                print("   ⚠️  Não foi possível aplicar filtro de Estado")
            
            print("   📄 Configurando 50 vagas por página...")
            success_pagination = self.apply_pagination_filter()
            
            if success_pagination:
                print("   ✅ Filtro de paginação aplicado com sucesso")
                time.sleep(5)
            else:
                print("   ⚠️  Não foi possível aplicar filtro de paginação")
            
            print("🔧 Filtros configurados, aguardando carregamento...")
            time.sleep(5)
            
            return success_state or success_pagination
            
        except Exception as e:
            print(f"❌ Erro ao aplicar filtros: {e}")
            return False
    
    def apply_state_filter(self):
        try:
            state_selectors = [
                "#state-select",
                "input[id='state-select']",
                "input[aria-label='Estado']",
                "//input[@id='state-select']",
                "//input[@aria-label='Estado']",
                "//div[contains(@class, 'css') and contains(text(), 'Estado')]/..//input",
                "//label[contains(text(), 'Estado')]/..//input"
            ]
            
            for selector in state_selectors:
                try:
                    if selector.startswith('//'):
                        element = self.driver.find_element(By.XPATH, selector)
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if element:
                        print(f"     ✓ Encontrado campo de Estado: {selector}")
                        
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(1)
                        
                        element.click()
                        time.sleep(2)
                        
                        ms_options = [
                            "//div[contains(text(), 'Mato Grosso do Sul')]",
                            "//div[contains(text(), 'MS')]",
                            "//option[contains(text(), 'Mato Grosso do Sul')]",
                            "//*[contains(text(), 'Mato Grosso do Sul (MS)')]",
                            "//div[contains(@class, 'option') and contains(text(), 'Mato Grosso')]"
                        ]
                        
                        for option_selector in ms_options:
                            try:
                                option = self.driver.find_element(By.XPATH, option_selector)
                                if option and option.is_displayed():
                                    print(f"     ✓ Encontrada opção MS: {option.text}")
                                    option.click()
                                    time.sleep(2)
                                    return True
                            except:
                                continue
                        
                        try:
                            element.clear()
                            element.send_keys("Mato Grosso do Sul")
                            time.sleep(2)
                            
                            suggestions = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Mato Grosso')]")
                            if suggestions:
                                suggestions[0].click()
                                time.sleep(2)
                                return True
                        except:
                            pass
                        
                except Exception:
                    continue
            
            print("     ❌ Não foi possível aplicar filtro de Estado")
            return False
            
        except Exception:
            return False
    
    def apply_pagination_filter(self):
        try:
            pagination_selectors = [
                "//select[contains(@aria-label, 'itens por página')]",
                "//select[contains(@aria-label, 'vagas por página')]",
                "//select[contains(@name, 'page-size')]",
                "//select[contains(@name, 'per-page')]",
                "//div[contains(text(), 'por página')]/..//select",
                "//div[contains(text(), '20')]/..//select",
                "//div[contains(text(), '10')]/..//select"
            ]
            
            for selector in pagination_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element:
                        print(f"     ✓ Encontrado controle de paginação: {selector}")
                        
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(1)
                        
                        element.click()
                        time.sleep(1)
                        
                        options_50 = self.driver.find_elements(By.XPATH, "//option[@value='50' or text()='50']")
                        if options_50:
                            options_50[0].click()
                            time.sleep(2)
                            return True
                        
                except Exception:
                    continue
            
            react_pagination_selectors = [
                "//div[contains(@class, 'css') and contains(text(), '20')]",
                "//div[contains(@class, 'select') and contains(text(), '20')]",
                "//div[contains(@class, 'css') and contains(text(), '10')]",
                "//div[contains(@class, 'select') and contains(text(), '10')]"
            ]
            
            for selector in react_pagination_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element:
                        print(f"     ✓ Encontrado React select de paginação")
                        
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(1)
                        element.click()
                        time.sleep(2)
                        
                        option_50 = self.driver.find_elements(By.XPATH, "//*[text()='50']")
                        if option_50:
                            option_50[0].click()
                            time.sleep(2)
                            return True
                        
                except Exception:
                    continue
            
            print("     ⚠️  Controle de paginação não encontrado ou não aplicável")
            return False
            
        except Exception:
            return False
    
    def navigate_to_next_page(self):
        try:
            print("    🔍 Procurando botão de próxima página...")
            
            time.sleep(2)
            
            next_page_selectors = [
                "//*[@id='job-listing']/div[4]/nav/ul/li[5]/button/div/svg",
                "//*[@id='job-listing']/div[4]/nav/ul/li[5]/button",
                "//button[contains(@aria-label, 'next')]",
                "//button[contains(@aria-label, 'próxima')]",
                "//button[contains(@aria-label, 'Next')]",
                "//*[@id='job-listing']//nav//button[contains(@aria-label, 'next')]",
                "//*[@id='job-listing']//nav//button[position()=last()]",
                "//nav//button[contains(., '>')]",
                "//button[contains(., 'Próxima')]",
                "//button[contains(., 'Next')]"
            ]
            
            for selector in next_page_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_enabled() and element.is_displayed():
                            print(f"    ✓ Botão de próxima página encontrado: {selector}")
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            time.sleep(1)
                            self.driver.execute_script("arguments[0].click();", element)
                            print("    ✅ Clicou no botão de próxima página")
                            time.sleep(5)
                            return True
                            
                except Exception:
                    continue
            
            print("    ❌ Nenhum botão de próxima página encontrado")
            return False
            
        except Exception:
            return False
    
    def check_if_last_page(self):
        try:
            print("    🔍 Verificando se é a última página...")
            
            time.sleep(2)
            
            main_selector = "//*[@id='job-listing']/div[4]/nav/ul/li[5]/button/div/svg"
            
            try:
                svg_element = self.driver.find_element(By.XPATH, main_selector)
                button_element = svg_element.find_element(By.XPATH, "./..")
                
                if button_element.is_enabled() and button_element.is_displayed():
                    print("    ➡️  Botão próxima página DISPONÍVEL - pode continuar")
                    return False
                else:
                    print("    🏁 Botão próxima página DESABILITADO - última página")
                    return True
                    
            except NoSuchElementException:
                print("    🔍 Seletor específico não encontrado, verificando alternativas...")
            
            nav_buttons = self.driver.find_elements(By.XPATH, "//*[@id='job-listing']//nav//button")
            
            enabled_nav_buttons = 0
            for btn in nav_buttons:
                try:
                    if btn.is_enabled() and btn.is_displayed():
                        btn_text = btn.get_attribute('aria-label') or btn.text or ""
                        btn_html = btn.get_attribute('outerHTML') or ""
                        
                        if any(keyword in btn_text.lower() for keyword in ['next', 'próxima']) or \
                           any(keyword in btn_html.lower() for keyword in ['next', 'próxima']):
                            enabled_nav_buttons += 1
                            print(f"    ✓ Botão de navegação habilitado encontrado: {btn_text}")
                except:
                    continue
            
            if enabled_nav_buttons > 0:
                print(f"    ➡️  {enabled_nav_buttons} botões de navegação habilitados - pode continuar")
                return False
            
            disabled_buttons = self.driver.find_elements(By.XPATH, 
                "//*[@id='job-listing']//nav//button[@disabled or contains(@class, 'disabled')]")
            
            if disabled_buttons:
                print(f"    🏁 {len(disabled_buttons)} botões desabilitados encontrados - última página")
                return True
            
            all_nav_buttons = self.driver.find_elements(By.XPATH, "//*[@id='job-listing']//nav//button")
            if not all_nav_buttons:
                print("    🏁 Nenhum botão de navegação encontrado - última página")
                return True
            
            print("    ❓ Não foi possível determinar com certeza - tentando continuar")
            return False
            
        except Exception:
            return False
    
    def extract_job_listings(self):
        try:
            time.sleep(3)
            
            job_selectors = [
                "li[data-testid='job-list__listitem']",
                "li[class*='sc-']",
                "a[data-testid='job-list__listitem-href']",
                "li a[href*='job']",
                "div[class*='job']",
                "article"
            ]
            
            job_items = []
            for selector in job_selectors:
                try:
                    items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if items:
                        job_items = items
                        print(f"    ✓ Encontradas {len(items)} vagas com seletor: {selector}")
                        break
                except:
                    continue
            
            if not job_items:
                xpath_selectors = [
                    "//li[contains(@data-testid, 'job')]",
                    "//a[contains(@href, 'job')]",
                    "//li[contains(@class, 'job')]",
                    "//article",
                    "//*[contains(@class, 'job-list')]//li"
                ]
                
                for xpath in xpath_selectors:
                    try:
                        items = self.driver.find_elements(By.XPATH, xpath)
                        if items:
                            job_items = items
                            print(f"    ✓ Encontradas {len(items)} vagas com XPath: {xpath}")
                            break
                    except:
                        continue
            
            jobs_added = 0
            existing_jobs = {(job['titulo'], job['localizacao_completa']) for job in self.jobs_data}
            
            for item in job_items:
                try:
                    html = item.get_attribute('outerHTML')
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    title = self.extract_job_title(soup, item)
                    
                    location = self.extract_job_location(soup, item)
                    
                    contract_type = self.extract_contract_type(soup, item)
                    
                    job_link = self.extract_job_link(soup, item)
                    
                    is_ms, city, cleaned_location = MSLocationValidator.is_ms_location(f"{title} {location}")
                    
                    if is_ms:
                        job_key = (title, location)
                        if (title != "Título não encontrado" or job_link) and job_key not in existing_jobs:
                            
                            job_id = f"simple-gupy-{self.company.id}-{len(self.jobs_data)+1:03d}-{int(time.time()) % 1000}"
                            
                            job = MSJob(
                                id=job_id,
                                titulo=title,
                                empresa=self.company.nome,
                                empresa_id=self.company.id,
                                setor=self.company.setor,
                                cidade=city,
                                estado="MS",
                                localizacao_completa=cleaned_location,
                                tipo_contrato=contract_type,
                                trabalho_remoto="remoto" in location.lower(),
                                link=job_link,
                                data_coleta=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                ms_verified=True,
                                extraction_method="simple_gupy_selenium",
                                responsabilidades="Não extraído - modo simples",
                                requisitos="Não extraído - modo simples", 
                                beneficios="Não extraído - modo simples"
                            )
                            
                            self.jobs_data.append(job.to_dict())
                            existing_jobs.add(job_key)
                            jobs_added += 1
                
                except Exception:
                    continue
            
            return jobs_added
            
        except Exception:
            return 0
    
    def extract_job_title(self, soup, element):
        title_selectors = [
            soup.find('div', class_=lambda x: x and 'sc-' in str(x) and '2' in str(x)),
            soup.find('h1'), soup.find('h2'), soup.find('h3'),
            soup.find('div', class_=lambda x: x and 'title' in str(x).lower()),
            soup.find('a')
        ]
        
        for selector in title_selectors:
            if selector and selector.get_text(strip=True):
                text = selector.get_text(strip=True)
                if len(text) > 5:
                    return text
        
        try:
            text = element.text.strip()
            if text:
                lines = text.split('\n')
                for line in lines:
                    if any(word in line.upper() for word in ['ANALISTA', 'ASSISTENTE', 'COORDENADOR', 'GERENTE', 'TÉCNICO', 'OPERADOR', 'ESPECIALISTA', 'AUXILIAR', 'SUPERVISOR']):
                        return line.strip()
                return lines[0].strip() if lines and len(lines[0].strip()) > 5 else "Título não encontrado"
        except:
            pass
        
        return "Título não encontrado"
    
    def extract_job_location(self, soup, element):
        location_selectors = [
            soup.find('div', class_=lambda x: x and 'sc-' in str(x) and '3' in str(x)),
            soup.find('div', class_=lambda x: x and 'location' in str(x).lower()),
            soup.find('span', class_=lambda x: x and 'location' in str(x).lower())
        ]
        
        for selector in location_selectors:
            if selector and selector.get_text(strip=True):
                return selector.get_text(strip=True)
        
        try:
            text = element.text
            lines = text.split('\n')
            for line in lines:
                if any(indicator in line for indicator in [' - MS', 'MS', 'Mato Grosso', 'Campo Grande', 'Três Lagoas', 'Dourados']):
                    return line.strip()
        except:
            pass
        
        return "Mato Grosso do Sul - MS"
    
    def extract_contract_type(self, soup, element):
        contract_selectors = [
            soup.find('div', class_=lambda x: x and 'sc-' in str(x) and '4' in str(x)),
            soup.find('div', class_=lambda x: x and 'contract' in str(x).lower()),
            soup.find('span', class_=lambda x: x and 'type' in str(x).lower())
        ]
        
        for selector in contract_selectors:
            if selector and selector.get_text(strip=True):
                return selector.get_text(strip=True)
        
        try:
            text = element.text.lower()
            contract_types = ['efetivo', 'estágio', 'temporário', 'terceirizado', 'pj', 'clt', 'jovem aprendiz', 'trainee']
            for contract_type in contract_types:
                if contract_type in text:
                    return contract_type.title()
        except:
            pass
        
        return "Tipo não informado"
    
    def extract_job_link(self, soup, element):
        if CONFIG.enable_enhanced_url_extraction:
            return self.url_extractor.extract_and_validate_job_link(soup, element, self.driver)
        
        link_element = soup.find('a', {'data-testid': 'job-list__listitem-href'}) or soup.find('a', href=True)
        if link_element:
            job_link = link_element.get('href')
            if job_link and not job_link.startswith('http'):
                job_link = self.base_url.rstrip('/') + job_link
            return job_link
        
        try:
            link_elem = element.find_element(By.TAG_NAME, 'a')
            job_link = link_elem.get_attribute('href')
            if job_link:
                return job_link
        except:
            pass
        
        return ""
    
    def scrape_all_jobs(self):
        try:
            print(f"   🌐 URL: {self.base_url}")
            
            self.driver.get(self.base_url)
            time.sleep(10)
            
            filters_applied = self.apply_filters()
            if not filters_applied:
                print("   ⚠️  Filtros não aplicados, continuando mesmo assim...")
            
            current_page = 1
            consecutive_empty_pages = 0
            max_empty_pages = 3
            
            while True:
                jobs_added = self.extract_job_listings()
                
                if jobs_added > 0:
                    consecutive_empty_pages = 0
                    print(f"   ✅ Página {current_page}: {jobs_added} vagas MS | Total: {len(self.jobs_data)}")
                else:
                    consecutive_empty_pages += 1
                    print(f"   ⚠️ Página {current_page}: 0 vagas MS")
                
                if consecutive_empty_pages >= max_empty_pages:
                    print(f"   ⏹️ Parando: {consecutive_empty_pages} páginas consecutivas sem vagas")
                    break
                
                if current_page >= CONFIG.max_pages_per_company:
                    print(f"   ⏹️ Parando: Limite de páginas atingido ({current_page})")
                    break
                
                if self.check_if_last_page():
                    print(f"   ⏹️ Parando: Última página detectada")
                    break
                
                print(f"   ➡️ Tentando navegar para página {current_page + 1}...")
                if self.navigate_to_next_page():
                    current_page += 1
                    time.sleep(6)
                else:
                    print(f"   ❌ Falha na navegação para próxima página")
                    break
            
            return self.jobs_data
            
        except Exception as e:
            print(f"   ❌ Error scraping {self.company.nome}: {e}")
            return []
    
    def close(self):
        if self.driver:
            self.driver.quit()

class ProprietaryScraper:
    
    def __init__(self, company: Company):
        self.company = company
        self.session = requests.Session()
        self.jobs_data = []
        self.url_extractor = None
        self.setup_session()
    
    def setup_session(self):
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive'
        })
        self.session.timeout = 15
    
    def setup_driver_for_dynamic_content(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(f"--user-data-dir=/tmp/chrome_prop_{self.company.id}_{int(time.time())}")
            
            prefs = {
                "profile.default_content_setting_values": {
                    "images": 2,
                    "media": 2,
                    "stylesheets": 1
                }
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(8)
            return True
        except Exception as e:
            print(f"⚠️ Não foi possível configurar driver para {self.company.nome}: {e}")
            return False
    
    def extract_with_selenium(self, url: str) -> List[MSJob]:
        jobs = []
        
        if not self.setup_driver_for_dynamic_content():
            return jobs
        
        try:
            print(f"🔍 Extraindo com Selenium: {url}")
            self.driver.get(url)
            time.sleep(3)
            
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)
            except TimeoutException:
                pass
            
            jobs = self.extract_jobs_multiple_strategies()
            
        except Exception as e:
            print(f"❌ Erro na extração com Selenium: {e}")
        finally:
            if self.driver:
                self.driver.quit()
        
        return jobs
    
    def extract_jobs_multiple_strategies(self) -> List[MSJob]:
        jobs = []
        
        strategies = [
            self.extract_strategy_enhanced_cards,
            self.extract_strategy_enhanced_tables,
            self.extract_strategy_enhanced_lists,
            self.extract_strategy_enhanced_semantic
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                strategy_jobs = strategy()
                if strategy_jobs:
                    jobs.extend(strategy_jobs)
                    print(f"✅ Estratégia avançada {i} encontrou {len(strategy_jobs)} vagas")
                    break
            except Exception as e:
                continue
        
        return jobs
    
    def extract_strategy_enhanced_cards(self) -> List[MSJob]:
        jobs = []
        
        enhanced_selectors = [
            '.card', '.job-card', '.vaga-card', '.position-card',
            '[class*="card"]', '[class*="job"]', '[class*="vaga"]',
            '.vacancy', '.opportunity', '.opening',
            '[data-testid*="job"]', '[data-testid*="vaga"]',
            '.hcm-vacancy', '.senior-job', '.position-item',
            '.career-item', '.work-opportunity'
        ]
        
        for selector in enhanced_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements[:15]:
                    job = self.extract_enhanced_job_from_element(element)
                    if job:
                        jobs.append(job)
                
                if jobs:
                    break
                    
            except Exception:
                continue
        
        return jobs
    
    def extract_strategy_enhanced_tables(self) -> List[MSJob]:
        jobs = []
        
        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                headers = table.find_elements(By.TAG_NAME, "th")
                header_text = [h.text.lower() for h in headers]
                
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows[1:]:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        job = self.extract_enhanced_job_from_table_row(row, cells, header_text)
                        if job:
                            jobs.append(job)
        except Exception:
            pass
        
        return jobs
    
    def extract_strategy_enhanced_lists(self) -> List[MSJob]:
        jobs = []
        
        enhanced_list_selectors = [
            'ul li', 'ol li', '.list-item', '[class*="list"]',
            '[class*="item"]', '.row', '.job-row', '.vacancy-row'
        ]
        
        for selector in enhanced_list_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements[:25]:
                    text = element.text.strip()
                    if len(text) > 15 and any(keyword in text.lower() for keyword in JOB_KEYWORDS):
                        job = self.extract_enhanced_job_from_element(element)
                        if job:
                            jobs.append(job)
                
                if jobs:
                    break
                    
            except Exception:
                continue
        
        return jobs
    
    def extract_strategy_enhanced_semantic(self) -> List[MSJob]:
        jobs = []
        
        try:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            job_patterns = [
                r'vaga\s*(?:para|de)?\s*([^:\n]{5,50})',
                r'cargo\s*(?:de)?\s*([^:\n]{5,50})',
                r'contrata(?:mos)?\s*([^:\n]{5,50})',
                r'oportunidade\s*(?:para|de)?\s*([^:\n]{5,50})',
                r'admite\s*([^:\n]{5,50})'
            ]
            
            text_content = soup.get_text()
            
            for pattern in job_patterns:
                matches = re.finditer(pattern, text_content, re.IGNORECASE)
                
                for match in matches:
                    title = match.group(1).strip()
                    if len(title) > 5 and len(title) < 80:
                        context = text_content[max(0, match.start()-200):match.end()+200]
                        is_ms, city, _ = MSLocationValidator.is_ms_location(context)
                        
                        if is_ms:
                            job = self.create_enhanced_job(title, city, context, "enhanced_semantic")
                            if job:
                                jobs.append(job)
        except Exception:
            pass
        
        return jobs
    
    def extract_enhanced_job_from_element(self, element) -> Optional[MSJob]:
        try:
            text_content = element.text.strip()
            
            if not text_content or len(text_content) < 10:
                return None
            
            title = self.extract_enhanced_title(text_content)
            if not title:
                return None
            
            is_ms, city, cleaned_location = MSLocationValidator.is_ms_location(text_content)
            if not is_ms:
                return None
            
            responsabilidades = self.extract_enhanced_details(text_content, "responsabilidades")
            requisitos = self.extract_enhanced_details(text_content, "requisitos") 
            beneficios = self.extract_enhanced_details(text_content, "beneficios")
            
            nivel_experiencia = self.extract_experience_level(text_content)
            area_atuacao = self.extract_work_area(text_content)
            
            link = ""
            try:
                if not self.url_extractor:
                    self.url_extractor = EnhancedURLExtractor(self.driver.current_url)
                
                element_html = element.get_attribute('outerHTML')
                element_soup = BeautifulSoup(element_html, 'html.parser')
                
                if CONFIG.enable_enhanced_url_extraction:
                    link = self.url_extractor.extract_and_validate_job_link(element_soup, element, self.driver)
                else:
                    link_element = element.find_element(By.TAG_NAME, "a")
                    href = link_element.get_attribute("href")
                    if href:
                        link = href if href.startswith('http') else urljoin(self.driver.current_url, href)
            except:
                pass
            
            return self.create_enhanced_job(
                title, city, text_content, "enhanced_element",
                link=link, responsabilidades=responsabilidades,
                requisitos=requisitos, beneficios=beneficios,
                nivel_experiencia=nivel_experiencia, area_atuacao=area_atuacao
            )
            
        except Exception:
            return None
    
    def extract_enhanced_job_from_table_row(self, row, cells, headers) -> Optional[MSJob]:
        try:
            cell_texts = [cell.text.strip() for cell in cells]
            combined_text = " | ".join(cell_texts)
            
            title = None
            location = None
            
            if headers:
                for i, header in enumerate(headers):
                    if i < len(cell_texts):
                        if any(keyword in header for keyword in ['cargo', 'vaga', 'posição', 'job', 'title']):
                            title = cell_texts[i]
                        elif any(keyword in header for keyword in ['local', 'cidade', 'location', 'city']):
                            location = cell_texts[i]
            
            if not title:
                title = self.extract_enhanced_title(combined_text)
            
            if not title:
                return None
            
            search_text = f"{combined_text} {location or ''}"
            is_ms, city, _ = MSLocationValidator.is_ms_location(search_text)
            if not is_ms:
                return None
            
            return self.create_enhanced_job(title, city, combined_text, "enhanced_table")
            
        except Exception:
            return None
    
    def extract_enhanced_title(self, text: str) -> Optional[str]:
        try:
            title_patterns = [
                r'(?:vaga|cargo|função|oportunidade)\s*(?:para|de)?\s*[:]?\s*([^\n\r|]{5,80})',
                r'(?:contrata|admite)\s*[:]?\s*([^\n\r|]{5,80})',
                r'([^\n\r|]{5,80})\s*[-–]\s*(?:vaga|cargo|oportunidade)',
                r'^([^\n\r|]{5,80})(?:\s*[-–]\s*|$)'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    if self.is_valid_job_title(title):
                        return title.title()
            
            lines = text.split('\n')
            for line in lines[:3]:
                line = line.strip()
                if self.is_valid_job_title(line):
                    return line.title()
            
            return None
            
        except Exception:
            return None
    
    def is_valid_job_title(self, title: str) -> bool:
        if not title or len(title) < 5 or len(title) > 80:
            return False
        
        job_indicators = [
            'analista', 'assistente', 'coordenador', 'gerente', 'supervisor',
            'técnico', 'operador', 'auxiliar', 'especialista', 'consultor',
            'diretor', 'engenheiro', 'administrador', 'vendedor', 'contador'
        ]
        
        title_lower = title.lower()
        return any(indicator in title_lower for indicator in job_indicators)
    
    def extract_enhanced_details(self, text: str, detail_type: str) -> str:
        try:
            if detail_type == "responsabilidades":
                keywords = ['responsabilidades', 'atividades', 'atribuições', 'funções', 'duties']
            elif detail_type == "requisitos":
                keywords = ['requisitos', 'qualificações', 'exigências', 'perfil', 'requirements']
            elif detail_type == "beneficios":
                keywords = ['benefícios', 'vantagens', 'oferecemos', 'benefits']
            else:
                return "Não encontrado"
            
            text_lower = text.lower()
            
            for keyword in keywords:
                if keyword in text_lower:
                    start_pos = text_lower.find(keyword)
                    
                    section_end = len(text)
                    for boundary in ['responsabilidades', 'requisitos', 'benefícios', 'salário', 'local']:
                        if boundary != keyword:
                            next_pos = text_lower.find(boundary, start_pos + len(keyword))
                            if next_pos != -1:
                                section_end = min(section_end, next_pos)
                    
                    section_text = text[start_pos:section_end].strip()
                    
                    if len(section_text) > 20:
                        return section_text[:400]
            
            return "Não encontrado"
            
        except Exception:
            return "Erro na extração"
    
    def extract_experience_level(self, text: str) -> str:
        try:
            text_lower = text.lower()
            
            if any(keyword in text_lower for keyword in ['júnior', 'junior', 'trainee', 'estagiário']):
                return "Júnior"
            elif any(keyword in text_lower for keyword in ['pleno', 'plena']):
                return "Pleno"
            elif any(keyword in text_lower for keyword in ['sênior', 'senior', 'especialista']):
                return "Sênior"
            elif any(keyword in text_lower for keyword in ['coordenador', 'gerente', 'supervisor', 'liderança']):
                return "Liderança"
            
            return "Não especificado"
            
        except Exception:
            return "Não especificado"
    
    def extract_work_area(self, text: str) -> str:
        try:
            text_lower = text.lower()
            
            areas = {
                'Vendas': ['vendas', 'comercial', 'negócios'],
                'Administração': ['administrativo', 'administração', 'gestão'],
                'Produção': ['produção', 'operação', 'fábrica', 'industrial'],
                'Qualidade': ['qualidade', 'controle'],
                'Logística': ['logística', 'transporte', 'distribuição'],
                'Financeiro': ['financeiro', 'contabilidade', 'fiscal'],
                'Recursos Humanos': ['recursos humanos', 'rh', 'pessoas'],
                'TI': ['tecnologia', 'sistema', 'informática', 'ti'],
                'Agronegócio': ['agrícola', 'agronegócio', 'campo', 'rural']
            }
            
            for area, keywords in areas.items():
                if any(keyword in text_lower for keyword in keywords):
                    return area
            
            return "Geral"
            
        except Exception:
            return "Geral"
    
    def create_enhanced_job(self, title: str, city: str, text_content: str, 
                          extraction_method: str, **kwargs) -> MSJob:
        
        job_id = f"prop-enh-{self.company.id}-{len(self.jobs_data)+1:03d}-{int(time.time()) % 1000}"
        
        job = MSJob(
            id=job_id,
            titulo=title,
            empresa=self.company.nome,
            empresa_id=self.company.id,
            setor=self.company.setor,
            cidade=city,
            estado="MS",
            localizacao_completa=f"{city}, MS",
            tipo_contrato=kwargs.get('tipo_contrato', 'Não informado'),
            trabalho_remoto="remoto" in text_content.lower(),
            link=kwargs.get('link', ''),
            data_coleta=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ms_verified=True,
            extraction_method=extraction_method,
            responsabilidades=kwargs.get('responsabilidades', 'Não encontrado'),
            requisitos=kwargs.get('requisitos', 'Não encontrado'),
            beneficios=kwargs.get('beneficios', 'Não encontrado')
        )
        
        return job
    
    def get_all_portal_urls(self) -> List[str]:
        urls = []
        
        if self.company.portal_principal:
            urls.append(self.company.portal_principal)
        
        for portal_attr in ['portal_alternativo', 'portal_site', 'portal_brasil', 
                           'portal_pandape', 'portal_global']:
            portal_url = getattr(self.company, portal_attr, None)
            if portal_url:
                urls.append(portal_url)
        
        return [url.rstrip('/') for url in urls if url]
    
    def generate_career_urls(self, base_url: str) -> List[str]:
        career_paths = [
            '/carreiras', '/careers', '/trabalhe-conosco', '/vagas',
            '/jobs', '/oportunidades', '/recrutamento', '/rh'
        ]
        
        urls = [base_url]
        for path in career_paths:
            urls.append(f"{base_url}{path}")
        
        return urls
    
    def fetch_page_content(self, url: str) -> Optional[BeautifulSoup]:
        try:
            response = self.session.get(url, allow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                return soup
                
        except Exception:
            pass
        
        return None
    
    def extract_jobs_from_page(self, soup: BeautifulSoup, base_url: str) -> List[MSJob]:
        jobs = []
        
        job_containers = []
        selectors = [
            'article', 'section', '.job', '.vaga', '.position',
            '.career', '[class*="job"]', '[class*="vaga"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                job_containers.extend(elements[:20])
                break
        
        for i, container in enumerate(job_containers):
            try:
                text_content = container.get_text(separator='\n', strip=True)
                text_lower = text_content.lower()
                
                if any(keyword in text_lower for keyword in JOB_KEYWORDS):
                    title, location, contract_type = MSLocationValidator.extract_job_info_from_text(text_content)
                    
                    if title:
                        is_ms, city, cleaned_location = MSLocationValidator.is_ms_location(f"{title} {location} {text_content}")
                        
                        if is_ms:
                            link_elem = container.find('a', href=True)
                            job_link = ""
                            if link_elem:
                                href = link_elem.get('href')
                                if href:
                                    job_link = href if href.startswith('http') else f"{base_url}{href}"
                            
                            job_id = f"prop-{self.company.id}-{len(jobs)+1:03d}-{int(time.time()) % 1000}"
                            
                            job = MSJob(
                                id=job_id,
                                titulo=title,
                                empresa=self.company.nome,
                                empresa_id=self.company.id,
                                setor=self.company.setor,
                                cidade=city,
                                estado="MS",
                                localizacao_completa=cleaned_location,
                                tipo_contrato=contract_type or "Não informado",
                                trabalho_remoto="remoto" in text_lower,
                                link=job_link,
                                data_coleta=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                ms_verified=True,
                                extraction_method="proprietary_semantic",
                                responsabilidades=self.extract_details_from_text(text_content, "responsabilidades"),
                                requisitos=self.extract_details_from_text(text_content, "requisitos"),
                                beneficios=self.extract_details_from_text(text_content, "beneficios")
                            )
                            
                            jobs.append(job)
            
            except Exception:
                continue
        
        return jobs
    
    def extract_details_from_text(self, text_content, detail_type):
        try:
            text_lower = text_content.lower()
            
            if detail_type == "responsabilidades":
                keywords = ['responsabilidades', 'atividades', 'atribuições', 'funções']
            elif detail_type == "requisitos":
                keywords = ['requisitos', 'qualificações', 'exigências', 'formação']
            elif detail_type == "beneficios":
                keywords = ['benefícios', 'vantagens', 'oferecemos', 'plano']
            else:
                return "Não encontrado"
            
            for keyword in keywords:
                if keyword in text_lower:
                    lines = text_content.split('\n')
                    for i, line in enumerate(lines):
                        if keyword in line.lower():
                            detail_text = ""
                            for j in range(i, min(i+5, len(lines))):
                                detail_text += lines[j] + " "
                            
                            if len(detail_text.strip()) > 20:
                                return detail_text.strip()[:400]
            
            return "Não encontrado"
            
        except:
            return "Erro na extração"
    
    def scrape_company_jobs(self) -> List[MSJob]:
        try:
            all_urls = self.get_all_portal_urls()
            
            for base_url in all_urls:
                try:
                    career_urls = self.generate_career_urls(base_url)
                    
                    for url in career_urls[:CONFIG.max_career_urls_per_company]:
                        print(f"🔍 Testando URL: {url}")
                        
                        soup = self.fetch_page_content(url)
                        page_jobs = []
                        
                        if soup:
                            page_jobs = self.extract_jobs_from_page(soup, base_url)
                        
                        if not page_jobs:
                            if self.is_senior_platform(url):
                                print(f"🏢 Senior platform detectada, usando extrator especializado...")
                                senior_jobs = self.extract_with_senior_platform(url)
                                if senior_jobs:
                                    page_jobs = senior_jobs
                            elif self.should_use_selenium(url):
                                print(f"🔧 Tentando extração avançada com Selenium...")
                                selenium_jobs = self.extract_with_selenium(url)
                                if selenium_jobs:
                                    page_jobs = selenium_jobs
                        
                        if page_jobs:
                            self.jobs_data.extend(page_jobs)
                            print(f"✅ Encontradas {len(page_jobs)} vagas em {url}")
                            break
                        else:
                            print(f"⚠️ Nenhuma vaga encontrada em {url}")
                        
                        time.sleep(random.uniform(1, 2))
                
                except Exception as e:
                    print(f"❌ Erro processando {base_url}: {e}")
                    continue
            
            return self.jobs_data
            
        except Exception:
            return []
    
    def should_use_selenium(self, url: str) -> bool:
        selenium_indicators = [
            'senior.com.br',
            'gupy.io',
            'workday.com',
            'bamboohr.com',
            'angular',
            'react',
            'app.'
        ]
        
        return any(indicator in url.lower() for indicator in selenium_indicators)
    
    def is_senior_platform(self, url: str) -> bool:
        senior_indicators = [
            'senior.com.br',
            'senior',
            'hcm.senior',
            'platform.senior'
        ]
        
        return any(indicator in url.lower() for indicator in senior_indicators)
    
    def extract_with_senior_platform(self, url: str) -> List[MSJob]:
        try:
            print(f"🏢 Detectada plataforma Senior: {url}")
            
            senior_scraper = SeniorPlatformScraper(self.company, url)
            
            jobs = senior_scraper.scrape_all_jobs()
            
            if not jobs:
                print("🔧 API extraction failed, trying Selenium fallback...")
                selenium_jobs = senior_scraper.extract_with_selenium_fallback()
                if selenium_jobs:
                    ms_jobs = []
                    for job_dict in selenium_jobs:
                        ms_job = MSJob(
                            id=job_dict['id'],
                            titulo=job_dict['titulo'],
                            empresa=job_dict['empresa'],
                            empresa_id=job_dict['empresa_id'],
                            setor=job_dict['setor'],
                            cidade=job_dict['cidade'],
                            estado=job_dict['estado'],
                            localizacao_completa=job_dict['localizacao_completa'],
                            tipo_contrato=job_dict['tipo_contrato'],
                            trabalho_remoto=job_dict['trabalho_remoto'],
                            link=job_dict['link'],
                            data_coleta=job_dict['data_coleta'],
                            ms_verified=job_dict['ms_verified'],
                            extraction_method=job_dict['extraction_method'],
                            responsabilidades=job_dict['responsabilidades'],
                            requisitos=job_dict['requisitos'],
                            beneficios=job_dict['beneficios']
                        )
                        ms_jobs.append(ms_job)
                    jobs = ms_jobs
            else:
                if jobs and isinstance(jobs[0], dict):
                    ms_jobs = []
                    for job_dict in jobs:
                        ms_job = MSJob(
                            id=job_dict['id'],
                            titulo=job_dict['titulo'],
                            empresa=job_dict['empresa'],
                            empresa_id=job_dict['empresa_id'],
                            setor=job_dict['setor'],
                            cidade=job_dict['cidade'],
                            estado=job_dict['estado'],
                            localizacao_completa=job_dict['localizacao_completa'],
                            tipo_contrato=job_dict['tipo_contrato'],
                            trabalho_remoto=job_dict['trabalho_remoto'],
                            link=job_dict['link'],
                            data_coleta=job_dict['data_coleta'],
                            ms_verified=job_dict['ms_verified'],
                            extraction_method=job_dict['extraction_method'],
                            responsabilidades=job_dict['responsabilidades'],
                            requisitos=job_dict['requisitos'],
                            beneficios=job_dict['beneficios']
                        )
                        ms_jobs.append(ms_job)
                    jobs = ms_jobs
            
            return jobs
            
        except Exception as e:
            print(f"❌ Erro na extração Senior platform: {e}")
            return []

class SeniorPlatformScraper:
    
    def __init__(self, company: Company, base_url: str):
        self.company = company
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.jobs_data = []
        self.access_token = None
        self.token_expires_at = None
        
        self.tenant = "copasul"
        self.tenant_domain = "copasul.coop.br"
        self.platform_base = "https://platform.senior.com.br"
        self.hcm_url = f"{self.platform_base}/hcmrs/hcm/curriculo/?tenant={self.tenant}&tenantdomain={self.tenant_domain}&fromRecruitment=false#!/vacancies/list"
        
        self.setup_session()
    
    def setup_session(self):
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/json',
            'Origin': self.platform_base,
            'Referer': self.hcm_url,
            'tenant': self.tenant,
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
        self.session.timeout = 30
    
    def authenticate(self) -> bool:
        try:
            print(f"🔐 Autenticando com plataforma Senior: {self.base_url}")
            
            initial_response = self.session.get(f"{self.base_url}/")
            if initial_response.status_code != 200:
                print(f"❌ Falha ao carregar página inicial: {initial_response.status_code}")
                return False
            
            client_id = self.extract_client_id(initial_response.text)
            if not client_id:
                print("❌ Não foi possível extrair client_id da página")
                return False
            
            token_url = f"{self.base_url}/api/oauth/token"
            
            token_headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {base64.b64encode(f"{client_id}:".encode()).decode()}'
            }
            
            token_data = {
                'grant_type': 'client_credentials',
                'scope': 'public'
            }
            
            token_response = self.session.post(
                token_url,
                data=token_data,
                headers=token_headers
            )
            
            if token_response.status_code == 200:
                token_info = token_response.json()
                self.access_token = token_info.get('access_token')
                expires_in = token_info.get('expires_in', 3600)
                self.token_expires_at = time.time() + expires_in
                
                self.session.headers['Authorization'] = f'Bearer {self.access_token}'
                
                print(f"✅ Autenticação bem-sucedida. Token expira em {expires_in}s")
                return True
            else:
                print(f"❌ Falha na autenticação: {token_response.status_code}")
                try:
                    print(f"Resposta: {token_response.text}")
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"❌ Erro durante autenticação: {e}")
            return False
    
    def extract_client_id(self, page_content: str) -> Optional[str]:
        try:
            patterns = [
                r'clientId["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'client_id["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'CLIENT_ID["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'oauthConfig.*?clientId["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                r'window\.env\s*=.*?clientId["\']?\s*[:=]\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_content, re.IGNORECASE | re.DOTALL)
                if match:
                    client_id = match.group(1)
                    print(f"✓ Client ID encontrado: {client_id[:8]}...")
                    return client_id
            
            soup = BeautifulSoup(page_content, 'html.parser')
            
            meta_selectors = [
                'meta[name="oauth-client-id"]',
                'meta[name="client-id"]',
                '[data-client-id]',
                '[data-oauth-client]'
            ]
            
            for selector in meta_selectors:
                element = soup.select_one(selector)
                if element:
                    client_id = element.get('content') or element.get('data-client-id') or element.get('data-oauth-client')
                    if client_id:
                        print(f"✓ Client ID encontrado em meta: {client_id[:8]}...")
                        return client_id
            
            default_client_ids = [
                'hcm-public-client',
                'senior-hcm-client',
                'public-client',
                'webapp-client'
            ]
            
            for default_id in default_client_ids:
                if default_id in page_content.lower():
                    print(f"✓ Usando client ID padrão: {default_id}")
                    return default_id
            
            print("⚠️ Client ID não encontrado, tentando valor padrão")
            return 'hcm-public-client'
            
        except Exception as e:
            print(f"⚠️ Erro ao extrair client_id: {e}")
            return 'hcm-public-client'
    
    def is_token_valid(self) -> bool:
        return (self.access_token is not None and 
                self.token_expires_at is not None and 
                time.time() < self.token_expires_at - 60)
    
    def ensure_authentication(self) -> bool:
        if not self.is_token_valid():
            return self.authenticate()
        return True
    
    def get_job_listings(self, page: int = 0, per_page: int = 100) -> List[Dict]:
        try:
            api_endpoints = [
                f"{self.platform_base}/t/{self.tenant_domain}/bridge/1.0/rest/hcm/vacancymanagement/queries/getPublicVacancies",
                f"{self.platform_base}/bridge/1.0/rest/hcm/vacancymanagement/queries/getPublicVacancies",
                f"{self.platform_base}/api/hcm/vacancymanagement/queries/getPublicVacancies",
                f"{self.platform_base}/rest/hcm/vacancymanagement/queries/getPublicVacancies",
                f"{self.platform_base}/hcm/vacancymanagement/queries/getPublicVacancies"
            ]
            
            for api_url in api_endpoints:
                payload = {
                    "tenant": self.tenant,
                    "page": page,
                    "size": per_page,
                    "orderBy": "publicationDate desc"
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "tenant": self.tenant,
                    "Accept": "application/json, text/plain, */*",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                
                print(f"🔍 Tentando endpoint: {api_url}")
                
                try:
                    response = self.session.post(api_url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"✅ Resposta API recebida: {response.status_code}")
                        
                        jobs = []
                        if isinstance(data, dict):
                            if 'content' in data:
                                jobs = data['content']
                                print(f"✅ Encontradas {len(jobs)} vagas via API (paginated)")
                            elif 'data' in data:
                                jobs = data['data']
                                print(f"✅ Encontradas {len(jobs)} vagas via API (data)")
                            elif 'vacancies' in data:
                                jobs = data['vacancies']
                                print(f"✅ Encontradas {len(jobs)} vagas via API (vacancies)")
                            elif 'result' in data:
                                jobs = data['result']
                                print(f"✅ Encontradas {len(jobs)} vagas via API (result)")
                            elif isinstance(data, list):
                                jobs = data
                                print(f"✅ Encontradas {len(jobs)} vagas via API (direct list)")
                            else:
                                jobs = [data] if data else []
                                print(f"✅ Encontrada 1 vaga via API (single object)")
                        elif isinstance(data, list):
                            jobs = data
                            print(f"✅ Encontradas {len(jobs)} vagas via API (list)")
                        
                        if jobs:
                            print(f"🎯 Endpoint funcional encontrado: {api_url}")
                            return jobs
                        else:
                            print(f"⚠️ Endpoint {api_url} retornou resposta vazia")
                        
                    else:
                        print(f"⚠️ Endpoint {api_url}: HTTP {response.status_code}")
                        if response.status_code == 404:
                            continue
                
                except Exception as e:
                    print(f"⚠️ Erro no endpoint {api_url}: {e}")
                    continue
            
            print("❌ Todos os endpoints da API falharam")
            return []
        
        except Exception as e:
            print(f"❌ Erro ao obter listagem de vagas COPASUL: {e}")
            return []
            
        return self.get_job_listings_fallback(page, per_page)
    
    def get_job_listings_fallback(self, page: int = 1, per_page: int = 20) -> List[Dict]:
        try:
            if not self.ensure_authentication():
                print("❌ Falha na autenticação para obter vagas (fallback)")
                return []
            
            api_endpoints = [
                f"/api/hcm/v1/vacancies",
                f"/api/v1/jobs", 
                f"/api/v1/positions",
                f"/api/hcm/jobs",
                f"/api/recruitment/vacancies"
            ]
            
            for endpoint in api_endpoints:
                try:
                    api_url = f"{self.base_url}{endpoint}"
                    
                    params = {
                        'page': page,
                        'size': per_page,
                        'active': True,
                        'status': 'OPEN',
                        'sort': 'createdDate,desc'
                    }
                    
                    print(f"🔍 Tentando endpoint: {endpoint}")
                    
                    response = self.session.get(api_url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        jobs = []
                        if isinstance(data, dict):
                            if 'content' in data:
                                jobs = data['content']
                            elif 'data' in data:
                                jobs = data['data']
                            elif 'vacancies' in data:
                                jobs = data['vacancies']
                            elif 'jobs' in data:
                                jobs = data['jobs']
                            else:
                                jobs = [data] if data else []
                        elif isinstance(data, list):
                            jobs = data
                        
                        if jobs:
                            print(f"✅ Encontradas {len(jobs)} vagas via {endpoint}")
                            return jobs
                        else:
                            print(f"⚠️ Endpoint {endpoint} retornou resposta vazia")
                    
                    elif response.status_code == 401:
                        print(f"🔐 Token expirado, reautenticando...")
                        if self.authenticate():
                            response = self.session.get(api_url, params=params)
                            if response.status_code == 200:
                                data = response.json()
                                jobs = self.extract_jobs_from_response(data)
                                if jobs:
                                    print(f"✅ Encontradas {len(jobs)} vagas via {endpoint} (após reauth)")
                                    return jobs
                    
                    else:
                        print(f"⚠️ Endpoint {endpoint}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ Erro no endpoint {endpoint}: {e}")
                    continue
            
            print("❌ Nenhum endpoint da API retornou vagas válidas")
            return []
            
        except Exception as e:
            print(f"❌ Erro ao obter listagem de vagas: {e}")
            return []
    
    def extract_jobs_from_response(self, data: Dict) -> List[Dict]:
        try:
            jobs = []
            
            if isinstance(data, dict):
                if 'content' in data:
                    jobs = data['content']
                elif 'data' in data:
                    jobs = data['data']
                elif 'vacancies' in data:
                    jobs = data['vacancies']
                elif 'jobs' in data:
                    jobs = data['jobs']
                else:
                    jobs = [data] if data else []
            elif isinstance(data, list):
                jobs = data
                
            return jobs if isinstance(jobs, list) else []
            
        except Exception:
            return []
    
    def get_job_details(self, job_id: str) -> Optional[Dict]:
        try:
            api_url = f"{self.platform_base}/t/{self.tenant_domain}/bridge/1.0/rest/hcm/vacancymanagement/entities/vacancy/{job_id}"
            
            headers = {
                "Content-Type": "application/json",
                "tenant": self.tenant,
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            print(f"🔍 Obtendo detalhes da vaga: {job_id}")
            
            response = self.session.post(api_url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ Erro ao obter detalhes da vaga {job_id}: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ Erro na requisição de detalhes: {e}")
        
        return self.get_job_details_fallback(job_id)
    
    def get_job_details_fallback(self, job_id: str) -> Optional[Dict]:
        try:
            if not self.ensure_authentication():
                return None
            
            detail_endpoints = [
                f"/api/hcm/v1/vacancies/{job_id}",
                f"/api/v1/jobs/{job_id}",
                f"/api/v1/positions/{job_id}",
                f"/api/hcm/jobs/{job_id}"
            ]
            
            for endpoint in detail_endpoints:
                try:
                    api_url = f"{self.base_url}{endpoint}"
                    response = self.session.get(api_url)
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 401:
                        if self.authenticate():
                            response = self.session.get(api_url)
                            if response.status_code == 200:
                                return response.json()
                                
                except Exception:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def map_senior_job_to_ms_job(self, senior_job: Dict, job_details: Dict = None) -> Optional[MSJob]:
        try:
            job_id_field = self.find_field_value(senior_job, ['id', 'jobId', 'vacancyId', 'positionId'])
            title = self.find_field_value(senior_job, ['title', 'name', 'jobTitle', 'position', 'cargo'])
            
            if not title:
                return None
            
            location_data = self.extract_location_info(senior_job, job_details)
            if not location_data:
                return None
                
            is_ms, city, location_full = location_data
            if not is_ms:
                return None
            
            description = self.find_field_value(senior_job, ['description', 'jobDescription', 'summary'])
            requirements = self.find_field_value(senior_job, ['requirements', 'qualifications', 'requisitos'])
            responsibilities = self.find_field_value(senior_job, ['responsibilities', 'duties', 'atividades'])
            benefits = self.find_field_value(senior_job, ['benefits', 'beneficios', 'perks'])
            
            contract_type = self.find_field_value(senior_job, ['contractType', 'employmentType', 'tipoContrato'])
            if not contract_type:
                contract_type = "Efetivo"
            
            remote_indicators = ['remote', 'remoto', 'homeoffice', 'home_office', 'home office']
            is_remote = any(indicator in str(senior_job).lower() for indicator in remote_indicators)
            
            job_link = self.generate_job_link(job_id_field)
            
            ms_job_id = f"senior-{self.company.id}-{len(self.jobs_data)+1:03d}-{int(time.time()) % 1000}"
            
            job = MSJob(
                id=ms_job_id,
                titulo=title,
                empresa=self.company.nome,
                empresa_id=self.company.id,
                setor=self.company.setor,
                cidade=city,
                estado="MS",
                localizacao_completa=location_full,
                tipo_contrato=contract_type,
                trabalho_remoto=is_remote,
                link=job_link,
                data_coleta=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                ms_verified=True,
                extraction_method="senior_platform_api",
                responsabilidades=responsibilities or "Não informado",
                requisitos=requirements or "Não informado",
                beneficios=benefits or "Não informado"
            )
            
            return job
            
        except Exception as e:
            print(f"⚠️ Erro ao mapear vaga Senior: {e}")
            return None
    
    def find_field_value(self, data: Dict, field_names: List[str]) -> str:
        try:
            for field_name in field_names:
                if field_name in data and data[field_name]:
                    value = data[field_name]
                    return str(value).strip() if value else ""
                    
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, dict) and field_name in value:
                            nested_value = value[field_name]
                            return str(nested_value).strip() if nested_value else ""
            
            return ""
            
        except Exception:
            return ""
    
    def extract_location_info(self, senior_job: Dict, job_details: Dict = None) -> Optional[tuple]:
        try:
            all_data = {**senior_job}
            if job_details:
                all_data.update(job_details)
            
            location_fields = [
                'location', 'city', 'cidade', 'local', 'workplace', 
                'address', 'endereco', 'state', 'estado'
            ]
            
            location_text = ""
            for field in location_fields:
                value = self.find_field_value(all_data, [field])
                if value:
                    location_text += f" {value}"
            
            if 'location' in all_data and isinstance(all_data['location'], dict):
                location_obj = all_data['location']
                for field in ['city', 'state', 'name', 'description']:
                    if field in location_obj:
                        location_text += f" {location_obj[field]}"
            
            full_text = f"{location_text} {str(all_data)}"
            
            is_ms, city, cleaned_location = MSLocationValidator.is_ms_location(full_text)
            
            if is_ms:
                return (True, city, cleaned_location)
            
            return None
            
        except Exception:
            return None
    
    def generate_job_link(self, job_id: str) -> str:
        if not job_id:
            return ""
        
        url_patterns = [
            f"{self.base_url}/jobs/{job_id}",
            f"{self.base_url}/vacancies/{job_id}",
            f"{self.base_url}/positions/{job_id}",
            f"{self.base_url}/career/{job_id}",
            f"{self.base_url}/apply/{job_id}"
        ]
        
        return url_patterns[0]
    
    def scrape_all_jobs(self) -> List[Dict[str, Any]]:
        try:
            print(f"🏢 Iniciando extração Senior para {self.company.nome}")
            print(f"🌐 URL: {self.base_url}")
            
            if not self.authenticate():
                print("❌ Falha na autenticação inicial")
                return []
            
            page = 1
            per_page = 50
            total_jobs_found = 0
            consecutive_empty_pages = 0
            max_empty_pages = 3
            max_pages = 20
            
            while page < max_pages:
                print(f"📄 Processando página {page + 1}...")
                
                jobs_data = self.get_job_listings(page=page, per_page=per_page)
                
                if not jobs_data:
                    consecutive_empty_pages += 1
                    print(f"⚠️ Página {page} vazia ({consecutive_empty_pages}/{max_empty_pages})")
                    
                    if consecutive_empty_pages >= max_empty_pages:
                        print(f"⏹️ Parando após {consecutive_empty_pages} páginas vazias consecutivas")
                        break
                    
                    page += 1
                    continue
                
                consecutive_empty_pages = 0
                jobs_processed = 0
                
                for job_data in jobs_data:
                    try:
                        job_id = self.find_field_value(job_data, ['id', 'jobId', 'vacancyId'])
                        job_details = None
                        
                        if job_id:
                            job_details = self.get_job_details(job_id)
                        
                        ms_job = self.map_senior_job_to_ms_job(job_data, job_details)
                        
                        if ms_job:
                            job_dict = ms_job.to_dict()
                            
                            if self.validate_senior_job_data(job_dict):
                                enhanced_job_dict = self.enhance_job_data_with_senior_context(job_dict)
                                self.jobs_data.append(enhanced_job_dict)
                                jobs_processed += 1
                                total_jobs_found += 1
                            else:
                                print(f"⚠️ Vaga rejeitada por falha na validação: {ms_job.titulo}")
                            
                    except Exception as e:
                        print(f"⚠️ Erro ao processar vaga: {e}")
                        continue
                
                print(f"✅ Página {page + 1}: {jobs_processed} vagas MS de {len(jobs_data)} total")
                
                if len(jobs_data) < per_page:
                    print(f"📄 Página retornou {len(jobs_data)} < {per_page} itens - última página")
                    break
                
                page += 1
                time.sleep(1)
            
            print(f"🎯 Extração Senior concluída: {total_jobs_found} vagas MS encontradas")
            return self.jobs_data
            
        except Exception as e:
            print(f"❌ Erro na extração Senior: {e}")
            return []
    
    def setup_selenium_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            prefs = {
                "profile.default_content_setting_values": {
                    "images": 2,
                    "media": 2,
                    "stylesheets": 1
                }
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.implicitly_wait(10)
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao configurar driver Selenium: {e}")
            return False
    
    def extract_with_selenium_fallback(self) -> List[Dict[str, Any]]:
        try:
            print("🔧 Iniciando extração com Selenium (fallback)")
            
            if not self.setup_selenium_driver():
                print("❌ Falha na configuração do driver Selenium")
                return []
            
            try:
                print(f"🌐 Navegando para COPASUL HCM: {self.hcm_url}")
                self.driver.get(self.hcm_url)
                
                print("⏳ Aguardando carregamento do Angular...")
                time.sleep(8)
                
                try:
                    WebDriverWait(self.driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[ng-app], [data-ng-app]"))
                    )
                    print("✅ Angular app detectada")
                except TimeoutException:
                    print("⚠️ Angular app não detectada, continuando...")
                
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ng-repeat*='vacancy'], .vacancy-list, .jobs-list"))
                    )
                    print("✅ Container de vagas detectado")
                except TimeoutException:
                    print("⚠️ Container de vagas não detectado")
                
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading, .spinner, .loading-spinner, .ng-hide"))
                    )
                    print("✅ Loading concluído")
                except TimeoutException:
                    print("⚠️ Loading ainda ativo, continuando...")
                
                time.sleep(3)
                
                all_jobs = []
                max_pages = 5
                current_page = 1
                
                while current_page <= max_pages:
                    print(f"🔍 Extraindo página {current_page} via Selenium...")
                    
                    page_jobs = self.extract_jobs_from_selenium()
                    
                    if page_jobs:
                        all_jobs.extend(page_jobs)
                        print(f"✅ Página {current_page}: {len(page_jobs)} vagas extraídas")
                        
                        if current_page < max_pages:
                            if not self.handle_pagination_selenium():
                                print(f"⏹️ Não foi possível avançar para página {current_page + 1}")
                                break
                        
                    else:
                        print(f"⚠️ Página {current_page} sem vagas - parando")
                        break
                    
                    current_page += 1
                
                print(f"🎯 Selenium extraction concluída: {len(all_jobs)} vagas total")
                return all_jobs
                
            finally:
                if hasattr(self, 'driver') and self.driver:
                    self.driver.quit()
                    
        except Exception as e:
            print(f"❌ Erro na extração Selenium: {e}")
            return []
    
    def extract_jobs_from_selenium(self) -> List[Dict[str, Any]]:
        jobs = []
        
        try:
            time.sleep(3)
            
            job_selectors = [
                '[data-ng-repeat*="vacancy"]',
                '.vacancy-list .vacancy-item',
                '.jobs-list .job-item', 
                '.vacancy-card',
                
                '[ng-repeat*="vacancy"]',
                '[data-ng-repeat*="job"]',
                '[ng-repeat*="job"]',
                
                '.vacancy-item', '.job-item', '.position-item',
                '.hcm-job', '.senior-job', '.career-item',
                
                '.vacancy-list li', '.jobs-list li',
                '.vacancy-container > div', '.jobs-container > div'
            ]
            
            job_elements = []
            
            for selector in job_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        job_elements = elements
                        print(f"✓ Encontrados {len(elements)} elementos com seletor: {selector}")
                        break
                except Exception:
                    continue
            
            if not job_elements:
                xpath_selectors = [
                    "//*[@data-ng-repeat and contains(@data-ng-repeat, 'vacancy')]",
                    "//*[@ng-repeat and contains(@ng-repeat, 'vacancy')]",
                    "//*[@data-ng-repeat and contains(@data-ng-repeat, 'job')]",
                    
                    "//div[contains(@class, 'vacancy') or contains(@class, 'job')]",
                    "//li[contains(@class, 'vacancy') or contains(@class, 'job')]",
                    
                    "//h3[contains(text(), 'Analista') or contains(text(), 'Técnico') or contains(text(), 'Assistente') or contains(text(), 'Coordenador')]/..",
                    "//h4[contains(text(), 'Analista') or contains(text(), 'Técnico') or contains(text(), 'Assistente') or contains(text(), 'Coordenador')]/..",
                    
                    "//*[@data-ng-bind or @ng-bind]/..",
                    
                    "//*[contains(@class, 'card') and (contains(., 'vaga') or contains(., 'job') or contains(., 'cargo'))]",
                    "//div[contains(text(), 'COPASUL')]/../.."
                ]
                
                for xpath in xpath_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        if elements:
                            job_elements = elements[:20]
                            print(f"✓ Encontrados {len(elements)} elementos com XPath")
                            break
                    except Exception:
                        continue
            
            if not job_elements:
                print("⚠️ Nenhum elemento de vaga encontrado")
                return []
            
            print(f"🔍 Processando {len(job_elements)} elementos de vaga...")
            
            for i, element in enumerate(job_elements[:25]):
                try:
                    job_data = self.extract_job_data_from_element(element)
                    if job_data:
                        if self.validate_senior_job_data(job_data):
                            enhanced_job_data = self.enhance_job_data_with_senior_context(job_data)
                            jobs.append(enhanced_job_data)
                        else:
                            print(f"⚠️ Vaga rejeitada por falha na validação Selenium: {job_data.get('titulo', 'N/A')}")
                        
                except Exception as e:
                    print(f"⚠️ Erro ao processar elemento {i+1}: {e}")
                    continue
            
            print(f"✅ Extraídas {len(jobs)} vagas via Selenium")
            return jobs
            
        except Exception as e:
            print(f"❌ Erro na extração de vagas com Selenium: {e}")
            return []
    
    def extract_job_data_from_element(self, element) -> Optional[Dict[str, Any]]:
        try:
            text_content = element.text.strip()
            
            if not text_content or len(text_content) < 10:
                return None
            
            title = self.extract_title_from_element(element, text_content)
            if not title:
                return None
            
            is_ms, city, location_full = MSLocationValidator.is_ms_location(text_content)
            if not is_ms:
                return None
            
            contract_type = self.extract_contract_type_from_text(text_content)
            is_remote = any(indicator in text_content.lower() for indicator in ['remoto', 'remote', 'home office'])
            
            job_link = self.extract_link_from_element(element)
            
            details = self.extract_job_details_from_text(text_content)
            
            job_dict = {
                'id': f"senior-selenium-{self.company.id}-{int(time.time()) % 10000}",
                'titulo': title,
                'empresa': self.company.nome,
                'empresa_id': self.company.id,
                'setor': self.company.setor,
                'cidade': city,
                'estado': 'MS',
                'localizacao_completa': location_full,
                'tipo_contrato': contract_type,
                'trabalho_remoto': is_remote,
                'link': job_link,
                'data_coleta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ms_verified': True,
                'extraction_method': 'senior_platform_selenium',
                'responsabilidades': details.get('responsabilidades', 'Não informado'),
                'requisitos': details.get('requisitos', 'Não informado'),
                'beneficios': details.get('beneficios', 'Não informado')
            }
            
            return job_dict
            
        except Exception as e:
            print(f"⚠️ Erro ao extrair dados do elemento: {e}")
            return None
    
    def extract_title_from_element(self, element, text_content: str) -> Optional[str]:
        try:
            headings = element.find_elements(By.TAG_NAME, "h1") + \
                      element.find_elements(By.TAG_NAME, "h2") + \
                      element.find_elements(By.TAG_NAME, "h3") + \
                      element.find_elements(By.TAG_NAME, "h4")
            
            for heading in headings:
                title_text = heading.text.strip()
                if self.is_valid_job_title_text(title_text):
                    return title_text
            
            title_selectors = [
                '[data-ng-bind*="title"]', '[ng-bind*="title"]',
                '[data-ng-bind*="name"]', '[ng-bind*="name"]',
                
                '.vacancy-title', '.job-title', '.position-title',
                '[class*="title"]', '[class*="nome"]', '[class*="cargo"]',
                '.mat-card-title', '.card-title',
                
                '.hcm-title', '.senior-title'
            ]
            
            for selector in title_selectors:
                try:
                    title_elements = element.find_elements(By.CSS_SELECTOR, selector)
                    for title_elem in title_elements:
                        title_text = title_elem.text.strip()
                        if self.is_valid_job_title_text(title_text):
                            return title_text
                except Exception:
                    continue
            
            lines = text_content.split('\n')
            for line in lines[:3]:
                line = line.strip()
                if self.is_valid_job_title_text(line):
                    return line
            
            return None
            
        except Exception:
            return None
    
    def is_valid_job_title_text(self, text: str) -> bool:
        if not text or len(text) < 5 or len(text) > 100:
            return False
        
        job_indicators = [
            'analista', 'assistente', 'coordenador', 'gerente', 'supervisor',
            'técnico', 'operador', 'auxiliar', 'especialista', 'consultor',
            'diretor', 'engenheiro', 'administrador', 'vendedor', 'contador',
            'desenvolvedor', 'programador', 'designer', 'estagiário'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in job_indicators)
    
    def extract_contract_type_from_text(self, text: str) -> str:
        try:
            text_lower = text.lower()
            
            contract_types = {
                'efetivo': ['efetivo', 'clt', 'carteira assinada'],
                'estágio': ['estágio', 'estagiário', 'trainee'],
                'temporário': ['temporário', 'temp', 'contrato determinado'],
                'terceirizado': ['terceirizado', 'terceiro'],
                'pj': ['pj', 'pessoa jurídica', 'freelancer'],
                'jovem aprendiz': ['jovem aprendiz', 'aprendiz']
            }
            
            for contract_type, keywords in contract_types.items():
                if any(keyword in text_lower for keyword in keywords):
                    return contract_type.title()
            
            return "Efetivo"
            
        except Exception:
            return "Não informado"
    
    def extract_link_from_element(self, element) -> str:
        try:
            if element.tag_name == 'a':
                href = element.get_attribute('href')
                if href and href.startswith('http'):
                    return href
            
            links = element.find_elements(By.TAG_NAME, 'a')
            for link in links:
                href = link.get_attribute('href')
                if href and href.startswith('http'):
                    href_lower = href.lower()
                    if any(keyword in href_lower for keyword in ['job', 'vaga', 'career', 'position', 'apply']):
                        return href
                    if not any(skip in href_lower for skip in ['mailto:', 'tel:', 'javascript:', '#']):
                        return href
            
            return ""
            
        except Exception:
            return ""
    
    def extract_job_details_from_text(self, text: str) -> Dict[str, str]:
        details = {
            'responsabilidades': 'Não informado',
            'requisitos': 'Não informado',
            'beneficios': 'Não informado'
        }
        
        try:
            text_lower = text.lower()
            
            resp_keywords = ['responsabilidades', 'atividades', 'atribuições', 'funções']
            for keyword in resp_keywords:
                if keyword in text_lower:
                    details['responsabilidades'] = self.extract_section_text(text, keyword)
                    break
            
            req_keywords = ['requisitos', 'qualificações', 'exigências', 'perfil']
            for keyword in req_keywords:
                if keyword in text_lower:
                    details['requisitos'] = self.extract_section_text(text, keyword)
                    break
            
            ben_keywords = ['benefícios', 'vantagens', 'oferecemos']
            for keyword in ben_keywords:
                if keyword in text_lower:
                    details['beneficios'] = self.extract_section_text(text, keyword)
                    break
            
            return details
            
        except Exception:
            return details
    
    def extract_section_text(self, text: str, keyword: str) -> str:
        try:
            text_lower = text.lower()
            start_pos = text_lower.find(keyword.lower())
            
            if start_pos == -1:
                return "Não informado"
            
            section_end = len(text)
            next_keywords = ['responsabilidades', 'requisitos', 'benefícios', 'salário', 'contato']
            
            for next_keyword in next_keywords:
                if next_keyword.lower() != keyword.lower():
                    next_pos = text_lower.find(next_keyword.lower(), start_pos + len(keyword))
                    if next_pos != -1:
                        section_end = min(section_end, next_pos)
            
            section_text = text[start_pos:section_end].strip()
            
            if len(section_text) > 20:
                return section_text[:500]
            
            return "Não informado"
            
        except Exception:
            return "Não informado"
    
    def handle_pagination_selenium(self, max_pages: int = 5) -> bool:
        try:
            pagination_selectors = [
                '[data-ng-click*="nextPage"]', '[ng-click*="nextPage"]',
                '.next-page', '.pagination .next',
                '.page-navigation .next',
                
                '.pagination a[rel="next"]',
                '.pagination .next:not(.disabled)',
                'button[aria-label*="próxima"]',
                'button[aria-label*="next"]'
            ]
            
            for selector in pagination_selectors:
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button and next_button.is_enabled():
                        print(f"✅ Botão próxima página encontrado: {selector}")
                        
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(1)
                        next_button.click()
                        
                        time.sleep(3)
                        
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading, .spinner"))
                            )
                        except TimeoutException:
                            pass
                        
                        return True
                        
                except Exception:
                    continue
            
            try:
                self.driver.execute_script("""
                    var scope = angular.element(document.body).scope();
                    if (scope && scope.nextPage && typeof scope.nextPage === 'function') {
                        scope.nextPage();
                        scope.$apply();
                    }
                """)
                time.sleep(3)
                return True
                
            except Exception:
                pass
            
            return False
            
        except Exception:
            return False
