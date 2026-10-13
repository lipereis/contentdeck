import { Suspense } from "react";

import { HANDLE } from "@/lib/api";

import Dashboard from "./dashboard";

export default function Page() {
  return (
    <main className="page">
      <header className="masthead">
        <span className="wordmark">ContentDeck</span>
        <span className="masthead-note">métricas de conteúdo sem chute</span>
      </header>
      {/* Os números vêm frescos da API a cada pedido; o cabeçalho acima já vai na casca estática. */}
      <Suspense fallback={<p className="status">Lendo a captura mais recente de @{HANDLE}…</p>}>
        <Dashboard />
      </Suspense>
    </main>
  );
}
