import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Importação das PÁGINAS REAIS
import ChatPage from './pages/ChatPage';       // Agente de Qualidade
import HubPage from './pages/HubPage';         // Hub Central
import DocRobosPage from './pages/DocRobosPage'; // <--- AQUI: A nova página do gerador de docs
import './App.css';

function App() {
  return (
    // O BrowserRouter habilita a navegação SPA (sem recarregar a página inteira)
    <BrowserRouter>
      <Routes>
        
        {/* 1. Rota Raiz (/): Mostra o HUB com os cards de seleção */}
        <Route path="/" element={<HubPage />} />

        {/* 2. Rota Agente (/agentqualidade): Abre o Chat do Agente de Qualidade */}
        <Route path="/agentqualidade" element={<ChatPage />} />

        {/* 3. Rota Robôs (/agentdocrobos): Abre o Formulário do Gerador de Docs */}
        {/* Antes estava o DocRobosPlaceholder aqui, agora é a página real */}
        <Route path="/agentdocrobos" element={<DocRobosPage />} />

        {/* 4. Rota Coringa (*): Se o usuário digitar url errada, volta pro Hub */}
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </BrowserRouter>
  );
}

export default App;