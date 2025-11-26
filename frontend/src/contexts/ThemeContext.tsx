import React, { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Tenta pegar do localStorage ou usa 'light' como padrão
  const [theme, setTheme] = useState<Theme>(() => {
    const savedTheme = localStorage.getItem('app-theme');
    return (savedTheme as Theme) || 'light';
  });

  useEffect(() => {
    // Salva no localStorage
    localStorage.setItem('app-theme', theme);
    // Aplica o atributo no HTML para o CSS saber o que fazer
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme deve ser usado dentro de um ThemeProvider');
  return context;
};