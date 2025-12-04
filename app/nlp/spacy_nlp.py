import spacy
from spacy.matcher import PhraseMatcher
import re

# Carrega o modelo (precisa ter baixado: python -m spacy download pt_core_news_sm)
_nlp = spacy.load("pt_core_news_sm")

# --- Skills via PhraseMatcher (MULTIDISCIPLINAR: Todas as áreas) ---
_SKILLS = [
    # ========== TI & PROGRAMAÇÃO ==========
    # Linguagens
    "python", "java", "javascript", "typescript", "c", "c++", "c#", "golang", "go",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql",
    # Web
    "html", "html5", "css", "css3", "react", "angular", "vue", "vue.js", "next.js",
    "node", "nodejs", "node.js", "express", "fastapi", "django", "flask", "spring",
    "asp.net", ".net", "blazor",
    "desenvolvimento web", "front-end", "back-end", "full-stack", "full stack",
    # Mobile
    "flutter", "react native", "android", "ios", "mobile", "app mobile",
    "desenvolvimento mobile", "aplicativo", "aplicativos",
    # Bancos de Dados
    "mongodb", "mysql", "postgresql", "postgres", "sqlite", "redis", "elasticsearch",
    "dynamodb", "cassandra", "oracle", "sql server", "mariadb",
    "banco de dados", "database", "nosql", "sql",
    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s", "terraform",
    "ansible", "jenkins", "gitlab", "github", "circleci", "travis",
    "nuvem", "cloud", "devops", "integração contínua", "ci/cd",
    # Data Science & ML
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras", "spark",
    "hadoop", "airflow", "mlflow", "jupyter", "matplotlib", "seaborn", "plotly",
    "machine learning", "deep learning", "inteligência artificial", "ia", "ai",
    "ciência de dados", "data science", "análise de dados", "big data",
    # Ferramentas Dev
    "git", "linux", "bash", "powershell", "vim", "vscode", "intellij", "eclipse",
    "postman", "jira", "confluence", "slack", "trello",
    
    # ========== MARKETING & VENDAS ==========
    "marketing digital", "seo", "sem", "google ads", "facebook ads", "instagram ads",
    "redes sociais", "social media", "marketing de conteúdo", "content marketing",
    "inbound marketing", "outbound marketing", "email marketing", "crm",
    "copywriting", "branding", "brand management", "gestão de marca",
    "análise de mercado", "pesquisa de mercado", "market research",
    "google analytics", "google tag manager", "gtm", "meta ads",
    "hubspot", "salesforce", "rdstation", "mailchimp",
    "vendas", "prospecção", "negociação", "fechamento",
    "inside sales", "outside sales", "account management", "customer success",
    
    # ========== DESIGN & CRIAÇÃO ==========
    "photoshop", "illustrator", "indesign", "figma", "sketch", "adobe xd",
    "corel draw", "canva", "after effects", "premiere", "lightroom",
    "ui design", "ux design", "design gráfico", "design thinking",
    "prototipagem", "wireframe", "mockup", "tipografia", "identidade visual",
    "motion design", "animação", "edição de vídeo", "design de produto",
    
    # ========== FINANÇAS & CONTABILIDADE ==========
    "contabilidade", "auditoria", "perícia contábil", "controladoria",
    "análise financeira", "planejamento financeiro", "orçamento", "budget",
    "demonstrações financeiras", "balanço patrimonial", "dre",
    "custos", "gestão de custos", "análise de custos",
    "impostos", "tributação", "fiscal", "compliance fiscal",
    "excel", "power bi", "tableau", "qlik", "sap", "erp",
    "conciliação bancária", "fluxo de caixa", "cash flow",
    "ifrs", "cpc", "sped", "nota fiscal eletrônica", "nfe",
    
    # ========== RH & RECURSOS HUMANOS ==========
    "recrutamento", "seleção", "r&s", "hunting", "headhunting",
    "employer branding", "gestão de pessoas", "people analytics",
    "treinamento", "desenvolvimento", "t&d", "capacitação",
    "avaliação de desempenho", "performance", "feedback",
    "climate organizacional", "pesquisa de clima", "endomarketing",
    "remuneração", "benefícios", "folha de pagamento",
    "relações trabalhistas", "sindicato", "clt", "legislação trabalhista",
    "onboarding", "offboarding", "employee experience",
    
    # ========== JURÍDICO & DIREITO ==========
    "direito civil", "direito penal", "direito trabalhista",
    "direito tributário", "direito empresarial", "direito contratual",
    "advocacia", "consultoria jurídica", "parecer jurídico",
    "processo judicial", "petição", "recursos", "contratos",
    "compliance", "governança corporativa", "due diligence",
    "mediação", "arbitragem", "negociação de conflitos",
    
    # ========== ENGENHARIA & ARQUITETURA ==========
    "autocad", "revit", "sketchup", "solidworks", "catia", "inventor",
    "bim", "projetos", "cálculo estrutural", "gestão de obras",
    "orçamento de obras", "cronograma", "ms project",
    "segurança do trabalho", "nr", "cipa", "ppra", "pcmso",
    "qualidade", "iso 9001", "lean", "six sigma", "kaizen",
    
    # ========== SAÚDE & BEM-ESTAR ==========
    "enfermagem", "medicina", "farmácia", "nutrição", "fisioterapia",
    "psicologia", "terapia", "atendimento clínico", "diagnóstico",
    "prescrição", "prontuário eletrônico", "sus", "vigilância sanitária",
    
    # ========== EDUCAÇÃO & ENSINO ==========
    "docência", "ensino", "pedagogia", "didática", "metodologia",
    "ead", "educação a distância", "moodle", "plataforma educacional",
    "avaliação educacional", "plano de aula", "currículo",
    
    # ========== LOGÍSTICA & SUPPLY CHAIN ==========
    "logística", "supply chain", "cadeia de suprimentos",
    "armazenagem", "estoque", "inventário", "wms", "tms",
    "compras", "procurement", "fornecedores", "cotação",
    "importação", "exportação", "comércio exterior",
    "transporte", "distribuição", "roteirização",
    
    # ========== ATENDIMENTO & RELACIONAMENTO ==========
    "atendimento ao cliente", "customer service", "sac",
    "call center", "telemarketing", "contact center",
    "relacionamento com cliente", "pós-venda", "fidelização",
    "experiência do cliente", "customer experience", "cx",
    
    # ========== SOFT SKILLS & METODOLOGIAS ==========
    "agile", "scrum", "kanban", "metodologia ágil", "pmbok", "pmp",
    "gestão de projetos", "project management", "liderança",
    "trabalho em equipe", "comunicação", "negociação",
    "resolução de problemas", "pensamento crítico", "criatividade",
    "gestão de tempo", "organização", "proatividade",
    "inglês", "espanhol", "francês", "alemão", "mandarim",
    "fluente", "avançado", "intermediário", "conversação",
    
    # ========== ADMINISTRATIVO & GESTÃO ==========
    "gestão", "administração", "planejamento estratégico",
    "indicadores", "kpi", "dashboard", "relatórios gerenciais",
    "processos", "mapeamento de processos", "bpm", "melhoria contínua",
    "office", "word", "excel", "powerpoint", "outlook",
    "google workspace", "sheets", "docs", "slides",
]
_phrase = PhraseMatcher(_nlp.vocab, attr="LOWER")
_phrase.add("SKILL", [_nlp.make_doc(s) for s in _SKILLS])

# --- EntityRuler no spaCy v3: use o NOME do componente ---
if "entity_ruler" in _nlp.pipe_names:
    ruler = _nlp.get_pipe("entity_ruler")
else:
    ruler = _nlp.add_pipe("entity_ruler", before="ner", config={"overwrite_ents": True})

ruler.add_patterns([
    {"label": "CERT", "pattern": [{"LOWER": "az-900"}]},
    {"label": "CERT", "pattern": [{"LOWER": "dp-203"}]},
    {"label": "CERT", "pattern": [{"LOWER": "security+"}]},
])

def extract_email(text: str) -> bool:
    """Detecta se há email no texto."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return bool(re.search(email_pattern, text))

def extract_phone(text: str) -> bool:
    """Detecta se há telefone no texto (formatos brasileiros).
    
    Normaliza o texto antes para remover caracteres Unicode extras
    que podem aparecer na extração de PDFs.
    """
    # Normalizar texto: remover espaços extras, tabs, quebras de linha estranhas
    normalized = ' '.join(text.split())
    
    phone_patterns = [
        r'\(\d{2}\)\s*\d{4,5}\s*[-\s]?\s*\d{4}',  # (11) 98765-4321 ou (11) 98765 -4321 (PDF)
        r'\d{2}[\s.-]?\d{4,5}\s*[-\s]?\s*\d{4}',  # 11 98765-4321 ou 11 98765 -4321
        r'\+55[\s.-]?\d{2}[\s.-]?\(?\d{2}\)?[\s.-]?\d{4,5}\s*[-\s]?\s*\d{4}',  # +55 11 98765-4321 ou +55 (11) 98765 -4321
        r'\d{10,11}',  # 11987654321 (formato sem separadores)
    ]
    return any(re.search(pattern, normalized) for pattern in phone_patterns)

def count_sections(text: str) -> int:
    """Conta seções importantes do currículo (PT-BR + EN)."""
    if not text:
        return 0
    
    text_lower = text.lower()
    sections = [
        # Contato/Dados pessoais (PT + EN)
        r'\b(contato|dados pessoais|informações pessoais|contact|personal info)\b',
        # Resumo/Objetivo (PT + EN)
        r'\b(resumo|perfil|objetivo|sobre|summary|profile|about|objective)\b',
        # Experiência Profissional (PT + EN)
        r'\b(experiência|experiencia|histórico profissional|carreira|experience|work history|employment)\b',
        # Formação/Educação (PT + EN)
        r'\b(formação|educação|education|academic|qualificações|qualifications)\b',
        # Habilidades/Skills (PT + EN)
        r'\b(habilidades|competências|skills|tecnologias|technologies|conhecimentos)\b',
        # Projetos (PT + EN)
        r'\b(projetos|portfolio|portfólio|projects|work samples)\b',
        # Certificações (PT + EN)
        r'\b(certificações|certificados|cursos|certifications|certificates|courses)\b',
        # Idiomas (PT + EN)
        r'\b(idiomas|languages)\b',
        # Extras comuns em PT-BR
        r'\b(conquistas|realizações|achievements)\b',
        r'\b(publicações|publications)\b',
    ]
    
    count = sum(1 for pattern in sections if re.search(pattern, text_lower))
    return count

def detect_projects(text: str) -> int:
    """Detecta menções a projetos (acadêmicos, pessoais, profissionais) PT-BR + EN."""
    if not text:
        return 0
    
    text_lower = text.lower()
    project_patterns = [
        # Padrões PT-BR
        r'\bprojeto\s+(de|em|sobre|para|com|usando)',
        r'\bdesenvol(vi|veu|vemos|vendo|vimento de)\s+(um|uma|o|a|sistema|aplicativo|site|aplicação|aplicativo)',
        r'\b(criação|criou|criei|criamos)\s+(de|do|da|um|uma)\s+(sistema|aplicativo|app|site|plataforma|solução)',
        r'\b(implementação|implementou|implementei|implementamos)\s+(de|do|da)',
        r'\b(construção|construí|construiu)\s+(de|do|da)',
        r'\batuei\s+(no|na)\s+(desenvolvimento|criação|implementação)',
        # Padrões EN
        r'\b(developed|created|built|implemented)\s+(a|an|the)?\s*(system|application|app|website|platform|solution)',
        r'\bproject\s+(for|with|using|in)',
        # Comuns
        r'\b(trabalho de conclusão|tcc|projeto final|final project)',
        r'\b(projeto acadêmico|academic project|projeto pessoal|personal project)',
        r'\bgithub\.com',
        r'\bgitlab\.com',
        r'\bportfólio|portfolio',
    ]
    
    count = sum(1 for pattern in project_patterns if re.search(pattern, text_lower))
    return min(count, 5)  # Cap em 5 para evitar falsos positivos

def analyze(text: str) -> dict:
    """Analisa o texto e retorna features básicas para o scoring."""
    doc = _nlp(text or "")
    skills = sorted(set(doc[s:e].text.lower() for _, s, e in _phrase(doc)))
    certs  = [ent.text for ent in doc.ents if ent.label_ == "CERT"]
    dates  = [ent.text for ent in doc.ents if ent.label_ == "DATE"]
    lemmas = [t.lemma_.lower() for t in doc if not t.is_space]
    
    # Detecções adicionais
    has_email = extract_email(text)
    has_phone = extract_phone(text)
    sections_count = count_sections(text)
    project_hits = detect_projects(text)
    
    return {
        "tokens": len(doc), 
        "skills": skills, 
        "certs": certs, 
        "dates": dates, 
        "lemmas": lemmas,
        "has_email": has_email,
        "has_phone": has_phone,
        "sections_count": sections_count,
        "project_hits": project_hits
    }
