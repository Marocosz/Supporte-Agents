import React from 'react';
import { Link } from 'react-router-dom';
import ThemeToggle from '../components/ThemeToggle';
// 1. Importe o hook do tema
import { useTheme } from '../contexts/ThemeContext'; 
import './HubPage.css';

// 2. Importe as DUAS imagens
import logoPadrao from '../assets/supporte_logo.png';       // Para tema claro
import logoBranca from '../assets/supporte_logo_branca.png'; // Para tema escuro

const HubPage: React.FC = () => {
    // 3. Acesse o estado do tema
    const { theme } = useTheme();

    // 4. Lógica de seleção da imagem
    // Se o tema for 'light', usa a logo padrão (escura/colorida).
    // Caso contrário (dark), usa a logo branca.
    const logoSrc = theme === 'light' ? logoPadrao : logoBranca;

    return (
        <div className="hub-wrapper">
            <div className="floating-toggle-wrapper">
                <ThemeToggle /> 
            </div>
            
            <div className="hub-header">
                {/* 5. Use a variável logoSrc aqui */}
                <img 
                    src={logoSrc} 
                    alt="Supporte Logística" 
                    className="hub-main-logo" 
                />
                
                <h1>Central de Ferramentas</h1>
            </div>

            <div className="hub-grid">
                {/* Card 1 */}
                <Link to="/agentqualidade" className="hub-card quali">
                    <div className="hub-card-icon">🧠</div>
                    <h2>Agente de Qualidade IA</h2>
                    <p>Gerador de documentação, análise de conformidade e suporte via IA.</p>
                    <div className="hub-status-badge">
                        <span className="hub-status-dot"></span> Online
                    </div>
                </Link>

                {/* Card 2 */}
                <Link to="/agentdocrobos" className="hub-card robo">
                    <div className="hub-card-icon">🤖</div>
                    <h2>Gerador Docs Robôs</h2>
                    <p>Documentação automática de processos RPA.</p>
                    <div className="hub-status-badge">
                        <span className="hub-status-dot"></span> Online
                    </div>
                </Link>
            </div>
        </div>
    );
};

export default HubPage;