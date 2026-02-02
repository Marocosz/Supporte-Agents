import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import {
    FiActivity, FiSearch, FiX
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

const ScopeIntelPage: React.FC = () => {
    // theme removido pois não é usado aqui
    const [data, setData] = useState<AnaliseData | null>(null);
    const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]); // Lista de análises disponíveis
    const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

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



    const filteredClusters = data?.clusters.filter(c =>
        c.titulo.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.descricao.toLowerCase().includes(searchTerm.toLowerCase())
    ) || [];

    // Ordenar clusters por volume (maior primeiro)
    const sortedClusters = [...filteredClusters].sort((a, b) => b.metricas.volume - a.metricas.volume);

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
                            contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                            itemStyle={{ color: '#fff' }}
                        />
                        <Bar dataKey="qtd" fill="#8884d8" radius={[4, 4, 0, 0]} />
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
                                        style={{ borderTopColor: config.color }}
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
                title={`Scope: ${data.metadata.sistema}`}
                icon={<FiActivity size={24} />}
                onBack={() => setData(null)}
                backLabel="Sistemas"
            />

            <main className="app-main">
                {/* Header / KPI Row */}
                <div className="intel-header">
                    {/* Removido título daqui pois está na navbar */}
                    <div style={{ flex: 1 }}></div>

                    <div className="intel-kpi-row">
                        <div className="intel-kpi">
                            <span className="intel-kpi-label">Total Chamados</span>
                            <span className="intel-kpi-value">{data.metadata.total_chamados}</span>
                        </div>
                        <div className="intel-kpi">
                            <span className="intel-kpi-label">Padrões Detectados</span>
                            <span className="intel-kpi-value">{data.metadata.total_grupos}</span>
                        </div>
                        <div className="intel-kpi" title="Porcentagem de chamados úteis após remoção de ruído (spam, logs, mensagens curtas).">
                            <span className="intel-kpi-label">Eficiência IA</span>
                            <span className="intel-kpi-value">
                                {((1 - data.metadata.taxa_ruido) * 100).toFixed(1)}%
                            </span>
                        </div>

                    </div>
                </div>

                {/* Main Content */}
                <div className="intel-content">

                    {/* Search Bar */}
                    <div className="intel-search-bar">
                        <FiSearch className="intel-search-icon" />
                        <input
                            type="text"
                            placeholder="Buscar por erro, descrição..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>

                    {/* Clusters Grid */}
                    <div className="intel-grid">
                        {sortedClusters.map(cluster => (
                            <div
                                key={cluster.cluster_id}
                                className="intel-card"
                                onClick={() => setSelectedCluster(cluster)}
                            >
                                <div className="intel-card-header">
                                    <span className="intel-vol-badge">{cluster.metricas.volume}</span>
                                    <h3>{cluster.titulo}</h3>
                                </div>
                                <p className="intel-card-desc">{cluster.descricao}</p>

                                <div className="intel-card-mini-stats">
                                    <div className="mini-stat">
                                        <FiActivity />
                                        <span>
                                            Top: {Object.keys(cluster.metricas.top_servicos)[0] || 'N/A'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        ))}
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
                            <h2>{selectedCluster.titulo}</h2>
                            <div className="intel-modal-chips">
                                <span className="chip">ID: {selectedCluster.cluster_id}</span>
                                <span className="chip volume">{selectedCluster.metricas.volume} eventos</span>
                            </div>
                        </div>

                        <p className="intel-modal-desc">{selectedCluster.descricao}</p>

                        <div className="intel-modal-body">
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
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ScopeIntelPage;
