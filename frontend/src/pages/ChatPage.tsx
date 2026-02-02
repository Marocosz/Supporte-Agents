import React, { useState, useEffect, useRef } from "react";
import { useSession } from "../contexts/SessionContext";
import { useChatSocket } from "../hooks/useChatSocket";
import type { ISessionStartRequest, IWsMessage } from "../types/chat.types";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import TextareaAutosize from 'react-textarea-autosize';

import { useTheme } from "../contexts/ThemeContext";
import Navbar from "../components/Navbar"; // Novo Import
import NavAction from "../components/NavAction";
import MermaidModal from "../components/MermaidModal";

// --- ÍCONES SVG GLOBAIS ---
const ArrowLeftIcon: React.FC = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="19" y1="12" x2="5" y2="12" />
        <polyline points="12 19 5 12 12 5" />
    </svg>
);

const BotIcon: React.FC = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 8V4H8" />
        <rect width="16" height="12" x="4" y="8" rx="2" />
        <path d="M2 14h2" />
        <path d="M20 14h2" />
        <path d="M15 13v2" />
        <path d="M9 13v2" />
    </svg>
);

const MermaidIcon: React.FC = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7" />
        <path d="M17 5.1a2 2 0 0 0-3.16.83l-3.34 6.35-3.34-6.35A2 2 0 0 0 3.96 5.1" />
    </svg>
);
// --- FIM DOS ÍCONES SVG ---

// --- FUNÇÃO DE LIMPEZA NO FRONTEND (CORREÇÃO DE TABELA E MERMAID) ---
const formatMessageContent = (content: string) => {
    if (!content) return "";

    let fixed = content;

    // 1. REMOÇÃO DE ARTEFATOS VISUAIS (Lógica de Conjunto)
    // Remove crases soltas que estejam sozinhas em uma linha (comum em erros de LLM)
    // A flag 'gm' aplica a regra para cada linha, não só inicio/fim da string total
    fixed = fixed.replace(/^\s*`\s*$/gm, "");

    // Limpeza de bordas gerais (mantida, mas ajustada)
    fixed = fixed.replace(/^[\s`]+/, "");
    fixed = fixed.replace(/[\s`]+$/, "");

    // 2. CORREÇÃO DE TABELAS ACHATADAS
    fixed = fixed.replace(/\|\s*\|\s*([-:]{3,})/g, "|\n|$1");
    fixed = fixed.replace(/\|\s*\|\s*(?=[^\|\n])/g, "|\n|");

    return fixed;
};

/**
 * Componente auxiliar para renderizar blocos de código de forma segura.
 * ATUALIZADO: Agora usa variáveis CSS para suportar temas Claro/Escuro.
 */
const SafeCodeBlock = (props: any) => {
    const { children, className, node, ...rest } = props;
    const isMermaid = /mermaid/i.test(className || '');

    if (isMermaid) {
        return (
            <div style={{
                backgroundColor: 'var(--input-bg)', // Adapta ao tema (escuro ou claro)
                color: 'var(--text-primary)',       // Adapta a cor do texto
                borderRadius: '6px',
                padding: '1rem',
                margin: '1rem 0',
                border: '1px solid var(--border-color)',
                boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                fontFamily: 'Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace'
            }}>
                <div style={{
                    borderBottom: '1px solid var(--border-color)',
                    paddingBottom: '8px',
                    marginBottom: '8px',
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <span style={{ fontWeight: 'bold' }}>MERMAID</span>
                    <span style={{ fontSize: '0.85em', opacity: 0.8 }}>(Código Fonte)</span>
                </div>
                <code {...rest} style={{
                    whiteSpace: 'pre-wrap',
                    fontSize: '0.9em',
                    display: 'block',
                    lineHeight: '1.5',
                    color: 'var(--text-primary)'
                }}>
                    {children}
                </code>
            </div>
        );
    }

    // Estilo padrão para outros códigos que não sejam mermaid (inline codes)
    return (
        <code {...rest} className={className} style={{
            background: 'var(--input-bg)',
            color: 'var(--accent-red)', // Destaque sutil para código inline
            padding: '2px 5px',
            borderRadius: '4px',
            border: '1px solid var(--border-color)',
            fontSize: '0.9em'
        }}>
            {children}
        </code>
    );
};

// --- COMPONENTES PERSONALIZADOS PARA RENDERIZAÇÃO DE MARKDOWN (TABELAS) ---
// ATUALIZADO: Agora usa variáveis CSS para suportar temas Claro/Escuro.
const MarkdownComponents = {
    code: SafeCodeBlock,
    // Força estilos de tabela para garantir visualização correta no chat
    table: (props: any) => (
        <div style={{ overflowX: 'auto', margin: '1rem 0' }}>
            <table {...props} style={{
                borderCollapse: 'collapse',
                width: '100%',
                fontSize: '0.9rem',
                color: 'var(--text-primary)' // Garante cor correta do texto
            }} />
        </div>
    ),
    thead: (props: any) => (
        <thead {...props} style={{
            backgroundColor: 'var(--input-bg)', // Fundo do cabeçalho adaptativo
            color: 'var(--text-primary)'
        }} />
    ),
    th: (props: any) => (
        <th {...props} style={{
            border: '1px solid var(--border-color)',
            padding: '10px',
            fontWeight: '600',
            textAlign: 'left',
            color: 'var(--text-primary)'
        }} />
    ),
    td: (props: any) => (
        <td {...props} style={{
            border: '1px solid var(--border-color)',
            padding: '8px',
            color: 'var(--text-primary)'
        }} />
    ),
    tr: (props: any) => <tr {...props} />
};


/**
 * Componente: O formulário para iniciar uma nova sessão.
 */
const StartSessionForm: React.FC<{ onMermaidOpen: () => void }> = ({ onMermaidOpen }) => {
    const { startSession, status, error } = useSession();

    const [formData, setFormData] = useState<ISessionStartRequest>({
        tipo_documento: "",
        codificacao: "",
        titulo_documento: "",
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        console.log("Iniciando sessão com:", formData);
        startSession(formData);
    };

    return (
        <div className="start-form">
            {/* Header removido -> Navbar Global */}

            <h2>Iniciar Novo Documento</h2>
            <form onSubmit={handleSubmit}>
                <div>
                    <label htmlFor="codificacao">Codificação</label>
                    <input
                        type="text"
                        id="codificacao"
                        name="codificacao"
                        value={formData.codificacao}
                        onChange={handleChange}
                        placeholder="Digite o código do documento..."
                        required
                    />
                </div>
                <div>
                    <label htmlFor="titulo_documento">Título do Documento</label>
                    <input
                        type="text"
                        id="titulo_documento"
                        name="titulo_documento"
                        value={formData.titulo_documento}
                        onChange={handleChange}
                        placeholder="Ex: Padrão de Acesso ao Sistema..."
                        required
                    />
                </div>
                <div>
                    <label htmlFor="tipo_documento">Tipo de Documento</label>
                    <input
                        type="text"
                        id="tipo_documento"
                        name="tipo_documento"
                        value={formData.tipo_documento}
                        onChange={handleChange}
                        placeholder="Digite o tipo do documento..."
                        required
                    />
                </div>
                <button type="submit" disabled={status === "connecting"}>
                    {status === "connecting" ? "Iniciando..." : "Iniciar Chat"}
                </button>
                {status === "error" && error && (
                    <p style={{ color: "red" }}>Erro: {error}</p>
                )}
            </form>
        </div>
    );
};


/**
 * Componente: A janela principal do chat.
 */
const ChatWindow: React.FC<{ onMermaidOpen: () => void }> = ({ onMermaidOpen }) => {
    const {
        messages,
        setMessages,
        sendMessage,
        isConnecting,
        isConnected,
        isAgentResponding,
        error
    } = useChatSocket();

    const [userMessage, setUserMessage] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const handleGoHome = () => {
        window.location.href = '/';
    };

    const isFinal = messages.length > 0 && messages[messages.length - 1].type === "final";

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isAgentResponding]);

    const handleSend = () => {
        if (userMessage.trim() && isConnected) {
            const userMsg: IWsMessage = {
                type: "user",
                content: userMessage,
                actions: [],
            };
            setMessages((prevMessages) => [...prevMessages, userMsg]);
            sendMessage(userMessage);
            setUserMessage("");
        }
    };

    const handleActionClick = (messageIndex: number, actionValue: string) => {
        sendMessage(actionValue);
        setMessages((prevMessages) =>
            prevMessages.map((msg, index) => {
                if (index === messageIndex) {
                    return { ...msg, selectedActionValue: actionValue };
                }
                return msg;
            })
        );
    };

    const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const AgentPersona: React.FC = () => (
        <div className="agent-persona">
            <div className="agent-persona-icon">DC</div>
            <div className="agent-persona-name">Assistente de Documentação</div>
        </div>
    );

    const TypingIndicator: React.FC = () => (
        <div className="typing-indicator">
            <div className="agent-persona-icon">DC</div>
            <div className="typing-indicator-bubble">
                <div className="spinner"></div>
                <span>Digitando...</span>
            </div>
        </div>
    );

    const ProcessingIndicator: React.FC<{ content: string }> = ({ content }) => (
        <div className="typing-indicator">
            <div className="agent-persona-icon">DC</div>
            <div className="typing-indicator-bubble">
                <div className="spinner"></div>
                <span>{content || "Processando..."}</span>
            </div>
        </div>
    );

    const DocumentIcon: React.FC = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <line x1="10" y1="9" x2="8" y2="9" />
        </svg>
    );

    const PlusIcon: React.FC = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
    );

    return (
        <div className="chat-window">
            {/* Header removido -> Navbar Global */}

            <div className="message-list">
                <div className="message-list-content">
                    {messages.map((msg, index) => (
                        msg.type === 'user' ? (
                            <div key={index} className="message-bubble type-user">
                                {/* CORREÇÃO: Aplica formatMessageContent e usa MarkdownComponents */}
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={MarkdownComponents}
                                >
                                    {formatMessageContent(msg.content)}
                                </ReactMarkdown>
                            </div>
                        ) : msg.type === 'processing' ? (
                            <div key={index} className="agent-message-block">
                                <ProcessingIndicator content={msg.content} />
                            </div>
                        ) : (
                            <div key={index} className="agent-message-block">
                                <AgentPersona />
                                <div className={`message-bubble type-${msg.type}`}>
                                    {/* CORREÇÃO: Aplica formatMessageContent e usa MarkdownComponents */}
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={MarkdownComponents}
                                    >
                                        {formatMessageContent(msg.content)}
                                    </ReactMarkdown>

                                    {msg.actions && msg.actions.length > 0 && (
                                        <div className="action-buttons">
                                            {msg.actions.map(action => {
                                                const isSelected = msg.selectedActionValue === action.value;
                                                const isOtherActionClicked = msg.selectedActionValue && !isSelected;
                                                let buttonClass = action.value.startsWith("reject") || action.value.startsWith("skip") ? "reject" : "";
                                                if (isOtherActionClicked) buttonClass += " inactive";

                                                return (
                                                    <button
                                                        key={action.value}
                                                        onClick={() => handleActionClick(index, action.value)}
                                                        disabled={!!msg.selectedActionValue}
                                                        className={buttonClass.trim()}
                                                    >
                                                        {action.label}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    )}
                                    {msg.type === 'final' && msg.file_path && (
                                        <a
                                            href={`${import.meta.env.VITE_API_QUALITY_URL || "http://127.0.0.1:8000"}/v1/download/${msg.file_path}`}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="download-chip"
                                        >
                                            <DocumentIcon />
                                            <span>{msg.file_path}</span>
                                        </a>
                                    )}
                                </div>
                            </div>
                        )
                    ))}

                    {isAgentResponding && (<div className="agent-message-block"><TypingIndicator /></div>)}
                    {error && (<div className="agent-message-block"><AgentPersona /><div className="message-bubble type-error"><p>{error}</p></div></div>)}
                    {isFinal && (
                        <div className="new-document-button-wrapper">
                            <button className="new-document-button" onClick={handleGoHome}>
                                <PlusIcon /><span>Criar Novo Documento</span>
                            </button>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            <div className="chat-input-wrapper">
                <div className="chat-input-content">
                    <div className="chat-input">
                        <TextareaAutosize
                            value={userMessage}
                            onChange={(e) => setUserMessage(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder={isConnected ? "Digite sua resposta aqui... (Shift+Enter para nova linha)" : (isConnecting ? "Conectando ao chat..." : "Desconectado")}
                            disabled={!isConnected}
                            maxRows={5}
                        />
                        <button onClick={handleSend} disabled={!isConnected}>Enviar</button>
                    </div>
                </div>
            </div>
        </div>
    );
};


/**
 * Página principal que decide qual componente mostrar
 */
const ChatPage: React.FC = () => {
    const { sessionId, status } = useSession();
    const { theme } = useTheme();
    const [isMermaidModalOpen, setIsMermaidModalOpen] = useState(false);

    const mermaidButton = (
        <NavAction
            icon={<MermaidIcon />}
            label="Abrir Editor Mermaid"
            onClick={() => setIsMermaidModalOpen(true)}
        />
    );

    return (
        <div className="app-shell">
            <Navbar
                title="Agente de Qualidade IA"
                rightContent={mermaidButton}
            />

            <main className="app-main full-height">
                {sessionId && status === "connected" ? (
                    <ChatWindow onMermaidOpen={() => setIsMermaidModalOpen(true)} />
                ) : (
                    <div className="start-page-layout">
                        <div className="start-page-left">
                            <div className="start-page-promo">
                                <div className="promo-design-line"></div>
                                <div className="promo-image-container"><BotIcon /></div>
                                <div className="promo-text-container">
                                    <h3>Assistente de Documentação IA</h3>
                                    <p>Bem-vindo ao assistente inteligente da Supporte Logística...</p>
                                </div>
                            </div>
                        </div>
                        <div className="vertical-divider"></div>
                        <div className="start-page-right">
                            <StartSessionForm onMermaidOpen={() => setIsMermaidModalOpen(true)} />
                        </div>
                    </div>
                )}
            </main>

            {isMermaidModalOpen && (
                <MermaidModal theme={theme} onClose={() => setIsMermaidModalOpen(false)} />
            )}
        </div>
    );
};

export default ChatPage;