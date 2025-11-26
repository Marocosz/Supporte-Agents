import React, { useState, useEffect, useRef } from "react";
import { useSession } from "../contexts/SessionContext";
import { useChatSocket } from "../hooks/useChatSocket";
import type { ISessionStartRequest, IWsMessage } from "../types/chat.types";
import ReactMarkdown from 'react-markdown';
import TextareaAutosize from 'react-textarea-autosize';
// --- INÍCIO DA MUDANÇA ---
import MermaidModal from "../components/MermaidModal"; // Importa o novo modal
// --- FIM DA MUDANÇA ---

// --- ÍCONES SVG GLOBAIS (Usados por ambos) ---
const SunIcon: React.FC = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="5" />
        <line x1="12" y1="1" x2="12" y2="3" />
        <line x1="12" y1="21" x2="12" y2="23" />
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
        <line x1="1" y1="12" x2="3" y2="12" />
        <line x1="21" y1="12" x2="23" y2="12" />
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
);

const MoonIcon: React.FC = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
);

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

// --- INÍCIO DA MUDANÇA: Novo Ícone Mermaid ---
const MermaidIcon: React.FC = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7" />
        <path d="M17 5.1a2 2 0 0 0-3.16.83l-3.34 6.35-3.34-6.35A2 2 0 0 0 3.96 5.1" />
    </svg>
);
// --- FIM DA MUDANÇA ---


/**
 * Interface para as props que os filhos precisam
 */
interface ThemeProps {
    theme: "dark" | "light";
    toggleTheme: () => void;
    onMermaidOpen: () => void; // Função para abrir o modal
}

/**
 * Componente: O formulário para iniciar uma nova sessão.
 */
// Alteração pontual no componente StartSessionForm
const StartSessionForm: React.FC<ThemeProps> = ({ theme, toggleTheme, onMermaidOpen }) => {
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
            {/* --- ALTERAÇÃO AQUI: Mudamos a classe para 'start-header-actions' --- */}
            {/* Isso vai alinhar com o novo CSS (flexbox, canto superior direito) */}
            <div className="start-header-actions">
                <button className="icon-button" onClick={onMermaidOpen} title="Abrir Editor Mermaid">
                    <MermaidIcon />
                </button>
                <button className="icon-button" onClick={toggleTheme} title={theme === 'dark' ? "Mudar para Tema Claro" : "Mudar para Tema Escuro"}>
                    {theme === "dark" ? <SunIcon /> : <MoonIcon />}
                </button>
            </div>
            {/* --- FIM DA ALTERAÇÃO --- */}

            <h2>Iniciar Novo Documento</h2>
            <form onSubmit={handleSubmit}>
                {/* ... (inputs do formulário sem mudanças) ... */}
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
const ChatWindow: React.FC<ThemeProps> = ({ theme, toggleTheme, onMermaidOpen }) => {
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
        window.location.reload();
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

    // --- ÍCONES SVG (Apenas os específicos do Chat) ---
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
    // --- FIM DOS ÍCONES SVG ---

    return (
        <div className="chat-window">
            {/* --- CABEÇALHO ATUALIZADO (com botões de volta e tema) --- */}
            <div className="chat-header">
                <div className="chat-header-content">

                    <button
                        className="icon-button header-back-button"
                        onClick={handleGoHome}
                        title="Voltar ao Início"
                    >
                        <ArrowLeftIcon />
                    </button>

                    <h2>Chat de Geração de Documento</h2>

                    {/* --- INÍCIO DA MUDANÇA: Botão Mermaid adicionado --- */}
                    <div className="header-actions">
                        <button className="icon-button" onClick={onMermaidOpen} title="Abrir Editor Mermaid">
                            <MermaidIcon />
                        </button>
                        <button className="icon-button" onClick={toggleTheme} title={theme === 'dark' ? "Mudar para Tema Claro" : "Mudar para Tema Escuro"}>
                            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
                        </button>
                    </div>
                    {/* --- FIM DA MUDANÇA --- */}

                </div>
            </div>
            {/* --- FIM DO CABEÇALHO --- */}

            <div className="message-list">
                <div className="message-list-content">
                    {messages.map((msg, index) => (
                        msg.type === 'user' ? (
                            <div key={index} className="message-bubble type-user">
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </div>
                        ) : msg.type === 'processing' ? (
                            <div key={index} className="agent-message-block">
                                <ProcessingIndicator content={msg.content} />
                            </div>
                        ) : (
                            <div key={index} className="agent-message-block">
                                <AgentPersona />
                                <div className={`message-bubble type-${msg.type}`}>
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                    {msg.actions && msg.actions.length > 0 && (
                                        <div className="action-buttons">
                                            {msg.actions.map(action => {
                                                const isSelected = msg.selectedActionValue === action.value;
                                                const isOtherActionClicked = msg.selectedActionValue && !isSelected;

                                                let buttonClass = action.value.startsWith("reject") || action.value.startsWith("skip") ? "reject" : "";
                                                if (isOtherActionClicked) {
                                                    buttonClass += " inactive";
                                                }

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
                                            href={`${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}/v1/download/${msg.file_path}`}
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

                    {isAgentResponding && (
                        <div className="agent-message-block">
                            <TypingIndicator />
                        </div>
                    )}

                    {error && (
                        <div className="agent-message-block">
                            <AgentPersona />
                            <div className="message-bubble type-error">
                                <p>{error}</p>
                            </div>
                        </div>
                    )}

                    {isFinal && (
                        <div className="new-document-button-wrapper">
                            <button className="new-document-button" onClick={handleGoHome}>
                                <PlusIcon />
                                <span>Criar Novo Documento</span>
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
                            onKeyPress={handleKeyPress} // Usa a nova função
                            placeholder={isConnected ? "Digite sua resposta aqui... (Shift+Enter para nova linha)" : (isConnecting ? "Conectando ao chat..." : "Desconectado")}
                            disabled={!isConnected}
                            maxRows={5}
                        />
                        <button onClick={handleSend} disabled={!isConnected}>
                            Enviar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};


/**
 * Página principal que decide qual componente mostrar
 * (Agora controla o estado do tema)
 */
const ChatPage: React.FC = () => {
    const { sessionId, status } = useSession();

    // --- LÓGICA DE TEMA (Centralizada no Pai) ---
    const [theme, setTheme] = useState<"dark" | "light">("dark");

    // --- INÍCIO DA MUDANÇA: Estado do Modal ---
    const [isMermaidModalOpen, setIsMermaidModalOpen] = useState(false);
    // --- FIM DA MUDANÇA ---

    useEffect(() => {
        // Aplica o tema salvo no carregamento inicial
        const savedTheme = (localStorage.getItem("chatTheme") as "dark" | "light") || "dark";
        setTheme(savedTheme);
        if (savedTheme === "light") {
            document.body.classList.add("light-theme");
        } else {
            document.body.classList.remove("light-theme");
        }
    }, []); // Executa apenas uma vez no carregamento

    useEffect(() => {
        // Atualiza o body e o localStorage QUANDO o tema mudar
        if (theme === "light") {
            document.body.classList.add("light-theme");
        } else {
            document.body.classList.remove("light-theme");
        }
        localStorage.setItem("chatTheme", theme);
    }, [theme]); // Executa sempre que 'theme' mudar

    const toggleTheme = () => {
        setTheme(theme === "dark" ? "light" : "dark");
    };
    // --- FIM DA LÓGICA DE TEMA ---

    return (
        <>
            {/* Lógica de renderização existente */}
            {sessionId && status === "connected" ? (
                // Passa o tema e a função para o ChatWindow
                <ChatWindow
                    theme={theme}
                    toggleTheme={toggleTheme}
                    onMermaidOpen={() => setIsMermaidModalOpen(true)} // Passa a função
                />
            ) : (
                // --- NOVO LAYOUT DA PÁGINA INICIAL ---
                <div className="start-page-layout">

                    <div className="start-page-left">
                        <div className="start-page-promo">
                            <div className="promo-design-line"></div>
                            <div className="promo-image-container">
                                <BotIcon />
                            </div>
                            <div className="promo-text-container">
                                <h3>Assistente de Documentação IA</h3>
                                <p>
                                    Bem-vindo ao assistente inteligente da Supporte Logística.
                                    Descreva o documento que você precisa, e nossos agentes de IA
                                    irão planear, escrever e formatar um rascunho para si.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="vertical-divider"></div>

                    <div className="start-page-right">
                        {/* Passa o tema e a função para o StartSessionForm */}
                        <StartSessionForm
                            theme={theme}
                            toggleTheme={toggleTheme}
                            onMermaidOpen={() => setIsMermaidModalOpen(true)} // Passa a função
                        />
                    </div>

                </div>
                // --- FIM DO NOVO LAYOUT ---
            )}

            {/* --- INÍCIO DA MUDANÇA: Renderiza o Modal globalmente --- */}
            {isMermaidModalOpen && (
                <MermaidModal
                    theme={theme}
                    onClose={() => setIsMermaidModalOpen(false)}
                />
            )}
            {/* --- FIM DA MUDANÇA --- */}
        </>
    );
};

export default ChatPage;