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
    type: 'text' | 'chart' | 'error';
    content?: string | any; // Pode ser string (texto) ou objeto (dados do gráfico)
    
    // --- Metadados Técnicos (Adicionados) ---
    title?: string;           // Título do gráfico (se houver)
    sql?: string;            // SQL gerado pelo agente
    generated_sql?: string;   // Compatibilidade legada
    query?: string;          // A pergunta original do usuário
    response_time?: string;   // Tempo formatado "0.45"
    execution_time?: number;  // Tempo float
    session_id?: string;
    
    // Propriedades de gráfico mescladas
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