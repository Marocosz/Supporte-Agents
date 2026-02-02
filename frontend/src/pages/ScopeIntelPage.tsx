
import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, CartesianGrid
} from 'recharts';
import {
    FiUpload, FiActivity, FiSearch, FiX
} from 'react-icons/fi';
import './ScopeIntelPage.css';

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

const ScopeIntelPage: React.FC = () => {
    const { theme } = useTheme();
    const [data, setData] = useState<AnaliseData | null>(null);
    const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);
    const [searchTerm, setSearchTerm] = useState('');

    const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const json = JSON.parse(e.target?.result as string);
                setData(json);
            } catch (error) {
                alert('Erro ao ler arquivo JSON. Verifique o formato.');
            }
        };
        reader.readAsText(file);
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

    const [loading, setLoading] = useState(false);

    // Lista de Sistemas disponíveis para análise
    // Lista de Sistemas disponíveis para análise
    const sistemas = [
        { id: 'NEW TRACKING', nome: 'New Tracking', icon: '�', color: '#0ea5e9' },
        { id: 'SARA', nome: 'Sara', icon: '📦', color: '#10b981' },
        { id: 'PROTHEUS', nome: 'Protheus', icon: '🏭', color: '#eab308' },
        { id: 'LOGIX', nome: 'Logix', icon: '🔧', color: '#f97316' },
    ];

    const loadSystemData = async (sistemaId: string) => {
        setLoading(true);
        try {
            // Tenta buscar o arquivo JSON padrão na pasta public/data
            // O nome do arquivo deve seguir o padrão: analise_NOMESISTEMA.json
            const response = await fetch(`/data/analise_${sistemaId}.json`);

            if (!response.ok) {
                throw new Error('Arquivo de análise não encontrado.');
            }

            const json = await response.json();
            setData(json);
        } catch (error) {
            alert(`Não foi possível carregar a análise do ${sistemaId}.\n\nCertifique-se que o arquivo "analise_${sistemaId}.json" está na pasta "frontend/public/data".`);
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    if (!data) {
        return (
            <div className={`intel-page ${theme}`}>
                <div className="intel-home-container">
                    <div className="intel-hero">
                        <h1>Selecione o Sistema</h1>
                        <p>Escolha uma aplicação para visualizar a inteligência de chamados.</p>
                    </div>

                    <div className="intel-systems-grid">
                        {sistemas.map(sys => (
                            <div
                                key={sys.id}
                                className="intel-sys-card"
                                onClick={() => loadSystemData(sys.id)}
                                style={{ borderTopColor: sys.color }}
                            >
                                <div className="intel-sys-icon" style={{ backgroundColor: `${sys.color}20` }}>
                                    {sys.icon}
                                </div>
                                <h2>{sys.nome}</h2>
                                <p>Clique para ver relatórios</p>
                            </div>
                        ))}


                    </div>

                    {loading && <p className="intel-loading">Carregando inteligência...</p>}
                </div>
            </div>
        );
    }

    return (
        <div className={`intel-page ${theme}`}>
            {/* Header / KPI Row */}
            <div className="intel-header">
                <div className="intel-title">
                    <h1>Ticket Intel AI</h1>
                    <span className="intel-badge-sys">{data.metadata.sistema}</span>
                </div>

                <div className="intel-kpi-row">
                    <div className="intel-kpi">
                        <span className="intel-kpi-label">Total Chamados</span>
                        <span className="intel-kpi-value">{data.metadata.total_chamados}</span>
                    </div>
                    <div className="intel-kpi">
                        <span className="intel-kpi-label">Padrões Detectados</span>
                        <span className="intel-kpi-value">{data.metadata.total_grupos}</span>
                    </div>
                    <div className="intel-kpi">
                        <span className="intel-kpi-label">Eficiência IA</span>
                        <span className="intel-kpi-value">
                            {((1 - data.metadata.taxa_ruido) * 100).toFixed(1)}%
                        </span>
                    </div>
                    <div className="intel-actions">
                        <label className="intel-btn-upload-small">
                            <FiUpload /> Nova Análise
                            <input type="file" accept=".json" onChange={handleFileUpload} hidden />
                        </label>
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
