import React, { useState, useEffect, useRef } from "react";
import mermaid from "mermaid";
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import "./MermaidModal.css";

interface MermaidModalProps {
    onClose: () => void;
    theme: "light" | "dark";
}

// --- CONFIGURAÇÃO GLOBAL DO MERMAID ---
// Isso roda assim que o arquivo é importado, protegendo a aplicação inteira.

mermaid.initialize({
    startOnLoad: false, // Impede que o Mermaid tente renderizar automaticamente o chat
    securityLevel: 'loose',
    fontFamily: "sans-serif",
});

// CORREÇÃO CRÍTICA: Sobrescreve a função de erro global.
// Isso impede que o Mermaid injete aquele HTML de "Syntax Error" (bomba) no final da página
// quando encontra código incompleto no chat ou no editor.
mermaid.parseError = (err) => {
    // Apenas loga no console (silencioso), não altera o DOM visível
    console.debug("Mermaid Parse Error (Silenciado):", err);
};

const MermaidModal: React.FC<MermaidModalProps> = ({ onClose, theme }) => {
    const [code, setCode] = useState(
        `graph TD;
A[Comece aqui] --> B(Cole seu código Mermaid);
B --> C{Renderizar};
C --> D[Visualizar com Zoom];`
    );

    const [debouncedCode, setDebouncedCode] = useState(code);
    const [error, setError] = useState("");

    // Referência para o container onde o Mermaid injeta o SVG
    const svgRef = useRef<HTMLDivElement>(null);

    // --- LÓGICA UX: Evitar fechar ao arrastar para fora ---
    const mouseDownTarget = useRef<EventTarget | null>(null);

    // 1. Debounce: Aguarda usuário parar de digitar
    useEffect(() => {
        const t = setTimeout(() => setDebouncedCode(code), 400);
        return () => clearTimeout(t);
    }, [code]);

    // 2. Renderização do Mermaid
    useEffect(() => {
        // Reinicializa com o tema correto quando ele muda
        mermaid.initialize({
            startOnLoad: false,
            theme: theme === "dark" ? "dark" : "default",
            fontFamily: "sans-serif",
            securityLevel: 'loose',
        });

        const render = async () => {
            // Se a referência sumiu, não faz nada
            if (!svgRef.current) return;

            // Se o código estiver vazio, limpa o preview
            if (!debouncedCode.trim()) {
                svgRef.current.innerHTML = "";
                setError("");
                return;
            }

            try {
                // Tenta fazer o parse (validação de sintaxe)
                // Se falhar aqui, ele cai no catch e NÃO executa o render()
                // O parseError global (definido acima) impede a bomba de aparecer.
                await mermaid.parse(debouncedCode);

                // Se o parse passou, renderiza o SVG
                const id = "m-" + Math.floor(Math.random() * 999999);
                const { svg } = await mermaid.render(id, debouncedCode);

                if (svgRef.current) {
                    svgRef.current.innerHTML = svg;
                }
                setError(""); // Limpa erros anteriores
            } catch (err: any) {
                console.error("Mermaid Render Error:", err);
                
                // Define o erro no estado local para mostrar a mensagem amigável no Modal
                setError("Erro na sintaxe do código. Verifique se o padrão Mermaid está correto.");
                
                // Limpa o SVG anterior para evitar confusão visual
                if (svgRef.current) {
                    svgRef.current.innerHTML = "";
                }
            }
        };

        render();
    }, [debouncedCode, theme]);

    // --- LÓGICA UX: Handler do clique no overlay ---
    const handleOverlayClick = (e: React.MouseEvent) => {
        // Só fecha se o clique COMEÇOU e TERMINOU no overlay (fundo escuro)
        if (mouseDownTarget.current === e.currentTarget && e.target === e.currentTarget) {
            onClose();
        }
        mouseDownTarget.current = null;
    };

    return (
        <div
            className="mm-overlay"
            onMouseDown={(e) => mouseDownTarget.current = e.target}
            onClick={handleOverlayClick}
        >
            <div className="mm-content" onClick={(e) => e.stopPropagation()}>
                <div className="mm-header">
                    <h3>Renderizador Mermaid</h3>
                    <button className="mm-close" onClick={onClose}>
                        &times;
                    </button>
                </div>

                <div className="mm-body">
                    {/* COLUNA EDITOR */}
                    <div className="mm-editor">
                        <label>Código Mermaid</label>
                        <textarea
                            value={code}
                            onChange={(e) => setCode(e.target.value)}
                            spellCheck={false}
                            placeholder="Cole seu código Mermaid aqui..."
                        />
                    </div>

                    {/* COLUNA PREVIEW */}
                    <div className="mm-preview">
                        <label>Pré-visualização (Zoom e Pan habilitados)</label>

                        <div className="mm-preview-area">
                            <TransformWrapper
                                initialScale={1}
                                minScale={0.2}
                                maxScale={4}
                                centerOnInit={true}
                                limitToBounds={false}
                            >
                                <TransformComponent
                                    wrapperStyle={{ width: "100%", height: "100%" }}
                                    contentStyle={{ width: "100%", height: "100%" }}
                                >
                                    <div
                                        ref={svgRef}
                                        className="mm-svg-container"
                                        style={{
                                            width: "100%",
                                            height: "100%",
                                            display: "flex",
                                            alignItems: "center",
                                            justifyContent: "center"
                                        }}
                                    />
                                </TransformComponent>
                            </TransformWrapper>

                            {/* Exibe erro amigável se houver */}
                            {error && <div className="mm-error">{error}</div>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MermaidModal;