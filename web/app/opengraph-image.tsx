import { ImageResponse } from "next/og";

import { HANDLE, loadDeck } from "@/lib/api";
import { headline } from "@/lib/findings";
import { int, longDate } from "@/lib/format";

// Cartão de prévia do link (LinkedIn, WhatsApp): a tese do perfil, com as cores do painel.
export const alt = "ContentDeck: o post típico do perfil e o peso do maior post";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  let main = "Métricas de conteúdo sem chute.";
  let second = "";
  let footer = `@${HANDLE}`;
  try {
    const deck = await loadDeck(HANDLE);
    ({ main, second } = headline(deck));
    const { summary } = deck;
    footer = `@${HANDLE} · ${int(summary.posts)} posts · captura de ${summary.captured_on ? longDate(summary.captured_on) : "—"}`;
  } catch {
    // sem API, o cartão sai genérico em vez de falhar
  }

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between",
          background: "#0e1116", color: "#f3f5f8", padding: "56px 64px", fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 30 }}>
          <div style={{ fontWeight: 800, letterSpacing: 3 }}>CONTENTDECK</div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
            {[38, 22, 26, 96, 20, 30, 24].map((h, i) => (
              <div key={i} style={{ width: 18, height: h, borderRadius: "4px 4px 0 0", background: h > 60 ? "#d95926" : "#9085e9" }} />
            ))}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", fontSize: 92, fontWeight: 800, lineHeight: 1.02, textTransform: "uppercase" }}>
          <div>{main}</div>
          <div style={{ color: "#8a93a2" }}>{second}</div>
        </div>
        <div style={{ fontSize: 28, color: "#b6bdc9" }}>{footer}</div>
      </div>
    ),
    size,
  );
}
