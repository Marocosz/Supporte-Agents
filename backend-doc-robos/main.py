import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Funções principais de negócio importadas do nosso módulo 'app'.
# Certifique-se que a pasta 'app' tem um __init__.py vazio para isso funcionar
from app.functions import (
    ler_conteudo_py,
    ler_conteudo_pas,
    gerar_resposta_ia_document,
    criar_docx_formatado
)

# Configuração de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# --- CONFIGURAÇÃO DO CORS ---
# Permite que o Frontend (React) acesse este Backend
CORS(app, resources={r"/*": {"origins": "*"}})

# Define constantes
UPLOAD_FOLDER = 'uploads'
DOCS_FOLDER = 'docs_gerados' # Ajustei para bater com o volume do Docker planejado
ALLOWED_EXTENSIONS = {'py', 'pas', 'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOCS_FOLDER'] = DOCS_FOLDER

# Garante que as pastas existam
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOCS_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Helper para validar a extensão dos arquivos enviados."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Health Check da API"""
    return jsonify({
        "status": "online",
        "service": "Doc Robos API",
        "version": "2.0.0"
    })

@app.route('/gerar', methods=['POST'])
def gerar_documentacao():
    """Recebe arquivos via API, processa e retorna JSON com resultados."""
    logger.info("Recebendo requisição de geração de documentos...")

    if 'arquivos' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    files = request.files.getlist('arquivos')
    contexto_adicional = request.form.get('contexto', 'Nenhum.')
    
    sucessos = []
    erros = []

    for file in files:
        if not file or not allowed_file(file.filename):
            continue

        filename_seguro = secure_filename(file.filename)
        caminho_salvo = os.path.join(app.config['UPLOAD_FOLDER'], filename_seguro)
        
        try:
            # 1. Salvar Arquivo Temporário
            file.save(caminho_salvo)
            logger.info(f"Processando arquivo: {filename_seguro}")

            # 2. Ler Conteúdo
            if filename_seguro.lower().endswith('.py'):
                resultado_leitura = ler_conteudo_py(caminho_salvo)
            else:
                # Assume .pas ou .txt
                resultado_leitura = ler_conteudo_pas(caminho_salvo)
            
            if isinstance(resultado_leitura, str):
                erros.append(f"Erro ao ler '{filename_seguro}': {resultado_leitura}")
                continue
            
            conteudo_codigo, nome_base = resultado_leitura
            
            # 3. Gerar com IA
            logger.info(f"Enviando '{nome_base}' para IA...")
            documentacao_ia = gerar_resposta_ia_document(conteudo_codigo, nome_base, contexto_adicional)
            
            if documentacao_ia.startswith("Erro"):
                erros.append(f"IA falhou em '{filename_seguro}': {documentacao_ia}")
                continue

            # 4. Criar DOCX
            nome_docx = f"DOC_{nome_base}.docx"
            logger.info(f"Gerando DOCX: {nome_docx}")
            
            if criar_docx_formatado(documentacao_ia, nome_docx, app.config['DOCS_FOLDER']):
                sucessos.append(nome_docx) # Retorna apenas o nome do arquivo para o front montar o link
            else:
                erros.append(f"Falha ao salvar DOCX para '{filename_seguro}'.")

        except Exception as e:
            logger.error(f"Erro fatal em {filename_seguro}: {str(e)}")
            erros.append(f"Erro interno processando '{filename_seguro}': {str(e)}")

        finally:
            # Limpeza
            if os.path.exists(caminho_salvo):
                os.remove(caminho_salvo)

    # Retorna JSON para o React
    return jsonify({
        "sucessos": sucessos,
        "erros": erros
    })

@app.route('/download/<path:filename>')
def download_file(filename):
    """Rota para download do arquivo gerado."""
    try:
        return send_from_directory(app.config['DOCS_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "Arquivo não encontrado"}), 404

if __name__ == '__main__':
    # Rodando na porta 5000 para bater com a config do React
    app.run(debug=True, use_reloader=False, port=5000)