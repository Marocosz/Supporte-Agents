import { useState, useEffect, useRef } from "react";
import { useSession } from "../contexts/SessionContext";
import type { IWsMessage } from "../types/chat.types";

// CORREÇÃO: Usar VITE_API_QUALITY_URL e fallback para porta 8000
const WS_URL_BASE = (import.meta.env.VITE_API_QUALITY_URL || "http://localhost:8000")
    .replace("http", "ws");

// Constante para o delay mínimo
const MIN_TYPING_DELAY = 1000; // 1000ms = 1 segundo

/**
 * Hook customizado para gerenciar a conexão WebSocket do chat.
 */
export const useChatSocket = () => {
    const { sessionId, status } = useSession();
    const [messages, setMessages] = useState<IWsMessage[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [isConnecting, setIsConnecting] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [isAgentResponding, setIsAgentResponding] = useState(false);

    const socketRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Só conecta se tivermos um ID e o status da sessão HTTP for "connected"
        if (sessionId && status === "connected") {

            // Impede re-conexões se o hook re-renderizar
            if (socketRef.current) return;

            setIsConnecting(true);
            setError(null);
            setMessages([]); // Limpa mensagens de sessões anteriores
            console.log(`[useChatSocket] Tentando conectar ao WebSocket: ${WS_URL_BASE}/v1/session/chat/${sessionId}`);

            const socket = new WebSocket(`${WS_URL_BASE}/v1/session/chat/${sessionId}`);
            socketRef.current = socket;

            // --- Define os "Listeners" (Ouvintes) do WebSocket ---

            socket.onopen = () => {
                console.log("[useChatSocket] Conexão WebSocket estabelecida.");
                setIsConnecting(false);
                setIsConnected(true);
                // Inicia o "digitando" para a primeira mensagem do Agente 1 (Planner)
                setIsAgentResponding(true);
            };

            socket.onclose = (event) => {
                console.log(`[useChatSocket] Conexão WebSocket fechada. Código: ${event.code}, Razão: ${event.reason}`);
                setIsConnecting(false);
                setIsConnected(false);
                setIsAgentResponding(false); // Garante que para de "digitar"
                socketRef.current = null;
                if (event.code !== 1000) {
                    setError(`Conexão perdida: ${event.reason || 'Erro desconhecido'}`);
                }
            };

            socket.onerror = (event) => {
                console.error("[useChatSocket] Erro no WebSocket:", event);
                setError("Ocorreu um erro na conexão do chat.");
                setIsConnecting(false);
                setIsConnected(false);
                setIsAgentResponding(false);
            };

            // --- INÍCIO DA MUDANÇA: Lógica de 'onmessage' (Corrigida) ---
            socket.onmessage = (event) => {
                const messageData: IWsMessage = JSON.parse(event.data);
                console.log("[useChatSocket] Mensagem recebida:", messageData);

                // Espera 1 segundo ANTES de mostrar a mensagem
                setTimeout(() => {
                    // 1. Esconde o "Digitando..." global (na barra de input)
                    setIsAgentResponding(false);

                    // 2. Atualiza a lista de mensagens
                    setMessages((prevMessages) => {
                        // Filtra (remove) todas as mensagens do tipo 'processing'
                        const filteredMessages = prevMessages.filter(
                            (msg) => msg.type !== "processing"
                        );

                        // Adiciona a nova mensagem (seja ela qual for)
                        return [...filteredMessages, messageData];
                    });

                }, MIN_TYPING_DELAY);
            };
            // --- FIM DA MUDANÇA ---

            // Função de Limpeza (quando o componente "desmonta")
            return () => {
                if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
                    console.log("[useChatSocket] Limpando e fechando conexão WS.");
                    socketRef.current.close(1000, "Componente desmontado");
                }
                socketRef.current = null;
            };
        }
    }, [sessionId, status]); // Dependências do Efeito

    /**
     * Função pública para ENVIAR uma mensagem (ou ação) para o Orquestrador
     */
    const sendMessage = (message: string) => {
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
            console.log("[useChatSocket] Enviando mensagem:", message);
            socketRef.current.send(message);

            // --- LÓGICA DE UX ATUALIZADA ---
            // Verifica se a mensagem é um clique de botão (baseado nos prefixos do Orquestrador).
            const isButtonAction =
                message.startsWith("approve_") ||    // approve_toc, approve_draft
                message.startsWith("reject_") ||     // reject_toc, reject_draft, reject_ativo
                message.startsWith("accept_") ||     // accept_ativo
                message.startsWith("skip_") ||       // skip_pergunta
                message.startsWith("generate_") ||   // generate_final_doc
                message.startsWith("final_");        // final_review

            // SÓ ativa "Digitando..." se for uma mensagem de texto (Resumo, Feedback, Resposta)
            if (!isButtonAction) {
                setIsAgentResponding(true);
            }
            // --- FIM DA LÓGICA DE UX ---

        } else {
            console.error("[useChatSocket] Não é possível enviar: WebSocket não conectado.");
            setError("Não foi possível enviar a mensagem. Conexão perdida.");
        }
    };

    // Retorna tudo o que nossa UI (Página de Chat) vai precisar
    return {
        messages,
        setMessages, // Exportado para o ChatPage.tsx (balão do usuário)
        sendMessage,
        isConnecting,
        isConnected,
        isAgentResponding, // Exportado para o ChatPage.tsx (animação de digitação)
        error,
    };
};