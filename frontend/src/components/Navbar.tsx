import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FiArrowLeft } from 'react-icons/fi';
import ThemeToggle from './ThemeToggle';
import './Navbar.css';

interface NavbarProps {
    title?: string;         // Título do módulo/página
    icon?: React.ReactNode; // Ícone opcional
    children?: React.ReactNode; // Conteúdo central
    rightContent?: React.ReactNode; // Botões extras na direita
    showThemeToggle?: boolean;
    onBack?: () => void;    // Sobrescreve comportamento padrão de voltar
    backLabel?: string;     // Texto do botão voltar
    hideBackButton?: boolean; // Se true, esconde o botão voltar
    className?: string;     // Classes extras
}

const Navbar: React.FC<NavbarProps> = ({
    title,
    icon,
    children,
    rightContent,
    showThemeToggle = true,
    onBack,
    backLabel = "Hub",
    hideBackButton = false,
    className = ""
}) => {
    const navigate = useNavigate();

    const handleBack = () => {
        if (onBack) {
            onBack();
        } else {
            navigate('/');
        }
    };

    return (
        <nav className={`shared-navbar ${className}`}>
            <div className="navbar-left">
                {!hideBackButton && (
                    <button className="navbar-back-btn" onClick={handleBack} title="Voltar">
                        <FiArrowLeft size={20} />
                        {backLabel && <span className="back-label">{backLabel}</span>}
                    </button>
                )}

                {(!hideBackButton && (title || icon)) && <div className="navbar-brand-divider"></div>}

                {icon && <div className="navbar-icon">{icon}</div>}
                {title && <h1 className="navbar-title">{title}</h1>}
            </div>

            <div className="navbar-center">
                {children}
            </div>

            <div className="navbar-right">
                {rightContent}
                {showThemeToggle && <ThemeToggle />}
            </div>
        </nav>
    );
};

export default Navbar;
