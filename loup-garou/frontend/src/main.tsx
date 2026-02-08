import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

try {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
} catch (error) {
  // Afficher l'erreur visuellement si React crash
  const root = document.getElementById('root')!
  root.style.cssText = 'padding:2rem;color:#ff6b6b;font-family:monospace;white-space:pre-wrap'
  root.textContent = `Erreur au démarrage:\n${error}`
  console.error('React render failed:', error)
}
