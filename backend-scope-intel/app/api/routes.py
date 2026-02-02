import os
import json
from fastapi import APIRouter, HTTPException
from typing import List
from app.core.config import settings
from app.api.schemas import AnalysisResponse, AnalysisFileSummary

router = APIRouter()

@router.get("/analyses", response_model=List[AnalysisFileSummary])
def list_available_analyses():
    """
    Lista todos os arquivos JSON gerados na pasta de saída.
    O Frontend usa isso para mostrar um menu: "Selecione a análise..."
    """
    results = []
    
    # Garante que a pasta existe
    if not os.path.exists(settings.OUTPUT_DIR):
        return []

    # Varre a pasta
    for filename in os.listdir(settings.OUTPUT_DIR):
        if filename.endswith(".json") and filename.startswith("analise_"):
            filepath = os.path.join(settings.OUTPUT_DIR, filename)
            stats = os.stat(filepath)
            
            # Tenta extrair sistema do nome do arquivo (analise_PROTHEUS_2024...)
            parts = filename.split("_")
            sistema = parts[1] if len(parts) > 1 else "DESCONHECIDO"
            
            results.append({
                "filename": filename,
                "sistema": sistema,
                # Data de modificação do arquivo
                "data_criacao": str(stats.st_mtime), 
                "tamanho_bytes": stats.st_size
            })
    
    return results

@router.get("/analyses/{filename}", response_model=AnalysisResponse)
def get_analysis_detail(filename: str):
    """
    Lê o conteúdo de um arquivo JSON específico e retorna para o Dashboard.
    """
    # Segurança básica: impedir que o usuário navegue para outras pastas (../)
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")
    
    filepath = os.path.join(settings.OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler arquivo: {str(e)}")