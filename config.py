"""Configuration module for MS Job Scraper with type-safe settings."""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import psutil


@dataclass
class ScrapingConfig:
    
    max_companies: Optional[int] = None
    max_pages_per_company: int = 200
    max_workers: int = field(default_factory=lambda: _detect_optimal_workers())
    max_career_urls_per_company: int = 10
    timeout_multiplier: float = 1.0
    request_timeout: int = 30
    page_load_timeout: int = 30
    implicit_wait: int = 10
    enable_full_power: bool = False
    enable_enhanced_url_extraction: bool = True
    enable_url_validation: bool = True
    enable_async: bool = True
    enable_caching: bool = True
    verbose_logging: bool = False
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    
    def enable_full_power_mode(self) -> 'ScrapingConfig':
        self.enable_full_power = True
        self.max_companies = None
        self.max_pages_per_company = 500
        self.max_workers = min(_detect_optimal_workers() * 2, 20)
        self.max_career_urls_per_company = 20
        self.timeout_multiplier = 1.5
        return self


@dataclass
class LoggingConfig:
    
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_handler_enabled: bool = True
    console_handler_enabled: bool = True
    log_file: str = "scraper.log"
    max_file_size: int = 10 * 1024 * 1024
    backup_count: int = 5


@dataclass
class PathConfig:
    
    output_dir: Path = field(default_factory=lambda: Path("output"))
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    data_dir: Path = field(default_factory=lambda: Path("data"))
    cache_dir: Path = field(default_factory=lambda: Path(".cache"))
    
    def __post_init__(self):
        for directory in [self.output_dir, self.log_dir, self.data_dir, self.cache_dir]:
            directory.mkdir(exist_ok=True)


@dataclass
class UIConfig:
    
    theme: str = "dark"
    default_window_size: tuple = (1200, 800)
    min_window_size: tuple = (800, 600)
    font_family: str = "Segoe UI"
    font_size: int = 12


class AppConfig:
    
    def __init__(self):
        self.scraping = ScrapingConfig()
        self.logging = LoggingConfig()
        self.paths = PathConfig()
        self.ui = UIConfig()
        self._load_from_env()
    
    def _load_from_env(self):
        if max_workers := os.getenv("SCRAPER_MAX_WORKERS"):
            self.scraping.max_workers = int(max_workers)
        
        if rate_limit := os.getenv("SCRAPER_RATE_LIMIT"):
            self.scraping.rate_limit_delay = float(rate_limit)
        
        if timeout := os.getenv("SCRAPER_TIMEOUT"):
            self.scraping.request_timeout = int(timeout)
        
        self.scraping.enable_async = os.getenv("SCRAPER_ENABLE_ASYNC", "true").lower() == "true"
        self.scraping.enable_caching = os.getenv("SCRAPER_ENABLE_CACHING", "true").lower() == "true"
        self.scraping.verbose_logging = os.getenv("SCRAPER_VERBOSE_LOGGING", "false").lower() == "true"
        
        if output_dir := os.getenv("SCRAPER_OUTPUT_DIR"):
            self.paths.output_dir = Path(output_dir)
        
        if log_dir := os.getenv("SCRAPER_LOG_DIR"):
            self.paths.log_dir = Path(log_dir)
        
        if log_level := os.getenv("SCRAPER_LOG_LEVEL"):
            self.logging.level = log_level.upper()
    
    def setup_logging(self):
        handlers = []
        
        if self.logging.console_handler_enabled:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(self.logging.format))
            handlers.append(console_handler)
        
        if self.logging.file_handler_enabled:
            log_file_path = self.paths.log_dir / self.logging.log_file
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=self.logging.max_file_size,
                backupCount=self.logging.backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(self.logging.format))
            handlers.append(file_handler)
        
        logging.basicConfig(
            level=getattr(logging, self.logging.level),
            handlers=handlers,
            force=True
        )
    
    def validate(self) -> bool:
        try:
            assert self.scraping.max_workers > 0, "max_workers must be positive"
            assert self.scraping.max_pages_per_company > 0, "max_pages_per_company must be positive"
            assert self.scraping.timeout_multiplier > 0, "timeout_multiplier must be positive"
            assert self.scraping.rate_limit_delay >= 0, "rate_limit_delay must be non-negative"
            
            assert self.paths.output_dir.exists(), f"Output directory {self.paths.output_dir} does not exist"
            
            return True
        except AssertionError as e:
            logging.error(f"Configuration validation failed: {e}")
            return False


def _detect_optimal_workers() -> int:
    try:
        cpu_count = psutil.cpu_count(logical=True)
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        optimal_workers = min(cpu_count * 2, 16)
        
        memory_limited_workers = int(memory_gb * 2)
        
        return min(optimal_workers, memory_limited_workers, 16)
    except (OSError, AttributeError, ImportError):
        return 6


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

config = AppConfig()