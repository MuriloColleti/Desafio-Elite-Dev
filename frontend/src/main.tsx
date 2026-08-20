import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App'
import './estilos/global.css'
import './estilos/componentes.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
