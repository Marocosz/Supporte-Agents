import React, { useState } from 'react';

import {
    BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import {
    FiActivity, FiX
} from 'react-icons/fi';
import Navbar from '../components/Navbar';
import './ScopeIntelPage.css';

// Interfaces baseadas no JSON de saída do backend
// Interfaces baseadas no JSON de saída do backend
interface TimelineItem {
    mes: string;
    qtd: number;
}

interface Metricas {
    volume: number;
    top_servicos: Record<string, number>;
    top_solicitantes: Record<string, number>;
    timeline: TimelineItem[];
}

interface Cluster {
    cluster_id: number;
    titulo: string;
    descricao: string;
    ids_chamados: string[];
    metricas: Metricas;
    sub_clusters?: Cluster[]; // Adicionado para suportar hierarquia
}

interface Metadata {
    sistema: string;
    data_analise: string;
    periodo_dias: number;
    total_chamados: number;
    total_grupos: number;
    taxa_ruido: number;
}

interface AnaliseData {
    metadata: Metadata;
    clusters: Cluster[];
}

// Interface para a lista de análises disponíveis (endpoint /api/analyses)
interface AnalysisSummary {
    filename: string;
    sistema: string;
    data_criacao: string;
    tamanho_bytes: number;
}

// Configuração Visual dos Sistemas (Mapeamento)
const SYSTEM_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
    'NEW TRACKING': { icon: '🚛', color: '#0ea5e9', label: 'New Tracking' },
    'SARA': { icon: '📦', color: '#10b981', label: 'Sara' },
    'PROTHEUS': { icon: '🏭', color: '#eab308', label: 'Protheus' },
    'LOGIX': { icon: '🔧', color: '#f97316', label: 'Logix' },
};

const DEFAULT_CONFIG = { icon: '📁', color: '#64748b', label: 'Sistema' };

// Interface para os detalhes de um chamado carregado sob demanda
interface TicketDetail {
    id_chamado: string;
    titulo: string;
    solicitante: string;
    data_abertura: string;
    status: string;
    descricao_limpa: string;
}

const ScopeIntelPage: React.FC = () => {
    // theme removido pois não é usado aqui
    const [data, setData] = useState<AnaliseData | null>(null);
    const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]); // Lista de análises disponíveis
    const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);
    // const [searchTerm, setSearchTerm] = useState(''); // REMOVIDO
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // --- CACHE DE CHAMADOS (LAZY LOADING) ---
    // Estrutura: { [cluster_id]: TicketDetail[] }
    // Isso evita múltiplas chamadas de API para o mesmo cluster.
    const [ticketsCache, setTicketsCache] = useState<Record<number, TicketDetail[]>>({});
    const [loadingTickets, setLoadingTickets] = useState(false);

    // Função para buscar exemplos de chamados quando abrir o modal
    React.useEffect(() => {
        if (!selectedCluster) return;

        // SE FOR PAI (MACRO), NÃO BUSCA CHAMADOS DIRETOS (Os chamados estão nos filhos)
        if (selectedCluster.sub_clusters && selectedCluster.sub_clusters.length > 0) {
            return;
        }

        // 1. Verifica se já está no cache
        if (ticketsCache[selectedCluster.cluster_id]) {
            return; // Já temos, não precisa buscar
        }

        // 2. Se não tem IDs para buscar, aborta
        const idsToFetch = selectedCluster.ids_chamados?.slice(0, 5) || [];
        if (idsToFetch.length === 0) return;

        // 3. Busca na API
        const fetchTickets = async () => {
            setLoadingTickets(true);
            try {
                const response = await fetch('http://localhost:8001/api/tickets/batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: idsToFetch })
                });

                if (!response.ok) throw new Error('Falha ao buscar chamados');

                const data: TicketDetail[] = await response.json();

                // 4. Salva no Cache
                setTicketsCache(prev => ({
                    ...prev,
                    [selectedCluster.cluster_id]: data
                }));

            } catch (err) {
                console.error("Erro ao carregar exemplos de chamados", err);
            } finally {
                setLoadingTickets(false);
            }
        };

        fetchTickets();

    }, [selectedCluster]);

    // Carregar a lista de análises disponíveis ao montar o componente
    React.useEffect(() => {
        fetchAnalysesList();
    }, []);

    const fetchAnalysesList = async () => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:8001/api/analyses');
            if (!response.ok) {
                throw new Error('Falha ao conectar com o Backend (API).');
            }
            const list = await response.json();
            setAnalyses(list);
            setError(null);
        } catch (err) {
            console.error(err);
            setError('Não foi possível carregar as análises. Verifique se o Backend está rodando (porta 8001).');
        } finally {
            setLoading(false);
        }
    };


    // Filtro removido - agora mostra todos (ou adicione lógica simples se precisar ordenar)
    const sortedClusters = data?.clusters ? [...data.clusters].sort((a, b) => b.metricas.volume - a.metricas.volume) : [];

    // Renderiza a Timeline do cluster selecionado
    const renderTimeline = (timeline: TimelineItem[]) => {
        if (!timeline || timeline.length === 0) return <p>Sem dados temporais.</p>;

        return (
            <div style={{ width: '100%', height: 200 }}>
                <ResponsiveContainer>
                    <BarChart data={timeline}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                        <XAxis dataKey="mes" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <RechartsTooltip
                            contentStyle={{ backgroundColor: '#431407', border: 'none', borderRadius: '8px' }}
                            itemStyle={{ color: '#fff' }}
                        />
                        <Bar dataKey="qtd" fill="#F97316" radius={[4, 4, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        );
    };

    // Carregar dados de um arquivo específico via API
    const loadAnalysisData = async (filename: string) => {
        setLoading(true);
        try {
            const response = await fetch(`http://localhost:8001/api/analyses/${filename}`);

            if (!response.ok) {
                throw new Error('Erro ao carregar análise.');
            }

            const json = await response.json();
            setData(json);
            setError(null);
        } catch (error) {
            alert(`Não foi possível carregar a análise "${filename}".`);
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    // Helper para obter config visual do sistema
    const getSystemConfig = (sistemaName: string) => {
        const key = Object.keys(SYSTEM_CONFIG).find(k => sistemaName.toUpperCase().includes(k));
        return key ? SYSTEM_CONFIG[key] : { ...DEFAULT_CONFIG, label: sistemaName };
    };

    if (!data) {
        return (
            <div className="app-shell">
                <Navbar
                    title="Scope Intelligence"
                    icon={<FiActivity size={24} />}
                />

                <main className="app-main centered">
                    <div className="intel-home-container">
                        <div className="intel-hero">
                            <h1>Selecione o Sistema</h1>
                            <p>Escolha uma análise disponível para visualizar a inteligência de chamados.</p>
                        </div>

                        {error && (
                            <div style={{ color: '#ef4444', marginBottom: '20px', textAlign: 'center' }}>
                                <p>{error}</p>
                                <button onClick={fetchAnalysesList} style={{ marginTop: '10px', padding: '8px 16px', cursor: 'pointer' }}>
                                    Tentar Novamente
                                </button>
                            </div>
                        )}

                        <div className="intel-systems-grid">
                            {analyses.map(analysis => {
                                const config = getSystemConfig(analysis.sistema);
                                return (
                                    <div
                                        key={analysis.filename}
                                        className="intel-sys-card"
                                        onClick={() => loadAnalysisData(analysis.filename)}
                                    >
                                        <div className="intel-sys-icon" style={{ color: config.color, backgroundColor: 'var(--bg-page)', border: `1px solid ${config.color}40` }}>
                                            {config.icon}
                                        </div>
                                        <h2>{config.label}</h2>
                                        <p>{new Date(parseFloat(analysis.data_criacao) * 1000).toLocaleDateString()}</p>
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                            {(analysis.tamanho_bytes / 1024).toFixed(1)} KB
                                        </span>
                                    </div>
                                );
                            })}

                            {/* Empty State se não houver análises */}
                            {!loading && analyses.length === 0 && !error && (
                                <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                                    <p>Nenhuma análise encontrada.</p>
                                    <p style={{ fontSize: '0.9rem' }}>Execute o pipeline Python para gerar novos relatórios.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </main>
                {loading && <p className="intel-loading">Carregando...</p>}
            </div>
        );
    }

    return (
        <div className="app-shell">
            <Navbar
                title={`${data.metadata.sistema}`}
                icon={<FiActivity size={24} />}
                onBack={() => setData(null)}
                backLabel="Sistemas"
            />

            <main className="app-main">
                {/* Header / KPI Row */}
                {/* Header / KPI Row Nova Estrutura */}
                <div className="intel-header-redesigned">

                    {/* LADO ESQUERDO: Títulos e Metadados */}
                    <div className="intel-header-info">
                        <h1>Grupos dos Chamados</h1>
                        <p className="intel-subtitle">
                            Análise baseada nos últimos <strong>{data.metadata.periodo_dias} dias</strong>. <br />
                            Última atualização: {new Date(data.metadata.data_analise).toLocaleDateString()} às {new Date(data.metadata.data_analise).toLocaleTimeString().slice(0, 5)}
                        </p>
                    </div>

                    {/* LADO DIREITO: 3 Cards de KPI */}
                    <div className="intel-kpi-cards-wrapper">

                        <div className="intel-kpi-card">
                            <span className="kpi-label">Volume de Chamados</span>
                            <span className="kpi-value">{data.metadata.total_chamados}</span>
                        </div>

                        <div className="intel-kpi-card">
                            <span className="kpi-label">Grupos Detectados</span>
                            <span className="kpi-value">{data.metadata.total_grupos}</span>
                        </div>

                    </div>
                </div>

                {/* Main Content */}
                <div className="intel-content">

                    {/* Search Bar REMOVIDA DAQUI */}

                    {/* Clusters Grid */}
                    <div className="intel-grid">
                        {sortedClusters.map(cluster => {
                            // Pega APENAS o serviço mais frequente (índice 0)
                            const topService = Object.keys(cluster.metricas.top_servicos)[0];
                            const isMacro = !!(cluster.sub_clusters && cluster.sub_clusters.length > 0);

                            return (
                                <div
                                    key={cluster.cluster_id}
                                    className={`intel-card ${isMacro ? 'macro-card' : ''}`}
                                    onClick={() => setSelectedCluster(cluster)}
                                    style={isMacro ? { borderLeft: '4px solid #f97316' } : {}} // Destaque visual
                                >
                                    {/* Cabeçalho: Título + Volume */}
                                    <div className="intel-card-header">
                                        <h3>{cluster.titulo}</h3>
                                        <span className="intel-vol-badge">{cluster.metricas.volume} chamados</span>
                                    </div>

                                    {/* Corpo: Resumo Completo */}
                                    <div className="intel-card-body">
                                        <p className="intel-card-desc">{cluster.descricao}</p>
                                    </div>

                                    {/* Rodapé: Tag do Principal Serviço ou Contador de Filhos */}
                                    <div className="intel-card-footer">
                                        {isMacro ? (
                                            <span style={{ fontSize: '0.8rem', marginRight: 'auto', color: '#f97316', fontWeight: 600 }}>
                                                📂 {cluster.sub_clusters?.length} sub-grupos
                                            </span>
                                        ) : (
                                            topService && (
                                                <span className="service-tag">
                                                    {topService}
                                                </span>
                                            )
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </main>

            {/* Modal de Detalhes */}
            {selectedCluster && (
                <div className="intel-modal-overlay" onClick={() => setSelectedCluster(null)}>
                    <div className="intel-modal" onClick={e => e.stopPropagation()}>
                        <button className="intel-close-btn" onClick={() => setSelectedCluster(null)}>
                            <FiX />
                        </button>

                        <div className="intel-modal-header">
                            <h2>
                                {selectedCluster.titulo}
                                {selectedCluster.sub_clusters && selectedCluster.sub_clusters.length > 0 && (
                                    <span style={{ fontSize: '0.6em', marginLeft: '10px', color: '#999', fontWeight: 'normal' }}>(Categoria Macro)</span>
                                )}
                            </h2>
                            <div className="intel-modal-chips">
                                <span className="chip">ID: {selectedCluster.cluster_id}</span>
                                <span className="chip volume">{selectedCluster.metricas.volume} eventos</span>
                            </div>
                        </div>

                        <p className="intel-modal-desc">{selectedCluster.descricao}</p>

                        <div className="intel-modal-body">

                            {/* LÓGICA DE EXIBIÇÃO: MACRO (Filhos) ou MICRO (Detalhes) */}
                            {selectedCluster.sub_clusters && selectedCluster.sub_clusters.length > 0 ? (
                                // --- MODO MACRO: LISTA DE FILHOS ---
                                <div className="intel-section full-width">
                                    <h3>📂 Sub-problemas Identificados</h3>
                                    <div className="intel-subclusters-grid" style={{
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                                        gap: '15px',
                                        marginTop: '15px'
                                    }}>
                                        {selectedCluster.sub_clusters.map(sub => (
                                            <div
                                                key={sub.cluster_id}
                                                className="intel-sub-card"
                                                style={{
                                                    background: 'var(--bg-secondary)',
                                                    padding: '16px',
                                                    borderRadius: '8px',
                                                    cursor: 'pointer',
                                                    border: '1px solid var(--border-color)',
                                                    transition: 'all 0.2s ease'
                                                }}
                                                // Dril-down: Clicar no filho atualiza o modal para o filho
                                                onClick={() => setSelectedCluster(sub)}
                                                onMouseEnter={e => (e.currentTarget.style.borderColor = '#f97316')}
                                                onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border-color)')}
                                            >
                                                <h4 style={{ margin: '0 0 8px 0', color: 'var(--text-primary)', fontSize: '0.95rem' }}>
                                                    {sub.titulo}
                                                </h4>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                                        {sub.metricas.volume} chamados
                                                    </span>
                                                    <span style={{ fontSize: '1.2rem' }}>➡️</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Métricas Agregadas do Pai */}
                                    <div className="intel-row-split" style={{ marginTop: '30px', borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                                        <div className="intel-section">
                                            <h3>🔧 Top Serviços Afetados (Total)</h3>
                                            <ul>
                                                {Object.entries(selectedCluster.metricas.top_servicos)
                                                    .slice(0, 5)
                                                    .map(([name, qtd]) => (
                                                        <li key={name}>
                                                            <span>{name}</span>
                                                            <strong>{qtd}</strong>
                                                        </li>
                                                    ))}
                                            </ul>
                                        </div>
                                    </div>
                                </div>

                            ) : (
                                // --- MODO MICRO: DETALHES COMPLETOS ---
                                <>
                                    <div className="intel-section">
                                        <h3>📈 Tendência Temporal</h3>
                                        {renderTimeline(selectedCluster.metricas.timeline)}
                                    </div>

                                    <div className="intel-row-split">
                                        <div className="intel-section">
                                            <h3>🔧 Top Serviços</h3>
                                            <ul>
                                                {Object.entries(selectedCluster.metricas.top_servicos)
                                                    .slice(0, 5)
                                                    .map(([name, qtd]) => (
                                                        <li key={name}>
                                                            <span>{name}</span>
                                                            <strong>{qtd}</strong>
                                                        </li>
                                                    ))}
                                            </ul>
                                        </div>
                                        <div className="intel-section">
                                            <h3>👤 Top Solicitantes</h3>
                                            <ul>
                                                {Object.entries(selectedCluster.metricas.top_solicitantes)
                                                    .slice(0, 5)
                                                    .map(([name, qtd]) => (
                                                        <li key={name}>
                                                            <span>{name}</span>
                                                            <strong>{qtd}</strong>
                                                        </li>
                                                    ))}
                                            </ul>
                                        </div>
                                    </div>

                                    {/* --- SEÇÃO DE EXEMPLOS (LAZY LOADED) --- */}
                                    <div className="intel-section full-width" style={{ marginTop: '20px' }}>
                                        <h3>📌 Exemplos Recentes</h3>
                                        {loadingTickets && !ticketsCache[selectedCluster.cluster_id] ? (
                                            <p className="intel-loading-text">Carregando exemplos...</p>
                                        ) : (
                                            <div className="intel-tickets-list">
                                                {ticketsCache[selectedCluster.cluster_id]?.map(ticket => (
                                                    <div key={ticket.id_chamado} className="intel-ticket-item">
                                                        <div className="ticket-header">
                                                            <strong>{ticket.id_chamado}</strong>
                                                            <span className="ticket-date">
                                                                {new Date(ticket.data_abertura).toLocaleDateString()}
                                                            </span>
                                                        </div>
                                                        <p className="ticket-title">{ticket.titulo}</p>
                                                        <p className="ticket-desc-preview">
                                                            {ticket.descricao_limpa}
                                                        </p>
                                                        <span className="ticket-badge">{ticket.status}</span>
                                                    </div>
                                                ))}

                                                {(!ticketsCache[selectedCluster.cluster_id] || ticketsCache[selectedCluster.cluster_id].length === 0) && (
                                                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                                                        Nenhum detalhe disponível para exibição.
                                                    </p>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ScopeIntelPage;
