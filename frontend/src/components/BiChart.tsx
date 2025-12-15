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
  y_axis_label?: string;
}

interface BiChartProps {
  data: ChartData;
}

const COLORS = ['#5e72e4', '#2dce89', '#11cdef', '#fb6340', '#f5365c', '#8965e0', '#32325d', '#adb5bd'];

// Função para formatar datas no eixo X (ex: 2023-10-01 -> 01/10)
const formatXAxisDate = (tickItem: string) => {
    if (!tickItem) return '';
    try {
        // Tenta detectar se é data ISO
        if (tickItem.includes('-') && tickItem.length >= 10) {
            const date = new Date(tickItem);
            if (!isNaN(date.getTime())) {
                return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
            }
        }
    } catch (e) {
        return tickItem;
    }
    // Se não for data, encurta texto longo
    const str = String(tickItem);
    return str.length > 12 ? str.substring(0, 12) + '...' : str;
};

// Formata valores grandes (ex: 1000000 -> 1M, 1000 -> 1k)
const formatYAxisNumber = (num: any) => {
    if (typeof num !== 'number') return num;
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num;
};

const BiChart: React.FC<BiChartProps> = ({ data }) => {
  const { chart_type, data: chartData, x_axis, y_axis } = data;

  // --- GRÁFICO DE BARRAS ---
  if (chart_type === 'bar') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={chartData}
          // Margens ajustadas para evitar cortes
          margin={{ top: 30, right: 30, left: 20, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#32325d" vertical={false} opacity={0.2} />
          
          <XAxis 
            dataKey={x_axis} 
            stroke="#8898aa" 
            tick={{ fill: '#8898aa', fontSize: 11 }} 
            axisLine={{ stroke: '#8898aa' }}
            tickLine={false}
            // Ângulo -45 ajuda a ler, mas sem interval={0} para não sobrepor se tiver muitos
            angle={-45}
            textAnchor="end"
            height={60} 
            tickFormatter={formatXAxisDate} 
          />
          
          <YAxis 
            stroke="#8898aa" 
            tick={{ fill: '#8898aa', fontSize: 11 }} 
            axisLine={false}
            tickLine={false}
            tickFormatter={formatYAxisNumber}
            // Legenda do Eixo Y
            label={data.y_axis_label ? { 
                value: data.y_axis_label, 
                angle: -90, 
                position: 'insideLeft', 
                fill: '#8898aa',
                style: { textAnchor: 'middle' }
            } : undefined}
          />
          
          <Tooltip 
            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
            contentStyle={{ backgroundColor: '#172b4d', border: '1px solid #5e72e4', borderRadius: '8px', color: '#fff' }}
            itemStyle={{ color: '#fff' }}
            formatter={(value: any) => [value, 'Valor']} // Simplifica o tooltip
          />
          
          {/* Se tiver apenas 1 série de dados, a legenda é redundante, mas mantemos para consistência visual */}
          <Legend verticalAlign="top" height={36} wrapperStyle={{ top: 0 }} iconType="circle" />
          
          {y_axis?.map((key, index) => (
            <Bar 
                key={key} 
                dataKey={key} 
                fill={COLORS[index % COLORS.length]} 
                radius={[4, 4, 0, 0]}
                barSize={40}
                name={key.replace(/_/g, ' ')} // Remove underliers do nome na legenda
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // --- GRÁFICO DE LINHA ---
  if (chart_type === 'line') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 30, right: 30, left: 10, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#32325d" vertical={false} opacity={0.2} />
          
          <XAxis 
            dataKey={x_axis} 
            stroke="#8898aa" 
            tick={{ fill: '#8898aa', fontSize: 11 }} 
            axisLine={false}
            tickLine={false}
            // REMOVIDO interval={0} -> Isso resolve o problema da barra preta
            minTickGap={30} // Garante espaço mínimo entre datas
            tickFormatter={formatXAxisDate}
          />
          
          <YAxis 
            stroke="#8898aa" 
            tick={{ fill: '#8898aa', fontSize: 11 }} 
            axisLine={false}
            tickLine={false}
            tickFormatter={formatYAxisNumber}
          />
          
          <Tooltip 
            contentStyle={{ backgroundColor: '#172b4d', border: '1px solid #11cdef', borderRadius: '8px', color: '#fff' }}
            itemStyle={{ color: '#fff' }}
          />
          
          <Legend verticalAlign="top" height={36} iconType="plainline" />
          
          {y_axis?.map((key, index) => (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={COLORS[index % COLORS.length]}
              strokeWidth={3}
              dot={false} // Removemos os pontos para linhas com muitos dados (fica mais limpo)
              activeDot={{ r: 6 }}
              name={key.replace(/_/g, ' ')}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  // --- GRÁFICO DE PIZZA ---
  if (chart_type === 'pie') {
    const valueKey = y_axis && y_axis.length > 0 ? y_axis[0] : 'value';
    const nameKey = x_axis || 'name';

    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart margin={{ top: 20, right: 40, left: 40, bottom: 20 }}>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            // Reduzi o raio para dar espaço às legendas externas
            outerRadius={100} 
            innerRadius={40} // Donut chart fica mais moderno e legível
            fill="#8884d8"
            dataKey={valueKey}
            nameKey={nameKey}
            paddingAngle={2}
            minAngle={3} // Garante que fatias pequenas apareçam
            label={({ name, percent }: any) => {
                // Só mostra label se for relevante (> 1%)
                if (percent < 0.01) return null;
                return `${formatXAxisDate(name)} (${(percent * 100).toFixed(0)}%)`;
            }}
          >
            {chartData.map((_: any, index: number) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} stroke="#172b4d" strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip 
            contentStyle={{ backgroundColor: '#172b4d', border: '1px solid #fb6340', borderRadius: '8px', color: '#fff' }}
            itemStyle={{ color: '#fff' }}
          />
          <Legend verticalAlign="bottom" height={36} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return <p style={{ color: '#8898aa', padding: 20, textAlign: 'center' }}>Tipo de gráfico não suportado.</p>;
};

export default BiChart;