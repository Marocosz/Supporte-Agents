import React from 'react';
import { Link } from 'react-router-dom';
import './HubPage.css';

const HubPage: React.FC = () => {
    return (
        <div className="hub-wrapper">
            <div className="hub-header">
                <h1>Central de Ferramentas</h1>
                <p>Selecione o sistema que deseja acessar</p>
            </div>

            <div className="hub-grid">
                {/* Card 1: Agente de Qualidade (Linka para a rota existente) */}
                <Link to="/agentqualidade" className="hub-card quali">
                    <div className="hub-card-icon">🧠</div>
                    <h2>Agente de Qualidade AI</h2>
                    <p>Gerador de documentação, análise de conformidade e suporte via IA.</p>
                    <div className="hub-status-badge">
                        <span className="hub-status-dot"></span> Online
                    </div>
                </Link>

                {/* Card 2: Doc Robos (Linka para a nova rota que faremos depois) */}
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