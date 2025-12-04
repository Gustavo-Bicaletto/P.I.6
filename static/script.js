// Elementos DOM
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const uploadPlaceholder = document.getElementById('uploadPlaceholder');
const fileSelected = document.getElementById('fileSelected');
const fileName = document.getElementById('fileName');
const removeFile = document.getElementById('removeFile');
const analyzeBtn = document.getElementById('analyzeBtn');
const progressContainer = document.getElementById('progressContainer');
const resultsCard = document.getElementById('resultsCard');
const resultsContent = document.getElementById('resultsContent');

let selectedFile = null;

// Upload area click
uploadArea.addEventListener('click', () => {
    if (!selectedFile) {
        fileInput.click();
    }
});

// File selection
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFileSelect(file);
    }
});

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith('.pdf') || file.name.endsWith('.txt'))) {
        handleFileSelect(file);
    } else {
        alert('Por favor, selecione apenas arquivos PDF ou TXT');
    }
});

// Handle file selection
function handleFileSelect(file) {
    selectedFile = file;
    fileName.textContent = file.name;
    uploadPlaceholder.style.display = 'none';
    fileSelected.style.display = 'flex';
    analyzeBtn.disabled = false;
    resultsCard.style.display = 'none';
}

// Remove file
removeFile.addEventListener('click', (e) => {
    e.stopPropagation();
    selectedFile = null;
    fileInput.value = '';
    fileName.textContent = '';
    uploadPlaceholder.style.display = 'block';
    fileSelected.style.display = 'none';
    analyzeBtn.disabled = true;
    resultsCard.style.display = 'none';
});

// Analyze button
analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    
    // Show progress
    analyzeBtn.disabled = true;
    progressContainer.style.display = 'block';
    resultsCard.style.display = 'none';
    
    // Create form data
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    try {
        console.log('Enviando arquivo para análise:', selectedFile.name);
        
        // Send to API
        const response = await fetch('/api/analyze', {
            method: 'POST',
            body: formData
        });
        
        console.log('Resposta recebida:', response.status, response.statusText);
        
        // Verificar se a resposta é válida
        const contentType = response.headers.get('content-type');
        console.log('Content-Type:', contentType);
        
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Resposta não é JSON:', text);
            throw new Error('Servidor retornou resposta inválida. Verifique o console do servidor.');
        }
        
        const result = await response.json();
        
        console.log('Dados:', result);
        
        if (!response.ok || !result.success) {
            throw new Error(result.error || 'Erro desconhecido na análise');
        }
        
        // Display results
        displayResults(result);
        
    } catch (error) {
        console.error('Erro:', error);
        
        let errorMessage = error.message || 'Erro desconhecido';
        
        // Mensagens mais amigáveis
        if (errorMessage.includes('Failed to fetch')) {
            errorMessage = 'Não foi possível conectar ao servidor. Verifique se o servidor está rodando.';
        } else if (errorMessage.includes('NetworkError')) {
            errorMessage = 'Erro de rede. Verifique sua conexão com a internet.';
        } else if (errorMessage.includes('JSON')) {
            errorMessage = 'Erro ao processar resposta do servidor. Verifique o console do servidor (terminal).';
        }
        
        resultsContent.innerHTML = `
            <div class="result-error">
                <div class="result-bold">❌ ERRO NA ANÁLISE</div><br>
                <div>${errorMessage}</div><br>
                <div class="result-info">💡 Dicas:</div>
                <div>   • Verifique se o servidor está rodando (python web_server.py)</div>
                <div>   • Verifique o console do servidor para mensagens de erro detalhadas</div>
                <div>   • Certifique-se que o arquivo é PDF ou TXT</div>
                <div>   • Tamanho máximo: 16MB</div>
                <div>   • Pressione F12 e veja a aba Console para mais detalhes</div>
            </div>
        `;
        resultsCard.style.display = 'block';
    } finally {
        progressContainer.style.display = 'none';
        analyzeBtn.disabled = false;
    }
});

// Display results
function displayResults(data) {
    const { features, result } = data;
    
    const isExperienced = features.has_experience;
    const finalScore = result.score;
    const label = result.label;
    const subscores = result.rb_subscores || {};
    
    // Build result HTML
    let html = '';
    
    // Header
    html += '<div class="result-title">RESULTADO DA AVALIAÇÃO</div>\n';
    html += '<div class="result-separator"></div>\n\n';
    
    // Score
    html += `<div class="result-bold">Score Final: ${finalScore.toFixed(1)}/100</div>\n\n`;
    
    // Profile
    const perfil = isExperienced ? "EXPERIENTE" : "ESTAGIÁRIO/JÚNIOR";
    html += `<div class="result-bold">Perfil: ${perfil}</div>\n\n`;
    
    // Evaluation
    html += '<div class="result-bold">Avaliação: ';
    if (label === "Bom") {
        if (finalScore >= 80) {
            html += '<span class="result-success">EXCELENTE</span></div>\n';
            html += '<div class="result-success">Currículo de alta qualidade.</div>\n\n';
        } else if (finalScore >= 65) {
            html += '<span class="result-success">BOM</span></div>\n';
            html += '<div class="result-info">Currículo sólido, com espaço para otimizações.</div>\n\n';
        } else {
            html += '<span class="result-success">BOM</span></div>\n';
            html += '<div class="result-info">Aprovado, mas pode ser melhorado.</div>\n\n';
        }
    } else {
        html += '<span class="result-error">RUIM</span></div>\n';
        html += '<div class="result-error">Currículo precisa de melhorias significativas.</div>\n\n';
    }
    
    // Strengths and weaknesses
    html += buildStrengthsWeaknesses(subscores);
    
    // Recommendations
    html += buildRecommendations(finalScore, isExperienced, subscores, label);
    
    resultsContent.innerHTML = html;
    resultsCard.style.display = 'block';
    
    // Scroll to results
    resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Build strengths and weaknesses
function buildStrengthsWeaknesses(subscores) {
    let html = '';
    
    const names = {
        'skills': 'Habilidades',
        'experience': 'Experiência',
        'doc_quality': 'Qualidade do Documento',
        'contact': 'Informações de Contato',
        'certs': 'Certificações',
        'projects': 'Projetos',
        'impact': 'Impacto/Métricas'
    };
    
    // Strengths (>= 90%)
    const strongPoints = Object.entries(subscores)
        .filter(([k, v]) => v >= 0.9)
        .slice(0, 3);
    
    if (strongPoints.length > 0) {
        html += '<span class="result-success">Pontos Fortes:</span>\n';
        strongPoints.forEach(([key]) => {
            const name = names[key] || key;
            html += `<span class="result-success">  - ${name}</span>\n`;
        });
        html += '\n';
    }
    
    // Weaknesses (< 80%)
    const improvementTips = {
        'skills': "Adicione mais habilidades técnicas relevantes para sua área",
        'experience': "Detalhe melhor sua experiência: responsabilidades, conquistas, período exato",
        'projects': "Mencione projetos desenvolvidos (acadêmicos, pessoais ou profissionais)",
        'impact': "Quantifique seus resultados: números, percentuais, métricas de impacto",
        'doc_quality': "Melhore a estrutura: adicione mais seções (Formação, Projetos, Idiomas, etc.)",
        'certs': "Adicione certificações, cursos ou qualificações relevantes",
        'contact': "Inclua informações completas de contato: telefone, email, LinkedIn, localização"
    };
    
    const weakPoints = Object.entries(subscores)
        .filter(([k, v]) => k !== 'semantic' && k !== 'context' && v < 0.8)
        .sort((a, b) => a[1] - b[1])
        .slice(0, 5);
    
    if (weakPoints.length > 0) {
        html += '<span class="result-warning">Oportunidades de Melhoria:</span>\n';
        weakPoints.forEach(([key]) => {
            const tip = improvementTips[key] || "Revisar este item";
            html += `<span class="result-warning">  - ${tip}</span>\n`;
        });
        html += '\n';
    } else {
        html += '<span class="result-success">Todos os critérios estão em níveis excelentes (&gt;80%).</span>\n\n';
    }
    
    return html;
}

// Build recommendations
function buildRecommendations(finalScore, isExperienced, subscores, label) {
    let html = '';
    
    html += '<div class="result-separator"></div>\n';
    html += '<div class="result-bold">Análise Detalhada e Recomendações:</div>\n\n';
    
    const cutoff = isExperienced ? 50.0 : 40.0;
    
    if (finalScore >= cutoff) {
        html += '<span class="result-success">CURRÍCULO APROVADO</span>\n\n';
        
        if (finalScore >= 80) {
            html += '<div class="result-bold">Avaliação Geral:</div>\n';
            html += 'Excelente trabalho! Seu currículo demonstra um alto nível de profissionalismo\n';
            html += 'e está muito bem estruturado. Você possui um perfil forte que se destaca\n';
            html += 'significativamente da competição no mercado.\n\n';
            
            html += '<div class="result-bold">Pontos de Destaque:</div>\n';
            html += '  • Documento bem organizado e de fácil leitura\n';
            html += '  • Experiências profissionais claramente descritas\n';
            html += '  • Conjunto sólido de habilidades técnicas\n';
            html += '  • Informações de contato completas e acessíveis\n\n';
            
            html += '<div class="result-bold">Recomendações para Manter a Excelência:</div>\n';
            html += '  • Atualize regularmente com suas conquistas mais recentes\n';
            html += '  • Adicione métricas específicas sempre que possível (ex: "aumentou vendas em 35%")\n';
            html += '  • Considere incluir links para portfólio online, GitHub ou LinkedIn\n';
            html += '  • Adapte o resumo profissional para cada tipo de vaga que candidatar\n';
            html += '  • Continue investindo em certificações e cursos relevantes para sua área\n';
        } else if (finalScore >= 65) {
            html += '<div class="result-bold">Avaliação Geral:</div>\n';
            html += 'Seu currículo está bem estruturado e apresenta informações relevantes de forma\n';
            html += 'clara. Você possui uma base sólida que atende aos critérios principais para\n';
            html += 'processos seletivos. Com algumas otimizações específicas, seu perfil pode\n';
            html += 'se destacar ainda mais.\n\n';
            
            html += '<div class="result-bold">O que está funcionando bem:</div>\n';
            html += '  • Estrutura organizada e profissional\n';
            html += '  • Experiências relevantes demonstradas\n';
            html += '  • Habilidades técnicas identificadas\n';
            html += '  • Informações essenciais presentes\n\n';
            
            html += '<div class="result-bold">Oportunidades de Melhoria Identificadas:</div>\n';
            
            if ((subscores.impact || 1.0) < 0.7) {
                html += '\n<div class="result-bold">1. Impacto e Resultados Quantificáveis:</div>\n';
                html += '  • Problema: Faltam métricas e números que comprovem seus resultados\n';
                html += '  • Por que importa: Recrutadores valorizam dados concretos de performance\n';
                html += '  • Como melhorar:\n';
                html += '    - Adicione percentuais de crescimento (ex: "aumentou engajamento em 45%")\n';
                html += '    - Inclua valores financeiros quando relevante (ex: "gerenciei orçamento de R$ 200k")\n';
                html += '    - Cite quantidades (ex: "liderei equipe de 8 pessoas", "processei 150+ tickets/mês")\n';
                html += '    - Use números em projetos (ex: "reduziu tempo de resposta em 30%")\n\n';
            }
            
            if ((subscores.projects || 1.0) < 0.7) {
                html += '<div class="result-bold">2. Projetos e Realizações:</div>\n';
                html += '  • Problema: Poucos projetos mencionados ou não detalhados suficientemente\n';
                html += '  • Por que importa: Projetos demonstram iniciativa e aplicação prática de habilidades\n';
                html += '  • Como melhorar:\n';
                html += '    - Descreva projetos acadêmicos relevantes para a área\n';
                html += '    - Inclua projetos pessoais (GitHub, sites, aplicativos desenvolvidos)\n';
                html += '    - Mencione projetos profissionais com resultados alcançados\n';
                html += '    - Para cada projeto: tecnologias usadas + problema resolvido + resultado\n';
                html += '    - Exemplo: "Desenvolvido sistema de vendas em Python/Django que automatizou\n';
                html += '      30% dos processos manuais, reduzindo erros em 25%"\n\n';
            }
            
            if ((subscores.certs || 1.0) < 0.7) {
                html += '<div class="result-bold">3. Certificações e Qualificações:</div>\n';
                html += '  • Problema: Poucas certificações ou cursos complementares listados\n';
                html += '  • Por que importa: Certificações validam conhecimento e mostram dedicação\n';
                html += '  • Como melhorar:\n';
                html += '    - Adicione certificações técnicas relevantes (AWS, Google, Microsoft, etc.)\n';
                html += '    - Inclua cursos online relevantes (Coursera, Udemy, plataformas especializadas)\n';
                html += '    - Mencione workshops e treinamentos profissionais\n';
                html += '    - Liste idiomas com nível de proficiência\n';
                html += '    - Priorize certificações recentes (últimos 3 anos) e reconhecidas no mercado\n\n';
            }
            
            if ((subscores.skills || 1.0) < 0.9) {
                html += '<div class="result-bold">4. Habilidades Técnicas:</div>\n';
                html += '  • Sugestão: Expanda sua seção de habilidades\n';
                html += '  • Como melhorar:\n';
                html += '    - Liste todas as tecnologias/ferramentas que domina\n';
                html += '    - Agrupe por categoria (ex: Linguagens, Frameworks, Ferramentas, Metodologias)\n';
                html += '    - Inclua soft skills relevantes (liderança, comunicação, trabalho em equipe)\n';
                html += '    - Seja específico (ao invés de "Office", liste "Excel avançado, Power BI")\n\n';
            }
            
            html += '<div class="result-bold">Próximos Passos Recomendados:</div>\n';
            html += '  1. Revise cada experiência e adicione pelo menos 1-2 métricas quantificáveis\n';
            html += '  2. Dedique uma seção específica para "Projetos Relevantes" com 2-3 destaques\n';
            html += '  3. Busque pelo menos 1 certificação adicional relevante para sua área\n';
            html += '  4. Peça feedback de colegas ou mentores da sua área\n';
            html += '  5. Personalize o resumo profissional para cada vaga específica\n';
        } else {
            html += '<div class="result-bold">Avaliação Geral:</div>\n';
            html += 'Seu currículo atende aos requisitos mínimos e contém as informações básicas\n';
            html += 'necessárias. No entanto, há oportunidades significativas de melhoria que podem\n';
            html += 'aumentar consideravelmente suas chances em processos seletivos.\n\n';
            
            html += '<div class="result-bold">Áreas Prioritárias para Desenvolvimento:</div>\n\n';
            
            const weakAreas = Object.entries(subscores)
                .filter(([k, v]) => k !== 'semantic' && k !== 'context' && v < 0.8)
                .sort((a, b) => a[1] - b[1]);
            
            if (weakAreas.some(([k]) => k === 'skills')) {
                html += '<div class="result-bold">1. Habilidades Técnicas (PRIORIDADE ALTA):</div>\n';
                html += '  • Situação atual: Poucas habilidades listadas ou seção pouco desenvolvida\n';
                html += '  • Impacto: Recrutadores buscam palavras-chave específicas para filtrar candidatos\n';
                html += '  • Ação imediata:\n';
                html += '    - Crie uma seção dedicada "Habilidades Técnicas" ou "Competências"\n';
                html += '    - Liste no mínimo 10-15 habilidades relevantes para sua área\n';
                html += '    - Inclua: linguagens de programação, ferramentas, frameworks, metodologias\n';
                html += '    - Adicione soft skills importantes (trabalho em equipe, comunicação, etc.)\n';
                html += '    - Seja específico e use termos do mercado\n\n';
            }
            
            if (weakAreas.some(([k]) => k === 'experience')) {
                html += '<div class="result-bold">2. Experiência Profissional (PRIORIDADE ALTA):</div>\n';
                html += '  • Situação atual: Experiências pouco detalhadas ou mal estruturadas\n';
                html += '  • Impacto: Impossível avaliar suas reais competências e contribuições\n';
                html += '  • Ação imediata:\n';
                html += '    - Para cada experiência, inclua: cargo, empresa, período (mês/ano)\n';
                html += '    - Liste 3-5 responsabilidades principais em bullet points\n';
                html += '    - Adicione conquistas específicas com números\n';
                html += '    - Use verbos de ação: "Desenvolvi", "Gerenciei", "Implementei", "Otimizei"\n';
                html += '    - Foque em resultados, não apenas tarefas\n\n';
            }
            
            if (weakAreas.some(([k]) => k === 'projects')) {
                html += '<div class="result-bold">3. Projetos (IMPORTANTE):</div>\n';
                html += '  • Situação atual: Nenhum ou poucos projetos mencionados\n';
                html += '  • Impacto: Perde oportunidade de demonstrar aplicação prática\n';
                html += '  • Ação imediata:\n';
                html += '    - Adicione seção "Projetos" com pelo menos 2-3 exemplos\n';
                html += '    - Inclua projetos acadêmicos relevantes\n';
                html += '    - Liste projetos pessoais (mesmo que não profissionais)\n';
                html += '    - Estrutura ideal: Nome do Projeto | Tecnologias | Descrição breve | Link\n\n';
            }
            
            if (weakAreas.some(([k]) => k === 'impact')) {
                html += '<div class="result-bold">4. Métricas e Resultados (IMPORTANTE):</div>\n';
                html += '  • Situação atual: Faltam números e dados quantificáveis\n';
                html += '  • Impacto: Dificulta comprovar suas contribuições reais\n';
                html += '  • Ação imediata:\n';
                html += '    - Revise cada experiência e adicione números específicos\n';
                html += '    - Exemplos: "Reduziu custos em 20%", "Gerenciei 5 pessoas", "100+ clientes atendidos"\n';
                html += '    - Use percentuais de melhoria sempre que possível\n';
                html += '    - Quantifique escopo: tamanho de equipe, orçamento, volume de trabalho\n\n';
            }
            
            if (weakAreas.some(([k]) => k === 'doc_quality')) {
                html += '<div class="result-bold">5. Qualidade do Documento (IMPORTANTE):</div>\n';
                html += '  • Situação atual: Estrutura incompleta ou desorganizada\n';
                html += '  • Impacto: Dificulta leitura e passa impressão de despreparo\n';
                html += '  • Ação imediata:\n';
                html += '    - Organize em seções claras: Contato, Resumo, Experiência, Formação, Skills\n';
                html += '    - Adicione seções opcionais relevantes: Projetos, Certificações, Idiomas\n';
                html += '    - Use formatação consistente em todo documento\n';
                html += '    - Mantenha entre 1-2 páginas (ideal: 1 página para júnior, 2 para sênior)\n';
                html += '    - Revise ortografia e gramática cuidadosamente\n\n';
            }
            
            html += '<div class="result-bold">Plano de Ação Sugerido (próximos 7 dias):</div>\n';
            html += '  Dia 1-2: Expanda seção de habilidades e adicione palavras-chave relevantes\n';
            html += '  Dia 3-4: Reescreva experiências com foco em resultados e adicione métricas\n';
            html += '  Dia 5: Crie seção de projetos com pelo menos 2 exemplos detalhados\n';
            html += '  Dia 6: Adicione certificações e cursos relevantes\n';
            html += '  Dia 7: Revise formatação, ortografia e peça feedback de alguém da área\n\n';
            
            html += '<div class="result-bold">Recursos Recomendados:</div>\n';
            html += '  • Busque exemplos de currículos da sua área no LinkedIn\n';
            html += '  • Use ferramentas de correção ortográfica (LanguageTool, Grammarly)\n';
            html += '  • Pesquise descrições de vagas para identificar palavras-chave importantes\n';
            html += '  • Considere consultoria de carreira ou revisão por profissional de RH\n';
        }
    } else {
        html += '<span class="result-warning">CURRÍCULO PRECISA DE REVISÃO COMPLETA</span>\n\n';
        
        html += '<div class="result-bold">Avaliação Geral:</div>\n';
        html += 'Seu currículo não atende aos critérios mínimos estabelecidos para processos\n';
        html += 'seletivos competitivos. É fortemente recomendado uma revisão completa e\n';
        html += 'reestruturação do documento antes de submeter candidaturas.\n\n';
        
        html += '<div class="result-bold">Situação Crítica Identificada:</div>\n';
        html += 'O documento apresenta deficiências significativas em múltiplas áreas essenciais.\n';
        html += 'Sem estas melhorias, as chances de aprovação em triagens iniciais são muito baixas.\n\n';
        
        const weakAreas = Object.entries(subscores)
            .filter(([k, v]) => k !== 'semantic' && k !== 'context' && v < 0.7)
            .sort((a, b) => a[1] - b[1]);
        
        if (weakAreas.length >= 3) {
            html += '<div class="result-bold">Problemas Críticos Encontrados:</div>\n\n';
            
            html += '<div class="result-bold">1. ESTRUTURA E ORGANIZAÇÃO (CRÍTICO):</div>\n';
            html += '  • Problema: Documento desorganizado, incompleto ou mal formatado\n';
            html += '  • Consequência: Recrutadores descartam currículos mal estruturados imediatamente\n';
            html += '  • Ação obrigatória:\n';
            html += '    - Reconstrua o currículo do zero usando um template profissional\n';
            html += '    - Estrutura mínima obrigatória:\n';
            html += '      1. Cabeçalho: Nome + Cargo desejado + Contato (email, telefone, cidade)\n';
            html += '      2. Resumo Profissional: 3-4 linhas sobre você\n';
            html += '      3. Experiência Profissional: Cargo, Empresa, Período, Descrição\n';
            html += '      4. Formação Acadêmica: Curso, Instituição, Período\n';
            html += '      5. Habilidades: Lista de competências técnicas e comportamentais\n';
            html += '    - Mantenha formatação consistente (fontes, tamanhos, espaçamentos)\n';
            html += '    - Use bullet points para listas\n';
            html += '    - Limite a 1-2 páginas máximo\n\n';
            
            html += '<div class="result-bold">2. CONTEÚDO INSUFICIENTE (CRÍTICO):</div>\n';
            html += '  • Problema: Informações essenciais faltando ou muito vagas\n';
            html += '  • Consequência: Impossível avaliar sua qualificação para qualquer vaga\n';
            html += '  • Ação obrigatória:\n';
            html += '    - Contato: Adicione email profissional, telefone com DDD, cidade/estado\n';
            html += '    - Experiências: Descreva TODAS suas experiências relevantes:\n';
            html += '      * O que você fazia? (responsabilidades principais)\n';
            html += '      * Quais resultados alcançou? (com números sempre que possível)\n';
            html += '      * Quais ferramentas/tecnologias usou?\n';
            html += '    - Habilidades: Liste no MÍNIMO 10-15 habilidades da sua área\n';
            html += '    - Formação: Curso completo, instituição, ano de conclusão/previsão\n\n';
            
            html += '<div class="result-bold">3. FALTA DE DIFERENCIAÇÃO (CRÍTICO):</div>\n';
            html += '  • Problema: Nenhum ou poucos elementos que destaquem seu perfil\n';
            html += '  • Consequência: Seu currículo se perde em meio a centenas de outros\n';
            html += '  • Ação obrigatória:\n';
            html += '    - Projetos: Adicione PELO MENOS 2 projetos que desenvolveu\n';
            html += '      * Pode ser acadêmico, pessoal ou profissional\n';
            html += '      * Descreva: o que fez, como fez, resultado obtido\n';
            html += '    - Certificações: Busque pelo menos 1-2 cursos/certificações online\n';
            html += '      * Coursera, Udemy, Google, Microsoft, AWS têm opções gratuitas\n';
            html += '    - Resultados: Transforme tarefas em conquistas:\n';
            html += '      * RUIM: "Atendimento ao cliente"\n';
            html += '      * BOM: "Atendi 50+ clientes/dia com 95% de satisfação"\n\n';
            
            html += '<div class="result-bold">PLANO DE RECONSTRUÇÃO URGENTE:</div>\n\n';
            
            html += 'Semana 1 - Estrutura Básica:\n';
            html += '  □ Dia 1: Pesquise 3-5 exemplos de currículos da sua área (LinkedIn/Google)\n';
            html += '  □ Dia 2: Escolha ou crie um template limpo e profissional\n';
            html += '  □ Dia 3: Preencha todas as seções obrigatórias com informações básicas\n';
            html += '  □ Dia 4: Revise e corrija formatação, ortografia e gramática\n\n';
            
            html += 'Semana 2 - Conteúdo de Qualidade:\n';
            html += '  □ Dia 5-6: Reescreva cada experiência com foco em RESULTADOS e NÚMEROS\n';
            html += '  □ Dia 7: Expanda lista de habilidades para pelo menos 15 itens relevantes\n';
            html += '  □ Dia 8: Adicione seção de Projetos com 2-3 exemplos detalhados\n';
            html += '  □ Dia 9: Faça pelo menos 1 curso online e adicione como certificação\n\n';
            
            html += 'Semana 3 - Refinamento:\n';
            html += '  □ Dia 10: Adicione resumo profissional impactante (3-4 linhas)\n';
            html += '  □ Dia 11: Revise TODA ortografia e gramática (use LanguageTool)\n';
            html += '  □ Dia 12: Peça feedback de 2-3 pessoas (amigos, professores, mentores)\n';
            html += '  □ Dia 13: Aplique correções finais\n';
            html += '  □ Dia 14: Teste com esta ferramenta novamente\n\n';
            
        } else {
            html += '<div class="result-bold">Principais Deficiências Identificadas:</div>\n\n';
            
            const detailedTips = {
                'skills': {
                    title: 'Habilidades Técnicas Insuficientes',
                    impact: 'ATS (sistemas de triagem) e recrutadores filtram por palavras-chave',
                    action: 'Liste no mínimo 12-15 habilidades relevantes da sua área, incluindo ferramentas, tecnologias e metodologias'
                },
                'experience': {
                    title: 'Experiência Mal Descrita',
                    impact: 'Impossível avaliar suas reais competências e nível profissional',
                    action: 'Detalhe cada experiência com cargo, empresa, período, responsabilidades (3-5 bullets) e conquistas específicas'
                },
                'projects': {
                    title: 'Falta de Projetos',
                    impact: 'Sem projetos, não há como comprovar aplicação prática de conhecimento',
                    action: 'Adicione 2-3 projetos relevantes (acadêmicos, pessoais ou profissionais) com descrição e tecnologias usadas'
                },
                'impact': {
                    title: 'Ausência de Métricas e Resultados',
                    impact: 'Currículos sem números não comprovam contribuições reais',
                    action: 'Adicione dados quantificáveis em cada experiência: percentuais, valores, quantidades, melhorias alcançadas'
                },
                'doc_quality': {
                    title: 'Qualidade Documental Baixa',
                    impact: 'Documento mal estruturado é descartado antes mesmo de ser lido',
                    action: 'Reorganize com seções claras, formatação consistente, ortografia correta e layout profissional'
                },
                'certs': {
                    title: 'Falta de Certificações',
                    impact: 'Certificações validam conhecimento e mostram proatividade',
                    action: 'Busque cursos online (Coursera, Udemy, LinkedIn Learning) e adicione pelo menos 2 certificações relevantes'
                },
                'contact': {
                    title: 'Informações de Contato Incompletas',
                    impact: 'Recrutadores não conseguirão te contatar',
                    action: 'Inclua obrigatoriamente: email profissional, telefone com DDD, cidade/estado, LinkedIn (opcional)'
                }
            };
            
            weakAreas.forEach(([key], index) => {
                const info = detailedTips[key];
                if (info) {
                    html += `<div class="result-bold">${index + 1}. ${info.title.toUpperCase()}:</div>\n`;
                    html += `  • Por que é crítico: ${info.impact}\n`;
                    html += `  • O que fazer: ${info.action}\n\n`;
                }
            });
            
            html += '<div class="result-bold">Próximos Passos Imediatos:</div>\n';
            html += '  1. Revise cada área crítica listada acima\n';
            html += '  2. Foque primeiro nas deficiências mais graves\n';
            html += '  3. Busque exemplos de currículos bem avaliados na sua área\n';
            html += '  4. Implemente as mudanças sistematicamente\n';
            html += '  5. Teste novamente nesta ferramenta para validar melhorias\n\n';
        }
        
        html += '<div class="result-bold">Recursos de Apoio:</div>\n';
        html += '  • Templates: Canva, Google Docs, Microsoft Word (templates gratuitos)\n';
        html += '  • Exemplos: LinkedIn (busque currículos de profissionais da sua área)\n';
        html += '  • Cursos: Coursera, Udemy, LinkedIn Learning, Google Digital Garage\n';
        html += '  • Correção: LanguageTool, Grammarly (verificação gratuita)\n';
        html += '  • Orientação: Busque centros de carreira, professores ou mentores\n\n';
        
        html += '<span class="result-warning">⚠️ IMPORTANTE: Não envie este currículo para vagas antes das correções!</span>\n';
    }
    
    html += '\n<div class="result-separator"></div>\n';
    
    return html;
}
