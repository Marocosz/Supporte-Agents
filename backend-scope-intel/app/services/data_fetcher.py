import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from bs4 import BeautifulSoup
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def clean_html(raw_html: str) -> str:
    """
    Remove tags HTML e caracteres invisíveis do texto rico do Fluig.
    Ex: '<div><p>Erro &nbsp;</p></div>' vira 'Erro'
    """
    if not isinstance(raw_html, str):
        return ""
    
    # BeautifulSoup extrai apenas o texto visível
    soup = BeautifulSoup(raw_html, "html.parser")
    text_content = soup.get_text(separator=" ")
    
    # Remove espaços extras e quebras de linha excessivas
    return " ".join(text_content.split())

def build_embedding_text(row: dict) -> str:
    """
    Cria o 'Documento Virtual' unificando as colunas.
    Essa é a string que será transformada em vetor pela OpenAI.
    """
    # Montamos um bloco de texto estruturado
    # O uso de prefixos (TITULO:, DESCRIÇÃO:) ajuda a IA a focar
    documento = (
        f"SISTEMA: {row.get('sistema', 'N/A')} | "
        f"SERVIÇO: {row.get('servico', 'N/A')} | "
        f"SUB-ÁREA: {row.get('subarea', 'N/A')} | "
        f"TÍTULO: {row.get('titulo', 'N/A')}. " 
        f"DESCRIÇÃO DETALHADA: {row.get('descricao_limpa', '')}"
    )
    return documento

def fetch_chamados(db: Session, sistema: str, dias_atras: int = 180):
    """
    Busca chamados no MySQL e prepara para vetorização.
    """
    logger.info(f"Iniciando busca de chamados para o sistema: {sistema} (últimos {dias_atras} dias)")
    
    # Query otimizada para pegar a última versão do formulário e converter data
    # Ajuste o formato STR_TO_DATE conforme o seu banco (aqui assumi DD/MM/YYYY)
    query = text(f"""
        SELECT 
            processInstanceId as id_chamado,
            txt_solicitante as solicitante,
            txt_email_solicitante as email,
            STR_TO_DATE(txt_dt_solicitacao, '%d/%m/%Y') as data_abertura,
            text_status_chamado as status,
            
            -- Colunas de Contexto
            cat_sistema as sistema,
            cat_servico as servico,
            cat_subarea as subarea,
            txt_num_titulo as titulo,
            txt_detalhe_sol as descricao_raw
            
        FROM {settings.FLUIG_TABLE_NAME} t1
        WHERE 
            -- Filtro de Versão (Crucial para Fluig)
            t1.version = (
                SELECT MAX(version) FROM {settings.FLUIG_TABLE_NAME} t2 
                WHERE t2.documentid = t1.documentid
            )
            AND t1.cat_sistema = :sistema
            -- Filtro de Data (MySQL)
            AND STR_TO_DATE(t1.txt_dt_solicitacao, '%d/%m/%Y') >= DATE_SUB(NOW(), INTERVAL :dias DAY)
    """)
    
    try:
        # Executa a query e joga num DataFrame do Pandas
        df = pd.read_sql(query, db.bind, params={"sistema": sistema, "dias": dias_atras})
        
        if df.empty:
            logger.warning("Nenhum chamado encontrado com os filtros atuais.")
            return []

        # 1. Limpeza do HTML
        df['descricao_limpa'] = df['descricao_raw'].apply(clean_html)
        
        # 2. Criação do Texto para IA
        # Convertemos para dict antes de aplicar para facilitar
        records = df.to_dict(orient='records')
        
        for record in records:
            # Adiciona o campo 'texto_vetor' no dicionário
            record['texto_vetor'] = build_embedding_text(record)
            
            # Converte data para string ISO para salvar no JSON/Qdrant sem erro
            if record['data_abertura']:
                record['data_abertura'] = record['data_abertura'].strftime('%Y-%m-%d')

        logger.info(f"Processamento concluído. {len(records)} chamados preparados.")
        return records

    except Exception as e:
        logger.error(f"Erro crítico ao buscar dados: {e}")
        raise e