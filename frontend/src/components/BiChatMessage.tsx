import React, { useState } from 'react';
import { FiUser, FiCpu, FiCode, FiChevronDown } from 'react-icons/fi';
import BiChart from './BiChart';
import type { BiChatMessage as BiMessageType } from '../types/bi.types';

const BiChatMessage: React.FC<{ message: BiMessageType }> = ({ message }) => {
  const isBot = message.sender === 'bot';
  const content = message.content;
  
  // Controle local para mostrar/esconder SQL
  const [showQuery, setShowQuery] = useState(false);

  // Normalização de campos (compatibilidade backend novo/velho)
  const actualSql = content.sql || content.generated_sql;
  const responseTime = content.response_time;
  
  // Verifica se deve mostrar o rodapé (só se for bot e tiver tempo ou sql)
  const hasFooter = isBot && (actualSql || responseTime);

  // Classes dinâmicas baseadas no tipo (igual ao template)
  const wrapperClass = `bi-message-wrapper ${isBot ? 'bot-wrapper' : 'user-wrapper'} ${content.type === 'chart' ? 'wrapper-has-chart' : ''}`;
  const bubbleClass = `bi-message-bubble ${isBot ? 'bot-message' : 'user-message'} ${content.type === 'chart' ? 'has-chart' : ''}`;

  return (
    <div className={wrapperClass}>
      {/* Avatar (Igual ao template) */}
      <div className="bi-avatar">
        {isBot ? <FiCpu size={20} /> : <FiUser size={20} />}
      </div>
      
      {/* Balão da Mensagem */}
      <div className={bubbleClass}>
        
        {/* CONTEÚDO PRINCIPAL */}
        {content.type === 'chart' ? (
            <div className="bi-chart-content">
                {content.title && <h4 className="bi-chart-title-internal">{content.title}</h4>}
                <div className="bi-chart-container-wrapper">
                    <BiChart data={content as any} />
                </div>
                {content.content && <p className="bi-chart-description">{content.content}</p>}
            </div>
        ) : (
            <p className="bi-text-content">{content.content}</p>
        )}

        {/* RODAPÉ (Igual ao Template: Tempo + Botão Toggle) */}
        {hasFooter && (
            <div className="bi-message-footer">
                {responseTime && (
                    <div className="bi-response-time">
                        <span>Gerado em {responseTime}s</span>
                    </div>
                )}
                
                {actualSql && (
                    <button 
                        className="bi-query-toggle-btn" 
                        onClick={() => setShowQuery(!showQuery)}
                        title="Ver SQL Original"
                    >
                        <FiCode size={14} /> 
                        <span>Ver Query</span>
                        <FiChevronDown 
                            size={14} 
                            className={`bi-arrow-icon ${showQuery ? 'toggled' : ''}`} 
                        />
                    </button>
                )}
            </div>
        )}

        {/* ÁREA DO SQL (Expandível) */}
        {showQuery && actualSql && (
            <div className="bi-query-display">
                <pre><code>{actualSql}</code></pre>
            </div>
        )}
      </div>
    </div>
  );
};

export default BiChatMessage;