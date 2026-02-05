# ==============================================================================
# ARQUIVO: app/services/data_fetcher.py
#
# OBJETIVO:
#   Consultar dados brutos do Fluig (MySQL) para alimentar o pipeline de IA.
#   Esta é a "boca de entrada" do sistema que extrai informações de negócio.
#
# PARTE DO SISTEMA:
#   Backend / Integração de Dados (ETL)
#
# RESPONSABILIDADES:
#   - Conectar no banco SQL via SQLAlchemy
#   - Executar query otimizada para buscar chamados de um sistema específico
#   - Limpar HTML sujo (tags, &nbsp;) dos campos de texto rico do Fluig
#   - Preparar o texto concatenado ("Documento Virtual") que será vetorizado
#
# COMUNICAÇÃO:
#   Entrada: Conecta ao Banco MySQL (Tabela Fluig)
#   Saída: Retorna lista de dicionários para run_pipeline.py e API (Lazy Loading)
# ==============================================================================

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from bs4 import BeautifulSoup
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def clean_html(raw_html: str) -> str:
    """
    Limpa strings que contém HTML (comum em campos Memo/Richtext do Fluig).
    
    ENTRADA: '<p>Erro no sistema &nbsp;<strong>Crítico</strong></p>'
    SAÍDA:   'Erro no sistema Crítico'
    
    Por que isso é necessário?
    Tags HTML sujam o vetor semântico. A IA precisa focar no CONTEÚDO, não na formatação.
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
    Essa é a string COMPLETA que será enviada para a OpenAI para virar vetor.
    
    ESTRATÉGIA:
    Concatenamos campos estruturados (Sistema, Serviço) com campos livres (Título, Descrição)
    usando rótulos explícitos (ex: 'SISTEMA:', 'ERRO:'). Isso ajuda o modelo de Embedding
    a entender a topologia da informação.
    """
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
    Executa a query principal de extração de dados.
    
    PARÂMETROS:
        - sistema: Nome exato do sistema no campo 'cat_sistema' (ex: 'Logix').
        - dias_atras: Janela de tempo de análise (Data de Abertura).
        
    RETORNO:
        - Lista de dicionários prontos para serem vetorizados.
    """
    logger.info(f"Iniciando busca de chamados para o sistema: {sistema} (últimos {dias_atras} dias)")
    
    # QUERY EXPLICADA:
    # 1. Selecionamos campos de Identificação (ID, Solicitante) e Contexto (Sistema, Erro).
    # 2. Convertemos a data de string ('dd/mm/yyyy') para DATE real para filtro.
    # 3. FILTRO DE VERSÃO (CRÍTICO): O Fluig cria uma nova linha na tabela para cada 'save' do formulário.
    #    A subquery ``WHERE t1.version = (SELECT MAX(version)...)`` garante que pegamos apenas
    #    o estado FINAL do chamado, evitando duplicatas e dados desatualizados.
    query = text(f"""
        SELECT 
            processInstanceId as id_chamado,
            txt_solicitante as solicitante,
            txt_email_solicitante as email,
            STR_TO_DATE(txt_dt_solicitacao, '%d/%m/%Y') as data_abertura,
            text_status_chamado as status,
            
            -- Colunas de Contexto (Usadas no Embedding)
            cat_sistema as sistema,
            cat_servico as servico,
            cat_subarea as subarea,
            txt_num_titulo as titulo,
            txt_detalhe_sol as descricao_raw
            
        FROM {settings.FLUIG_TABLE_NAME} t1
        WHERE 
            -- Filtro de Versão (Garante registro único e atualizado por chamado)
            t1.version = (
                SELECT MAX(version) FROM {settings.FLUIG_TABLE_NAME} t2 
                WHERE t2.documentid = t1.documentid
            )
            AND t1.cat_sistema = :sistema
            -- Filtro de Janela de Tempo (Otimização de performance)
            AND STR_TO_DATE(t1.txt_dt_solicitacao, '%d/%m/%Y') >= DATE_SUB(NOW(), INTERVAL :dias DAY)
    """)
    
    try:
        # Pandas facilita o manuseio dos dados SQL -> Memória
        df = pd.read_sql(query, db.bind, params={"sistema": sistema, "dias": dias_atras})
        
        if df.empty:
            logger.warning("Nenhum chamado encontrado com os filtros atuais.")
            return []

        # 0. Proteção Extra contra Duplicidade (Blindagem)
        # Se por algum motivo o banco trouxer IDs repetidos, garantimos unicidade aqui.
        qtd_antes = len(df)
        df.drop_duplicates(subset=['id_chamado'], keep='last', inplace=True)
        if len(df) < qtd_antes:
            logger.warning(f"🛡️ Desduplicação: {qtd_antes - len(df)} registros repetidos foram removidos.")
        df['descricao_limpa'] = df['descricao_raw'].apply(clean_html)
        
        # 2. Conversão para Dicionários Python
        records = df.to_dict(orient='records')
        
        # 3. Enriquecimento
        for record in records:
            # Gera o texto final para a IA
            record['texto_vetor'] = build_embedding_text(record)
            
            # Formatação de data para JSON/ISO 8601 (Compatibilidade com Qdrant/Frontend)
            if record['data_abertura']:
                record['data_abertura'] = record['data_abertura'].strftime('%Y-%m-%d')

        logger.info(f"Processamento concluído. {len(records)} chamados preparados.")
        return records

    except Exception as e:
        logger.error(f"Erro crítico ao buscar dados: {e}")
        # Relançamos o erro para parar o pipeline, pois sem dados não faz sentido continuar.
        raise e

def fetch_batch_by_ids(db: Session, ids: list[str]):
    """
    Busca detalhes completos de uma lista específica de IDs de chamados.
    Usado pelo Frontend para "hidratar" os exemplos sob demanda (Lazy Loading).
    
    PARÂMETROS:
        - ids: Lista de strings com os IDs dos chamados (ex: ['12345', '12346'])
        
    RETORNO:
        - Lista de dicionários com os detalhes limpos.
    """
    if not ids:
        return []

    # Solução Robusta para 'IN clause': Expandir manualmente os parâmetros
    # Isso evita incompatibilidades de drivers (mysql-connector vs pyodbc vs sqlite) ao passar tuplas/listas
    bind_keys = [f"id_{i}" for i in range(len(ids))]
    params = {f"id_{i}": val for i, val in enumerate(ids)}
    
    # Cria string ":id_0, :id_1, :id_2"
    bind_placeholders = ", ".join([f":{k}" for k in bind_keys])
    
    query = text(f"""
        SELECT 
            processInstanceId as id_chamado,
            txt_solicitante as solicitante,
            STR_TO_DATE(txt_dt_solicitacao, '%d/%m/%Y') as data_abertura,
            text_status_chamado as status,
            cat_sistema as sistema,
            txt_num_titulo as titulo,
            txt_detalhe_sol as descricao_raw
        FROM {settings.FLUIG_TABLE_NAME} t1
        WHERE 
            processInstanceId IN ({bind_placeholders})
            AND t1.version = (
                SELECT MAX(version) FROM {settings.FLUIG_TABLE_NAME} t2 
                WHERE t2.documentid = t1.documentid
            )
    """)

    try:
        # Executa query passando o dicionário explícito de parâmetros
        result = db.execute(query, params)
        rows = result.fetchall()
        
        output = []
        for row in rows:
            # Row mapping (acesso por nome da coluna)
            # SQLAlchemy moderno retorna Row que age como dict ou tupla nomeada
            
            # Limpeza HTML
            desc_limpa = clean_html(row.descricao_raw if hasattr(row, 'descricao_raw') else row[6])
            
            # Formata data se necessário (se o driver retornar date object)
            dt_abertura = row.data_abertura if hasattr(row, 'data_abertura') else row[2]
            if not isinstance(dt_abertura, str) and dt_abertura is not None:
                dt_abertura = dt_abertura.strftime('%Y-%m-%d')
            elif dt_abertura is None:
                dt_abertura = ""

            item = {
                "id_chamado": row.id_chamado if hasattr(row, 'id_chamado') else row[0],
                "solicitante": row.solicitante if hasattr(row, 'solicitante') else row[1],
                "data_abertura": dt_abertura,
                "status": row.status if hasattr(row, 'status') else row[3],
                "titulo": row.titulo if hasattr(row, 'titulo') else row[5],
                "descricao_limpa": desc_limpa
            }
            output.append(item)
            
        return output

    except Exception as e:
        logger.error(f"Erro ao buscar batch de IDs: {e}")
        return []