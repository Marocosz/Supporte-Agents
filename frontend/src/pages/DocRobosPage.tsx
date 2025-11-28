import React, { useState } from 'react';
import ThemeToggle from '../components/ThemeToggle'; // IMPORTADO AQUI
import './DocRobosPage.css';

// URL base da API do backend de Robos (definida no docker-compose ou .env)
const API_BASE_URL = import.meta.env.VITE_API_DOCS_URL || 'http://localhost:5000';

interface GeneratedResults {
    sucessos: string[];
    erros: string[];
}

// Ícone SVG para a nova área de upload
const CloudUploadIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="upload-icon">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
);

// --- NOVO: Ícone de Download para o botão ---
const DownloadIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
    </svg>
);

const DocRobosPage: React.FC = () => {
    // --- ESTADOS ---
    const [files, setFiles] = useState<FileList | null>(null);
    const [context, setContext] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState<GeneratedResults | null>(null);

    // --- HANDLERS ---
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            setFiles(e.target.files);
        }
    };

    const handleReset = () => {
        setResults(null);
        setFiles(null);
        setContext('');
        setIsLoading(false);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!files || files.length === 0) return;

        setIsLoading(true);

        const formData = new FormData();
        // Adiciona todos os arquivos selecionados
        Array.from(files).forEach((file) => {
            formData.append('arquivos', file);
        });
        // Adiciona o contexto
        formData.append('contexto', context);

        try {
            // Chamada para a API (Que iremos criar no próximo passo do backend)
            const response = await fetch(`${API_BASE_URL}/gerar`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Erro na requisição ao servidor');
            }

            const data = await response.json();
            setResults(data); // Espera receber { sucessos: [], erros: [] }

        } catch (error) {
            console.error('Erro:', error);
            // alert('Ocorreu um erro ao tentar conectar com o servidor. Verifique se o backend está rodando.');
            // Substituído por log para evitar bloqueio em ambiente Canvas
        } finally {
            setIsLoading(false);
        }
    };

    // Helper para exibir o texto de status do upload
    const getFileStatusText = () => {
        if (!files || files.length === 0) return "Clique para selecionar arquivos";
        if (files.length === 1) return `1 arquivo selecionado: ${files[0].name}`;
        return `${files.length} arquivos selecionados`;
    };

    // --- RENDERIZAÇÃO ---
    return (
        <div className="doc-robos-page">
            {/* Wrapper adicionado para posicionar no canto, resolvendo o problema de layout */}
            <div className="floating-toggle-wrapper">
                <ThemeToggle />
            </div>
            
            <div className="doc-container">
                
                {/* 1. ESTADO DE CARREGAMENTO */}
                {isLoading && (
                    <div className="loading-wrapper">
                        <h2>Gerando documentação, por favor aguarde...</h2>
                        <p>Este processo pode levar alguns segundos dependendo do tamanho dos arquivos.</p>
                        <div className="spinner"></div>
                    </div>
                )}

                {/* 2. ESTADO DE RESULTADOS (Sucesso/Erro) */}
                {!isLoading && results && (
                    <div className="results-wrapper">
                        <h1>Resultados da Geração</h1>

                        {results.sucessos.length > 0 && (
                            <>
                                <h2>Documentos Gerados com Sucesso:</h2>
                                <ul className="results-list">
                                    {results.sucessos.map((filename, index) => (
                                        <li key={index} className="result-item success">
                                            <span className="file-name-text">{filename}</span>
                                            {/* Link para endpoint de download que criaremos */}
                                            <a 
                                                href={`${API_BASE_URL}/download/${filename}`} 
                                                className="download-link"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                <DownloadIcon />
                                                Baixar Documento
                                            </a>
                                        </li>
                                    ))}
                                </ul>
                            </>
                        )}

                        {results.erros.length > 0 && (
                            <>
                                <h2>Ocorreram Erros:</h2>
                                <ul className="results-list">
                                    {results.erros.map((erro, index) => (
                                        <li key={index} className="result-item error">{erro}</li>
                                    ))}
                                </ul>
                            </>
                        )}

                        <button onClick={handleReset} className="btn-back">
                            &larr; Voltar e Gerar Nova Documentação
                        </button>
                    </div>
                )}

                {/* 3. ESTADO INICIAL (Formulário) */}
                {!isLoading && !results && (
                    <div className="form-wrapper">
                        <h1>Gerador de Documentação com IA</h1>
                        <p style={{textAlign: 'center', color: "var(--text-secondary)"}}>Supporte Agents</p>
                        
                        <form onSubmit={handleSubmit}>
                            <div className="form-group">
                                <label className="form-label" htmlFor="arquivos">
                                    Arquivos do Projeto (.py ou .pas):
                                </label>
                                
                                {/* --- NOVA ESTRUTURA DE UPLOAD (LABEL + INPUT HIDDEN) --- */}
                                <div className="file-upload-wrapper">
                                    <input 
                                            type="file" 
                                            id="arquivos" 
                                            className="hidden-input"
                                            multiple 
                                            required
                                            onChange={handleFileChange}
                                            accept=".py,.pas,.txt" 
                                    />
                                    <label 
                                            htmlFor="arquivos" 
                                            className={`custom-file-upload ${files && files.length > 0 ? 'has-files' : ''}`}
                                    >
                                            <CloudUploadIcon />
                                            <span className="upload-text">
                                                {files && files.length > 0 ? "Arquivos Prontos!" : "Clique para Escolher Arquivos"}
                                            </span>
                                            <span className="upload-hint">
                                                {getFileStatusText()}
                                            </span>
                                            {files && files.length > 0 && (
                                                <div className="file-count-badge">
                                                    {files.length} selecionado(s)
                                                </div>
                                            )}
                                    </label>
                                </div>
                                {/* --- FIM DA NOVA ESTRUTURA --- */}
                            </div>

                            <div className="form-group">
                                <label className="form-label" htmlFor="contexto">
                                    Contexto Adicional (Opcional):
                                </label>
                                <textarea 
                                    id="contexto" 
                                    className="form-textarea"
                                    placeholder="Ex: Este sistema faz parte de um projeto de ERP..."
                                    value={context}
                                    onChange={(e) => setContext(e.target.value)}
                                ></textarea>
                            </div>

                            <button type="submit" className="btn-submit">
                                Gerar Documentação
                            </button>
                            
                            <div style={{marginTop: '20px', textAlign: 'center'}}>
                                <a href="/" className="btn-back" style={{fontSize: '14px'}}>Voltar para o Hub</a>
                            </div>
                        </form>
                    </div>
                )}

            </div>
        </div>
    );
};

export default DocRobosPage;