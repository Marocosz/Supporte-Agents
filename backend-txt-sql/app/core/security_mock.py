# app/core/security_mock.py
from typing import Dict, Any

# Simulando um banco de usuários/tenants
MOCK_USERS = {
    "admin": {
        "role": "admin",
        "description": "Acesso total a todas as filiais e fornecedores.",
        "filters": {} # Sem filtros
    },
    "bic": {
        "role": "client",
        "description": "Cliente BIC AMAZONIA. Apenas visualiza seus dados.",
        "filters": {
            "COD_FORNECEDOR": "007703111000103",
            "FILIAL": "02" # Supor que BIC opera só na filial 02
        }
    },
    "harman": {
        "role": "client",
        "description": "Cliente HARMAN DO BRASIL.",
        "filters": {
            "COD_FORNECEDOR": "00223344000199"
        }
    }
}

def get_user_context(user_key: str) -> Dict[str, Any]:
    """
    Retorna o contexto de segurança para o Prompt.
    Se user_key não existir, retorna convidado (sem acesso).
    """
    user = MOCK_USERS.get(user_key, MOCK_USERS["admin"]) # Default admin para dev facilitar
    
    if not user["filters"]:
        return {
            "role_desc": user["description"],
            "sql_constraints": "NENHUMA restrição de acesso. Você pode consultar toda a base."
        }
    
    # Monta a string de restrição SQL
    constraints = []
    for col, val in user["filters"].items():
        constraints.append(f"AND {col} = '{val}'")
    
    constraint_str = "\n".join(constraints)
    
    return {
        "role_desc": user["description"],
        "sql_constraints": f"""
        --- 🚨 RESTRIÇÃO DE SEGURANÇA (CRÍTICO) ---
        Você está agindo em nome de um cliente específico.
        Toda query gerada DEVE conter obrigatoriamente no WHERE:
        {constraint_str}
        
        NUNCA mostre dados que não atendam a esses filtros.
        """
    }