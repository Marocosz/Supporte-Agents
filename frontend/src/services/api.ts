import type { ISessionStartRequest, ISessionStartResponse } from "../types/chat.types";
// IMPORT NOVO: Necessário para o retorno do BI
import type { BiMessage } from "../types/bi.types";

// =============================================================================
// BACKEND 1: DOCUMENTAÇÃO / QUALIDADE (Porta 8000)
// =============================================================================

// DEBUG: Forçamos a URL aqui para garantir que não é erro de variável de ambiente.
// Se funcionar assim, sabemos que o problema era o arquivo .env
const API_URL = import.meta.env.VITE_API_QUALITY_URL || "http://localhost:8000";

console.log("------------------------------------------------");
console.log("[DEBUG API] URL Base definida (Qualidade):", API_URL);
console.log("------------------------------------------------");

/**
 * Chama o endpoint HTTP para iniciar uma nova sessão de chat.
 * @param startData Os dados iniciais (codificação, título, etc.)
 * @returns O session_id e a mensagem de boas-vindas.
 */
export const startSession = async (
  startData: ISessionStartRequest
): Promise<ISessionStartResponse> => {
  
  const fullUrl = `${API_URL}/v1/session/start`;
  console.log(`[DEBUG API] Tentando POST em: ${fullUrl}`);

  try {
    const response = await fetch(fullUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(startData),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("[DEBUG API] Erro na resposta:", errorData);
      throw new Error(errorData.detail || "Falha ao iniciar a sessão.");
    }

    const data = await response.json();
    console.log("[DEBUG API] Sucesso:", data);
    return data;

  } catch (error) {
    console.error("[DEBUG API] Erro CRÍTICO no fetch:", error);
    // Relança o erro para a UI tratar
    throw error;
  }
};

// =============================================================================
// BACKEND 2: BI / TEXT-TO-SQL (Porta 8002)
// (NOVA IMPLEMENTAÇÃO ADICIONADA ABAIXO)
// =============================================================================

const BI_API_URL = import.meta.env.VITE_API_BI_URL || "http://localhost:8002";
console.log("[DEBUG API] URL Base definida (BI):", BI_API_URL);

/**
 * Envia uma pergunta para o novo Agente de BI (Porta 8002).
 * Retorna dados estruturados (Tabela, SQL, Texto).
 */
export const sendBiMessage = async (
  question: string,
  sessionId: string | null,
  userRole: string = 'admin' // Contexto de segurança
): Promise<BiMessage> => {

  const fullUrl = `${BI_API_URL}/chat`;

  try {
    const response = await fetch(fullUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Header essencial para o Security Mock do backend novo
        "X-User-ID": userRole 
      },
      body: JSON.stringify({
        question: question,
        session_id: sessionId
      }),
    });

    if (!response.ok) {
      throw new Error(`Erro BI API: ${response.status}`);
    }

    const data = await response.json();

    // Retorna formatado para o componente BiChatMessage
    // Adicionamos sender='bot' aqui para facilitar o frontend
    return {
      ...data,
      sender: 'bot'
    };

  } catch (error) {
    console.error("[API BI ERROR]", error);
    
    // Retorna erro amigável para a UI
    const errorMsg: BiMessage = {
      sender: 'bot',
      session_id: sessionId || 'error',
      query: question,
      type: 'error',
      content: "Erro ao conectar com o servidor de BI (8002). Verifique se ele está rodando.",
      response_time: "0"
    };
    return errorMsg;
  }
};