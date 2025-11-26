import sys
import os
from app.functions import *


for arq in os.listdir("scripts_a_ler"):
    caminho_completo = os.path.join("scripts_a_ler", arq)
    print(f"Lendo o arquivo: {caminho_completo}")
    str_codigo_fonte, nome_arquivo = ler_conteudo_py(caminho_completo)
    
    if not str_codigo_fonte or not nome_arquivo:
        print(f"Erro ao ler o arquivo: {caminho_completo}")
        sys.exit(1)
        
    str_codigo_safe = str_codigo_fonte.replace("```", "'''").replace('"""', "'''")
    
    resp = gerar_resposta_ia_document(str_codigo_safe, nome_arquivo, contexto_adicional="Nenhum.")

    criar_docx_formatado(resp, nome_arquivo.split(".")[0])