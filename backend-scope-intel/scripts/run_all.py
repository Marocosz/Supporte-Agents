# ==============================================================================
# ARQUIVO: scripts/run_all.py
#
# OBJETIVO:
#   Orquestrador mestre que executa o pipeline de análise para múltiplos sistemas
#   de forma sequencial e automática.
#
# COMO USAR:
#   No terminal: python scripts/run_all.py
# ==============================================================================

import subprocess
import time
import logging
import sys

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO ---
# Lista exata dos sistemas que você quer processar
SISTEMAS_PARA_PROCESSAR = [
    "PROTHEUS",
    "LOGIX",
    "NEW TRACKING",
    "SARA"
]

# Quantos dias de histórico analisar
DIAS_ANALISE = 180

# Tempo de pausa (em segundos) entre um sistema e outro
# Importante para "esfriar" a conexão com a OpenAI e o Banco de Dados
PAUSA_SEGURANCA = 10 

def run_pipeline_for_system(sistema):
    logger.info(f"🚀 [ORQUESTRADOR] Iniciando processamento para: {sistema}")
    
    try:
        # Monta o comando: python scripts/run_pipeline.py --sistema "NOME" --dias 180
        comando = [
            sys.executable, # Garante que usa o mesmo Python do ambiente virtual atual
            "scripts/run_pipeline.py",
            "--sistema", sistema,
            "--dias", str(DIAS_ANALISE)
        ]
        
        # Executa o script e aguarda terminar
        # check=True lança erro se o script filho falhar
        subprocess.run(comando, check=True)
        
        logger.info(f"✅ [ORQUESTRADOR] Sucesso: {sistema} finalizado.")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ [ORQUESTRADOR] Erro ao processar {sistema}. Código de saída: {e.returncode}")
    except Exception as e:
        logger.error(f"❌ [ORQUESTRADOR] Erro inesperado: {e}")

if __name__ == "__main__":
    start_global = time.time()
    
    print("\n" + "="*60)
    print(f"   INICIANDO PROCESSAMENTO EM LOTE ({len(SISTEMAS_PARA_PROCESSAR)} SISTEMAS)")
    print("="*60 + "\n")

    for i, sistema in enumerate(SISTEMAS_PARA_PROCESSAR):
        run_pipeline_for_system(sistema)
        
        # Se não for o último, faz a pausa
        if i < len(SISTEMAS_PARA_PROCESSAR) - 1:
            logger.info(f"⏳ Aguardando {PAUSA_SEGURANCA} segundos antes do próximo...")
            time.sleep(PAUSA_SEGURANCA)

    total_time = time.time() - start_global
    minutes = int(total_time // 60)
    seconds = int(total_time % 60)
    
    print("\n" + "="*60)
    print(f"   🏁 FIM DO PROCESSO GERAL")
    print(f"   ⏱️  Tempo Total: {minutes}m {seconds}s")
    print("="*60)