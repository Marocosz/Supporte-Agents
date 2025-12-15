import React, { useState } from 'react';
import { FiDatabase, FiMessageSquare, FiBarChart2, FiArrowLeft, FiMoon, FiSun } from 'react-icons/fi';
import { useNavigate } from 'react-router-dom';
import BiDashboard from './BiDashboard'; 
import BiChat from './BiChat';           
import './BiStyles.css'; 

const BiAgentPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'chat'>('dashboard');
  // Estado local para controlar o ícone visualmente (assumindo que a lógica global de tema já existe no App)
  // Se você tiver um Context de tema, substitua isso pelo useTheme()
  const [isDarkMode, setIsDarkMode] = useState(true); 
  const navigate = useNavigate();

  // Função auxiliar para alternar tema (conecte com sua lógica global se houver)
  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
    document.body.classList.toggle('light-theme');
  };

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
        
        <div className="bi-nav-center">
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
        </div>

        <div className="bi-nav-actions">
            {/* Botão de Tema */}
            <button className="bi-theme-btn" onClick={toggleTheme}>
                {isDarkMode ? <FiSun size={20} /> : <FiMoon size={20} />}
            </button>
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