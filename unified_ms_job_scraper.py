import json
import time
import argparse
import sys
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import unidecode
if sys.platform.startswith('win'):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_scraper.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
@dataclass
class Company:
    id: int
    nome: str
    portal_principal: str
    setor: str = "Diversos"
    cidade: str = "MS"
@dataclass
class MSJob:
    id: str
    titulo: str
    empresa: str
    empresa_id: int
    cidade: str
    link: str
    setor: str = "Diversos"
    estado: str = "MS"
    localizacao_completa: str = ""
    tipo_contrato: str = "Não informado"
    trabalho_remoto: bool = False
    data_coleta: str = ""
    data_publicacao: str = ""
    ms_verified: bool = True
    extraction_method: str = ""
    responsabilidades: str = ""
    requisitos: str = ""
    beneficios: str = ""
    salario: str = ""
    descricao: str = ""
    portal_origem: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}
MS_CITIES = [
    'Campo Grande', 'Dourados', 'Três Lagoas', 'Corumbá', 'Ponta Porã',
    'Naviraí', 'Nova Andradina', 'Maracaju', 'Sidrolândia', 'Caarapó',
    'Aquidauana', 'Paranaíba', 'Chapadão do Sul', 'Coxim', 'Miranda',
    'Bonito', 'Jardim', 'Iguatemi', 'Itaquiraí', 'Água Clara',
    'Ribas do Rio Pardo', 'São Gabriel do Oeste', 'Costa Rica',
    'Anastácio', 'Terenos', 'Inocência', 'Cassilândia', 'Aparecida do Taboado'
]
class MSLocationValidator:
    @staticmethod
    def is_ms_location(text: str) -> tuple[bool, str, str]:
        if not text:
            return False, "", ""
        normalized_text = unidecode.unidecode(text).lower().strip()
        remote_indicators = ['remoto', 'remote', 'home office', 'hibrido']
        if any(indicator in normalized_text for indicator in remote_indicators):
            return True, "Remoto", text.strip()
        for city in MS_CITIES:
            if unidecode.unidecode(city).lower() in normalized_text:
                return True, city, text.strip()
        ms_indicators = ['ms', 'mato grosso do sul']
        if any(indicator in normalized_text for indicator in ms_indicators):
            return True, "Mato Grosso do Sul", text.strip()
        return False, "", ""
class InfoJobsIndependentScraper:
    def __init__(self):
        self.base_url = "https://www.infojobs.com.br/empregos.aspx?provincia=175"
        self.driver = None
        self.ms_cities = MS_CITIES
    def setup_driver(self):
        try:
            logger.info("Configurando driver do Selenium para InfoJobs...")
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--enable-unsafe-swiftshader')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Driver do InfoJobs configurado com sucesso.")
            return True
        except Exception as e:
            logger.error(f"Erro ao configurar driver do InfoJobs: {e}")
            return False
    def scrape_jobs(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        logger.info("Iniciando scraper do InfoJobs.")
        if not self.setup_driver():
            return []
        try:
            job_urls = self.collect_job_urls(max_pages)
            if not job_urls:
                logger.warning("InfoJobs: Nenhuma URL de vaga encontrada.")
                return []
            logger.info(f"InfoJobs: Coletadas {len(job_urls)} URLs. Iniciando extração com 10 workers...")
            all_jobs = []
            processed_count = 0
            failed_count = 0
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_url = {executor.submit(self._worker_extract_details, url, i, self.ms_cities): url for i, url in enumerate(job_urls, 1)}
                for future in as_completed(future_to_url):
                    job_data = future.result()
                    processed_count += 1
                    print(f"  [InfoJobs Progresso: {processed_count}/{len(job_urls)} | Válidas: {len(all_jobs)} | Inválidas: {failed_count}]", end='\r')
                    if job_data:
                        all_jobs.append(job_data)
                    else:
                        failed_count += 1
            print("\n")
            logger.info(f"InfoJobs: Extração concluída. {len(all_jobs)} vagas válidas encontradas de {len(job_urls)} URLs processadas.")
            if failed_count > 0:
                logger.info(f"InfoJobs: {failed_count} URLs inválidas ou inacessíveis ignoradas.")
            return all_jobs
        except Exception as e:
            logger.error(f"Erro durante scraping do InfoJobs: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Driver do InfoJobs fechado.")
    def collect_job_urls(self, max_pages: int) -> List[str]:
        job_urls = set()
        scroll_count = 0
        logger.info("InfoJobs: Coletando URLs com rolagem infinita...")
        self.driver.get(self.base_url)
        time.sleep(3)
        try:
            wait = WebDriverWait(self.driver, 10)
            total_jobs_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="resumeVacancies"]/span')))
            total_jobs_str = total_jobs_element.text.replace('.', '')
            total_jobs = int(total_jobs_str)
            logger.info(f"InfoJobs: Total de vagas encontradas no site: {total_jobs}")
        except (TimeoutException, ValueError) as e:
            logger.info(f"InfoJobs: Não foi possível encontrar o número total de vagas. Continuando com limite de rolagens.")
            total_jobs = float('inf')
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            if scroll_count >= max_pages:
                logger.info(f"InfoJobs: Limite de {int(max_pages)} rolagens atingido.")
                break
            scroll_count += 1
            logger.info(f"InfoJobs: Rolagem {scroll_count}/{max_pages if max_pages != float('inf') else '∞'}... ({len(job_urls)}/{total_jobs if total_jobs != float('inf') else '∞'} URLs)")
            initial_url_count = len(job_urls)
            job_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/vaga-de-']")
            for link in job_links:
                href = link.get_attribute('href')
                if href and '/vaga-de-' in href:
                    job_urls.add(href)
            new_urls_found = len(job_urls) - initial_url_count
            if new_urls_found > 0:
                logger.info(f"   ✅ {new_urls_found} novas URLs encontradas.")
            if len(job_urls) >= total_jobs:
                logger.info(f"InfoJobs: Todas as {total_jobs} vagas foram encontradas.")
                break
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(4)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logger.info("InfoJobs: Fim da lista de vagas alcançado (altura da página não mudou).")
                break
            last_height = new_height
        return list(job_urls)
    @staticmethod
    def _create_worker_driver() -> webdriver.Chrome:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--enable-unsafe-swiftshader')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)
    @staticmethod
    def _worker_extract_details(job_url: str, index: int, ms_cities: List[str]) -> Optional[Dict[str, Any]]:
        driver = None
        try:
            driver = InfoJobsIndependentScraper._create_worker_driver()
            wait = WebDriverWait(driver, 10)
            driver.get(job_url)
            time.sleep(1)
            try:
                cookie_button = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
                cookie_button.click()
                time.sleep(1)
            except TimeoutException:
                pass
            job_data = {'link': job_url}
            try:
                title_element = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="VacancyHeader"]//h2')))
                job_data['titulo'] = title_element.text.strip()
            except:
                try:
                    title_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                    job_data['titulo'] = title_element.text.strip()
                except:
                    job_data['titulo'] = "Título não encontrado"
            try:
                company_element = driver.find_element(By.XPATH, '//*[@id="VacancyHeader"]/div[1]/div/div[1]/div/a')
                job_data['empresa'] = company_element.text.strip()
            except:
                try:
                    company_element = driver.find_element(By.CSS_SELECTOR, "a[href*='/empresa-']")
                    job_data['empresa'] = company_element.text.strip()
                except:
                    job_data['empresa'] = "Empresa não informada"
            try:
                salary_element = driver.find_element(By.XPATH, '//*[@id="VacancyHeader"]/div[1]/div/div[2]/div[2]')
                job_data['salario'] = salary_element.text.strip()
            except:
                try:
                    salary_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='salary'], [class*='salario']")
                    if salary_elements:
                        job_data['salario'] = salary_elements[0].text.strip()
                    else:
                        job_data['salario'] = "A combinar"
                except:
                    job_data['salario'] = "A combinar"
            try:
                desc_element = driver.find_element(By.CSS_SELECTOR, "p.mb-16.text-break.white-space-pre-line")
                full_description = desc_element.text.strip()
                if full_description:
                    job_data['descricao'] = full_description
                    if "MISSÃO" in full_description:
                        mission_section = full_description.split("MISSÃO")[1].split("PRINCIPAIS ATIVIDADES")[0].strip()
                        job_data['responsabilidades'] = mission_section if mission_section else ""
                    if "PRINCIPAIS ATIVIDADES" in full_description:
                        activities_section = full_description.split("PRINCIPAIS ATIVIDADES")[1].strip()
                        activities_clean = activities_section.replace("*", "\n•").replace(";", ";\n")
                        job_data['requisitos'] = activities_clean[:800] + "..." if len(activities_clean) > 800 else activities_clean
            except:
                try:
                    requirements_element = driver.find_element(By.XPATH, '//*[@id="vacancylistDetail"]/div[2]/p[1]')
                    job_data['requisitos'] = requirements_element.text.strip()
                except:
                    try:
                        req_elements = driver.find_elements(By.CSS_SELECTOR, "p, div[class*='description'], [class*='requirement']")
                        for elem in req_elements:
                            text = elem.text.strip()
                            if len(text) > 50 and any(word in text.lower() for word in ['requisito', 'experiência', 'formação', 'escolaridade']):
                                job_data['requisitos'] = text
                                break
                    except:
                        job_data['requisitos'] = ""
                try:
                    desc_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='description'], [class*='detail'], .job-description, #vacancylistDetail")
                    for elem in desc_elements:
                        text = elem.text.strip()
                        if len(text) > 100:
                            job_data['descricao'] = text[:500] + "..." if len(text) > 500 else text
                            break
                except:
                    job_data['descricao'] = ""
            try:
                date_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='date'], [class*='publish'], time, .published")
                for elem in date_elements:
                    date_text = elem.text.strip()
                    if date_text and any(word in date_text.lower() for word in ['publicad', 'há', 'dias', 'semana', 'mês']):
                        job_data['data_publicacao'] = date_text
                        break
            except:
                job_data['data_publicacao'] = ""
            page_text = driver.page_source.lower()
            if any(keyword in page_text for keyword in ['clt', 'efetiv', 'carteira']):
                job_data['tipo_contrato'] = "CLT"
            elif any(keyword in page_text for keyword in ['pj', 'pessoa jurídica', 'freelancer']):
                job_data['tipo_contrato'] = "PJ"
            elif any(keyword in page_text for keyword in ['estágio', 'estagiário']):
                job_data['tipo_contrato'] = "Estágio"
            elif any(keyword in page_text for keyword in ['terceiriz', 'temporár']):
                job_data['tipo_contrato'] = "Temporário"
            else:
                job_data['tipo_contrato'] = "Não informado"
            if any(keyword in page_text for keyword in ['tecnologia', 'ti', 'software', 'desenvolviment']):
                job_data['setor'] = "Tecnologia"
            elif any(keyword in page_text for keyword in ['saúde', 'médic', 'hospital', 'clínic']):
                job_data['setor'] = "Saúde"
            elif any(keyword in page_text for keyword in ['educação', 'ensino', 'escola', 'professor']):
                job_data['setor'] = "Educação"
            elif any(keyword in page_text for keyword in ['vendas', 'comercial', 'marketing']):
                job_data['setor'] = "Comercial"
            elif any(keyword in page_text for keyword in ['construção', 'engenharia', 'obras']):
                job_data['setor'] = "Construção"
            elif any(keyword in page_text for keyword in ['financeiro', 'banco', 'contábil']):
                job_data['setor'] = "Financeiro"
            else:
                job_data['setor'] = "Diversos"
            try:
                location_div = driver.find_element(By.CSS_SELECTOR, "div.mb-8")
                location_text = location_div.text.strip()
                if " - " in location_text:
                    city_state = location_text.split(" - ")[0].strip() + " - " + location_text.split(" - ")[1].split(",")[0].strip()
                    job_data['localizacao'] = city_state
                else:
                    job_data['localizacao'] = location_text.split(",")[0].strip() if "," in location_text else location_text
                try:
                    coord_element = location_div.find_element(By.CSS_SELECTOR, "span.js_UserVagaDistance")
                    latitude = coord_element.get_attribute("data-vagalatitude")
                    longitude = coord_element.get_attribute("data-vagalongitude")
                    if latitude and longitude:
                        job_data['latitude'] = float(latitude)
                        job_data['longitude'] = float(longitude)
                except:
                    pass
            except:
                try:
                    location_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='location'], [class*='cidade']")
                    for elem in location_elements:
                        text = elem.text.strip()
                        if any(city in text for city in ms_cities + ['MS', 'Mato Grosso']):
                            job_data['localizacao'] = text
                            break
                except:
                    job_data['localizacao'] = "Mato Grosso do Sul"
            try:
                job_type_elements = driver.find_elements(By.CSS_SELECTOR, "div svg.icon-buildings")
                for elem in job_type_elements:
                    parent_div = elem.find_element(By.XPATH, "..")
                    job_type_text = parent_div.text.strip().lower()
                    if "presencial" in job_type_text:
                        job_data['trabalho_remoto'] = False
                        job_data['tipo_contrato'] = "Presencial"
                        break
                    elif "remoto" in job_type_text or "home office" in job_type_text:
                        job_data['trabalho_remoto'] = True
                        job_data['tipo_contrato'] = "Remoto"
                        break
                    elif "híbrido" in job_type_text:
                        job_data['trabalho_remoto'] = True
                        job_data['tipo_contrato'] = "Híbrido"
                        break
            except:
                pass
            page_text = driver.page_source.lower()
            if 'trabalho_remoto' not in job_data or job_data['trabalho_remoto'] is None:
                job_data['trabalho_remoto'] = any(keyword in page_text for keyword in ['remoto', 'home office', 'híbrido', 'trabalho remoto', 'remote'])
            if job_data['titulo'] == "Título não encontrado":
                return None
            return InfoJobsIndependentScraper._format_job_data(job_data, index, ms_cities)
        except Exception as e:
            return None
        finally:
            if driver:
                driver.quit()
    @staticmethod
    def _format_job_data(job_data: Dict[str, Any], index: int, ms_cities: List[str]) -> Dict[str, Any]:
        _, city, loc_completa = MSLocationValidator.is_ms_location(job_data.get('localizacao', ''))
        if " - " in job_data.get('localizacao', ''):
            city_part = job_data.get('localizacao', '').split(' - ')[0].strip()
            if city_part in ms_cities:
                city = city_part
        return MSJob(
            id=f"infojobs-{index:04d}-{int(time.time()) % 10000}",
            titulo=job_data.get('titulo', 'Título não encontrado'),
            empresa=job_data.get('empresa', 'Empresa não informada'),
            empresa_id=9999,
            cidade=city,
            link=job_data.get('link', ''),
            setor=job_data.get('setor', 'Diversos'),
            tipo_contrato=job_data.get('tipo_contrato', 'Não informado'),
            trabalho_remoto=job_data.get('trabalho_remoto', False),
            localizacao_completa=loc_completa if loc_completa else job_data.get('localizacao', ''),
            salario=job_data.get('salario', 'A combinar'),
            requisitos=job_data.get('requisitos', ''),
            responsabilidades=job_data.get('responsabilidades', ''),
            descricao=job_data.get('descricao', ''),
            data_publicacao=job_data.get('data_publicacao', ''),
            latitude=job_data.get('latitude'),
            longitude=job_data.get('longitude'),
            data_coleta=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            extraction_method="infojobs_unified_enhanced",
            portal_origem="InfoJobs"
        ).to_dict()
class SimpleGupyScraper:
    def __init__(self, company: Company):
        self.company = company
        self.base_url = company.portal_principal
        self.driver = None
    def setup_driver(self):
        try:
            logger.info(f"Configurando driver para Gupy: {self.company.nome}")
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--window-size=1920,1080')
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            return True
        except Exception as e:
            logger.error(f"Erro ao configurar driver da Gupy para {self.company.nome}: {e}")
            return False
    def scrape_all_jobs(self) -> List[Dict[str, Any]]:
        if not self.setup_driver():
            return []
        logger.info(f"Iniciando scraper Gupy para: {self.company.nome} | URL: {self.base_url}")
        jobs_data = []
        try:
            self.driver.get(self.base_url)
            time.sleep(5)
            job_elements = self.driver.find_elements(By.CSS_SELECTOR, "tr[data-testid^='job-list__row']")
            if not job_elements:
                job_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[data-testid^='job-list__listitem-href']")
            logger.info(f"Gupy ({self.company.nome}): Encontrados {len(job_elements)} elementos de vaga.")
            for element in job_elements:
                try:
                    text = element.text
                    is_ms, city, loc_completa = MSLocationValidator.is_ms_location(text)
                    if is_ms:
                        title_elem = element.find_element(By.CSS_SELECTOR, "td[data-testid^='job-list__cell-job-name']")
                        title = title_elem.text
                        link = element.find_element(By.CSS_SELECTOR, "a").get_attribute('href')
                        job_id = f"gupy-{self.company.id}-{len(jobs_data)+1:03d}"
                        job = MSJob(
                            id=job_id,
                            titulo=title,
                            empresa=self.company.nome,
                            empresa_id=self.company.id,
                            cidade=city,
                            link=link,
                            setor=self.company.setor,
                            tipo_contrato="Não informado",
                            trabalho_remoto=city == "Remoto",
                            localizacao_completa=loc_completa,
                            data_coleta=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            extraction_method="gupy_unified",
                            portal_origem="Gupy"
                        )
                        jobs_data.append(job.to_dict())
                except Exception:
                    continue
            logger.info(f"Gupy ({self.company.nome}): Extraídas {len(jobs_data)} vagas de MS.")
            return jobs_data
        except Exception as e:
            logger.error(f"Erro no scraper Gupy para {self.company.nome}: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
def save_jobs_to_json(jobs: List[Dict[str, Any]], output_file: str):
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        logger.info(f"Resultados salvos com sucesso em {output_file}")
    except Exception as e:
        logger.error(f"Erro ao salvar vagas em JSON: {e}")
def load_gupy_companies_from_json(file_path: str) -> List[Company]:
    gupy_companies = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        all_companies = data.get("portais_carreiras_ms", {}).get("empresas_com_portal_proprio", [])
        logger.info(f"Carregadas {len(all_companies)} empresas do arquivo JSON. Filtrando por Gupy...")
        for company_data in all_companies:
            portal = company_data.get("portal_principal", "")
            if "gupy.io" in portal:
                company = Company(
                    id=company_data.get("id"),
                    nome=company_data.get("nome"),
                    portal_principal=portal,
                    setor=company_data.get("setor", "Diversos"),
                    cidade=company_data.get("cidade", "MS")
                )
                gupy_companies.append(company)
        logger.info(f"Encontradas {len(gupy_companies)} empresas que usam a plataforma Gupy.")
        return gupy_companies
    except FileNotFoundError:
        logger.error(f"Arquivo de empresas não encontrado: {file_path}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Erro ao decodificar o arquivo JSON: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar empresas Gupy: {e}")
        return []
def main():
    parser = argparse.ArgumentParser(description='Scraper Unificado para Gupy e InfoJobs.')
    parser.add_argument('--limit', type=int, help='Limita o número de rolagens de página para o InfoJobs.')
    args = parser.parse_args()
    logger.info("🚀 Iniciando Scraper Unificado para Gupy e InfoJobs 🚀")
    all_jobs = []
    infojobs_max_pages = args.limit if args.limit is not None else 999
    if infojobs_max_pages == 999:
        logger.info("Modo InfoJobs: Rolagem ilimitada (padrão). Use --limit N para limitar.")
    else:
        logger.info(f"Modo InfoJobs: Rolagem limitada a {infojobs_max_pages} páginas.")
    logger.info("="*20 + " FASE 1: INFOJOBS " + "="*20)
    try:
        infojobs_scraper = InfoJobsIndependentScraper()
        infojobs_jobs = infojobs_scraper.scrape_jobs(max_pages=infojobs_max_pages)
        if infojobs_jobs:
            all_jobs.extend(infojobs_jobs)
        logger.info(f"InfoJobs: {len(infojobs_jobs)} vagas coletadas.")
    except Exception as e:
        logger.error(f"Erro fatal na fase do InfoJobs: {e}")
    logger.info("="*20 + " FASE 2: GUPY " + "="*20)
    gupy_companies = load_gupy_companies_from_json("data/json_portais_carreiras_ms.json")
    if not gupy_companies:
        logger.warning("Nenhuma empresa Gupy encontrada no arquivo JSON. Pulando fase Gupy.")
    else:
        for company in gupy_companies:
            try:
                gupy_scraper = SimpleGupyScraper(company)
                gupy_jobs = gupy_scraper.scrape_all_jobs()
                if gupy_jobs:
                    all_jobs.extend(gupy_jobs)
                logger.info(f"Gupy ({company.nome}): {len(gupy_jobs)} vagas coletadas.")
            except Exception as e:
                logger.error(f"Erro fatal no scraper Gupy para {company.nome}: {e}")
    logger.info("="*20 + " FASE 3: FINALIZAÇÃO " + "="*20)
    if all_jobs:
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            job_key = (job.get('titulo'), job.get('empresa'), job.get('cidade'))
            if job_key not in seen:
                seen.add(job_key)
                unique_jobs.append(job)
        output_dir = "output"
        import os
        os.makedirs(output_dir, exist_ok=True)
        output_file = f"{output_dir}/unified_ms_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_jobs_to_json(unique_jobs, output_file)
        logger.info(f"🎉 Processo concluído! Total de {len(unique_jobs)} vagas únicas salvas. 🎉")
        infojobs_count = len([j for j in unique_jobs if j.get('portal_origem') == 'InfoJobs'])
        gupy_count = len(unique_jobs) - infojobs_count
        logger.info(f"Resumo: {infojobs_count} vagas do InfoJobs | {gupy_count} vagas da Gupy.")
    else:
        logger.warning("Nenhuma vaga foi coletada de nenhuma plataforma.")
if __name__ == "__main__":
    main()