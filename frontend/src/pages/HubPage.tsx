import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
// 1. O hook do tema não é usado diretamente aqui, mas o Navbar usa e o Context gerencia.
import { FiArrowRight, FiCpu, FiFileText, FiBarChart2, FiActivity } from 'react-icons/fi';
import './HubPage.css';

// Configuração Modular das Aplicações
// Para adicionar um novo app, basta incluir um objeto aqui.
const APPLICATIONS = [
    {
        id: 'quality',
        title: 'Agente de Qualidade IA',
        route: '/agentqualidade',
        shortDesc: 'Analista de conformidade e docs.',
        fullDesc: 'Assistente inteligente que analisa tickets e processos para garantir conformidade técnica. Gera documentação automática, identifica desvios de padrão e fornece sugestões de correção em tempo real.',
        icon: <FiCpu size={24} />
    },
    {
        id: 'robots',
        title: 'Gerador Docs Robôs',
        route: '/agentdocrobos',
        shortDesc: 'Documentação automática RPA.',
        fullDesc: 'Ferramenta especializada para desenvolvedores RPA. Realiza a leitura automática de scripts (.py, .pas), entende a lógica de negócio e gera a documentação técnica completa e padronizada em segundos.',
        icon: <FiFileText size={24} />
    },
    {
        id: 'bi',
        title: 'Supporte BI',
        route: '/agentbi',
        shortDesc: 'Dashboard e Chat SQL.',
        fullDesc: 'Central de inteligência de dados logísticos. Permite visualizar KPIs em tempo real e, através de um Chatbot SQL avançado, permite que qualquer usuário faça perguntas complexas ao banco de dados em linguagem natural.',
        icon: <FiBarChart2 size={24} />
    },
    {
        id: 'scope',
        title: 'Scope Intelligence',
        route: '/scopeintel',
        shortDesc: 'Clustering de erros e padrões.',
        fullDesc: 'Módulo avançado de análise de tendências. Utiliza algoritmos de clustering para agrupar milhares de chamados, identificar problemas recorrentes (ofensores) e sugerir automações baseadas em volume e impacto.',
        icon: <FiActivity size={24} />
    }
];

const HubPage: React.FC = () => {
    const navigate = useNavigate();
    const [selectedAppId, setSelectedAppId] = useState<string | null>(null);

    const selectedApp = APPLICATIONS.find(app => app.id === selectedAppId);

    return (
        <div className="app-shell">
            <Navbar hideBackButton title="Central de Agentes" />

            {/* Layout Split: Esquerda (Lista) | Direita (Detalhes) */}
            <main className="app-main full-height">
                <div className="hub-split-layout">

                    {/* COLUNA ESQUERDA: Lista de Aplicações */}
                    <aside className="hub-sidebar">
                        <div className="hub-sidebar-header">
                            <h2>Aplicações Disponíveis</h2>
                            <p>Selecione um agente para ver detalhes</p>
                        </div>

                        <div className="hub-app-list">
                            {APPLICATIONS.map((app) => (
                                <button
                                    key={app.id}
                                    className={`hub-app-item ${selectedAppId === app.id ? 'active' : ''}`}
                                    onClick={() => setSelectedAppId(app.id)}
                                >
                                    <div className="hub-item-icon">{app.icon}</div>
                                    <div className="hub-item-info">
                                        <h3>{app.title}</h3>
                                        <span>{app.shortDesc}</span>
                                    </div>
                                    <FiArrowRight className="hub-arrow-icon" />
                                </button>
                            ))}
                        </div>
                    </aside>

                    {/* COLUNA DIREITA: Área de Conteúdo */}
                    <section className="hub-content-area">
                        <div className="hub-content-wrapper">
                            {selectedApp ? (
                                // CONTEÚDO DA APLICAÇÃO SELECIONADA
                                <div className="hub-detail-view animate-fade-in">
                                    <div className="hub-detail-header">
                                        <div className="hub-big-icon">{selectedApp.icon}</div>
                                        <h1>{selectedApp.title}</h1>
                                    </div>

                                    <div className="hub-detail-body">
                                        <h3>Sobre a aplicação</h3>
                                        <p>{selectedApp.fullDesc}</p>

                                        <div className="hub-detail-meta">
                                            <div className="meta-item">
                                                <strong>Status:</strong> <span className="status-online">Online</span>
                                            </div>
                                            <div className="meta-item">
                                                <strong>Versão:</strong> <span>v2.4.0</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="hub-detail-actions">
                                        <button
                                            className="hub-btn-primary"
                                            onClick={() => navigate(selectedApp.route)}
                                        >
                                            Acessar Aplicação <FiArrowRight />
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                // CONTEÚDO INSTITUCIONAL (Estado Inicial)
                                <div className="hub-welcome-view animate-fade-in">
                                    <h1>Bem-vindo à Central de Agentes</h1>
                                    <p className="welcome-subtitle">
                                        A plataforma unificada de inteligência artificial da Supporte Logística.
                                    </p>

                                    <div className="welcome-cards">
                                        <div className="welcome-card">
                                            <h3>🚀 Centralização</h3>
                                            <p>Todos os seus assistentes e ferramentas de automação reunidos em um único lugar.</p>
                                        </div>
                                        <div className="welcome-card">
                                            <h3>🤖 Inteligência Híbrida</h3>
                                            <p>De análise de tickets a geração de docs, nossos agentes utilizam IA avançada para acelerar seu trabalho.</p>
                                        </div>
                                        <div className="welcome-card">
                                            <h3>⚡ Alta Performance</h3>
                                            <p>Arquitetura modular projetada para processamento rápido e insights em tempo real.</p>
                                        </div>
                                    </div>

                                    <p className="welcome-instruction">
                                        &larr; Selecione uma aplicação ao lado para começar.
                                    </p>
                                </div>
                            )}
                        </div>
                    </section>
                </div>
            </main>
        </div>
    );
};

export default HubPage;