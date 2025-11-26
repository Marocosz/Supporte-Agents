import type { ISessionStartRequest, ISessionStartResponse } from "../types/chat.types";

// DEBUG: Forçamos a URL aqui para garantir que não é erro de variável de ambiente.
// Se funcionar assim, sabemos que o problema era o arquivo .env
const API_URL = import.meta.env.VITE_API_QUALITY_URL || "http://localhost:8000";

console.log("------------------------------------------------");
console.log("[DEBUG API] URL Base definida:", API_URL);
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