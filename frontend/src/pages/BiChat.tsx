import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { FiSend, FiCpu } from 'react-icons/fi';
import BiChatMessage from '../components/BiChatMessage'; 
// Importação da função de serviço centralizada
import { sendBiMessage } from '../services/api'; 
// Importação da tipagem correta
import type { BiMessage } from '../types/bi.types';

const BiChat: React.FC = () => {
    // 1. Gera ID de sessão único ao montar o componente
    const [sessionId] = useState<string>(() => uuidv4());

    // 2. Estado inicial corrigido: Estrutura plana conforme BiMessage
    const [messages, setMessages] = useState<BiMessage[]>([
        { 
            sender: 'bot', 
            type: 'text', 
            content: 'Olá! Sou seu assistente de BI Logístico. Posso gerar gráficos e relatórios sobre suas notas, pedidos e filiais. Como posso ajudar?',
            // Campos obrigatórios da interface preenchidos com valores de inicialização
            session_id: 'init',
            query: 'init',
            response_time: '0'
        }
    ]);
    
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const endRef = useRef<HTMLDivElement>(null);

    // Scroll automático para o fim da lista
    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        // Validação básica
        if (!input.trim() || loading || !sessionId) return;

        const userText = input;
        setInput(''); // Limpa o input imediatamente
        setLoading(true);

        // 3. Cria o objeto da mensagem do usuário (Estrutura plana)
        const userMsg: BiMessage = { 
            sender: 'user', 
            type: 'text', 
            content: userText,
            session_id: sessionId,
            query: userText,
            response_time: '0'
        };
        
        // Adiciona mensagem do usuário na interface
        setMessages(prev => [...prev, userMsg]);

        try {
            // 4. Chamada ao Backend novo (Porta 8002) via serviço api.ts
            // Passamos 'admin' como role padrão, ou você pode pegar do seu contexto de autenticação
            const botResponse = await sendBiMessage(userText, sessionId, 'admin');
            
            // O serviço já retorna o objeto no formato BiMessage correto
            setMessages(prev => [...prev, botResponse]);

        } catch (error) {
            console.error("Erro no chat:", error);
            
            // Mensagem de erro visual para o usuário
            const errorMsg: BiMessage = { 
                sender: 'bot', 
                type: 'error',
                content: 'Desculpe, não consegui conectar ao servidor de dados no momento. Verifique se o backend (porta 8002) está rodando.',
                session_id: sessionId,
                query: userText,
                response_time: '0'
            };
            setMessages(prev => [...prev, errorMsg]);
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
                    <div className="bi-message-wrapper bot-wrapper">
                        <div className="bi-avatar">
                            <FiCpu size={20} />
                        </div>
                        <div className="bi-message-bubble bot-message" style={{ color: '#8898aa', fontStyle: 'italic' }}>
                            {/* Mantendo a animação de loading original */}
                            <div className="loading-dots">
                                <span style={{animationDelay: '0s'}}>•</span>
                                <span style={{animationDelay: '0.2s'}}>•</span>
                                <span style={{animationDelay: '0.4s'}}>•</span>
                            </div>
                            <span style={{ marginLeft: '10px' }}>Analisando dados...</span>
                        </div>
                    </div>
                )}
                
                <div ref={endRef} />
            </div>
            
            <div className="bi-chat-input-area">
                <form onSubmit={handleSend} className="bi-chat-form">
                    <input 
                        className="bi-chat-input"
                        placeholder="Ex: Status da nota 40908 ou Lead Time de Manaus..."
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