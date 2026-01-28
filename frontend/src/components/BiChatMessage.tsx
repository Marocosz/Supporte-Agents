// frontend/src/components/BiChatMessage.tsx
import React, { useState } from 'react';
import { FiUser, FiCpu, FiCode, FiChevronDown } from 'react-icons/fi';
import ReactMarkdown from 'react-markdown';
import BiChart from './BiChart';
import { TrackingTable } from './TrackingTable';
import type { BiMessage } from '../types/bi.types';

const BiChatMessage: React.FC<{ message: BiMessage }> = ({ message }) => {
  const isBot = message.sender === 'bot';
  const [showQuery, setShowQuery] = useState(false);

  const actualSql = message.sql; 
  const responseTime = message.response_time;
  const executionTime = message.server_execution_time;
  
  const hasFooter = isBot && (actualSql || responseTime);
  const hasChart = message.type === 'chart_data';

  const wrapperClass = `bi-message-wrapper ${isBot ? 'bot-wrapper' : 'user-wrapper'} ${hasChart ? 'wrapper-has-chart' : ''}`;
  const bubbleClass = `bi-message-bubble ${isBot ? 'bot-message' : 'user-message'} ${hasChart ? 'has-chart' : ''}`;

  return (
    <div className={wrapperClass}>
      <div className="bi-avatar">
        {isBot ? <FiCpu size={20} /> : <FiUser size={20} />}
      </div>
      
      <div className={bubbleClass}>
        
        {/* --- GRÁFICO --- */}
        {message.type === 'chart_data' ? (
            <div className="bi-chart-content">
                {message.title && <h4 className="bi-chart-title-internal">{message.title}</h4>}
                <div className="bi-chart-container-wrapper">
                    {/* CORREÇÃO:
                        1. Espalhamos ...message para passar os dados.
                        2. Sobrescrevemos chart_type forçando o tipo literal "bar" | "line" | "pie" 
                           para satisfazer a interface estrita do BiChart.
                        3. Garantimos que data é sempre um array, não undefined.
                    */}
                    <BiChart data={{
                        ...message,
                        data: message.data || [],
                        chart_type: (message.chart_suggestion || message.chart_type || 'bar') as "bar" | "line" | "pie"
                    }} /> 
                </div>
                {message.content && <p className="bi-chart-description">{message.content}</p>}
            </div>
        ) : (
            // --- TEXTO E TABELA ---
            <div className="bi-content-body">
                <div className="bi-text-content prose prose-sm max-w-none text-gray-800">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>

                {message.type === 'data_result' && message.data && (
                    <div className="bi-data-table-container mt-4">
                        <TrackingTable data={message.data} />
                    </div>
                )}
            </div>
        )}

        {/* --- RODAPÉ --- */}
        {hasFooter && (
            <div className="bi-message-footer">
                <div className="bi-response-info">
                   {responseTime && <span>Total: {responseTime}s</span>}
                   {executionTime && <span className="ml-2 text-xs opacity-70">(Server: {executionTime}s)</span>}
                </div>
                
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

        {showQuery && actualSql && (
            <div className="bi-query-display">
                <pre className="language-sql"><code>{actualSql}</code></pre>
            </div>
        )}
      </div>
    </div>
  );
};

export default BiChatMessage;