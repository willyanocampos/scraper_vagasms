from typing import Dict, List, Any, Optional
import logging
import json
import html

logger = logging.getLogger(__name__)

class PopupGenerator:
    
    def __init__(self, style_manager=None, data_processor=None):
        self.style_manager = style_manager
        self.data_processor = data_processor
        self._popup_cache = {}
        
    def create_location_popup(self, location_data: Dict[str, Any]) -> str:
        try:
            location_name = location_data.get('location', 'Localização')
            job_count = location_data.get('job_count', 0)
            companies = location_data.get('companies', [])
            sectors = location_data.get('sectors', {})
            statistics = location_data.get('statistics', {})
            
            popup_theme = self._get_popup_theme()
            
            html_content = f"""
            <div class="location-popup" style="{self._get_container_style(popup_theme)}">
                {self._generate_header(location_name, job_count, popup_theme)}
                {self._generate_statistics_section(statistics)}
                {self._generate_sectors_section(sectors)}
                {self._generate_companies_section(companies, location_name)}
                {self._generate_lazy_load_section(location_name)}
                {self._generate_popup_styles()}
                {self._generate_popup_scripts()}
            </div>
            """
            return html_content
        except Exception as e:
            logger.error(f"Error creating location popup for {location_data.get('location')}: {e}")
            return self._create_error_popup(location_data.get('location', ''))

    def _get_popup_theme(self) -> Dict[str, str]:
        return {
            'header_bg': 'linear-gradient(135deg, #3b82f6, #60a5fa)',
        }

    def _get_container_style(self, theme: Dict[str, str]) -> str:
        return "width: 380px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;"

    def _generate_header(self, location_name: str, job_count: int, theme: Dict[str, str]) -> str:
        return f"""
        <div class="popup-header" style="
            background: {theme['header_bg']};
            color: white;
            padding: 16px 20px;
            margin: -1px -1px 0 -1px;
        ">
            <h3 style="margin: 0; font-size: 18px; font-weight: 600;">
                {html.escape(location_name)}
            </h3>
            <div style="
                display: flex;
                align-items: center;
                margin-top: 8px;
                font-size: 14px;
                opacity: 0.9;
            ">
                <span style="
                    background: rgba(255,255,255,0.2);
                    padding: 4px 8px;
                    border-radius: 12px;
                    font-weight: 500;
                ">
                    {job_count} vagas disponíveis
                </span>
            </div>
        </div>
        """

    def _generate_statistics_section(self, statistics: Dict[str, Any]) -> str:
        return ""

    def _generate_sectors_section(self, sectors: Dict[str, int]) -> str:
        try:
            if not sectors:
                return ""
            
            top_sectors = dict(list(sectors.items())[:6])
            
            sectors_html = []
            for sector, count in top_sectors.items():
                color = self._get_sector_color(sector)
                percentage = self._calculate_sector_percentage(count, sectors)
                
                sectors_html.append(f"""
                <div style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 6px 0;
                    border-bottom: 1px solid #e5e7eb;
                ">
                    <div style="display: flex; align-items: center;">
                        <div style="
                            width: 12px;
                            height: 12px;
                            border-radius: 50%;
                            background-color: {color};
                            margin-right: 10px;
                        "></div>
                        <span style="font-size: 14px; color: #374151;">
                            {html.escape(sector)}
                        </span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <span style="
                            font-size: 13px;
                            color: #6b7280;
                            margin-right: 8px;
                        ">
                            {percentage}%
                        </span>
                        <span style="
                            background-color: {color};
                            color: white;
                            padding: 2px 6px;
                            border-radius: 10px;
                            font-size: 12px;
                            font-weight: 500;
                        ">
                            {count}
                        </span>
                    </div>
                </div>
                """)
            return "<div style='padding: 12px 20px;'>" + "".join(sectors_html) + "</div>"
        except Exception as e:
            logger.warning(f"Error generating sectors section: {e}")
            return ""
    
    def _generate_companies_section(self, companies: List[Dict], location_name: str) -> str:
        try:
            if not companies:
                return ""
            
            top_companies = companies[:10]
            
            companies_html = []
            for company in top_companies:
                company_name = company.get('name', 'Empresa')
                job_count = company.get('job_count', 0)
                sectors = company.get('sectors', [])
                sectors_text = ', '.join(sectors[:2]) if sectors else 'Diversos'
                
                companies_html.append(f"""
                <div class="company-item" style="
                    padding: 10px 0;
                    border-bottom: 1px solid #e5e7eb;
                    cursor: pointer;
                    transition: background-color 0.2s;
                " onmouseover="this.style.backgroundColor='#f8fafc'" 
                   onmouseout="this.style.backgroundColor='transparent'"
                   onclick="loadCompanyJobs('{html.escape(location_name)}', '{html.escape(company_name)}')">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div style="flex: 1;">
                            <div style="
                                font-size: 14px;
                                font-weight: 500;
                                color: #1f2937;
                                margin-bottom: 2px;
                            ">
                                {html.escape(company_name)}
                            </div>
                            <div style="
                                font-size: 12px;
                                color: #6b7280;
                            ">
                                {html.escape(sectors_text)}
                            </div>
                        </div>
                        <div style="
                            background-color: #3b82f6;
                            color: white;
                            padding: 3px 8px;
                            border-radius: 12px;
                            font-size: 12px;
                            font-weight: 500;
                            min-width: 30px;
                            text-align: center;
                        ">
                            {job_count}
                        </div>
                    </div>
                </div>
                """)
            return "<div style='padding: 0 20px;'>" + "".join(companies_html) + "</div>"
        except Exception as e:
            logger.warning(f"Error generating companies section: {e}")
            return ""
    
    def _generate_lazy_load_section(self, location_name: str) -> str:
        return f"""
        <div class="jobs-section" style="padding: 16px 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="
                    margin: 0;
                    font-size: 16px;
                    color: #1f2937;
                    font-weight: 600;
                ">
                    Detalhes das Vagas
                </h4>
                <button id="load-jobs-btn" onclick="loadLocationJobs('{html.escape(location_name)}')" style="
                    background: linear-gradient(135deg, #3b82f6, #60a5fa);
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s;
                    box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
                " onmouseover="this.style.transform='translateY(-1px)'; this.style.boxShadow='0 4px 8px rgba(59, 130, 246, 0.4)'"
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(59, 130, 246, 0.3)'">
                    Ver Vagas
                </button>
            </div>
            
            <div id="jobs-content" style="
                min-height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #6b7280;
                font-style: italic;
                background: #f9fafb;
                border-radius: 6px;
                padding: 20px;
                text-align: center;
            ">
                Clique em "Ver Vagas" para carregar os detalhes das oportunidades
            </div>
            
            <div id="loading-indicator" style="display: none; text-align: center; padding: 20px;">
                <div style="
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    border: 3px solid #e5e7eb;
                    border-radius: 50%;
                    border-top-color: #3b82f6;
                    animation: spin 1s ease-in-out infinite;
                "></div>
                <div style="margin-top: 10px; color: #6b7280; font-size: 13px;">
                    Carregando vagas...
                </div>
            </div>
        </div>
        """

    def _generate_popup_styles(self) -> str:
        return """
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
        """
    
    def _generate_popup_scripts(self) -> str:
        return """
        <script>
            function loadLocationJobs(locationName) {
                const btn = document.getElementById('load-jobs-btn');
                const content = document.getElementById('jobs-content');
                const loading = document.getElementById('loading-indicator');
                
                btn.style.display = 'none';
                content.style.display = 'none';
                loading.style.display = 'block';
                
                setTimeout(() => {
                    content.innerHTML = generateJobsHTML(locationName);
                    loading.style.display = 'none';
                    content.style.display = 'block';
                }, 1000);
            }
            
            function loadCompanyJobs(locationName, companyName) {
                console.log('Loading jobs for company:', companyName, 'in', locationName);
            }
            
            function generateJobsHTML(locationName) {
                return `
                    <div class="job-card">
                        <div class="job-title">Exemplo de Vaga</div>
                        <div class="job-company">Empresa Exemplo</div>
                        <div class="job-details">
                            <span class="job-tag">Remoto</span>
                            <span class="job-tag">CLT</span>
                            <span class="job-tag">Pleno</span>
                        </div>
                    </div>
                    <div style="text-align: center; margin-top: 15px;">
                        <small style="color: #6b7280;">
                            Integração com dados reais em desenvolvimento
                        </small>
                    </div>
                `;
            }
        </script>
        """

    def create_job_card_html(self, job: Dict[str, Any]) -> str:
        try:
            return f"""
            <div class="job-card">
                <div class="job-title">{html.escape(job.get('titulo', ''))}</div>
                <div style="color: #ef4444; font-size: 12px;">
                    {html.escape(str(e))}
                </div>
            </div>
            """
        except Exception as e:
            logger.error(f"Error creating job card HTML: {e}")
            return ""

    def _get_sector_color(self, sector: str) -> str:
        if self.style_manager:
            return self.style_manager.get_sector_color(sector)
        
        default_colors = {
            'Tecnologia': '#3b82f6',
            'Saúde': '#ef4444',
            'Educação': '#22c55e',
            'Comércio': '#f59e0b',
            'Indústria': '#8b5cf6',
            'Serviços': '#06b6d4',
            'Outros': '#94a3b8'
        }
        
        return default_colors.get(sector, '#94a3b8')
    
    def _calculate_sector_percentage(self, count: int, all_sectors: Dict[str, int]) -> int:
        try:
            total = sum(all_sectors.values())
            if total == 0:
                return 0
            return round((count / total) * 100)
        except Exception:
            return 0
    
    def _create_error_popup(self, location_name: str) -> str:
        return f"""
        <div style="
            padding: 20px;
            text-align: center;
            color: #374151;
            font-family: Arial, sans-serif;
        ">
            <h4 style="margin: 0 0 10px 0; color: #dc2626;">
                Erro ao carregar informações
            </h4>
            <p style="margin: 0; color: #6b7280;">
                Não foi possível carregar os dados para {html.escape(location_name)}
            </p>
        </div>
        """