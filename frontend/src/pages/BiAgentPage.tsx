import React, { useState } from 'react';
import { FiDatabase, FiMessageSquare, FiBarChart2, FiArrowLeft } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import BiDashboard from './BiDashboard'; 
import BiChat from './BiChat';           
import './BiStyles.css'; 

const BiAgentPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'chat'>('dashboard');
  const navigate = useNavigate();

  return (
    <div className="bi-module-wrapper">
      {/* Navbar Interna */}
      <nav className="bi-navbar">
        <div className="bi-navbar-brand">
          <span className="bi-nav-back" onClick={() => navigate('/')}>
             <FiArrowLeft /> Hub
          </span>
          <div style={{ width: 1, height: 24, background: '#323248', margin: '0 15px' }}></div>
          <FiDatabase size={22} color="#5e72e4" />
          <h1>Supporte BI</h1>
        </div>
        
        <div className="bi-nav-links">
          <div 
            className={`bi-nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <FiBarChart2 /> Dashboard
          </div>
          <div 
            className={`bi-nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            <FiMessageSquare /> Chatbot
          </div>
        </div>
      </nav>

      {/* Conteúdo Dinâmico */}
      <main style={{ height: 'calc(100vh - 70px)', overflow: 'hidden' }}>
        {activeTab === 'dashboard' ? <BiDashboard /> : <BiChat />}
      </main>
    </div>
  );
};

export default BiAgentPage;