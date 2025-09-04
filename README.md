# 🗺️ Scrapper Vagas MS

**Sistema Inteligente de Coleta e Análise de Vagas de Emprego em Mato Grosso do Sul**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/Status-Ativo-green.svg)](https://github.com/seu-usuario/scrapper-vagasms)
[![Licença](https://img.shields.io/badge/Licença-MIT-yellow.svg)](LICENSE)

## 📋 Sobre o Projeto

O **Scrapper Vagas MS** é uma solução completa para coleta automatizada, análise e visualização de oportunidades de emprego específicas do estado de Mato Grosso do Sul. O sistema combina web scraping inteligente com uma interface desktop moderna e mapas interativos para fornecer insights valiosos sobre o mercado de trabalho regional.

### 🎯 Objetivos Principais

- ✅ **Automatizar** a coleta de vagas de emprego de múltiplas fontes
- ✅ **Filtrar** inteligentemente oportunidades específicas de MS
- ✅ **Visualizar** dados geográficos em mapas interativos
- ✅ **Analisar** tendências do mercado de trabalho regional
- ✅ **Facilitar** a descoberta de oportunidades pelos usuários

## 🚀 Funcionalidades Principais

### 🔍 Web Scraping Inteligente
- **Multi-Empresa**: Suporte a 141+ empresas com portais próprios
- **Detecção Automática**: Identificação inteligente de vagas MS
- **Processamento Paralelo**: Extração otimizada com multi-threading
- **Validação Geográfica**: Sistema robusto de verificação de localização
- **Múltiplas Estratégias**: Suporte a Gupy, sites proprietários e APIs

### 📊 Interface Desktop Moderna
- **Design Responsivo**: Interface customtkinter elegante
- **Gráficos Interativos**: Visualizações matplotlib integradas
- **Filtros Avançados**: Sistema de busca e filtragem poderoso
- **Exportação de Dados**: Suporte a múltiplos formatos (CSV, JSON, Excel)
- **Tema Escuro/Claro**: Interface adaptável às preferências

### 🗺️ Mapas Interativos
- **Leaflet Integration**: Mapas web responsivos e interativos
- **Clustering Inteligente**: Agrupamento automático de marcadores
- **Popups Informativos**: Detalhes completos das vagas por localização
- **Cores por Setor**: Sistema visual intuitivo por área de atuação
- **Estatísticas em Tempo Real**: Métricas atualizadas dinamicamente

### 🎨 Sistema de Filtros
- **Por Empresa**: Filtros específicos por empregador
- **Por Localização**: Busca geográfica precisa (28 cidades)
- **Por Setor**: Classificação por área de atuação
- **Por Tipo**: Contrato, remoto, presencial, híbrido
- **Por Data**: Período de coleta personalizável
- **Busca Textual**: Pesquisa inteligente em títulos e descrições

## 🏗️ Arquitetura do Sistema

```
scrapper_vagasms/
├── 📁 Core Sistema
│   ├── unified_ms_job_scraper.py    # 🎯 Motor principal de scraping
│   ├── ms_jobs_desktop.py           # 🖥️ Interface desktop
│   └── interactive_map_widget.py    # 🗺️ Widget de mapas
├── 📁 Dados e Configuração
│   ├── accurate_ms_map_data.py      # 📍 Dados geográficos MS
│   ├── enhanced_filters.py          # 🔍 Sistema de filtros
│   └── data/                        # 📊 Dados de empresas
├── 📁 Componentes de Mapa
│   ├── map_components/              # 🧩 Módulos especializados
│   │   ├── data_processor.py        # ⚙️ Processamento de dados
│   │   ├── map_renderer.py          # 🎨 Renderização de mapas
│   │   ├── popup_generator.py       # 💬 Geração de popups
│   │   └── style_manager.py         # 🎭 Gerenciamento de estilos
└── 📁 Utilitários
    └── logs/                        # 📝 Logs do sistema
```

## 💻 Tecnologias Utilizadas

### 🐍 Backend & Scraping
- **Python 3.9+** - Linguagem principal
- **Selenium WebDriver** - Automação de navegadores
- **BeautifulSoup4** - Parser HTML/XML
- **pandas** - Manipulação e análise de dados
- **requests/aiohttp** - Cliente HTTP síncrono/assíncrono
- **psutil** - Monitoramento de sistema
- **concurrent.futures** - Processamento paralelo

### 🖥️ Interface Desktop
- **customtkinter** - Interface moderna
- **matplotlib** - Gráficos e visualizações
- **tkinter** - Interface base do Python
- **geopandas** *(opcional)* - Dados geográficos avançados

### 🌐 Mapas e Visualização
- **Leaflet.js** - Biblioteca de mapas web
- **folium** - Interface Python para Leaflet
- **Marker Cluster** - Agrupamento de marcadores
- **HTML5/CSS3/JavaScript** - Frontend web

## 🛠️ Instalação e Configuração

### 📋 Pré-requisitos

- **Python 3.9 ou superior**
- **Google Chrome ou Chromium** (para Selenium)
- **Git** (para clonagem do repositório)

### 🔧 Instalação Passo a Passo

1. **Clone o repositório**
   ```bash
   git clone https://github.com/seu-usuario/scrapper-vagasms.git
   cd scrapper-vagasms
   ```

2. **Instale as dependências do sistema**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3-psutil python3-pip chromium-browser
   
   # CentOS/RHEL/Fedora
   sudo dnf install python3-psutil python3-pip chromium
   
   # Windows (via Chocolatey)
   choco install python googlechrome
   ```

3. **Crie e ative o ambiente virtual**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # ou
   .venv\Scripts\activate.bat  # Windows
   ```

4. **Instale dependências Python**
   ```bash
   pip install -r requirements.txt
   # ou instale manualmente:
   pip install selenium beautifulsoup4 pandas requests customtkinter matplotlib folium psutil aiohttp
   ```

5. **Configure as variáveis de ambiente**
   ```bash
   cp .env.example .env
   # Edite .env conforme necessário
   ```

6. **Instale dependências opcionais** *(para recursos avançados)*
   ```bash
   # Para análise geográfica avançada
   pip install geopandas
   
   # Para performance adicional
   pip install lxml html5lib
   ```

### ⚙️ Configuração Avançada

#### Arquivo `.env` Principal
```bash
# Performance do Scraper
SCRAPER_MAX_WORKERS=6
SCRAPER_RATE_LIMIT=1.0
SCRAPER_TIMEOUT=30

# Diretórios de Output
SCRAPER_OUTPUT_DIR=output
SCRAPER_LOG_DIR=logs

# Funcionalidades
SCRAPER_ENABLE_ASYNC=true
SCRAPER_ENABLE_CACHING=true
SCRAPER_VERBOSE_LOGGING=false
```

## 🚀 Como Usar

### 🎯 Execução do Scraper Principal

```bash
# Executar scraper completo
python3 unified_ms_job_scraper.py

# Executar com configurações específicas
python3 unified_ms_job_scraper.py --max-workers 8 --timeout 45

# Executar em modo verbose
python3 unified_ms_job_scraper.py --verbose

# Executar para empresas específicas
python3 unified_ms_job_scraper.py --companies "JBS,COPASUL,Vale"
```

### 🖥️ Interface Desktop

```bash
# Iniciar aplicação desktop
python3 ms_jobs_desktop.py

# Funcionalidades disponíveis:
# • Visualizar vagas coletadas
# • Aplicar filtros avançados
# • Gerar gráficos estatísticos
# • Exportar dados
# • Abrir mapas interativos
```

### 🗺️ Geração de Mapas

```bash
# Gerar mapa interativo standalone
python3 interactive_map_widget.py

# Opções de customização:
# • Escolher dados de entrada
# • Definir filtros geográficos
# • Configurar estilos visuais
# • Exportar HTML
```

## 📊 Dados Suportados

### 🏢 Empresas Cobertas
- **141+ empresas** com portais próprios em MS
- **Setores diversos**: Agronegócio, Frigorífico, Mineração, Serviços, Tecnologia
- **Cobertura geográfica**: 28 cidades de MS
- **Tipos de portal**: Gupy, plataformas proprietárias, sites corporativos

### 📍 Cidades Cobertas
```
Campo Grande    • Dourados        • Três Lagoas    • Corumbá
Ponta Porã      • Naviraí         • Nova Andradina • Maracaju  
Sidrolândia     • Caarapó         • Aquidauana     • Paranaíba
Chapadão do Sul • Coxim           • Miranda        • Bonito
Jardim          • Iguatemi        • Itaquiraí      • Água Clara
... e mais 8 cidades
```

### 💼 Informações Coletadas
- **Título da vaga** e descrição completa
- **Empresa** e setor de atuação
- **Localização** precisa (cidade/região)
- **Tipo de contrato** (CLT, PJ, Estágio, etc.)
- **Modalidade** (Presencial, Remoto, Híbrido)
- **Data de coleta** e validade
- **Link direto** para candidatura
- **Requisitos** e benefícios *(quando disponível)*

## 📈 Exemplos de Uso

### 🔍 Cenário 1: Análise de Mercado Regional
```python
# Coletar dados de todas as empresas de agronegócio
python3 unified_ms_job_scraper.py --sector "Agronegócio" --region "Centro-Oeste MS"

# Analisar na interface desktop
python3 ms_jobs_desktop.py
# → Aplicar filtros por setor
# → Visualizar distribuição geográfica
# → Gerar relatórios estatísticos
```

### 🎯 Cenário 2: Busca Personalizada
```python
# Buscar vagas específicas de TI
python3 unified_ms_job_scraper.py --keywords "desenvolvedor,programador,analista sistemas"

# Filtrar resultados
# → Remoto: Trabalho à distância
# → Campo Grande: Localização específica
# → Últimos 7 dias: Período recente
```

### 🗺️ Cenário 3: Visualização Geográfica
```python
# Gerar mapa de densidade de vagas
python3 interactive_map_widget.py --input "output/vagas_ms_latest.csv"

# Recursos do mapa:
# → Clustering por densidade
# → Filtros por empresa
# → Popups com detalhes
# → Estatísticas por região
```

## 🔧 Solução de Problemas

### ❗ Problemas Comuns

#### **ChromeDriver não encontrado**
```bash
# Ubuntu/Debian
sudo apt install chromium-chromedriver

# Manual
wget https://chromedriver.chromium.org/
sudo mv chromedriver /usr/local/bin/
```

#### **Erro de permissão psutil**
```bash
# Linux
sudo apt install python3-psutil

# Ou alternativa via pip
pip install --user psutil
```

#### **Timeout em sites lentos**
```bash
# Aumentar timeout no .env
SCRAPER_TIMEOUT=60
SCRAPER_RATE_LIMIT=2.0
```

#### **Interface não carrega**
```bash
# Instalar dependências de GUI
sudo apt install python3-tk python3-dev

# Atualizar customtkinter
pip install --upgrade customtkinter
```

### 🐛 Debug e Logs

```bash
# Habilitar logs detalhados
export SCRAPER_VERBOSE_LOGGING=true

# Verificar logs
tail -f logs/scraper_$(date +%Y%m%d).log

# Testar conexões
python3 -c "from selenium import webdriver; print('Selenium OK')"
```

## 🤝 Contribuição

### 📝 Como Contribuir

1. **Fork** o repositório
2. **Crie** uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. **Push** para a branch (`git push origin feature/AmazingFeature`)
5. **Abra** um Pull Request

### 🎯 Áreas de Contribuição

- **🔍 Novos Scrapers**: Adicionar suporte a mais empresas/plataformas
- **🎨 Interface**: Melhorar UX/UI da aplicação desktop
- **📊 Análises**: Implementar novas visualizações e insights
- **🗺️ Mapas**: Adicionar recursos geográficos avançados
- **🔧 Performance**: Otimizar velocidade e consumo de recursos
- **📚 Documentação**: Melhorar docs e exemplos

### 📋 Padrões de Código

- **PEP 8** para formatação Python
- **Type hints** obrigatórios em funções públicas
- **Docstrings** detalhadas para classes e métodos
- **Testes unitários** para funcionalidades críticas
- **Logs estruturados** para debugging

## 📄 Licença

Este projeto está licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🆘 Suporte

### 📞 Canais de Suporte

- **Issues**: [GitHub Issues](https://github.com/seu-usuario/scrapper-vagasms/issues)
- **Discussões**: [GitHub Discussions](https://github.com/seu-usuario/scrapper-vagasms/discussions)
- **Email**: seu.email@exemplo.com

### ❓ FAQ

**P: O scraper funciona 24/7?**  
R: Sim, mas recomenda-se intervalos para respeitar rate limits dos sites.

**P: Posso adicionar mais empresas?**  
R: Sim! Edite o arquivo `data/json_portais_carreiras_ms.json`.

**P: Os mapas funcionam offline?**  
R: Não, requerem conexão para carregar tiles do Leaflet.

**P: Há limites de coleta?**  
R: O sistema respeita robots.txt e implementa rate limiting ético.

---

## 📊 Estatísticas do Projeto

- **📁 Arquivos Python**: 6 principais + 5 módulos auxiliares
- **📏 Linhas de Código**: ~4.000+ linhas
- **🏢 Empresas Suportadas**: 141+ portais
- **📍 Cidades Cobertas**: 28 cidades MS
- **🎯 Precisão Geográfica**: >95% para localização MS

---

**Desenvolvido com ❤️ para o mercado de trabalho de Mato Grosso do Sul**

*Última atualização: Setembro 2024*