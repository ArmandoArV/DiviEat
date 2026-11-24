import estilos from "./Badge.module.css";

/** Variantes del componente `Badge` del Figma (`3:31`). */
export type ColorBadge = "exito" | "info" | "neutro" | "alerta" | "error";

export function Badge({
  color = "neutro",
  children,
}: {
  color?: ColorBadge;
  children: React.ReactNode;
}) {
  return (
    <span className={`${estilos.badge} ${estilos[color]}`}>{children}</span>
  );
}
