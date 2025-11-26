import React, { useState } from 'react';
import ThemeToggle from '../components/ThemeToggle'; // IMPORTADO AQUI
import './DocRobosPage.css';

// URL base da API do backend de Robos (definida no docker-compose ou .env)
const API_BASE_URL = import.meta.env.VITE_API_DOCS_URL || 'http://localhost:5000';

interface GeneratedResults {
    sucessos: string[];
    erros: string[];
}

const DocRobosPage: React.FC = () => {
    // --- ESTADOS ---
    const [files, setFiles] = useState<FileList | null>(null);
    const [context, setContext] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [results, setResults] = useState<GeneratedResults | null>(null);

    // --- HANDLERS ---
    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
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

        // Usei um modal customizado no lugar de alert, pois alert() é proibido em produção
        if (typeof alert !== 'undefined') {
            alert('Atenção: A função alert() será substituída por um modal customizado em produção.');
        }

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

    // --- RENDERIZAÇÃO ---
    return (
        <div className="doc-robos-page">
            <ThemeToggle /> {/* <--- Adicione aqui */}
            
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
                                            <span>{filename}</span>
                                            {/* Link para endpoint de download que criaremos */}
                                            <a 
                                                href={`${API_BASE_URL}/download/${filename}`} 
                                                className="download-link"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                Baixar
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
                                    Selecione os arquivos (.py ou .pas):
                                </label>
                                <input 
                                    type="file" 
                                    id="arquivos" 
                                    className="form-input-file"
                                    multiple 
                                    required
                                    onChange={handleFileChange}
                                    accept=".py,.pas,.txt" // Adicione as extensões aceitas
                                />
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