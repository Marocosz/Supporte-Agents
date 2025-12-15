import React, { useState } from 'react';
import { FiUser, FiCpu, FiCode, FiChevronDown, FiChevronUp } from 'react-icons/fi';
import BiChart from './BiChart';
import type { BiChatMessage as BiMessageType } from '../types/bi.types';

const BiChatMessage: React.FC<{ message: BiMessageType }> = ({ message }) => {
  const isBot = message.sender === 'bot';
  const content = message.content;
  const [showQuery, setShowQuery] = useState(false);

  // Define se a bolha é do usuário ou do bot para CSS
  const wrapperClass = `bi-message-wrapper ${message.sender}`;
  const bubbleClass = `bi-message-bubble ${message.sender}`;

  return (
    <div className={wrapperClass}>
      <div className="bi-avatar">
        {isBot ? <FiCpu size={20} color="#5e72e4" /> : <FiUser size={20} color="#fff" />}
      </div>
      
      <div className={bubbleClass}>
        {/* Renderização Condicional: Gráfico ou Texto */}
        {content.type === 'chart' ? (
            <div style={{ width: '100%', minWidth: '400px' }}>
                <BiChart data={content} />
                {/* Se tiver texto explicativo junto com o gráfico, mostra abaixo */}
                {content.content && <p style={{ marginTop: '10px', color: '#e8eaed' }}>{content.content}</p>}
            </div>
        ) : (
            <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{content.content}</p>
        )}

        {/* Rodapé da mensagem do Bot (Tempo + Query) */}
        {isBot && content.generated_sql && (
            <div style={{ marginTop: '12px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    {content.response_time && (
                        <span style={{ fontSize: '0.7rem', color: '#8898aa' }}>
                            Tempo: {content.response_time}s
                        </span>
                    )}
                    
                    <button 
                        onClick={() => setShowQuery(!showQuery)} 
                        className="bi-query-toggle"
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