import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Interfaz pendiente: la fase de diseño está detenida hasta disponer de la
// skill anti-ai-design (ver docs/FASE-0.md). La capa de datos ya funciona.
function App() {
  return (
    <main>
      <h1>C1 Companion</h1>
      <p>Interfaz pendiente de diseño.</p>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
