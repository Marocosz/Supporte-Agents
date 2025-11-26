import React, { useState, useEffect, useRef } from "react";
import mermaid from "mermaid";
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import "./MermaidModal.css";

interface MermaidModalProps {
    onClose: () => void;
    theme: "light" | "dark";
}

mermaid.initialize({
    startOnLoad: false,
});

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

    // 1. Debounce
    useEffect(() => {
        const t = setTimeout(() => setDebouncedCode(code), 400);
        return () => clearTimeout(t);
    }, [code]);

    // 2. Renderização do Mermaid
    useEffect(() => {
        mermaid.initialize({
            startOnLoad: false,
            theme: theme === "dark" ? "dark" : "default",
            fontFamily: "sans-serif",
            securityLevel: 'loose',
        });

        const render = async () => {
            if (!svgRef.current) return;

            if (!debouncedCode.trim()) {
                svgRef.current.innerHTML = "";
                setError("");
                return;
            }

            try {
                const id = "m-" + Math.floor(Math.random() * 999999);
                const { svg } = await mermaid.render(id, debouncedCode);

                svgRef.current.innerHTML = svg;
                setError("");
            } catch (err: any) {
                console.error("Mermaid Error:", err);
                setError("Erro na sintaxe do código. Verifique se o padrão Mermaid está correto.");
            }
        };

        render();
    }, [debouncedCode, theme]);

    // --- LÓGICA UX: Handler do clique no overlay ---
    const handleOverlayClick = (e: React.MouseEvent) => {
        // Só fecha se o clique COMEÇOU e TERMINOU no overlay
        if (mouseDownTarget.current === e.currentTarget && e.target === e.currentTarget) {
            onClose();
        }
        mouseDownTarget.current = null;
    };

    return (
        <div
            className="mm-overlay"
            // Captura onde o clique começou
            onMouseDown={(e) => mouseDownTarget.current = e.target}
            // Usa o handler inteligente
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

                            {error && <div className="mm-error">{error}</div>}
                        </div>
                    </div>
                </div>

                {/* Footer removido */}
            </div>
        </div>
    );
};

export default MermaidModal;