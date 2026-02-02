import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Importa o provedor de tema que criamos
import { ThemeProvider } from './contexts/ThemeContext';

// Importação das PÁGINAS REAIS
import ChatPage from './pages/ChatPage';       // Agente de Qualidade
import HubPage from './pages/HubPage';         // Hub Central
import DocRobosPage from './pages/DocRobosPage'; // Gerador de docs
import BiAgentPage from './pages/BiAgentPage';   // <--- NOVO: Agente de BI Logístico
import ScopeIntelPage from './pages/ScopeIntelPage'; // <--- NOVO: Dashboard Scope Intelligence
import './App.css';

function App() {
  return (
    // O ThemeProvider envolve toda a aplicação para compartilhar o estado 'light/dark'
    <ThemeProvider>
      <BrowserRouter>
        <Routes>

          {/* 1. Rota Raiz (/): Mostra o HUB com os cards de seleção */}
          <Route path="/" element={<HubPage />} />

          {/* 2. Rota Agente (/agentqualidade): Abre o Chat do Agente de Qualidade */}
          <Route path="/agentqualidade" element={<ChatPage />} />

          {/* 3. Rota Robôs (/agentdocrobos): Abre o Formulário do Gerador de Docs */}
          <Route path="/agentdocrobos" element={<DocRobosPage />} />

          {/* 4. NOVO: Rota BI (/agentbi): Abre o Supporte BI (Dashboard + Chat) */}
          <Route path="/agentbi" element={<BiAgentPage />} />

          {/* 5. NOVO: Rota Scope Intel (/scopeintel) */}
          <Route path="/scopeintel" element={<ScopeIntelPage />} />

          {/* 5. Rota Coringa (*): Se o usuário digitar url errada, volta pro Hub */}
          <Route path="*" element={<Navigate to="/" replace />} />

        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;