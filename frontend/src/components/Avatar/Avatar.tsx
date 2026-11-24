import estilos from "./Avatar.module.css";

/**
 * `Avatar` del Figma (`3:32`): la inicial es la propiedad y el relleno se
 * sobreescribe por instancia, asi que el color entra como prop, no como
 * variante.
 */
const PALETA = [
  "var(--color-primary-base)",
  "var(--color-teal-base)",
  "var(--color-rose-base)",
  "var(--color-sunset-base)",
  "var(--color-amber-base)",
];

/** Color estable a partir del nombre: la misma persona siempre se ve igual. */
export function colorDe(nombre: string): string {
  let suma = 0;
  for (const letra of nombre) suma += letra.codePointAt(0) ?? 0;
  return PALETA[suma % PALETA.length];
}

export function Avatar({
  nombre,
  medida = 34,
  color,
}: {
  nombre: string;
  medida?: number;
  color?: string;
}) {
  return (
    <span
      className={estilos.avatar}
      style={
        {
          "--medida": `${medida}px`,
          "--fondo": color ?? colorDe(nombre),
        } as React.CSSProperties
      }
      aria-hidden="true"
    >
      {nombre.charAt(0).toUpperCase()}
    </span>
  );
}
