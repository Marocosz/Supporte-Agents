import React from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

interface ChartData {
  chart_type: 'bar' | 'line' | 'pie';
  title?: string;
  data: any[];
  x_axis?: string;
  y_axis?: string[];
  y_axis_label?: string; // Novo campo para legenda do eixo Y
}

interface BiChartProps {
  data: ChartData;
}

const COLORS = ['#5e72e4', '#2dce89', '#11cdef', '#fb6340', '#f5365c', '#8965e0'];

const BiChart: React.FC<BiChartProps> = ({ data }) => {
  const { chart_type, data: chartData, x_axis, y_axis } = data;

  // Renderiza Gráfico de Barras
  if (chart_type === 'bar') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#32325d" vertical={false} />
          <XAxis 
            dataKey={x_axis} 
            stroke="#8898aa" 
            tick={{ fill: '#8898aa', fontSize: 12 }} 
            axisLine={false}
            tickLine={false}
          />
          <YAxis 
            stroke="#8898aa" 
            tick={{ fill: '#8898aa', fontSize: 12 }} 
            axisLine={false}
            tickLine={false}
            label={data.y_axis_label ? { value: data.y_axis_label, angle: -90, position: 'insideLeft', fill: '#8898aa' } : undefined}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#172b4d', border: 'none', borderRadius: '8px', color: '#fff' }}
            itemStyle={{ color: '#fff' }}
            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
          />
          <Legend wrapperStyle={{ paddingTop: '10px' }} />
          {y_axis?.map((key, index) => (
            <Bar 
                key={key} 
                dataKey={key} 
                fill={COLORS[index % COLORS.length]} 
                radius={[4, 4, 0, 0]}
                barSize={40} // Evita barras muito gordas
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // Renderiza Gráfico de Linha
  if (chart_type === 'line') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#32325d" vertical={false} />
          <XAxis 
            dataKey={x_axis} 
            stroke="#8898aa" 
            tick={{ fill: '#8898aa', fontSize: 12 }} 
            axisLine={false}
            tickLine={false}
          />
          <YAxis 
            stroke="#8898aa" 
            tick={{ fill: '#8898aa', fontSize: 12 }} 
            axisLine={false}
            tickLine={false}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#172b4d', border: 'none', borderRadius: '8px', color: '#fff' }}
            itemStyle={{ color: '#fff' }}
          />
          <Legend wrapperStyle={{ paddingTop: '10px' }} />
          {y_axis?.map((key, index) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={COLORS[index % COLORS.length]}
              strokeWidth={3}
              dot={{ r: 4, fill: '#172b4d', strokeWidth: 2 }}
              activeDot={{ r: 6 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  // Renderiza Gráfico de Pizza
  if (chart_type === 'pie') {
    // Para pizza, precisamos saber qual é a chave de valor. Assumimos a primeira do y_axis.
    const valueKey = y_axis && y_axis.length > 0 ? y_axis[0] : 'value';
    const nameKey = x_axis || 'name';

    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            // Label customizada para facilitar leitura
            label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
            outerRadius={120} // Um pouco maior
            fill="#8884d8"
            dataKey={valueKey}
            nameKey={nameKey}
          >
            {chartData.map((_: any, index: number) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="#172b4d" strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip 
            contentStyle={{ backgroundColor: '#172b4d', border: 'none', borderRadius: '8px', color: '#fff' }}
            itemStyle={{ color: '#fff' }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return <p>Tipo de gráfico não suportado.</p>;
};

export default BiChart;