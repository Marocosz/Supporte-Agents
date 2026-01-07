# =================================================================================================
# SCHEMAS DE SAÍDA (CONTRATO DE DADOS BACKEND -> FRONTEND)
# =================================================================================================
from typing import List, Literal, Union, Dict, Any, Optional
from pydantic import BaseModel, Field

# --- Modelo 1: Resposta de Texto (Cards, Listas, KPIs) ---


class TextResponse(BaseModel):
    type: Literal["text"] = Field(
        description="Sempre 'text' para respostas textuais")
    content: str = Field(
        description="O conteúdo da resposta, formatado e limpo (pode conter markdown simples ou quebras de linha).")

# --- Modelo 2: Resposta de Gráfico (Analytics) ---
# Unificamos pois a estrutura de dados vinda do SQL (Lista de Dicts) é universal.


class ChartResponse(BaseModel):
    type: Literal["chart"] = Field(description="Sempre 'chart' para gráficos")

    # O LLM é forçado a escolher um destes 3 tipos
    chart_type: Literal["bar", "line", "pie"] = Field(
        description="O tipo de visualização mais adequado para os dados."
    )

    title: str = Field(description="Título curto e descritivo do gráfico")

    # Dados brutos do SQL convertidos para lista de dicionários
    data: List[Dict[str, Any]] = Field(
        description="Lista de objetos contendo os dados. Ex: [{'filial': 'SP', 'valor': 100}, ...]"
    )

    # Configuração de mapeamento para o Frontend
    x_axis: str = Field(
        description="Nome exato da chave no dicionário que representa a Categoria ou Tempo (Eixo X / Fatias)"
    )
    y_axis: List[str] = Field(
        description="Lista com os nomes das chaves que representam os Valores Numéricos (Eixo Y / Tamanho)"
    )

    y_axis_label: Optional[str] = Field(
        default=None,
        description="Rótulo legível para a unidade de medida (ex: 'Valor (R$)', 'Qtd Volumes', 'Kg')"
    )


# --- Union Type para uso nos Parsers ---
# O parser tentará validar contra essas estruturas
AgentResponse = Union[ChartResponse, TextResponse]
