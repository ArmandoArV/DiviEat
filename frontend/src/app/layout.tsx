import type { Metadata, Viewport } from "next";
import { Nunito } from "next/font/google";
import "./globals.css";

// Nunito sustituye a una redondeada propia: Feather de Duolingo no es
// licenciable. Los pesos son los cuatro que usa el Figma.
const nunito = Nunito({
  subsets: ["latin"],
  weight: ["500", "700", "800", "900"],
  variable: "--fuente-nunito",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DiviEat",
  description:
    "Divide la cuenta y paga solo tu parte desde tu celular, sin descargar nada.",
};

export const viewport: Viewport = {
  themeColor: "#ff7a1a",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" className={nunito.variable}>
      <body>{children}</body>
    </html>
  );
}
