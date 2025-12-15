import React from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid, Legend
} from 'recharts';
import type { BiApiResponse } from '../types/bi.types';

// Mesma paleta do Dashboard para consistência visual
const COLORS = ['#5e72e4', '#2dce89', '#ff8d4e', '#f5365c', '#11cdef', '#fb6340', '#ffd600'];

// --- TOOLTIPS PERSONALIZADOS (Lógica do Template Original) ---

const CustomTooltip = ({ active, payload, label, y_axis_label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="custom-tooltip" style={{ 
          backgroundColor: '#1a1d24', 
          border: '1px solid #323248', 
          padding: '12px', 
          borderRadius: '8px',
          boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
      }}>
        <p style={{ color: '#5e72e4', fontWeight: 'bold', margin: '0 0 5px 0' }}>{data.name || label}</p>
        <p style={{ margin: 0, color: '#e8eaed' }}>
          {`${y_axis_label || 'Valor'}: ${new Intl.NumberFormat('pt-BR').format(payload[0].value)}`}
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
        <div className="custom-tooltip" style={{ 
            backgroundColor: '#1a1d24', 
            border: '1px solid #323248', 
            padding: '12px', 
            borderRadius: '8px'
        }}>
          <p style={{ color: '#e8eaed', fontWeight: 'bold', margin: '0 0 5px 0' }}>{data.name}</p>
          <p style={{ margin: '0 0 2px 0', color: '#2dce89' }}>
             Valor: {new Intl.NumberFormat('pt-BR').format(data.value)}
          </p>
          <p style={{ margin: 0, color: '#8898aa', fontSize: '0.85rem' }}>
             Percentual: {(payload[0].percent * 100).toFixed(1)}%
          </p>
        </div>
      );
    }
    return null;
  };

interface BiChartProps {
    data: BiApiResponse;
}

const BiChart: React.FC<BiChartProps> = ({ data }) => {
  const { title, data: rawData, x_axis, y_axis, y_axis_label, chart_type } = data;

  // --- PROCESSAMENTO DE DADOS (Lógica do Template Original) ---
  // A IA pode mandar chaves variadas (ex: "total_vendas", "mes"). 
  // O Recharts prefere "name" e "value". Essa lógica normaliza isso.
  
  const yAxisKey = y_axis ? y_axis[0] : 'value';
  const xAxisKey = x_axis || 'name';
  const yAxisLabel = y_axis_label || yAxisKey;

  const processedData = (rawData || []).map((item: any) => ({
      ...item,
      name: item[xAxisKey],
      value: Number(item[yAxisKey]) // Garante que é número
  }));

  const renderChart = () => {
    switch (chart_type) {
      case 'line':
        return (
          <LineChart data={processedData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#323248" />
            <XAxis dataKey="name" stroke="#8898aa" tick={{fontSize: 12}} />
            <YAxis stroke="#8898aa" />
            <Tooltip content={<CustomTooltip y_axis_label={yAxisLabel} />} cursor={{ stroke: 'rgba(255,255,255,0.1)' }} />
            <Legend />
            <Line 
                type="monotone" 
                dataKey="value" 
                name={yAxisLabel} 
                stroke="#ff8d4e" 
                strokeWidth={3} 
                dot={{r: 4}} 
                activeDot={{r: 6}} 
            />
          </LineChart>
        );
      case 'pie':
        return (
          <PieChart>
            <Pie
              data={processedData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={false}
            >
              {processedData.map((_entry: any, index: number) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="#272a30" strokeWidth={2} />
              ))}
            </Pie>
            <Tooltip content={<CustomPieTooltip />} />
            <Legend layout="vertical" verticalAlign="middle" align="right" />
          </PieChart>
        );
      case 'bar':
      default:
        return (
          <BarChart data={processedData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#323248" />
            <XAxis dataKey="name" stroke="#8898aa" tick={{fontSize: 12}} />
            <YAxis stroke="#8898aa" />
            <Tooltip content={<CustomTooltip y_axis_label={yAxisLabel} />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
            <Legend />
            <Bar dataKey="value" name={yAxisLabel} radius={[4, 4, 0, 0]}>
                {processedData.map((_entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
            </Bar>
          </BarChart>
        );
    }
  };

  return (
    <div style={{ width: '100%', height: 350, minWidth: '300px', marginTop: '10px' }}>
      {title && <h4 style={{ color: '#e8eaed', marginBottom: '15px', textAlign: 'center' }}>{title}</h4>}
      <ResponsiveContainer>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
};

export default BiChart;