import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { FiSend } from 'react-icons/fi';
import BiChatMessage from '../components/BiChatMessage'; 
import type { BiChatMessage as BiMessageType } from '../types/bi.types';

// URL do Backend BI
const API_URL = import.meta.env.VITE_API_BI_URL || 'http://localhost:8002';

const BiChat: React.FC = () => {
    // Estado inicial com mensagem de boas-vindas
    const [messages, setMessages] = useState<BiMessageType[]>([
        { 
            sender: 'bot', 
            content: { 
                type: 'text', 
                content: 'Olá! Sou seu assistente de BI Logístico. Posso gerar gráficos e relatórios sobre suas notas, pedidos e filiais. Como posso ajudar?' 
            } 
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const endRef = useRef<HTMLDivElement>(null);

    // Gera ID de sessão ao montar
    useEffect(() => {
        setSessionId(uuidv4());
    }, []);

    // Scroll automático para o fim
    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading || !sessionId) return;

        const userText = input;
        setInput(''); // Limpa input imediatamente
        
        // Adiciona mensagem do usuário
        const userMsg: BiMessageType = { 
            sender: 'user', 
            content: { type: 'text', content: userText } 
        };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            // Prepara o histórico para o backend (contexto conversacional)
            // Mapeia as mensagens atuais para o formato { role, content }
            const historyPayload = messages.map(msg => ({
                role: msg.sender === 'user' ? 'user' : 'assistant',
                content: typeof msg.content.content === 'string' 
                    ? msg.content.content 
                    : JSON.stringify(msg.content) // Caso seja objeto complexo
            }));

            // Envia POST com question + history
            const res = await axios.post(`${API_URL}/chat`, {
                question: userText,
                session_id: sessionId,
                history: historyPayload
            });
            
            // Adiciona resposta do bot (contendo type, content, sql, response_time)
            const botMsg: BiMessageType = { sender: 'bot', content: res.data };
            setMessages(prev => [...prev, botMsg]);

        } catch (error) {
            console.error(error);
            setMessages(prev => [...prev, { 
                sender: 'bot', 
                content: { 
                    type: 'text', 
                    content: 'Desculpe, não consegui conectar ao servidor de dados no momento.' 
                } 
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bi-chat-container">
            <div className="bi-chat-window">
                {messages.map((msg, idx) => (
                    <BiChatMessage key={idx} message={msg} />
                ))}
                
                {loading && (
                    <div className="bi-message-wrapper bot">
                        <div className="bi-avatar">
                             {/* Ícone de loading ou CPU */}
                             <div className="loading-dots">
                                <span style={{animationDelay: '0s'}}>•</span>
                                <span style={{animationDelay: '0.2s'}}>•</span>
                                <span style={{animationDelay: '0.4s'}}>•</span>
                             </div>
                        </div>
                        <div className="bi-message-bubble bot" style={{ color: '#8898aa', fontStyle: 'italic' }}>
                            Analisando dados...
                        </div>
                    </div>
                )}
                
                <div ref={endRef} />
            </div>
            
            <div className="bi-chat-input-area">
                <form onSubmit={handleSend} className="bi-chat-form">
                    <input 
                        className="bi-chat-input"
                        placeholder="Ex: Gere um gráfico de pizza com o valor por filial..."
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        disabled={loading}
                    />
                    <button type="submit" className="bi-send-btn" disabled={loading || !input.trim()}>
                        <FiSend size={20} />
                    </button>
                </form>
            </div>
        </div>
    );
};

export default BiChat;