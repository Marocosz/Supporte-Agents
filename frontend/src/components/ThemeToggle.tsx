import React from 'react';
import { useTheme } from '../contexts/ThemeContext';

const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        background: 'transparent',
        border: '1px solid var(--border-color)',
        borderRadius: '50%',
        width: '40px',
        height: '40px',
        cursor: 'pointer',
        fontSize: '1.2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--text-primary)',
        transition: 'all 0.3s ease',
        zIndex: 1000
      }}
      title={`Mudar para tema ${theme === 'light' ? 'Escuro' : 'Claro'}`}
    >
      {theme === 'light' ? '🌙' : '☀️'}
    </button>
  );
};

export default ThemeToggle;