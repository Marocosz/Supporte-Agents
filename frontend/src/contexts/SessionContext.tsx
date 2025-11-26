import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";
import { startSession as apiStartSession } from "../services/api";
import type { ISessionContext, ISessionStartRequest } from "../types/chat.types"; // Usando 'import type'

// 1. Cria o Context com um valor padrão
// O 'undefined' é sobreposto pelo Provedor
const SessionContext = createContext<ISessionContext | undefined>(undefined);

// 2. Define o Provedor (Provider)
// Este componente irá "envolver" nosso aplicativo
export const SessionProvider = ({ children }: { children: ReactNode }) => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<ISessionContext["status"]>("idle");
  const [error, setError] = useState<string | null>(null);

  /**
   * Função pública que nossos componentes usarão para iniciar a sessão.
   */
  const startSession = async (data: ISessionStartRequest) => {
    setStatus("connecting");
    setError(null);
    try {
      // 3. Chama nosso serviço de API (api.ts)
      const response = await apiStartSession(data);
      
      // 4. Armazena o ID e atualiza o status
      setSessionId(response.session_id);
      setStatus("connected");
      // CORREÇÃO: Trocado 'logger.info' por 'console.log'
      console.log(`Sessão iniciada com sucesso: ${response.session_id}`);
    } catch (err) {
      const error = err as Error;
      // CORREÇÃO: Trocado 'logger.error' por 'console.error'
      console.error(`Falha ao iniciar sessão: ${error.message}`);
      setStatus("error");
      setError(error.message);
    }
  };

  // O valor que será compartilhado com todos os componentes "filhos"
  const value = {
    sessionId,
    status,
    error, // Também expomos o erro, caso a UI queira mostrá-lo
    startSession,
  };

  return (
    <SessionContext.Provider value={value}>
      {children}
    </SessionContext.Provider>
  );
};

// 5. Hook customizado (Helper)
// Isso nos permite acessar o contexto de forma fácil em outros arquivos
export const useSession = () => {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error("useSession deve ser usado dentro de um SessionProvider");
  }
  return context;
};