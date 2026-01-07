# =================================================================================================
# MÓDULO DE SEGURANÇA UNIFICADO (CONTEXTO + INTERCEPTOR)
# =================================================================================================

import logging
import re

logger = logging.getLogger(__name__)

# --- PARTE 1: GESTÃO DE CONTEXTO (QUEM É O USUÁRIO?) ---

class SecurityContext:
    """
    Armazena o estado de segurança da sessão atual.
    Guarda os dados do usuário/fornecedor para uso no Interceptor SQL.
    """
    def __init__(self, supplier_code: str = None, supplier_name: str = None):
        # Se supplier_code for None, é ADMIN (Vê tudo).
        # Se tiver valor (ex: '0077...'), o Interceptor SQL aplicará o filtro.
        self.supplier_code = supplier_code 
        self.supplier_name = supplier_name

# --- SIMULAÇÃO DE AMBIENTE (MOCK) ---
# Altere aqui para testar diferentes visões:

# Opção A: Modo ADMIN (Vê tudo - Supporte)
current_security_context = SecurityContext(None, "ADMIN")

# Opção B: Modo FORNECEDOR (Ex: HARMAN - Só vê seus dados)
# Para testar, descomente a linha abaixo e comente a de cima:
# current_security_context = SecurityContext("007703111000103", "HARMAN")


# --- PARTE 2: INTERCEPTOR SQL (HARD SECURITY) ---

def apply_security_filters(sql: str) -> str:
    """
    Interceptor de Segurança (Middleware de SQL).
    Recebe a query gerada pelo LLM e injeta OBRIGATORIAMENTE o filtro de fornecedor
    se houver um contexto de segurança ativo.
    """
    
    # 1. Se for ADMIN (supplier_code is None), libera total.
    if not current_security_context.supplier_code:
        return sql.strip()

    supplier_code = current_security_context.supplier_code
    
    # Remove ponto e vírgula e espaços extras para manipulação
    clean_sql = sql.strip().rstrip(';')
    
    # Regra de Segurança (Hard Filter)
    security_clause = f"\"COD_FORNECEDOR\" = '{supplier_code}'"

    # 2. Verifica se já existe WHERE na query (Case Insensitive)
    if re.search(r"\bWHERE\b", clean_sql, re.IGNORECASE):
        # ESTRATÉGIA: Substituir a primeira ocorrência de "WHERE" por "WHERE (filtro) AND"
        final_sql = re.sub(r"(\bWHERE\b)", f"WHERE {security_clause} AND", clean_sql, count=1, flags=re.IGNORECASE)
    else:
        # Se NÃO TEM Where, precisamos inserir antes de GROUP BY, ORDER BY ou LIMIT.
        keywords = r"(\bGROUP BY\b|\bORDER BY\b|\bLIMIT\b)"
        match = re.search(keywords, clean_sql, re.IGNORECASE)
        
        if match:
            start_idx = match.start()
            final_sql = f"{clean_sql[:start_idx]} WHERE {security_clause} {clean_sql[start_idx:]}"
        else:
            # Caso mais simples: SELECT * FROM tabela
            final_sql = f"{clean_sql} WHERE {security_clause}"

    logger.info(f"[SECURITY CHECK] Filtro aplicado para Fornecedor {supplier_code}")
    
    return f"{final_sql};"