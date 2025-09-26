import json
import time
import argparse
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
@dataclass
class InfoJobsVaga:
    titulo: str
    empresa: str
    link: str
    localizacao: str
    data_publicacao: str
    responsabilidades: str = ""
    salario: str = ""
    remoto: bool = False
class InfoJobsIndependentScraper:
    def __init__(self):
        self.base_url = "https://www.infojobs.com.br/empregos.aspx?provincia=175"
        self.driver = None
        self.wait = None
        self.ms_cities = [
            'Campo Grande', 'Dourados', 'Três Lagoas', 'Corumbá', 'Ponta Porã',
            'Naviraí', 'Nova Andradina', 'Maracaju', 'Sidrolândia', 'Caarapó',
            'Aquidauana', 'Paranaíba', 'Chapadão do Sul', 'Coxim', 'Miranda',
            'Bonito', 'Jardim', 'Iguatemi', 'Itaquiraí', 'Água Clara',
            'São Gabriel do Oeste', 'Ivinhema', 'Angélica', 'Mundo Novo'
        ]
    def setup_driver(self):
        try:
            print("🔧 Configurando driver do Selenium...")
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
            self.wait = WebDriverWait(self.driver, 10)
            print("✅ Driver configurado com sucesso")
            return True
        except Exception as e:
            print(f"❌ Erro ao configurar driver: {e}")
            return False
    def scrape_jobs(self, max_pages: Optional[int] = 5, unlimited: bool = False) -> List[Dict[str, Any]]:
        print("🌐 InfoJobs MS Independent Scraper - VERSÃO CORRIGIDA")
        print("=" * 60)
        if not self.setup_driver():
            return []
        try:
            if unlimited or max_pages is None:
                print("🔄 Modo ILIMITADO: Extraindo todas as páginas disponíveis")
                max_pages = float('inf')
            else:
                print(f"📄 Modo LIMITADO: Máximo de {max_pages} páginas")
            all_jobs = []
            job_urls = self.collect_job_urls(max_pages)
            if not job_urls:
                print("⚠️ Nenhuma URL de vaga encontrada")
                return []
            print(f"📋 Coletadas {len(job_urls)} URLs de vagas")
            print(f"🔍 Extraindo informações com 10 workers...")
            processed_count = 0
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_url = {executor.submit(self._worker_extract_details, url, i, self.ms_cities): url for i, url in enumerate(job_urls, 1)}
                for future in as_completed(future_to_url):
                    job_data = future.result()
                    processed_count += 1
                    print(f"  [Progresso: {processed_count}/{len(job_urls)}]", end='\r')
                    if job_data:
                        all_jobs.append(job_data)
            print("\n") 
            if all_jobs:
                filename = self.save_jobs_to_json(all_jobs)
                print(f"\n✅ Scraping concluído!")
                print(f"📄 Arquivo salvo: {filename}")
                print(f"📊 Total de vagas MS coletadas: {len(all_jobs)}")
                self.show_job_samples(all_jobs)
                return all_jobs
            else:
                print("\n⚠️ Nenhuma vaga foi extraída com sucesso")
                return []
        finally:
            if self.driver:
                self.driver.quit()
                print("🔒 Driver fechado")
    def collect_job_urls(self, max_pages: int) -> List[str]:
        job_urls = set()
        scroll_count = 0
        print("🔍 Coletando URLs com rolagem infinita...")
        self.driver.get(self.base_url)
        time.sleep(3)  
        try:
            total_jobs_element = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="resumeVacancies"]/span')))
            total_jobs_str = total_jobs_element.text.replace('.', '')
            total_jobs = int(total_jobs_str)
            print(f"📊 Total de vagas encontradas no site: {total_jobs}")
        except (TimeoutException, ValueError) as e:
            print(f"⚠️ Não foi possível encontrar o número total de vagas. O scraper continuará com o limite de rolagens. Erro: {e}")
            total_jobs = float('inf')
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            if scroll_count >= max_pages:
                print(f"🏁 Limite de {int(max_pages)} rolagens atingido.")
                break
            scroll_count += 1
            print(f"🔄 Rolagem {scroll_count}/{max_pages if max_pages != float('inf') else '∞'}... ({len(job_urls)}/{total_jobs if total_jobs != float('inf') else '∞'} URLs)")
            initial_url_count = len(job_urls)
            job_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/vaga-de-']")
            for link in job_links:
                href = link.get_attribute('href')
                if href and '/vaga-de-' in href:
                    job_urls.add(href)
            new_urls_found = len(job_urls) - initial_url_count
            if new_urls_found > 0:
                print(f"   ✅ {new_urls_found} novas URLs encontradas.")
            if len(job_urls) >= total_jobs:
                print(f"🏁 Todas as {total_jobs} vagas foram encontradas.")
                break
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(4)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("🏁 Fim da lista de vagas alcançado (altura da página não mudou).")
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
            job_data = {
                'titulo': '', 'empresa': '', 'link': job_url, 'localizacao': '',
                'data_publicacao': '', 'responsabilidades': '', 'salario': '',
                'remoto': False, 'requisitos': '', 'beneficios': ''
            }
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
                except:
                    job_data['salario'] = ""
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
                location_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='location'], [class*='cidade']")
                for elem in location_elements:
                    text = elem.text.strip()
                    if any(city in text for city in ms_cities + ['MS', 'Mato Grosso']):
                        job_data['localizacao'] = text
                        break
            except:
                job_data['localizacao'] = "Mato Grosso do Sul"
            page_text = driver.page_source.lower()
            job_data['remoto'] = any(keyword in page_text for keyword in ['remoto', 'home office', 'híbrido'])
            if InfoJobsIndependentScraper._is_valid_ms_job(job_data['titulo'], job_data.get('localizacao', ''), job_url, ms_cities):
                return InfoJobsIndependentScraper._format_job_data(job_data, index, ms_cities)
            else:
                return None
        except Exception as e:
            print(f"[Worker Error] Failed to process {job_url}: {e}")
            return None
        finally:
            if driver:
                driver.quit()
    @staticmethod
    def _is_valid_ms_job(title: str, location: str, link: str, ms_cities: List[str]) -> bool:
        if not title or len(title) < 3 or title == "Título não encontrado":
            return False
        if location:
            if any(city in location for city in ms_cities + ['MS', 'Mato Grosso']):
                return True
        return True
    @staticmethod
    def _format_job_data(job_data: Dict[str, Any], index: int, ms_cities: List[str]) -> Dict[str, Any]:
        return {
            'id': f"infojobs-corrected-{index:04d}-{int(time.time()) % 10000}",
            'titulo': job_data.get('titulo', 'Título não encontrado'),
            'empresa': job_data.get('empresa', 'Empresa não informada'),
            'cidade': InfoJobsIndependentScraper._extract_city_from_location(job_data.get('localizacao', ''), ms_cities),
            'estado': 'MS',
            'link': job_data.get('link', ''),
            'data_coleta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'salario': job_data.get('salario', ''),
        }
    @staticmethod
    def _extract_city_from_location(location: str, ms_cities: List[str]) -> str:
        if not location:
            return "Mato Grosso do Sul"
        for city in ms_cities:
            if city.lower() in location.lower():
                return city
        if any(word in location.lower() for word in ['remoto', 'home office']):
            return "Remoto"
        return "Mato Grosso do Sul"
    def save_jobs_to_json(self, jobs: List[Dict[str, Any]]) -> str:
        try:
            filename = f"infojobs_corrected_ms_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_data = {
                'metadata': {
                    'fonte': 'InfoJobs MS via Scraper Corrigido',
                    'url_base': self.base_url,
                    'data_extracao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_vagas': len(jobs),
                    'metodo_extracao': 'corrected_selenium_individual_pages',
                    'estado_filtro': 'MS',
                    'xpath_empresa': '//*[@id="VacancyHeader"]/div[1]/div/div[1]/div/a',
                    'xpath_salario': '//*[@id="VacancyHeader"]/div[1]/div/div[2]/div[2]',
                    'xpath_requisitos': '//*[@id="vacancylistDetail"]/div[2]/p[1]'
                },
                'vagas': jobs
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            return filename
        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {e}")
            return ""
    def show_job_samples(self, jobs: List[Dict[str, Any]]):
        if not jobs:
            return
        print("\n📋 Amostra das vagas coletadas:")
        print("-" * 60)
        for i, job in enumerate(jobs[:5]):
            print(f"{i+1}. {job['titulo']}")
            print(f"   🏢 {job['empresa']}")
            print(f"   📍 {job['cidade']}, {job['estado']}")
            if job.get('data_publicacao'):
                print(f"   📅 {job['data_publicacao']}")
            if job.get('salario'):
                print(f"   💰 {job['salario']}")
            if job.get('requisitos'):
                print(f"   📋 {job['requisitos'][:100]}...")
            print(f"   🔗 {job['link']}")
            print()
        if len(jobs) > 5:
            print(f"... e mais {len(jobs) - 5} vagas.")
def main():
    parser = argparse.ArgumentParser(
        description='InfoJobs Independent Scraper - VERSÃO CORRIGIDA - Extrai vagas detalhadas do InfoJobs MS'
    )
    parser.add_argument(
        '--unlimited', '-u',
        action='store_true',
        help='Extrair todas as páginas disponíveis (sem limite)'
    )
    parser.add_argument(
        '--pages', '-p',
        type=int,
        default=2,
        help='Número máximo de páginas para extrair (padrão: 5)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Modo verbose com mais detalhes'
    )
    args = parser.parse_args()
    print("🚀 InfoJobs Independent Scraper - VERSÃO CORRIGIDA")
    print("Scraper corrigido com Selenium para extrair informações detalhadas")
    print("Baseado na análise MCP Firecrawl com XPath específicos")
    print()
    if args.verbose:
        print(f"🔧 Configurações:")
        if args.unlimited:
            print("   📄 Páginas: ILIMITADO (todas as páginas)")
        else:
            print(f"   📄 Páginas: máximo {args.pages}")
        print(f"   🔍 Verbose: {'Ativado' if args.verbose else 'Desativado'}")
        print("   🎯 XPath targets:")
        print("      Empresa: //*[@id='VacancyHeader']/div[1]/div/div[1]/div/a")
        print("      Salário: //*[@id='VacancyHeader']/div[1]/div/div[2]/div[2]")
        print("      Requisitos: //*[@id='vacancylistDetail']/div[2]/p[1]")
        print()
    scraper = InfoJobsIndependentScraper()
    if args.unlimited:
        jobs = scraper.scrape_jobs(unlimited=True)
    else:
        jobs = scraper.scrape_jobs(max_pages=args.pages)
    if jobs:
        print(f"\n✅ Sucesso! {len(jobs)} vagas coletadas do InfoJobs MS")
        if args.verbose:
            print(f"📊 Estatísticas:")
            cities = {}
            companies = {}
            for job in jobs:
                city = job.get('cidade', 'Não informado')
                cities[city] = cities.get(city, 0) + 1
                company = job.get('empresa', 'Não informado')
                companies[company] = companies.get(company, 0) + 1
            print(f"   🏙️ Cidades encontradas:")
            for city, count in sorted(cities.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      {city}: {count} vagas")
            print(f"   🏢 Principais empresas:")
            for company, count in sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"      {company}: {count} vagas")
    else:
        print("\n⚠️ Nenhuma vaga foi coletada")
if __name__ == "__main__":
    main()