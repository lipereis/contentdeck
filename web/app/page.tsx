import type { Metadata } from "next";

import { HANDLE, loadDeck } from "@/lib/api";
import { headline } from "@/lib/findings";

import Dashboard from "./dashboard";

// A página espera os dados e sai inteira no HTML, sem depender de JavaScript para
// mostrar o relatório. Assim prévias de link, buscadores e abas em segundo plano
// recebem o conteúdo, não uma frase de carregamento. Custa a casca instantânea,
// que aqui não tem o que mostrar sem os números.
export const instant = false;

export async function generateMetadata(): Promise<Metadata> {
  try {
    const deck = await loadDeck(HANDLE);
    const { main, second } = headline(deck);
    const description = `@${HANDLE}: ${main} ${second}`;
    return { description, openGraph: { title: "ContentDeck", description }, twitter: { card: "summary_large_image" } };
  } catch {
    return {}; // sem API, ficam o título e a descrição padrão do layout
  }
}

export default function Page() {
  return (
    <main className="page">
      <header className="masthead">
        <span className="wordmark">ContentDeck</span>
        <span className="masthead-note">métricas de conteúdo sem chute</span>
      </header>
      <Dashboard />
    </main>
  );
}
