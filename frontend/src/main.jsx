import React from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// React.StrictMode ha sido omitido intencionalmente para evitar 
// que los WebSockets se conecten/desconecten repetidamente en desarrollo.
createRoot(document.getElementById('root')).render(
  <App />
)
