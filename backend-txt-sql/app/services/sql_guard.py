# app/services/sql_guard.py
import logging
import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Exceção levantada quando uma violação de segurança SQL é detectada."""
    pass

class SQLGuard:
    """
    Camada de Segurança Hard-Code.
    Valida e sanitiza queries SQL via análise sintática (AST) antes do banco.
    """

    # Lista de comandos proibidos (Blacklist)
    FORBIDDEN_COMMANDS = (
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Update,
        exp.Insert,
        exp.Alter,
        exp.TruncateTable,
        exp.Grant,
        exp.Revoke
    )

    @staticmethod
    def validate_query(sql: str) -> str:
        """
        Analisa a query. Se contiver comandos proibidos (DML/DDL), levanta erro.
        Retorna o SQL limpo e formatado se estiver seguro.
        """
        if not sql or not sql.strip():
            raise SecurityError("Query SQL vazia.")

        try:
            # 1. Parse: Transforma texto em Árvore Sintática Abstrata (AST)
            # read="postgres" garante que entendemos o dialeto correto
            parsed = sqlglot.parse_one(sql, read="postgres")
        except Exception as e:
            logger.error(f"SQL Guard falhou ao parsear query: {sql[:50]}... Erro: {e}")
            raise ValueError("Erro de sintaxe SQL detectado pelo Guardião.")

        # 2. Inspeção: Caminha pela árvore procurando nós proibidos
        for node in parsed.walk():
            if isinstance(node, SQLGuard.FORBIDDEN_COMMANDS):
                logger.critical(f"🚨 [SECURITY BLOCK] Tentativa de comando proibido: {node.sql()}")
                raise SecurityError(f"Comando SQL não autorizado: {node.key.upper()}. Apenas consultas (SELECT) são permitidas.")

        # 3. Normalização: Reconstrói o SQL garantindo formatação segura
        clean_sql = parsed.sql(dialect="postgres")
        return clean_sql

    # Futuro: Método inject_tenant_filter(sql, tenant_id) será implementado aqui