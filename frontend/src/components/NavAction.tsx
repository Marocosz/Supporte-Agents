import React from 'react';
import './Navbar.css'; // Compartilha estilos com a Navbar ou podemos criar um separado

interface NavActionProps {
    icon: React.ReactNode;
    label: string; // Usado como title (tooltip) e aria-label
    onClick: () => void;
    isActive?: boolean;
    showLabel?: boolean; // Se true, mostra o texto ao lado do ícone
    variant?: 'ghost' | 'primary' | 'danger';
    disabled?: boolean;
}

const NavAction: React.FC<NavActionProps> = ({
    icon,
    label,
    onClick,
    isActive = false,
    showLabel = false,
    variant = 'ghost',
    disabled = false
}) => {
    return (
        <button
            className={`nav-action-btn ${variant} ${isActive ? 'active' : ''}`}
            onClick={onClick}
            title={label}
            aria-label={label}
            disabled={disabled}
        >
            <span className="nav-action-icon">{icon}</span>
            {showLabel && <span className="nav-action-label">{label}</span>}
        </button>
    );
};

export default NavAction;
