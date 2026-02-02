import React, { useState } from 'react';
import { FiDatabase, FiMessageSquare, FiBarChart2 } from 'react-icons/fi';
// navigate removido pois Navbar lida com isso se nao tiver override
import BiDashboard from './BiDashboard';
import BiChat from './BiChat';
import Navbar from '../components/Navbar';
import './BiStyles.css';

const BiAgentPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'chat'>('dashboard');

  return (
    <div className="app-shell">
      {/* Navbar Modular */}
      <Navbar
        title="Supporte BI"
        icon={<FiDatabase size={22} color="#5e72e4" />}
      >
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
      </Navbar>

      {/* Conteúdo Dinâmico */}
      <main className="app-main full-height">
        {activeTab === 'dashboard' ? <BiDashboard /> : <BiChat />}
      </main>
    </div>
  );
};

export default BiAgentPage;