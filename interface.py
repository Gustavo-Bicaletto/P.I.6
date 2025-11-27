#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interface Gráfica para Avaliação de Currículos - ResumAI
Interface simples que mostra apenas o resumo final da avaliação
"""
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
from threading import Thread

# Adicionar root ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.scoring.hybrid_scorer import HybridScorer
from app.scoring.use_case import build_features_from_doc

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrai texto de um arquivo PDF"""
    if not PDF_SUPPORT:
        raise ImportError("PyPDF2 não está instalado. Execute: pip install PyPDF2")
    
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Erro ao extrair texto do PDF: {e}")


class ResumAIApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ResumAI - Avaliação de Currículos")
        self.root.geometry("900x750")
        self.root.resizable(True, True)
        
        # Definir tema de cores moderno
        self.colors = {
            'bg': '#f5f7fa',
            'primary': '#4a90e2',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'text': '#2c3e50',
            'card': '#ffffff'
        }
        
        # Configurar estilo
        self.root.configure(bg=self.colors['bg'])
        
        # Variáveis
        self.file_path = None
        self.scorer = None
        
        # Configurar interface
        self.setup_ui()
        
    def setup_ui(self):
        """Configura a interface do usuário"""
        
        # Frame principal com padding
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Header com gradiente visual
        header_frame = tk.Frame(main_frame, bg=self.colors['primary'], height=100)
        header_frame.pack(fill=tk.X, pady=(0, 25))
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(
            header_frame,
            text="🎯 ResumAI",
            font=("Segoe UI", 28, "bold"),
            bg=self.colors['primary'],
            fg="white"
        )
        title_label.pack(pady=(20, 5))
        
        subtitle_label = tk.Label(
            header_frame,
            text="Análise Inteligente de Currículos",
            font=("Segoe UI", 12),
            bg=self.colors['primary'],
            fg="white"
        )
        subtitle_label.pack()
        
        # Card de seleção de arquivo
        file_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.FLAT, bd=0)
        file_card.pack(fill=tk.X, pady=(0, 20))
        
        file_inner = tk.Frame(file_card, bg=self.colors['card'])
        file_inner.pack(fill=tk.X, padx=20, pady=20)
        
        file_title = tk.Label(
            file_inner,
            text="📄 Selecionar Currículo",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors['card'],
            fg=self.colors['text']
        )
        file_title.pack(anchor=tk.W, pady=(0, 10))
        
        file_select_frame = tk.Frame(file_inner, bg=self.colors['card'])
        file_select_frame.pack(fill=tk.X)
        
        self.file_label = tk.Label(
            file_select_frame,
            text="Nenhum arquivo selecionado",
            font=("Segoe UI", 10),
            bg=self.colors['card'],
            fg="#95a5a6",
            anchor=tk.W
        )
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        select_btn = tk.Button(
            file_select_frame,
            text="📁 Escolher Arquivo",
            command=self.select_file,
            bg=self.colors['primary'],
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=10
        )
        select_btn.pack(side=tk.RIGHT)
        
        # Botão de análise grande e destacado
        self.analyze_btn = tk.Button(
            main_frame,
            text="🚀 Analisar Currículo",
            command=self.analyze_resume,
            state=tk.DISABLED,
            bg=self.colors['success'],
            fg="white",
            font=("Segoe UI", 14, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=40,
            pady=15
        )
        self.analyze_btn.pack(pady=(0, 20))
        
        # Barra de progresso com estilo
        progress_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        progress_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate', length=400)
        self.progress.pack()
        
        # Card de resultados
        results_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.FLAT, bd=0)
        results_card.pack(fill=tk.BOTH, expand=True)
        
        results_inner = tk.Frame(results_card, bg=self.colors['card'])
        results_inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        results_title = tk.Label(
            results_inner,
            text="📊 Resultado da Avaliação",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors['card'],
            fg=self.colors['text']
        )
        results_title.pack(anchor=tk.W, pady=(0, 10))
        
        # Frame para text widget com scrollbar
        text_frame = tk.Frame(results_inner, bg=self.colors['card'])
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Text widget para mostrar resultados
        self.results_text = tk.Text(
            text_frame,
            font=("Consolas", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#fafbfc",
            fg=self.colors['text'],
            relief=tk.FLAT,
            padx=15,
            pady=15
        )
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_text.config(yscrollcommand=scrollbar.set)
        
        # Configurar tags de cor (cores mais modernas)
        self.results_text.tag_config("title", font=("Segoe UI", 13, "bold"), foreground=self.colors['primary'])
        self.results_text.tag_config("success", foreground=self.colors['success'], font=("Consolas", 10, "bold"))
        self.results_text.tag_config("warning", foreground=self.colors['warning'], font=("Consolas", 10, "bold"))
        self.results_text.tag_config("error", foreground=self.colors['danger'], font=("Consolas", 10, "bold"))
        self.results_text.tag_config("info", foreground=self.colors['primary'])
        self.results_text.tag_config("bold", font=("Consolas", 10, "bold"))
        
    def select_file(self):
        """Abre diálogo para selecionar arquivo"""
        filetypes = [
            ("Arquivos de Currículo", "*.pdf *.txt"),
            ("PDF files", "*.pdf"),
            ("Text files", "*.txt"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Selecione o currículo",
            filetypes=filetypes
        )
        
        if filename:
            self.file_path = filename
            display_name = Path(filename).name
            if len(display_name) > 50:
                display_name = display_name[:47] + "..."
            self.file_label.config(text=display_name, fg=self.colors['text'])
            self.analyze_btn.config(state=tk.NORMAL, bg=self.colors['success'])
            self.clear_results()
    
    def clear_results(self):
        """Limpa os resultados anteriores"""
        self.results_text.config(state=tk.NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state=tk.DISABLED)
    
    def append_result(self, text, tag=None):
        """Adiciona texto aos resultados"""
        self.results_text.config(state=tk.NORMAL)
        if tag:
            self.results_text.insert(tk.END, text, tag)
        else:
            self.results_text.insert(tk.END, text)
        self.results_text.config(state=tk.DISABLED)
        self.results_text.see(tk.END)
    
    def analyze_resume(self):
        """Analisa o currículo em thread separada"""
        if not self.file_path:
            messagebox.showerror("Erro", "Selecione um arquivo primeiro!")
            return
        
        # Desabilitar botão e iniciar progresso
        self.analyze_btn.config(state=tk.DISABLED)
        self.progress.start(10)
        self.clear_results()
        
        # Executar análise em thread separada
        thread = Thread(target=self.run_analysis, daemon=True)
        thread.start()
    
    def run_analysis(self):
        """Executa a análise do currículo"""
        try:
            # 1. Carregar arquivo
            self.append_result("📄 Carregando currículo...\n\n")
            
            file_extension = Path(self.file_path).suffix.lower()
            
            if file_extension == '.pdf':
                resume_text = extract_text_from_pdf(self.file_path)
            elif file_extension == '.txt':
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    resume_text = f.read()
            else:
                raise ValueError(f"Formato não suportado: {file_extension}")
            
            # 2. Preparar documento
            doc = {
                "resume_text_clean": resume_text,
                "job_description": None
            }
            
            # 3. Extrair features
            self.append_result("🔍 Analisando conteúdo...\n\n")
            features = build_features_from_doc(doc)
            doc['has_experience'] = features.get('has_experience', False)
            
            # 4. Executar scoring
            self.append_result("⚙️ Calculando scores...\n\n")
            if not self.scorer:
                self.scorer = HybridScorer()
            
            result = self.scorer.score(doc)
            
            # 5. Mostrar apenas resumo final
            self.show_final_summary(features, result)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Erro na Análise", str(e)))
            self.append_result(f"\n❌ Erro: {str(e)}\n", "error")
        finally:
            # Parar progresso e reabilitar botão
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.analyze_btn.config(state=tk.NORMAL))
    
    def show_final_summary(self, features, result):
        """Mostra apenas o resumo final da avaliação"""
        self.clear_results()
        
        # Extrair dados
        is_experienced = features.get('has_experience', False)
        final_score = result.get('score', 0)
        label = result.get('label', 'Desconhecido')
        subscores = result.get('rb_subscores', {})
        
        # Usar confiança do classificador híbrido (mais precisa)
        classification_info = features.get('classification', {})
        confidence = classification_info.get('confidence', 0.5)
        
        # Se não houver confiança do classificador, usar fallback do ML metadata
        if confidence == 0.5 and 'ml_metadata' in result:
            ml_metadata = result.get('ml_metadata', {})
            proximity = ml_metadata.get('proximity_score', 0.5)
            cluster_quality = ml_metadata.get('cluster_quality', 0.5)
            confidence = (proximity * 0.6 + cluster_quality * 0.4)
        
        # Cabeçalho
        self.append_result("═" * 70 + "\n", "bold")
        self.append_result("  RESULTADO DA AVALIAÇÃO\n", "title")
        self.append_result("═" * 70 + "\n\n", "bold")
        
        # Score principal
        self.append_result(f"📊 Score Final: ", "bold")
        self.append_result(f"{final_score:.1f}/100\n\n")
        
        # Classificação
        perfil = "👔 EXPERIENTE" if is_experienced else "🎓 ESTAGIÁRIO/JÚNIOR"
        self.append_result(f"📌 Perfil: ", "bold")
        self.append_result(f"{perfil}\n\n")
        
        # Resultado
        self.append_result("🎯 Avaliação: ", "bold")
        if label == "Bom":
            if final_score >= 80:
                self.append_result("✅ EXCELENTE\n", "success")
                self.append_result("    Currículo de alta qualidade!\n\n", "success")
            elif final_score >= 65:
                self.append_result("✅ BOM\n", "success")
                self.append_result("    Currículo sólido, com espaço para otimizações.\n\n", "info")
            else:
                self.append_result("✅ BOM\n", "success")
                self.append_result("    Aprovado, mas pode ser melhorado.\n\n", "info")
        else:
            self.append_result("❌ RUIM\n", "error")
            self.append_result("    Currículo precisa de melhorias significativas.\n\n", "error")
        
        # Separador
        self.append_result("─" * 70 + "\n\n")
        
        # Estatísticas
        self.append_result("📈 Detalhes:\n\n", "bold")
        self.append_result(f"   • Skills identificadas: {len(features.get('skills', []))}\n")
        self.append_result(f"   • Anos de experiência: {features.get('years_total', 0):.1f}\n")
        self.append_result(f"   • Projetos mencionados: {features.get('project_hits', 0)}\n")
        
        # Calcular número real de certificações (cert_points pode ser decimal)
        cert_points = features.get('cert_points', 0)
        # Estimar número: cada certificação vale ~0.15-0.5 pontos
        num_certs = int(cert_points / 0.2) if cert_points > 0 else 0
        self.append_result(f"   • Certificações: {num_certs}\n")
        
        self.append_result(f"   • Métricas quantificáveis: {features.get('metrics_hits', 0)}\n\n")
        
        # Pontos fortes e fracos
        self.show_strengths_weaknesses(subscores)
        
        # Recomendação final detalhada
        self.append_result("─" * 70 + "\n\n")
        self.append_result("💡 Recomendação Final:\n\n", "bold")
        
        cutoff = 50.0 if is_experienced else 40.0
        
        if final_score >= cutoff:
            self.append_result("   ✅ CURRÍCULO APROVADO\n\n", "success")
            
            if final_score >= 80:
                self.append_result("   Parabéns! Seu currículo demonstra excelência e está muito\n")
                self.append_result("   bem estruturado. Você se destaca da competição.\n\n")
                self.append_result("   🎯 Próximos passos:\n", "bold")
                self.append_result("      • Mantenha seu currículo atualizado com novas conquistas\n")
                self.append_result("      • Continue desenvolvendo suas habilidades principais\n")
                self.append_result("      • Considere adicionar links para portfólio/GitHub/LinkedIn\n")
            elif final_score >= 65:
                self.append_result("   Seu currículo está bem estruturado e atende aos critérios\n")
                self.append_result("   principais. Pequenas melhorias podem destacá-lo ainda mais.\n\n")
                self.append_result("   🎯 Sugestões de melhoria:\n", "bold")
                
                # Sugestões específicas baseadas nos subscores
                if subscores.get('impact', 1.0) < 0.7:
                    self.append_result("      • Adicione mais resultados quantificáveis (%, números, métricas)\n")
                if subscores.get('projects', 1.0) < 0.7:
                    self.append_result("      • Destaque projetos relevantes que você desenvolveu\n")
                if subscores.get('certs', 1.0) < 0.7:
                    self.append_result("      • Inclua certificações e cursos complementares\n")
            else:
                self.append_result("   Seu currículo atende aos requisitos mínimos, mas há\n")
                self.append_result("   oportunidades significativas de melhoria.\n\n")
                self.append_result("   🎯 Ações recomendadas (prioridade alta):\n", "bold")
                
                # Identificar as 3 maiores fraquezas
                weak_areas = sorted([(k, v) for k, v in subscores.items() if v < 0.8], 
                                   key=lambda x: x[1])[:3]
                
                for key, score in weak_areas:
                    if key == 'skills':
                        self.append_result("      • URGENTE: Adicione mais habilidades técnicas relevantes\n")
                    elif key == 'experience':
                        self.append_result("      • URGENTE: Detalhe melhor suas experiências anteriores\n")
                    elif key == 'projects':
                        self.append_result("      • URGENTE: Mencione projetos desenvolvidos\n")
                    elif key == 'impact':
                        self.append_result("      • IMPORTANTE: Quantifique seus resultados com métricas\n")
                    elif key == 'doc_quality':
                        self.append_result("      • IMPORTANTE: Melhore a estrutura do documento\n")
        else:
            self.append_result("   ⚠️  CURRÍCULO PRECISA DE REVISÃO\n\n", "warning")
            self.append_result("   Seu currículo não atende aos critérios mínimos estabelecidos.\n")
            self.append_result("   Recomendamos fortemente uma revisão completa antes de submeter\n")
            self.append_result("   para processos seletivos.\n\n")
            self.append_result("   🛑 Ações obrigatórias:\n", "error")
            
            # Listar TODAS as fraquezas para currículos ruins
            weak_areas = [(k, v) for k, v in subscores.items() if v < 0.6]
            
            if len(weak_areas) >= 3:
                self.append_result("      • Refazer estrutura completa do currículo\n", "error")
                self.append_result("      • Adicionar seções faltantes (Formação, Experiência, Skills)\n", "error")
                self.append_result("      • Incluir informações de contato completas\n", "error")
                self.append_result("      • Detalhar experiências com responsabilidades e resultados\n", "error")
            else:
                for key, score in weak_areas:
                    tips = {
                        'skills': "Adicionar habilidades técnicas relevantes para a área",
                        'experience': "Detalhar experiências profissionais com mais profundidade",
                        'projects': "Incluir projetos desenvolvidos (acadêmicos ou profissionais)",
                        'impact': "Quantificar resultados e conquistas com números/métricas",
                        'doc_quality': "Melhorar estrutura e organização do documento",
                        'certs': "Adicionar certificações e cursos relevantes",
                        'contact': "Incluir informações completas de contato"
                    }
                    tip = tips.get(key, "Revisar este item")
                    self.append_result(f"      • {tip}\n", "error")
        
        self.append_result("\n" + "═" * 70 + "\n")
    
    def show_strengths_weaknesses(self, subscores):
        """Mostra pontos fortes e fracos - igual ao test_complete.py"""
        
        # Pontos fortes (>= 90%)
        strong_points = [(k, int(v*100)) for k, v in subscores.items() if v >= 0.9]
        if strong_points:
            self.append_result("⭐ Pontos Fortes:\n", "success")
            names = {
                'skills': 'Habilidades',
                'experience': 'Experiência',
                'doc_quality': 'Qualidade do Documento',
                'contact': 'Informações de Contato',
                'certs': 'Certificações',
                'projects': 'Projetos',
                'impact': 'Impacto/Métricas'
            }
            for key, percentage in strong_points[:3]:
                name = names.get(key, key)
                self.append_result(f"   • {name}\n", "success")
            self.append_result("\n")
        
        # Oportunidades de melhoria (< 80%)
        weak_points = []
        improvement_tips = {
            'skills': "Adicione mais habilidades técnicas relevantes para sua área",
            'experience': "Detalhe melhor sua experiência: responsabilidades, conquistas, período exato",
            'projects': "Mencione projetos desenvolvidos (acadêmicos, pessoais ou profissionais)",
            'impact': "Quantifique seus resultados: números, percentuais, métricas de impacto",
            'doc_quality': "Melhore a estrutura: adicione mais seções (Formação, Projetos, Idiomas, etc.)",
            'certs': "Adicione certificações, cursos ou qualificações relevantes",
        }
        
        for key, tip in improvement_tips.items():
            score = subscores.get(key, 0)
            if score < 0.8:  # Abaixo de 80% = oportunidade de melhoria
                weak_points.append((key, percentage, tip))
        
        # Ordenar por menor score (maior oportunidade de melhoria)
        weak_points.sort(key=lambda x: x[1])
        
        if weak_points:
            self.append_result("📊 Oportunidades de Melhoria:\n", "warning")
            for i, (key, percentage, tip) in enumerate(weak_points[:5], 1):
                self.append_result(f"   • {tip}\n", "warning")
            self.append_result("\n")
        else:
            self.append_result("✅ Todos os critérios estão em níveis excelentes (>80%)!\n\n", "success")
    
def main():
    """Função principal"""
    root = tk.Tk()
    app = ResumAIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
