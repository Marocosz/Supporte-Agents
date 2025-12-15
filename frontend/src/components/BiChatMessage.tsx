import React, { useState } from 'react';
import { FiUser, FiCpu, FiCode, FiChevronDown, FiChevronUp } from 'react-icons/fi';
import BiChart from './BiChart';
import type { BiChatMessage as BiMessageType } from '../types/bi.types';

const BiChatMessage: React.FC<{ message: BiMessageType }> = ({ message }) => {
  const isBot = message.sender === 'bot';
  const content = message.content;
  const [showQuery, setShowQuery] = useState(false);

  const wrapperClass = `bi-message-wrapper ${message.sender}`;
  const bubbleClass = `bi-message-bubble ${message.sender}`;

  return (
    <div className={wrapperClass}>
      <div className="bi-avatar">
        {isBot ? <FiCpu size={20} color="#5e72e4" /> : <FiUser size={20} color="#fff" />}
      </div>
      
      <div className={bubbleClass}>
        {/* Lógica de Renderização do Conteúdo */}
        {content.type === 'chart' ? (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
                {/* Título do Gráfico Centralizado */}
                {content.title && <span className="bi-chart-title">{content.title}</span>}
                
                {/* Container dedicado ao gráfico */}
                <div className="bi-chat-chart-container">
                    <BiChart data={content as any} />
                </div>

                {/* Texto explicativo abaixo do gráfico, se houver */}
                {content.content && (
                    <p style={{ marginTop: '10px', color: '#e8eaed', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '10px' }}>
                        {content.content}
                    </p>
                )}
            </div>
        ) : (
            // Mensagem de texto simples
            <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{content.content}</p>
        )}

        {/* Rodapé da mensagem do Bot (Tempo + Query) */}
        {isBot && content.generated_sql && (
            <div className="bi-query-section">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    {content.response_time && (
                        <span style={{ fontSize: '0.7rem', color: '#8898aa' }}>
                            Tempo: {content.response_time}s
                        </span>
                    )}
                    
                    <button 
                        onClick={() => setShowQuery(!showQuery)} 
                        className="bi-query-toggle"
                        title="Ver SQL gerado"
                    >
                        <FiCode style={{ marginRight: 4 }} /> 
                        {showQuery ? 'Ocultar Query' : 'Ver Query'} 
                        {showQuery ? <FiChevronUp style={{ marginLeft: 4 }} /> : <FiChevronDown style={{ marginLeft: 4 }} />}
                    </button>
                </div>
                
                {showQuery && (
                    <div className="bi-query-box">
                        {content.generated_sql}
                    </div>
                )}
            </div>
        )}
      </div>
    </div>
  );
};

export default BiChatMessage;