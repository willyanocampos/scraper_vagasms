from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class StyleManager:
    
    def __init__(self):
        self._design_tokens = self._create_design_tokens()
        self._sector_colors = self._create_sector_colors()
        
    def _create_design_tokens(self) -> Dict[str, str]:
        return {
            'primary': '#2563eb',
            'primary_hover': '#1d4ed8',
            'secondary': '#10b981',
            'secondary_hover': '#059669',
            'accent': '#8b5cf6',
            'accent_hover': '#7c3aed',
            'success': '#059669',
            'warning': '#d97706',
            'error': '#dc2626',
            'text_primary': '#111827',
            'text_secondary': '#6b7280',
            'background': '#f8fafc',
            'card_bg': '#ffffff',
            'border': '#e5e7eb',
            'border_hover': '#d1d5db'
        }
    
    def _create_sector_colors(self) -> Dict[str, str]:
        return {
            'Tecnologia': '#3b82f6',
            'Saúde': '#ef4444', 
            'Educação': '#22c55e',
            'Comércio': '#f59e0b',
            'Indústria': '#8b5cf6',
            'Serviços': '#06b6d4',
            'Agricultura': '#84cc16',
            'Construção': '#64748b',
            'Transporte': '#eab308',
            'Alimentação': '#14b8a6',
            'Financeiro': '#ec4899',
            'Agronegócio': '#f97316',
            'Frigorífico': '#dc2626',
            'Outros': '#94a3b8'
        }
    
    @property
    def design_tokens(self) -> Dict[str, str]:
        return self._design_tokens.copy()
    
    @property
    def sector_colors(self) -> Dict[str, str]:
        return self._sector_colors.copy()
    
    def get_design_token(self, token: str) -> str:
        return self._design_tokens.get(token, '#6b7280')
    
    def get_sector_color(self, sector: str) -> str:
        return self._sector_colors.get(sector, self._sector_colors['Outros'])
    
    def create_gradient_style(self, base_color: str, opacity: float = 1.0) -> str:
        try:
            if opacity < 1.0:
                return f"linear-gradient(135deg, {base_color}{int(opacity*255):02x} 0%, {base_color}CC 100%)"
            else:
                return f"linear-gradient(135deg, {base_color} 0%, {base_color}DD 100%)"
        except Exception as e:
            logger.warning(f"Failed to create gradient style: {e}")
            return base_color
    
    def get_marker_style(self, sector: str, job_count: int) -> Dict[str, Any]:
        base_color = self.get_sector_color(sector)
        
        if job_count < 10:
            size = 35
        elif job_count < 50:
            size = 45
        else:
            size = 55
            
        return {
            'color': base_color,
            'size': size,
            'gradient': self.create_gradient_style(base_color),
            'border_color': '#ffffff',
            'border_width': 3
        }
    
    def get_popup_theme(self) -> Dict[str, str]:
        return {
            'background': self.get_design_token('card_bg'),
            'header_bg': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'text_primary': self.get_design_token('text_primary'),
            'text_secondary': self.get_design_token('text_secondary'),
            'border': self.get_design_token('border'),
            'border_radius': '8px',
            'shadow': '0 4px 12px rgba(0,0,0,0.1)'
        }
    
    def validate_color(self, color: str) -> bool:
        try:
            if not color.startswith('#'):
                return False
            if len(color) not in [4, 7]:
                return False
            int(color[1:], 16)
            return True
        except ValueError:
            return False
    
    def add_custom_sector(self, sector: str, color: str) -> bool:
        if not self.validate_color(color):
            logger.error(f"Invalid color code: {color}")
            return False
            
        self._sector_colors[sector] = color
        logger.info(f"Added custom sector color: {sector} -> {color}")
        return True
    
    def get_theme_css(self) -> str:
        css_vars = []
        for token, value in self._design_tokens.items():
            css_vars.append(f"  --{token.replace('_', '-')}: {value};")
        
        return ":root {\n" + "\n".join(css_vars) + "\n}"