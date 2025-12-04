#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Servidor Web para Interface ResumAI
Serve a interface HTML/CSS/JS e processa análises de currículos
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import sys

# Adicionar root ao path
sys.path.insert(0, str(Path(__file__).parent))

from app.scoring.hybrid_scorer import HybridScorer
from app.scoring.use_case import build_features_from_doc

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)  # Habilitar CORS
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Criar pasta de uploads
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Instância global do scorer
scorer = None

def get_scorer():
    """Retorna instância singleton do scorer"""
    global scorer
    if scorer is None:
        scorer = HybridScorer()
    return scorer


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


@app.route('/')
def index():
    """Serve a página principal"""
    return send_from_directory('static', 'index.html')


@app.route('/styles.css')
def styles():
    """Serve o CSS"""
    return send_from_directory('static', 'styles.css', mimetype='text/css')


@app.route('/script.js')
def script():
    """Serve o JavaScript"""
    return send_from_directory('static', 'script.js', mimetype='application/javascript')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve arquivos estáticos"""
    return send_from_directory('static', filename)


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Endpoint para análise de currículo"""
    try:
        print("\n" + "="*70)
        print("📥 Nova requisição de análise recebida")
        print("="*70)
        
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            print("❌ Erro: Nenhum arquivo na requisição")
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            print("❌ Erro: Nome do arquivo vazio")
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        print(f"📄 Arquivo recebido: {file.filename}")
        
        # Verificar extensão
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ['.pdf', '.txt']:
            print(f"❌ Erro: Extensão inválida: {file_extension}")
            return jsonify({'error': 'Formato não suportado. Use PDF ou TXT'}), 400
        
        # Salvar arquivo temporariamente
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(f"💾 Arquivo salvo em: {filepath}")
        
        try:
            # Extrair texto
            print(f"📖 Extraindo texto do {file_extension.upper()}...")
            if file_extension == '.pdf':
                resume_text = extract_text_from_pdf(filepath)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    resume_text = f.read()
            
            print(f"✅ Texto extraído: {len(resume_text)} caracteres")
            
            # Preparar documento
            doc = {
                "resume_text_clean": resume_text,
                "job_description": None
            }
            
            # Extrair features
            print("🔍 Extraindo features...")
            features = build_features_from_doc(doc)
            doc['has_experience'] = features.get('has_experience', False)
            print(f"✅ Features extraídas: {len(features.get('skills', []))} skills, {features.get('years_total', 0):.1f} anos")
            
            # Executar scoring
            print("⚙️ Executando scoring...")
            result = get_scorer().score(doc)
            print(f"✅ Score calculado: {result.get('score', 0):.1f}/100")
            
            # Preparar resposta
            response_data = {
                'success': True,
                'features': {
                    'has_experience': features.get('has_experience', False),
                    'skills': features.get('skills', []),
                    'years_total': float(features.get('years_total', 0)),
                    'project_hits': int(features.get('project_hits', 0)),
                    'cert_points': float(features.get('cert_points', 0)),
                    'metrics_hits': int(features.get('metrics_hits', 0)),
                    'classification': features.get('classification', {})
                },
                'result': {
                    'score': float(result.get('score', 0)),
                    'label': str(result.get('label', 'Desconhecido')),
                    'rb_subscores': result.get('rb_subscores', {})
                }
            }
            
            print("✅ Análise concluída com sucesso!")
            print("="*70 + "\n")
            
            return jsonify(response_data)
            
        except Exception as e:
            print(f"❌ Erro durante processamento: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            # Remover arquivo temporário
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"🗑️ Arquivo temporário removido")
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ ERRO FATAL: {error_msg}")
        import traceback
        traceback.print_exc()
        print("="*70 + "\n")
        
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500


@app.errorhandler(413)
def too_large(e):
    """Erro quando arquivo é muito grande"""
    return jsonify({'error': 'Arquivo muito grande. Máximo: 16MB'}), 413


if __name__ == '__main__':
    print("=" * 70)
    print("🎯 ResumAI - Servidor Web Iniciando...")
    print("=" * 70)
    print("\n📍 Acesse a interface em: http://localhost:5000")
    print("\n⚠️  Pressione CTRL+C para parar o servidor\n")
    print("=" * 70)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
