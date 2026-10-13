import type { Metadata } from "next";
import { Big_Shoulders, IBM_Plex_Mono, Instrument_Sans } from "next/font/google";
import "./globals.css";

// Display: condensada, de claquete e de anilha de academia. Só em títulos.
const display = Big_Shoulders({ variable: "--font-display", subsets: ["latin"] });
// Corpo e números.
const body = Instrument_Sans({ variable: "--font-body", subsets: ["latin"] });
// Metadados da captura, eixos e tabela: leitura de timecode.
const mono = IBM_Plex_Mono({ variable: "--font-mono", subsets: ["latin"], weight: ["400", "500"] });

export const metadata: Metadata = {
  title: "ContentDeck",
  description: "Métricas de conteúdo sem chute: o que os números de um perfil dizem, e o que não dizem.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
