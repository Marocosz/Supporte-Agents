# ==============================================================================
# ARQUIVO: scripts/generate_report.py
#
# OBJETIVO:
#   Gerar relatórios em PDF ricos e visuais baseados nos JSONs de análise produzidos pelo Pipeline.
#   Cria gráficos (Tendência, Sazonalidade) e tabelas formatadas para consumo executivo.
#
# PARTE DO SISTEMA:
#   Scripts / Reporting
#
# RESPONSABILIDADES:
#   - Ler o JSON mais recente da pasta data_output/
#   - Gerar gráficos temporários usando Matplotlib
#   - Construir o PDF usando ReportLab (Platypus)
#   - Buscar exemplos reais no banco de dados se necessário para enriquecer o relatório
#
# COMUNICAÇÃO:
#   Lê: Arquivos JSON em data_output/
#   Acessa: Banco de Dados (opcional, para refresh de exemplos)
#   Gera: Arquivos PDF em reports/
# ==============================================================================

import os
import glob
import json
import logging
import io
import sys
from datetime import datetime
import matplotlib.pyplot as plt
from dotenv import load_dotenv # <--- NOVO IMPORT

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÃO DE CAMINHOS (CRÍTICO PARA O ERRO) ---
# Calcula a raiz do projeto (onde está o .env)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_OUTPUT_DIR = os.path.join(BASE_DIR, "data_output")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
TEMP_IMG_DIR = os.path.join(BASE_DIR, "temp_images")

# Força o carregamento do .env ANTES de importar o app.core
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
    logger.info(f"Variáveis de ambiente carregadas de: {env_path}")
else:
    logger.warning(f"Arquivo .env não encontrado em: {env_path}")

# Adiciona o diretório base ao Python Path
sys.path.append(BASE_DIR)

# --- DB & CORE Imports (Agora é seguro importar) ---
from app.core.database import SessionLocal
from app.services.data_fetcher import fetch_batch_by_ids

# --- ReportLab Imports ---
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT

# Garante diretórios
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(TEMP_IMG_DIR, exist_ok=True)

def get_latest_json(sistema):
    pattern = os.path.join(DATA_OUTPUT_DIR, f"analise_{sistema}_*.json")
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None

# --- GERAÇÃO DE GRÁFICOS (MATPLOTLIB) ---
def create_trend_chart(timeline_data, filename):
    if not timeline_data: return None
    
    # Tratamento robusto para dict ou objeto Pydantic
    meses = []
    qtds = []
    for item in timeline_data:
        if isinstance(item, dict):
            meses.append(item.get('mes', 'N/A'))
            qtds.append(item.get('qtd', 0))
        else:
            meses.append(getattr(item, 'mes', 'N/A'))
            qtds.append(getattr(item, 'qtd', 0))
    
    if not meses: return None

    plt.figure(figsize=(5, 3))
    plt.plot(meses, qtds, marker='o', color='#2563eb', linewidth=2)
    plt.title('Tendência (Volume Mensal)', fontsize=10, fontweight='bold', color='#333333')
    plt.xticks(rotation=45, fontsize=8)
    plt.yticks(fontsize=8)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    path = os.path.join(TEMP_IMG_DIR, filename)
    plt.savefig(path, dpi=100)
    plt.close()
    return path

def create_seasonality_chart(sazonalidade_data, filename):
    if not sazonalidade_data: return None
        
    dias = []
    qtds = []
    for item in sazonalidade_data:
        if isinstance(item, dict):
            dias.append(item.get('dia', 'N/A'))
            qtds.append(item.get('qtd', 0))
        else:
            dias.append(getattr(item, 'dia', 'N/A'))
            qtds.append(getattr(item, 'qtd', 0))
    
    if not dias: return None

    plt.figure(figsize=(5, 3))
    plt.bar(dias, qtds, color='#10b981')
    plt.title('Padrão Semanal', fontsize=10, fontweight='bold', color='#333333')
    plt.xticks(fontsize=8)
    plt.yticks(fontsize=8)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    
    path = os.path.join(TEMP_IMG_DIR, filename)
    plt.savefig(path, dpi=100)
    plt.close()
    return path

# --- HELPER PARA ESTILOS ---
def p(text, style):
    return Paragraph(str(text), style)

def get_example_tickets(cluster, limit=5):
    """
    Tenta obter exemplos de texto.
    1. Se já estiver no JSON (amostras_texto), usa.
    2. Se não, usa 'ids_chamados' para buscar no banco via fetch_batch_by_ids.
    """
    amostras = cluster.get('amostras_texto', [])
    if amostras:
        return amostras[:limit]
    
    ids = cluster.get('ids_chamados', [])
    if not ids:
        ids_filhos = []
        # Tenta pegar dos subclusters se existir
        sub = cluster.get('sub_clusters', [])
        for s in sub:
            ids_filhos.extend(s.get('ids_chamados', []))
        ids = ids_filhos

    if not ids:
        return []
    
    # Busca no Banco (limitando a N IDs para não sobrecarregar)
    target_ids = ids[:limit]
    
    db = SessionLocal()
    try:
        detailed_tickets = fetch_batch_by_ids(db, target_ids)
        # Formata: "TITULO: ... \n DESCRIÇÃO: ..."
        text_samples = []
        for t in detailed_tickets:
            # Texto rico formatado
            txt = f"<b>[{t['id_chamado']}] {t['titulo']}</b><br/>{t['descricao_limpa']}"
            text_samples.append(txt)
        return text_samples
    except Exception as e:
        logger.error(f"Erro ao buscar tickets no DB: {e}")
        return []
    finally:
        db.close()

def create_pdf(json_file_path):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Erro ao ler JSON: {e}")
        return

    metadata = data.get('metadata', {})
    clusters = data.get('clusters', [])
    sistema = metadata.get('sistema', 'Sistema')
    
    # Ordenação
    clusters_sorted = sorted(clusters, key=lambda x: x.get('metricas', {}).get('volume', 0), reverse=True)
    top_5 = clusters_sorted[:5]
    others = clusters_sorted[5:10]

    output_filename = f"Relatorio_Escopo_{sistema}_{datetime.now().strftime('%Y%m%d')}.pdf"
    output_path = os.path.join(REPORTS_DIR, output_filename)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    story = []
    styles = getSampleStyleSheet()
    
    # Estilos
    style_title = ParagraphStyle('MainTitle', parent=styles['Title'], fontSize=24, textColor=colors.HexColor("#1e3a8a"), spaceAfter=10)
    style_subtitle = ParagraphStyle('SubTitle', parent=styles['Normal'], fontSize=12, textColor=colors.grey, alignment=TA_CENTER)
    style_h1 = ParagraphStyle('Header1', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1f2937"), spaceBefore=10, spaceAfter=5)
    style_section_label = ParagraphStyle('Label', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#6b7280"), fontName='Helvetica-Bold')
    style_body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, alignment=TA_JUSTIFY)
    style_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor("#374151"))
    style_card_bg = colors.HexColor("#f3f4f6")

    # === CAPA ===
    story.append(Spacer(1, 2*cm))
    story.append(p(f"Análise de Clusters: {sistema}", style_title))
    story.append(p(f"Gerado em: {datetime.now().strftime('%d/%m/%Y')}", style_subtitle))
    story.append(Spacer(1, 1*cm))
    
    kpi_data = [
        [p("Total Chamados", style_section_label), p("Grupos", style_section_label), p("Ruído", style_section_label)],
        [p(metadata.get('total_chamados', 0), style_h1), p(metadata.get('total_grupos', 0), style_h1), p(f"{metadata.get('taxa_ruido', 0)*100:.1f}%", style_h1)]
    ]
    kpi_table = Table(kpi_data, colWidths=[6*cm, 6*cm, 6*cm])
    kpi_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 1, colors.lightgrey),
        ('PADDING', (0,0), (-1,-1), 15),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 1*cm))

    # === CONFIGURAÇÃO TÉCNICA (Hardcoded Header) ===
    story.append(p("Parâmetros do Pipeline de Inteligência", style_h1))
    tech_text = (
        "<b>Motor de Vetorização:</b> OpenAI Embeddings (1536 dimensões)<br/>"
        "<b>Algoritmo de Redução:</b> UMAP (Manifold Learning) - Redução para 5D (Cálculo) e 2D (Visualização)<br/>"
        "<b>Algoritmo de Agrupamento:</b> HDBSCAN Hierárquico (Densidade Variável)<br/>"
        "<b>LLM Analista:</b> GPT-4o (Análise Semântica e Racional)<br/>"
        "<b>Estratégia:</b> Abordagem Híbrida (Matemática + Semântica) com Validação Estatística."
    )
    story.append(p(tech_text, ParagraphStyle('Tech', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#4b5563"), leading=12)))
    
    story.append(PageBreak())

    # === TOP 5 ===
    for i, cluster in enumerate(top_5):
        rank = i + 1
        metricas = cluster.get('metricas', {})
        titulo = cluster.get('titulo', 'Sem Título')
        desc = cluster.get('descricao', '')
        
        # Leitura dos novos campos ricos
        racional = cluster.get('analise_racional', '')
        keywords = cluster.get('top_keywords', [])
        
        # Header
        header_table = Table([[
            p(f"Cluster #{rank}", ParagraphStyle('Rank', parent=styles['Normal'], fontSize=20, textColor=colors.HexColor("#2563eb"), fontName='Helvetica-Bold')),
            p(f"Volume: {metricas.get('volume', 0)}", ParagraphStyle('Vol', parent=styles['Normal'], fontSize=14, alignment=TA_RIGHT))
        ]], colWidths=[12*cm, 6*cm])
        story.append(header_table)
        
        story.append(p(titulo, style_h1))
        story.append(p(f"<b>Diagnóstico:</b> {desc}", style_body))
        story.append(Spacer(1, 0.3*cm))
        
        # --- Racional da IA (Se existir) ---
        if racional:
            racional_text = f"<b>🧠 Raciocínio da IA:</b> <i>{racional}</i>"
            story.append(p(racional_text, ParagraphStyle('Racional', parent=style_body, textColor=colors.HexColor("#4b5563"), backColor=colors.HexColor("#f3f4f6"), borderWidth=0, padding=5)))
            story.append(Spacer(1, 0.3*cm))

        # --- Keywords / Tags ---
        if keywords:
            # Pega top 10
            tags_str = ", ".join(keywords[:10])
            story.append(p(f"<b>Palavras-Chave (Evidências):</b> {tags_str}", style_small))
            story.append(Spacer(1, 0.5*cm))

        # Charts
        f_trend = f"trend_{sistema}_{rank}.png"
        f_season = f"season_{sistema}_{rank}.png"
        path_trend = create_trend_chart(metricas.get('timeline', []), f_trend)
        path_season = create_seasonality_chart(metricas.get('sazonalidade', []), f_season)
        
        charts_row = []
        charts_row.append(Image(path_trend, width=8*cm, height=5*cm) if path_trend else p("N/A", style_small))
        charts_row.append(Image(path_season, width=8*cm, height=5*cm) if path_season else p("N/A", style_small))
        story.append(Table([charts_row], colWidths=[9*cm, 9*cm], style=TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')])))
        story.append(Spacer(1, 0.5*cm))

        # --- SEPARAÇÃO: USERS | SERVIÇOS | SUBAREA HIGHLIGHT ---
        
        # 1. Top Subarea Card
        top_subs = metricas.get('top_subareas', {})
        if top_subs:
            best_sub = list(top_subs.keys())[0]
            val_sub = top_subs[best_sub]
            sub_card_content = [[
                p(f"🔥 Maior Sub-área Ofensora: <b>{best_sub}</b> ({val_sub} chamados)", 
                  ParagraphStyle('Alert', parent=styles['Normal'], textColor=colors.white, alignment=TA_CENTER))
            ]]
            sub_table = Table(sub_card_content, colWidths=[18*cm])
            sub_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ef4444")), # Vermelho alerta
                ('rx', (0,0), (-1,-1), 10), # Arredondado (simulate)
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(sub_table)
            story.append(Spacer(1, 0.3*cm))

        # 2. Tabelas Lado a Lado (Solicitantes vs Serviços)
        
        # Col 1: Solicitantes
        users_rows = [[p("Top Solicitantes", style_section_label), p("Qtd", style_section_label)]]
        for k, v in list(metricas.get('top_solicitantes', {}).items())[:5]:
            users_rows.append([p(k, style_small), p(str(v), style_small)])
            
        t_users = Table(users_rows, colWidths=[5*cm, 1.5*cm])
        t_users.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0,0), (-1,0), style_card_bg),
        ]))

        # Col 2: Serviços (Sem Subarea aqui)
        serv_rows = [[p("Top Serviços", style_section_label), p("Qtd", style_section_label)]]
        for k, v in list(metricas.get('top_servicos', {}).items())[:5]:
            serv_rows.append([p(k, style_small), p(str(v), style_small)])
            
        t_serv = Table(serv_rows, colWidths=[5*cm, 1.5*cm])
        t_serv.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('BACKGROUND', (0,0), (-1,0), style_card_bg),
        ]))
        
        dual_table = Table([[t_users, t_serv]], colWidths=[9*cm, 9*cm])
        dual_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        story.append(dual_table)
        story.append(Spacer(1, 0.5*cm))

        # --- EXEMPLOS REAIS (Fetching DB) ---
        story.append(p("Exemplos de Chamados (Amostra Real):", style_section_label))
        story.append(Spacer(1, 0.2*cm))
        
        examples = get_example_tickets(cluster, limit=5)
        
        if examples:
            for txt in examples:
                # Truncate seguro
                MAX_LEN = 350
                if len(txt) > MAX_LEN: txt = txt[:MAX_LEN] + "..."
                
                tbl_ex = Table([[p(txt, style_small)]], colWidths=[18*cm])
                tbl_ex.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f9fafb")),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.lightgrey),
                    ('PADDING', (0,0), (-1,-1), 6),
                ]))
                story.append(tbl_ex)
                story.append(Spacer(1, 0.15*cm))
        else:
             story.append(p("Não foi possível carregar exemplos detalhados.", style_small))

        story.append(PageBreak())

    # === RESUMO 6-10 ===
    if others:
        story.append(p("Radar de Outros Grupos (Top 6-10)", style_h1))
        story.append(Spacer(1, 0.5*cm))
        
        tbl_head = [p("Rank", style_section_label), p("Grupo / Descrição", style_section_label), p("Vol", style_section_label)]
        tbl_data = [tbl_head]
        
        for j, c in enumerate(others):
            rank = 6 + j
            txt = f"<b>{c.get('titulo','')}</b><br/>{c.get('descricao','')}"
            row = [p(str(rank), ParagraphStyle('C', parent=styles['Normal'], alignment=TA_CENTER)), p(txt, style_small), p(str(c.get('metricas',{}).get('volume',0)), ParagraphStyle('C', parent=styles['Normal'], alignment=TA_CENTER))]
            tbl_data.append(row)
            
        final_table = Table(tbl_data, colWidths=[1.5*cm, 14*cm, 2.5*cm])
        final_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e0e7ff")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.whitesmoke]),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(final_table)
        
    doc.build(story)
    logger.info(f"✅ PDF Finalizado: {output_path}")

    # Clean images
    for f in os.listdir(TEMP_IMG_DIR):
        try: os.remove(os.path.join(TEMP_IMG_DIR, f))
        except: pass

def main():
    sistemas = ["PROTHEUS", "LOGIX", "NEW TRACKING", "SARA"]
    print("Iniciando geração de relatórios...")
    for s in sistemas:
        j = get_latest_json(s)
        if j: 
            logger.info(f"Processando {s}...")
            create_pdf(j)
        else:
            logger.warning(f"Sem JSON para {s}")

if __name__ == "__main__":
    main()