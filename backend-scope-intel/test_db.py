# ==============================================================================
# ARQUIVO: test_db.py
#
# OBJETIVO:
#   Validar a conectividade com o Banco de Dados SQL.
#   Executa um "Ping" (SELECT 1) e uma contagem rápida na tabela alvo para garantir acesso.
#
# PARTE DO SISTEMA:
#   Scripts / Diagnóstico
#
# RESPONSABILIDADES:
#   - Testar conexão TCP/IP com o banco
#   - Testar credenciais e permissões na tabela do Fluig
#
# COMUNICAÇÃO:
#   Conecta ao MySQL definido no .env
# ==============================================================================

import sys
import os

# Adiciona o diretório atual ao path para conseguir importar a pasta 'app'
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.config import settings

def testar_conexao():
    print(f"🔌 Tentando conectar em: {settings.DATABASE_URL.split('@')[1]}") # Mostra só o IP para segurança
    
    db = SessionLocal()
    try:
        # 1. Teste básico de vida (Ping)
        db.execute(text("SELECT 1"))
        print("✅ Conexão com o banco estabelecida com sucesso!")
        
        # 2. Teste específico da tabela Fluig
        # Tenta buscar 1 linha da tabela alvo para garantir que o SCHEMA está certo
        tabela = settings.FLUIG_TABLE_NAME
        print(f"🔍 Verificando acesso à tabela '{tabela}'...")
        
        result = db.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
        count = result.scalar()
        
        print(f"✅ Tabela encontrada! Total de registros aproximado: {count}")
        
    except Exception as e:
        print("\n❌ FALHA NA CONEXÃO:")
        print("-" * 30)
        print(e)
        print("-" * 30)
        print("Dica: Verifique usuário, senha (caracteres especiais?), IP ou nome do banco no .env")
        
    finally:
        db.close()

if __name__ == "__main__":
    testar_conexao()