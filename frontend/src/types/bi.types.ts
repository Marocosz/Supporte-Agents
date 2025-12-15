// src/types/bi.types.ts

export interface BiChartData {
    title: string;
    chart_type: 'bar' | 'line' | 'pie';
    data: any[];
    x_axis?: string;
    y_axis?: string[];
    y_axis_label?: string;
}

export interface BiApiResponse {
    type: 'text' | 'chart';
    content?: string;
    title?: string; // Para gráficos
    generated_sql?: string;
    response_time?: string;
    session_id?: string;
    // Propriedades de gráfico mescladas aqui para facilitar
    chart_type?: 'bar' | 'line' | 'pie';
    data?: any[];
    x_axis?: string;
    y_axis?: string[];
    y_axis_label?: string;
}

export interface BiChatMessage {
    sender: 'user' | 'bot';
    content: BiApiResponse;
}