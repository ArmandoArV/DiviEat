import type { ButtonHTMLAttributes } from "react";
import estilos from "./Button.module.css";

/** Variantes del componente `Button` del Figma (`3:20`). */
type Color = "naranja" | "teal" | "blanco";
type Size = "l" | "m";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  color?: Color;
  size?: Size;
};

export function Button({
  color = "naranja",
  size = "l",
  className,
  children,
  ...resto
}: Props) {
  const clases = [estilos.boton, estilos[color], estilos[size], className]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={clases} {...resto}>
      <span className={estilos.cara}>{children}</span>
    </button>
  );
}
