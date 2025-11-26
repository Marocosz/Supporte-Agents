import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  
  // Define a raiz como '/' para que o Hub seja a página inicial.
  // Se tivéssemos mantido '/agentqualidade/', ele ignoraria o Hub.
  base: '/', 

  server: {
    // 'true' permite acessar pelo IP da rede (ex: testar pelo celular no wifi)
    host: true, 
    port: 5173,
    
    // Configuração opcional: Se você quisesse evitar CORS no futuro, 
    // configuraria proxies aqui. Como já configuramos CORS no Python,
    // não é necessário agora.
  }
})