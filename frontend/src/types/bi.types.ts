// frontend/src/types/bi.types.ts

// Tipo auxiliar para linhas do banco de dados (evita o uso de any)
export type DatabaseRow = Record<string, string | number | boolean | null>;

export interface IWsAction {
  label: string;
  value: string;
}

export interface IWsMessage {
  type: "text" | "suggestion" | "final" | "error" | "user" | "processing" | "validation"; 
  content: string;
  actions: IWsAction[];
  suggestion_id?: string; 
  file_path?: string;
  selectedActionValue?: string; 
}

export interface ISessionStartRequest {
  tipo_documento: string;
  codificacao: string;
  titulo_documento: string;
}

export interface ISessionStartResponse {
  session_id: string;
  message: string;
}

export interface ISessionContext {
  sessionId: string | null;
  status: "idle" | "connecting" | "connected" | "error";
  error: string | null;
  startSession: (data: ISessionStartRequest) => Promise<void>;
}

export type MessageType = 'text' | 'data_result' | 'chart_data' | 'error';

export interface BiMessage {
  sender: 'user' | 'bot';
  session_id: string;
  query: string;
  type: MessageType;
  content: string;
  response_time: string;
  server_execution_time?: number;

  sql?: string;
  
  // CORREÇÃO 1: Tipo forte para os dados
  data?: DatabaseRow[]; 
  
  chart_suggestion?: string; // Nome novo do backend
  
  // CORREÇÃO 2: Adicionado para compatibilidade com BiChart antigo
  chart_type?: string; 
  
  debug_info?: string;
  title?: string;
}