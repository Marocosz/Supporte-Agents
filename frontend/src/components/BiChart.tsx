import React from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

// --- Interfaces ---
interface ChartData {
  chart_type: 'bar' | 'line' | 'pie';
  title?: string;
  data: any[];
  x_axis?: string;
  y_axis?: string[];
  y_axis_label?: string;
}

interface BiChartProps {
  data: ChartData;
}

// --- Constantes e Utilitários ---
const COLORS = ['#5e72e4', '#2dce89', '#11cdef', '#fb6340', '#f5365c', '#8965e0', '#32325d', '#adb5bd'];

// Função para formatar datas no eixo X
const formatXAxisDate = (tickItem: string) => {
    if (!tickItem) return '';
    try {
        if (typeof tickItem === 'string' && tickItem.includes('-') && tickItem.length >= 10) {
            const date = new Date(tickItem);
            if (!isNaN(date.getTime())) {
                return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
            }
        }
    } catch (e) { return tickItem; }
    
    const str = String(tickItem);
    return str.length > 12 ? str.substring(0, 12) + '...' : str;
};

// Formata valores grandes (ex: 1M, 1k)
const formatYAxisNumber = (num: any) => {
    if (typeof num !== 'number') return num;
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return new Intl.NumberFormat('pt-BR').format(num);
};

// --- Componentes de Tooltip Personalizados (Estilo Template) ---

const CustomTooltip = ({ active, payload, label, y_axis_label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip">
        <p className="tooltip-label">{formatXAxisDate(label)}</p>
        <p className="tooltip-value">
          {y_axis_label || 'Valor'}: <strong>{formatYAxisNumber(payload[0].value)}</strong>
        </p>
      </div>
    );
  }
  return null;
};

const CustomPieTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="custom-tooltip">
        <p className="tooltip-label">{formatXAxisDate(data.name)}</p>
        <p className="tooltip-value">Valor: <strong>{formatYAxisNumber(data.value)}</strong></p>
        <p className="tooltip-percent">Percentual: <strong>{(payload[0].percent * 100).toFixed(1)}%</strong></p>
      </div>
    );
  }
  return null;
};

// --- Componente Principal ---

const BiChart: React.FC<BiChartProps> = ({ data }) => {
  const { chart_type, data: rawData, x_axis, y_axis, y_axis_label } = data;

  // 1. Processamento de Dados (Padronização para name/value)
  // Isso garante que o Recharts entenda os dados independente do nome da coluna SQL
  const xAxisKey = x_axis || 'name';
  const yAxisKey = y_axis && y_axis.length > 0 ? y_axis[0] : 'value';

  const processedData = rawData.map(item => ({
    ...item,
    name: item[xAxisKey],
    value: item[yAxisKey]
  }));

  // 2. Renderização Condicional baseada no tipo
  switch (chart_type) {
    case 'bar':
        return (
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={processedData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                    
                    <XAxis 
                        dataKey="name" 
                        stroke="#8898aa" 
                        tick={{ fill: '#8898aa', fontSize: 11 }} 
                        tickLine={false} 
                        axisLine={false}
                        angle={-45}
                        textAnchor="end"
                        height={60}
                        tickFormatter={formatXAxisDate} 
                    />
                    
                    <YAxis 
                        stroke="#8898aa" 
                        tick={{ fill: '#8898aa', fontSize: 11 }} 
                        tickLine={false} 
                        axisLine={false}
                        tickFormatter={formatYAxisNumber}
                        label={y_axis_label ? { 
                            value: y_axis_label, angle: -90, position: 'insideLeft', fill: '#8898aa', style: { textAnchor: 'middle' }
                        } : undefined}
                    />
                    
                    <Tooltip content={<CustomTooltip y_axis_label={y_axis_label} />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} iconType="circle" />
                    
                    <Bar 
                        dataKey="value" 
                        name={yAxisKey.replace(/_/g, ' ')}
                        fill={COLORS[0]} 
                        radius={[4, 4, 0, 0]} 
                        barSize={40}
                    >
                        {processedData.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        );

    case 'line':
        return (
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={processedData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                    
                    <XAxis 
                        dataKey="name" 
                        stroke="#8898aa" 
                        tick={{ fill: '#8898aa', fontSize: 11 }} 
                        tickLine={false} 
                        axisLine={false}
                        minTickGap={30}
                        tickFormatter={formatXAxisDate} 
                    />
                    
                    <YAxis 
                        stroke="#8898aa" 
                        tick={{ fill: '#8898aa', fontSize: 11 }} 
                        tickLine={false} 
                        axisLine={false}
                        tickFormatter={formatYAxisNumber}
                    />
                    
                    <Tooltip content={<CustomTooltip y_axis_label={y_axis_label} />} />
                    <Legend wrapperStyle={{ paddingTop: '10px' }} iconType="plainline" />
                    
                    <Line 
                        type="monotone" 
                        dataKey="value" 
                        name={yAxisKey.replace(/_/g, ' ')}
                        stroke={COLORS[0]} 
                        strokeWidth={3} 
                        dot={false} 
                        activeDot={{ r: 6 }} 
                    />
                </LineChart>
            </ResponsiveContainer>
        );

    case 'pie':
        return (
            <ResponsiveContainer width="100%" height="100%">
                <PieChart margin={{ top: 20, right: 40, left: 40, bottom: 20 }}>
                    <Pie
                        data={processedData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                        nameKey="name"
                        minAngle={3}
                    >
                        {processedData.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="rgba(0,0,0,0)" />
                        ))}
                    </Pie>
                    <Tooltip content={<CustomPieTooltip />} />
                    <Legend verticalAlign="bottom" height={36} />
                </PieChart>
            </ResponsiveContainer>
        );

    default:
        return <p style={{ color: '#8898aa', textAlign: 'center', padding: 20 }}>Gráfico indisponível.</p>;
  }
};

export default BiChart;