import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
    BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
    XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid 
} from 'recharts';
import { FiPackage, FiCheckCircle, FiTruck, FiDollarSign } from 'react-icons/fi';

// --- CONFIGURAÇÕES GLOBAIS ---
const API_URL = import.meta.env.VITE_API_BI_URL || 'http://localhost:8002';

// Cores usadas nos gráficos (mesma paleta do template)
const COLORS = ['#5e72e4', '#2dce89', '#ff8d4e', '#f5365c', '#11cdef', '#fb6340'];

// Estilo do Tooltip para combinar com o tema Dark
const TOOLTIP_STYLE = {
    backgroundColor: '#1a1d24',
    border: '1px solid #323248',
    borderRadius: '8px',
    color: '#e8eaed',
    fontSize: '0.9rem'
};

// --- HELPER FUNCTIONS ---
const formatBRL = (value: number) => {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
};

const formatNumber = (value: number) => {
    return new Intl.NumberFormat('pt-BR').format(value);
};

// Abrevia status longos para caber no eixo X
const abbreviateStatus = (statusName: string) => {
    const map: Record<string, string> = { 
        'SOLICITADO': 'Solicitado', 
        'AGUARDANDO_COLETA': 'Aguard. Coleta', 
        'EM_TRANSITO': 'Em Trânsito', 
        'ARMAZENADO': 'Armazenado', 
        'EM_ROTA_DE_ENTREGA': 'Em Entrega', 
        'ENTREGUE': 'Entregue', 
        'CANCELADO': 'Cancelado' 
    };
    return map[statusName] || statusName;
};

// --- HOOK DE DADOS (COM POLLING) ---
const useBiData = (endpoint: string) => {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const timeoutRef = useRef<any>(null);

    useEffect(() => {
        let mounted = true;
        const fetchData = async () => {
            if (!mounted) return;
            // Só ativa o loading visual se for a primeira carga
            if (!data) setLoading(true);
            
            try {
                const res = await axios.get(`${API_URL}/api/dashboard/${endpoint}`);
                if (mounted) {
                    setData(res.data);
                    setError(null);
                }
            } catch (err) {
                if (mounted) setError('Erro ao carregar dados.');
                console.error(err);
            } finally {
                if (mounted) {
                    setLoading(false);
                    // Agenda a próxima atualização para 15 segundos
                    timeoutRef.current = setTimeout(fetchData, 15000);
                }
            }
        };

        fetchData();

        return () => {
            mounted = false;
            if (timeoutRef.current) clearTimeout(timeoutRef.current);
        };
    }, [endpoint]);

    return { data, loading, error };
};

// --- COMPONENTES AUXILIARES ---

// 1. Componente de KPI (Card do Topo)
const KpiCard: React.FC<{ title: string; value: string; icon: React.ReactNode; colorClass?: string }> = ({ title, value, icon, colorClass }) => (
    <div className="bi-kpi-card">
        <div className={`bi-kpi-icon ${colorClass}`}>{icon}</div>
        <div className="bi-kpi-text">
            <h3>{title}</h3>
            <p>{value}</p>
        </div>
    </div>
);

// 2. Componente Wrapper para Gráficos (Loading/Error/Empty States)
const ChartWrapper: React.FC<{ title: string; loading: boolean; error: string | null; data: any; children: React.ReactNode }> = ({ 
    title, loading, error, data, children 
}) => {
    return (
        <div className="bi-chart-section">
            <h3 style={{ marginBottom: '1.5rem', color: '#e8eaed' }}>{title}</h3>
            
            {loading && !data && (
                <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8898aa' }}>
                    Carregando visualização...
                </div>
            )}
            
            {error && (
                <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f5365c' }}>
                    {error}
                </div>
            )}
            
            {!loading && !error && (!data || (Array.isArray(data) && data.length === 0)) && (
                <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8898aa' }}>
                    Nenhum dado disponível.
                </div>
            )}

            {!loading && !error && data && (
                <div style={{ width: '100%', height: 350 }}>
                    {children}
                </div>
            )}
        </div>
    );
};

// --- COMPONENTE PRINCIPAL DO DASHBOARD ---
const BiDashboard: React.FC = () => {
    // Hooks de dados para cada seção
    const { data: kpis, loading: kpiLoading } = useBiData('kpis');
    const { data: statusData, loading: statusLoading, error: statusError } = useBiData('operacoes_por_status');
    const { data: filialData, loading: filialLoading, error: filialError } = useBiData('valor_por_filial');
    const { data: dailyData, loading: dailyLoading, error: dailyError } = useBiData('operacoes_por_dia');
    const { data: clientsData, loading: clientsLoading, error: clientsError } = useBiData('top_clientes_por_valor');

    return (
        <div className="bi-dashboard" style={{ overflowY: 'auto', height: '100%' }}>
            {/* Header */}
            <header style={{ marginBottom: '30px' }}>
                <h2 style={{ margin: 0, fontSize: '1.8rem' }}>Dashboard Logístico</h2>
                <p style={{ color: 'var(--bi-text-secondary)', margin: 0 }}>Visão geral da operação e indicadores financeiros</p>
            </header>

            {/* Grid de KPIs */}
            <div className="bi-kpi-grid">
                <KpiCard 
                    title="Total de Operações" 
                    value={kpiLoading ? '-' : formatNumber(kpis?.total_operacoes || 0)} 
                    icon={<FiPackage />}
                    colorClass="text-blue"
                />
                <KpiCard 
                    title="Operações Entregues" 
                    value={kpiLoading ? '-' : formatNumber(kpis?.operacoes_entregues || 0)} 
                    icon={<FiCheckCircle />}
                    colorClass="text-green"
                />
                <KpiCard 
                    title="Pendentes / Trânsito" 
                    value={kpiLoading ? '-' : formatNumber(kpis?.operacoes_em_transito || 0)} 
                    icon={<FiTruck />}
                    colorClass="text-orange"
                />
                <KpiCard 
                    title="Valor Total (R$)" 
                    value={kpiLoading ? '-' : formatBRL(kpis?.valor_total_mercadorias || 0)} 
                    icon={<FiDollarSign />}
                    colorClass="text-red"
                />
            </div>

            {/* Grid de Gráficos */}
            <div className="bi-charts-grid">
                
                {/* 1. Gráfico de Barras: Operações por Status */}
                <ChartWrapper 
                    title="Volume por Status" 
                    loading={statusLoading} 
                    error={statusError} 
                    data={statusData}
                >
                    <ResponsiveContainer>
                        <BarChart data={statusData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#323248" vertical={false} />
                            <XAxis 
                                dataKey="name" 
                                stroke="#8898aa" 
                                tickFormatter={abbreviateStatus} 
                                tick={{ fontSize: 12 }} 
                                interval={0} 
                            />
                            <YAxis stroke="#8898aa" />
                            <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                            <Bar dataKey="value" name="Qtd" radius={[4, 4, 0, 0]}>
                                {statusData?.map((_entry: any, index: number) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </ChartWrapper>

                {/* 2. Gráfico de Barras Horizontais: Valor por Filial (Substituindo UF) */}
                <ChartWrapper 
                    title="Valor Total por Filial" 
                    loading={filialLoading} 
                    error={filialError} 
                    data={filialData}
                >
                    <ResponsiveContainer>
                        <BarChart data={filialData} layout="vertical" margin={{ left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#323248" horizontal={false} />
                            <XAxis type="number" stroke="#8898aa" tickFormatter={(val) => `R$ ${(val/1000).toFixed(0)}k`} />
                            <YAxis type="category" dataKey="name" stroke="#8898aa" width={80} tick={{ fontSize: 11 }} />
                            <Tooltip 
                                contentStyle={TOOLTIP_STYLE} 
                                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                formatter={(val: any) => formatBRL(Number(val))}
                            />
                            <Bar dataKey="value" name="Valor" fill="#2dce89" radius={[0, 4, 4, 0]} barSize={20} />
                        </BarChart>
                    </ResponsiveContainer>
                </ChartWrapper>

                {/* 3. Gráfico de Linha: Evolução Diária */}
                <ChartWrapper 
                    title="Evolução de Operações (30 dias)" 
                    loading={dailyLoading} 
                    error={dailyError} 
                    data={dailyData}
                >
                    <ResponsiveContainer>
                        <LineChart data={dailyData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#323248" />
                            <XAxis dataKey="name" stroke="#8898aa" tick={{ fontSize: 11 }} />
                            <YAxis stroke="#8898aa" />
                            <Tooltip contentStyle={TOOLTIP_STYLE} />
                            <Legend wrapperStyle={{ paddingTop: '10px' }}/>
                            <Line 
                                type="monotone" 
                                dataKey="value" 
                                name="Operações" 
                                stroke="#ff8d4e" 
                                strokeWidth={3}
                                dot={{ r: 4, fill: '#ff8d4e', strokeWidth: 0 }}
                                activeDot={{ r: 6 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </ChartWrapper>

                {/* 4. Gráfico de Pizza: Top Clientes */}
                <ChartWrapper 
                    title="Top 5 Clientes (Valor)" 
                    loading={clientsLoading} 
                    error={clientsError} 
                    data={clientsData}
                >
                    <ResponsiveContainer>
                        <PieChart>
                            <Pie
                                data={clientsData}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={100}
                                paddingAngle={5}
                                dataKey="value"
                                nameKey="name"
                            >
                                {clientsData?.map((_entry: any, index: number) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="#272a30" strokeWidth={2} />
                                ))}
                            </Pie>
                            <Tooltip 
                                contentStyle={TOOLTIP_STYLE} 
                                formatter={(val: any) => formatBRL(Number(val))}
                            />
                            <Legend 
                                layout="vertical" 
                                verticalAlign="middle" 
                                align="right"
                                iconType="circle"
                                wrapperStyle={{ fontSize: '0.85rem', color: '#8898aa' }}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                </ChartWrapper>
            </div>
        </div>
    );
};

export default BiDashboard;