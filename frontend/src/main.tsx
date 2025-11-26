import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

import { SessionProvider } from './contexts/SessionContext.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  // <React.StrictMode> FOI REMOVIDO DAQUI
  <SessionProvider>
    <App />
  </SessionProvider>
  // </React.StrictMode> FOI REMOVIDO DAQUI
)