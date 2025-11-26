"""
MÓDULO: app/api/endpoints/download.py - ENDPOINT DE DOWNLOAD DE ARQUIVOS (HTTP GET)

FUNÇÃO:
Define o endpoint de API responsável por servir os arquivos `.docx` gerados
pelo serviço `DocxGenerator` (que estão salvos no diretório `OUTPUTS_PATH`).
Ele permite que o cliente solicite o download de um arquivo específico pelo nome
(e.g., PGP-ADM-0001.docx).

ARQUITETURA:
- **`FileResponse`:** Utiliza o objeto `FileResponse` da Starlette (que é
  a base do FastAPI) para otimizar o envio de grandes arquivos, definindo
  o cabeçalho `Content-Disposition` (via `filename`) e o `media_type`
  correto para documentos Word.
- **Segurança Crítica:** Contém verificações essenciais para garantir a segurança,
  principalmente contra ataques de "Path Traversal" (tentativa de acessar
  arquivos fora do diretório de outputs).

FLUXO DE SEGURANÇA:
1. **Verificação de Diretório:** Garante que o diretório `settings.OUTPUTS_PATH`
   exista.
2. **Path Traversal Check:** Compara o caminho absoluto e resolvido (`resolve()`)
   do arquivo solicitado com o caminho absoluto da pasta de outputs, garantindo
   que o arquivo esteja contido dentro do diretório permitido.
3. **Verificação de Existência:** Confirma se o arquivo de fato existe no disco
   antes de tentar servi-lo.
"""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from starlette.responses import FileResponse

# Importa as configurações globais (que contêm o OUTPUTS_PATH)
from app.core.config import settings

logger = logging.getLogger(__name__)
# Cria um roteador específico para as rotas de download
router = APIRouter()

@router.get("/download/{file_name}")
async def download_file(file_name: str):
    """
    Endpoint para servir um arquivo específico do diretório de outputs para download.

    Args:
        file_name (str): O nome do arquivo a ser baixado (ex: PGP-ADM-0001.docx).

    Returns:
        FileResponse: O arquivo para download.
    """
    try:
        # Busca o caminho absoluto do diretório de saídas a partir das configurações
        output_dir = settings.OUTPUTS_PATH
        
        # 1. Checa se o diretório de outputs está configurado corretamente
        if not output_dir.is_dir():
            logger.error(f"O diretório de outputs não existe: {output_dir}")
            raise HTTPException(status_code=500, detail="Erro interno: Diretório de saída não configurado.")

        # Constrói o caminho completo do arquivo
        file_path = output_dir / file_name

        # 2. Medida de segurança CRÍTICA: Prevenção de Path Traversal
        # Compara se o caminho resolvido do arquivo está DENTRO do caminho resolvido do diretório.
        if not str(file_path.resolve()).startswith(str(output_dir.resolve())):
            logger.warning(f"Tentativa de Path Traversal bloqueada: {file_name}")
            # Retorna 404 para não dar dica sobre a estrutura de arquivos interna
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

        # 3. Checa se o arquivo existe
        if not file_path.is_file():
            logger.error(f"Arquivo não encontrado em {file_path}")
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
        
        logger.info(f"Servindo arquivo para download: {file_path}")
        
        # Cria e retorna a resposta de arquivo
        return FileResponse(
            path=file_path,
            filename=file_name,
            # Tipo MIME padrão para arquivos .docx
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except HTTPException:
        # Relança exceções HTTPException (404, 500) já tratadas
        raise
        
    except Exception as e:
        # Captura e trata qualquer erro inesperado
        logger.error(f"Erro no download do arquivo '{file_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar o arquivo.")