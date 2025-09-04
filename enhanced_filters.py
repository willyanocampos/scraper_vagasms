from typing import Dict, List, Set, Optional, Union
from functools import lru_cache
import re
from collections import defaultdict
from datetime import datetime, timedelta

class EnhancedJobFilter:
    
    def __init__(self):
        self.jobs_data: List[Dict] = []
        self.filter_cache = {}
        self.search_index = {}
        self._build_search_index()
    
    def set_jobs_data(self, jobs_data: List[Dict]):
        self.jobs_data = jobs_data
        self.filter_cache.clear()
        self._build_search_index()
    
    def _build_search_index(self):
        self.search_index = {
            'titles': {},
            'companies': {},
            'cities': {},
            'sectors': {},
            'descriptions': {}
        }
        
        for i, job in enumerate(self.jobs_data):
            title = job.get('titulo', '').lower()
            if title:
                for word in self._tokenize(title):
                    if word not in self.search_index['titles']:
                        self.search_index['titles'][word] = set()
                    self.search_index['titles'][word].add(i)
            
            company = job.get('empresa', '').lower()
            if company:
                for word in self._tokenize(company):
                    if word not in self.search_index['companies']:
                        self.search_index['companies'][word] = set()
                    self.search_index['companies'][word].add(i)
            
            city = job.get('cidade', '').lower()
            if city:
                for word in self._tokenize(city):
                    if word not in self.search_index['cities']:
                        self.search_index['cities'][word] = set()
                    self.search_index['cities'][word].add(i)
            
            sector = job.get('setor', '').lower()
            if sector:
                for word in self._tokenize(sector):
                    if word not in self.search_index['sectors']:
                        self.search_index['sectors'][word] = set()
                    self.search_index['sectors'][word].add(i)
            
            description = job.get('descricao', '').lower()
            if description:
                for word in self._tokenize(description):
                    if word not in self.search_index['descriptions']:
                        self.search_index['descriptions'][word] = set()
                    self.search_index['descriptions'][word].add(i)
    
    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r'\b\w+\b', text.lower())
        return [word for word in words if len(word) >= 2]
    
    def _search_in_index(self, search_term: str) -> Set[int]:
        if not search_term:
            return set(range(len(self.jobs_data)))
        
        search_words = self._tokenize(search_term.lower())
        if not search_words:
            return set(range(len(self.jobs_data)))
        
        result_indices = None
        
        for word in search_words:
            word_matches = set()
            
            for field_index in self.search_index.values():
                if word in field_index:
                    word_matches.update(field_index[word])
            
            if not word_matches:
                for field_index in self.search_index.values():
                    for indexed_word, indices in field_index.items():
                        if word in indexed_word or indexed_word in word:
                            word_matches.update(indices)
            
            if result_indices is None:
                result_indices = word_matches
            else:
                result_indices = result_indices.intersection(word_matches)
        
        return result_indices or set()
    
    @lru_cache(maxsize=100)
    def get_unique_values(self, field: str) -> List[str]:
        values = set()
        for job in self.jobs_data:
            value = job.get(field, '')
            if value and isinstance(value, str):
                values.add(value.strip())
        
        return sorted(list(values))
    
    def get_filter_options(self) -> Dict[str, List[str]]:
        return {
            'cities': ['Todas'] + self.get_unique_values('cidade'),
            'companies': ['Todas'] + self.get_unique_values('empresa'),
            'sectors': ['Todos'] + self.get_unique_values('setor'),
            'contract_types': ['Todos'] + self.get_unique_values('tipo_contrato')
        }
    
    def apply_filters(self, filters: Dict) -> List[Dict]:
        cache_key = self._create_cache_key(filters)
        
        if cache_key in self.filter_cache:
            return self.filter_cache[cache_key]
        
        if filters.get('search'):
            search_indices = self._search_in_index(filters['search'])
            filtered_jobs = [self.jobs_data[i] for i in search_indices]
        else:
            filtered_jobs = self.jobs_data.copy()
        
        filtered_jobs = self._apply_city_filter(filtered_jobs, filters.get('city'))
        filtered_jobs = self._apply_company_filter(filtered_jobs, filters.get('company'))
        filtered_jobs = self._apply_sector_filter(filtered_jobs, filters.get('sector'))
        filtered_jobs = self._apply_contract_filter(filtered_jobs, filters.get('contract_type'))
        filtered_jobs = self._apply_remote_filter(filtered_jobs, filters.get('remote_only'))
        filtered_jobs = self._apply_date_filter(filtered_jobs, filters.get('date_range'))
        filtered_jobs = self._apply_salary_filter(filtered_jobs, filters.get('salary_range'))
        
        self.filter_cache[cache_key] = filtered_jobs
        
        return filtered_jobs
    
    def _create_cache_key(self, filters: Dict) -> str:
        return str(sorted(filters.items()))
    
    def _apply_city_filter(self, jobs: List[Dict], city: Optional[str]) -> List[Dict]:
        if not city or city == "Todas":
            return jobs
        return [job for job in jobs if job.get('cidade', '').strip() == city]
    
    def _apply_company_filter(self, jobs: List[Dict], company: Optional[str]) -> List[Dict]:
        if not company or company == "Todas":
            return jobs
        return [job for job in jobs if job.get('empresa', '').strip() == company]
    
    def _apply_sector_filter(self, jobs: List[Dict], sector: Optional[str]) -> List[Dict]:
        if not sector or sector == "Todos":
            return jobs
        return [job for job in jobs if job.get('setor', '').strip() == sector]
    
    def _apply_contract_filter(self, jobs: List[Dict], contract_type: Optional[str]) -> List[Dict]:
        if not contract_type or contract_type == "Todos":
            return jobs
        return [job for job in jobs if job.get('tipo_contrato', '').strip() == contract_type]
    
    def _apply_remote_filter(self, jobs: List[Dict], remote_only: Optional[bool]) -> List[Dict]:
        if not remote_only:
            return jobs
        return [job for job in jobs if job.get('trabalho_remoto', False)]
    
    def _apply_date_filter(self, jobs: List[Dict], date_range: Optional[Dict]) -> List[Dict]:
        if not date_range:
            return jobs
        
        filtered = []
        for job in jobs:
            job_date_str = job.get('data_publicacao', '')
            if not job_date_str:
                continue
            
            try:
                job_date = self._parse_date(job_date_str)
                if job_date:
                    if date_range.get('start') and job_date < date_range['start']:
                        continue
                    if date_range.get('end') and job_date > date_range['end']:
                        continue
                    filtered.append(job)
            except:
                filtered.append(job)
        
        return filtered
    
    def _apply_salary_filter(self, jobs: List[Dict], salary_range: Optional[Dict]) -> List[Dict]:
        if not salary_range:
            return jobs
        
        filtered = []
        for job in jobs:
            salary_str = job.get('salario', '')
            if not salary_str:
                filtered.append(job)
                continue
            
            try:
                salary = self._parse_salary(salary_str)
                if salary:
                    if salary_range.get('min') and salary < salary_range['min']:
                        continue
                    if salary_range.get('max') and salary > salary_range['max']:
                        continue
                filtered.append(job)
            except:
                filtered.append(job)
        
        return filtered
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d/%m/%y',
            '%Y-%m-%d %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def _parse_salary(self, salary_str: str) -> Optional[float]:
        if not salary_str:
            return None
        
        clean_salary = re.sub(r'[R$\s,.]', '', salary_str.upper())
        clean_salary = re.sub(r'[A-Z]', '', clean_salary)
        
        try:
            return float(clean_salary)
        except ValueError:
            return None
    
    def get_statistics(self, jobs: Optional[List[Dict]] = None) -> Dict:
        if jobs is None:
            jobs = self.jobs_data
        
        if not jobs:
            return {}
        
        stats = {
            'total_jobs': len(jobs),
            'cities': defaultdict(int),
            'companies': defaultdict(int),
            'sectors': defaultdict(int),
            'contract_types': defaultdict(int),
            'remote_jobs': 0,
            'on_site_jobs': 0
        }
        
        for job in jobs:
            city = job.get('cidade', 'Unknown')
            stats['cities'][city] += 1
            
            company = job.get('empresa', 'Unknown')
            stats['companies'][company] += 1
            
            sector = job.get('setor', 'Unknown')
            stats['sectors'][sector] += 1
            
            contract = job.get('tipo_contrato', 'Unknown')
            stats['contract_types'][contract] += 1
            
            if job.get('trabalho_remoto', False):
                stats['remote_jobs'] += 1
            else:
                stats['on_site_jobs'] += 1
        
        stats['cities'] = dict(stats['cities'])
        stats['companies'] = dict(stats['companies'])
        stats['sectors'] = dict(stats['sectors'])
        stats['contract_types'] = dict(stats['contract_types'])
        
        return stats
    
    def suggest_searches(self, partial_term: str, limit: int = 5) -> List[str]:
        if not partial_term or len(partial_term) < 2:
            return []
        
        suggestions = set()
        partial_lower = partial_term.lower()
        
        for field_index in self.search_index.values():
            for word in field_index.keys():
                if word.startswith(partial_lower):
                    suggestions.add(word)
                elif partial_lower in word:
                    suggestions.add(word)
        
        return sorted(list(suggestions))[:limit]
    
    def clear_cache(self):
        self.filter_cache.clear()

def test_enhanced_filters():
    sample_jobs = [
        {
            'titulo': 'Desenvolvedor Python Senior',
            'empresa': 'TechCorp',
            'cidade': 'Campo Grande',
            'setor': 'Tecnologia',
            'tipo_contrato': 'CLT',
            'trabalho_remoto': True,
            'data_publicacao': '2024-08-20',
            'salario': 'R$ 8000'
        },
        {
            'titulo': 'Analista de Sistemas',
            'empresa': 'SoftwarePlus',
            'cidade': 'Dourados',
            'setor': 'Tecnologia', 
            'tipo_contrato': 'PJ',
            'trabalho_remoto': False,
            'data_publicacao': '2024-08-19',
            'salario': 'R$ 6000'
        }
    ]
    
    filter_system = EnhancedJobFilter()
    filter_system.set_jobs_data(sample_jobs)
    
    results = filter_system.apply_filters({'search': 'python'})
    print(f"Search results for 'python': {len(results)} jobs")
    
    options = filter_system.get_filter_options()
    print(f"Available cities: {options['cities']}")
    
    stats = filter_system.get_statistics()
    print(f"Statistics: {stats}")

if __name__ == "__main__":
    test_enhanced_filters()