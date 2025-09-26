from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict, Counter
import logging
logger = logging.getLogger(__name__)
class DataProcessor:
    def __init__(self):
        self._location_cache = {}
        self._stats_cache = {}
    def process_jobs_data(self, jobs_data: List[Dict]) -> Dict[str, Any]:
        try:
            if not jobs_data:
                logger.warning("Empty jobs data provided")
                return {"locations": {}, "stats": {}}
            location_groups = self._group_jobs_by_location(jobs_data)
            processed_locations = {}
            for location, jobs in location_groups.items():
                processed_locations[location] = self._process_location_group(location, jobs)
            global_stats = self._generate_global_statistics(jobs_data)
            return {
                "locations": processed_locations,
                "stats": global_stats,
                "total_jobs": len(jobs_data),
                "total_locations": len(processed_locations)
            }
        except Exception as e:
            logger.error(f"Failed to process jobs data: {e}")
            return {"locations": {}, "stats": {}, "error": str(e)}
    def _group_jobs_by_location(self, jobs_data: List[Dict]) -> Dict[str, List[Dict]]:
        location_groups = defaultdict(list)
        for job in jobs_data:
            try:
                location = self._extract_location(job)
                if location:
                    location_groups[location].append(job)
                else:
                    location_groups["Outros"].append(job)
            except Exception as e:
                logger.warning(f"Error processing job for location grouping: {e}")
                location_groups["Outros"].append(job)
        return dict(location_groups)
    def _extract_location(self, job: Dict) -> Optional[str]:
        location_fields = ['location', 'cidade', 'city', 'local', 'endereco']
        for field in location_fields:
            if field in job and job[field]:
                location = str(job[field]).strip()
                if location and location.lower() not in ['', 'n/a', 'none', 'null']:
                    return self._clean_location_name(location)
        if 'address' in job and job['address']:
            return self._extract_city_from_address(job['address'])
        return None
    def _clean_location_name(self, location: str) -> str:
        try:
            location = location.strip()
            if ' - ' in location:
                location = location.split(' - ')[0].strip()
            location = location.title()
            location_mappings = {
                'Sao Paulo': 'São Paulo',
                'Brasilia': 'Brasília',
                'Rio De Janeiro': 'Rio de Janeiro',
                'Belo Horizonte': 'Belo Horizonte'
            }
            return location_mappings.get(location, location)
        except Exception as e:
            logger.warning(f"Error cleaning location name: {e}")
            return location
    def _extract_city_from_address(self, address: str) -> Optional[str]:
        try:
            parts = address.split(',')
            if len(parts) >= 2:
                city = parts[-2].strip()
                return self._clean_location_name(city)
        except Exception as e:
            logger.warning(f"Error extracting city from address: {e}")
        return None
    def _process_location_group(self, location: str, jobs: List[Dict]) -> Dict[str, Any]:
        try:
            companies = self._analyze_companies(jobs)
            sectors = self._analyze_sectors(jobs)
            stats = self._generate_location_statistics(jobs)
            coordinates = self._extract_coordinates(jobs)
            return {
                "location": location,
                "job_count": len(jobs),
                "companies": companies,
                "sectors": sectors,
                "statistics": stats,
                "coordinates": coordinates,
                "jobs": jobs,
                "top_companies": companies[:10],
                "top_sectors": dict(list(sectors.items())[:6])
            }
        except Exception as e:
            logger.error(f"Error processing location group for {location}: {e}")
            return {
                "location": location,
                "job_count": len(jobs),
                "companies": [],
                "sectors": {},
                "statistics": {},
                "coordinates": None,
                "jobs": jobs,
                "error": str(e)
            }
    def _analyze_companies(self, jobs: List[Dict]) -> List[Dict[str, Any]]:
        company_stats = defaultdict(lambda: {
            "name": "",
            "job_count": 0,
            "sectors": set(),
            "jobs": []
        })
        for job in jobs:
            try:
                company_name = self._extract_company_name(job)
                if company_name:
                    stats = company_stats[company_name]
                    stats["name"] = company_name
                    stats["job_count"] += 1
                    stats["jobs"].append(job)
                    sector = self._extract_sector(job)
                    if sector:
                        stats["sectors"].add(sector)
            except Exception as e:
                logger.warning(f"Error analyzing company for job: {e}")
        companies = []
        for company_data in company_stats.values():
            companies.append({
                "name": company_data["name"],
                "job_count": company_data["job_count"],
                "sectors": list(company_data["sectors"]),
                "jobs": company_data["jobs"]
            })
        return sorted(companies, key=lambda x: x["job_count"], reverse=True)
    def _analyze_sectors(self, jobs: List[Dict]) -> Dict[str, int]:
        sector_counter = Counter()
        for job in jobs:
            try:
                sector = self._extract_sector(job)
                if sector:
                    sector_counter[sector] += 1
                else:
                    sector_counter["Outros"] += 1
            except Exception as e:
                logger.warning(f"Error analyzing sector for job: {e}")
                sector_counter["Outros"] += 1
        return dict(sector_counter.most_common())
    def _extract_company_name(self, job: Dict) -> Optional[str]:
        company_fields = ['company', 'empresa', 'company_name', 'employer']
        for field in company_fields:
            if field in job and job[field]:
                company = str(job[field]).strip()
                if company and company.lower() not in ['', 'n/a', 'none', 'null']:
                    return company
        return None
    def _extract_sector(self, job: Dict) -> Optional[str]:
        sector_fields = ['sector', 'setor', 'industry', 'area', 'category']
        for field in sector_fields:
            if field in job and job[field]:
                sector = str(job[field]).strip()
                if sector and sector.lower() not in ['', 'n/a', 'none', 'null']:
                    return sector.title()
        return self._infer_sector_from_content(job)
    def _infer_sector_from_content(self, job: Dict) -> Optional[str]:
        try:
            content = ""
            if 'title' in job:
                content += str(job['title']).lower() + " "
            if 'description' in job:
                content += str(job['description']).lower() + " "
            sector_keywords = {
                'Tecnologia': ['desenvolvedor', 'programador', 'ti', 'software', 'tech', 'developer', 'python', 'java', 'javascript'],
                'Saúde': ['médico', 'enfermeiro', 'saúde', 'hospital', 'clínica', 'health'],
                'Educação': ['professor', 'educador', 'ensino', 'escola', 'universidade', 'teacher'],
                'Comércio': ['vendedor', 'comercial', 'varejo', 'loja', 'sales'],
                'Indústria': ['operador', 'técnico', 'industrial', 'fábrica', 'produção'],
                'Serviços': ['atendimento', 'serviços', 'customer', 'support', 'service'],
                'Financeiro': ['banco', 'financeiro', 'contabilidade', 'finance', 'accounting']
            }
            for sector, keywords in sector_keywords.items():
                if any(keyword in content for keyword in keywords):
                    return sector
        except Exception as e:
            logger.warning(f"Error inferring sector from content: {e}")
        return None
    def _generate_location_statistics(self, jobs: List[Dict]) -> Dict[str, Any]:
        try:
            stats = {
                "total_jobs": len(jobs),
                "unique_companies": len(set(self._extract_company_name(job) for job in jobs if self._extract_company_name(job))),
                "job_types": Counter(),
                "experience_levels": Counter(),
                "recent_jobs": 0
            }
            for job in jobs:
                job_type = job.get('type', 'Outros')
                stats["job_types"][job_type] += 1
                level = job.get('experience_level', job.get('nivel', 'Não especificado'))
                stats["experience_levels"][level] += 1
            stats["job_types"] = dict(stats["job_types"])
            stats["experience_levels"] = dict(stats["experience_levels"])
            return stats
        except Exception as e:
            logger.error(f"Error generating location statistics: {e}")
            return {"total_jobs": len(jobs), "error": str(e)}
    def _extract_coordinates(self, jobs: List[Dict]) -> Optional[Tuple[float, float]]:
        for job in jobs:
            try:
                if 'latitude' in job and 'longitude' in job:
                    lat = float(job['latitude'])
                    lon = float(job['longitude'])
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        return (lat, lon)
                if 'coordinates' in job:
                    coords = job['coordinates']
                    if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                        lat, lon = float(coords[0]), float(coords[1])
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            return (lat, lon)
            except (ValueError, TypeError) as e:
                continue
        return None
    def _generate_global_statistics(self, jobs_data: List[Dict]) -> Dict[str, Any]:
        try:
            stats = {
                "total_jobs": len(jobs_data),
                "total_companies": len(set(self._extract_company_name(job) for job in jobs_data if self._extract_company_name(job))),
                "sectors_distribution": self._analyze_sectors(jobs_data),
                "top_companies": [],
                "data_quality": self._assess_data_quality(jobs_data)
            }
            all_companies = self._analyze_companies(jobs_data)
            stats["top_companies"] = all_companies[:20]
            return stats
        except Exception as e:
            logger.error(f"Error generating global statistics: {e}")
            return {"total_jobs": len(jobs_data), "error": str(e)}
    def _assess_data_quality(self, jobs_data: List[Dict]) -> Dict[str, Any]:
        try:
            total_jobs = len(jobs_data)
            if total_jobs == 0:
                return {"score": 0, "issues": ["No data available"]}
            quality_metrics = {
                "completeness": {
                    "company": sum(1 for job in jobs_data if self._extract_company_name(job)) / total_jobs,
                    "location": sum(1 for job in jobs_data if self._extract_location(job)) / total_jobs,
                    "sector": sum(1 for job in jobs_data if self._extract_sector(job)) / total_jobs,
                    "coordinates": sum(1 for job in jobs_data if self._extract_coordinates([job])) / total_jobs
                },
                "issues": [],
                "score": 0
            }
            completeness_scores = list(quality_metrics["completeness"].values())
            quality_metrics["score"] = sum(completeness_scores) / len(completeness_scores)
            if quality_metrics["completeness"]["company"] < 0.8:
                quality_metrics["issues"].append("Muitas vagas sem informação de empresa")
            if quality_metrics["completeness"]["location"] < 0.7:
                quality_metrics["issues"].append("Muitas vagas sem informação de localização")
            if quality_metrics["completeness"]["coordinates"] < 0.3:
                quality_metrics["issues"].append("Poucas vagas com coordenadas geográficas")
            return quality_metrics
        except Exception as e:
            logger.error(f"Error assessing data quality: {e}")
            return {"score": 0, "error": str(e)}
    def get_location_jobs(self, processed_data: Dict, location: str, 
                         company: Optional[str] = None) -> List[Dict]:
        try:
            if location not in processed_data.get("locations", {}):
                return []
            location_data = processed_data["locations"][location]
            jobs = location_data.get("jobs", [])
            if company:
                jobs = [job for job in jobs if self._extract_company_name(job) == company]
            return jobs
        except Exception as e:
            logger.error(f"Error getting location jobs: {e}")
            return []
    def clear_cache(self):
        self._location_cache.clear()
        self._stats_cache.clear()
        logger.info("Data processor caches cleared")