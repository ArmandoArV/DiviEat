import type { ReactNode } from "react";
import { pesos, type Centavos } from "@/dominio/dinero";
import estilos from "./ItemRow.module.css";

/** Variantes del componente `Item/Row` del Figma (`3:71`). */
export type EstadoRenglon =
  | "disponible"
  | "seleccionado"
  | "pagado"
  | "apartado";

type Props = {
  nombre: string;
  meta?: string;
  importe: Centavos;
  estado?: EstadoRenglon;
  marca?: ReactNode;
  insignia?: ReactNode;
  onClick?: () => void;
};

export function ItemRow({
  nombre,
  meta,
  importe,
  estado = "disponible",
  marca,
  insignia,
  onClick,
}: Props) {
  const clases = `${estilos.renglon} ${estilos[estado]}`;
  const contenido = (
    <>
      {marca ? <span className={estilos.marca}>{marca}</span> : null}
      <span className={estilos.info}>
        <span className={estilos.nombre}>{nombre}</span>
        {meta ? <span className={estilos.meta}>{meta}</span> : null}
      </span>
      <span className={estilos.derecha}>
        <span className={estilos.precio}>{pesos(importe)}</span>
        {insignia}
      </span>
    </>
  );

  // Sin `onClick` el renglon es informativo: no debe anunciarse como boton.
  return onClick ? (
    <button type="button" className={clases} onClick={onClick}>
      {contenido}
    </button>
  ) : (
    <div className={clases}>{contenido}</div>
  );
}

export function Palomita() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path
        d="M2.5 8.5l3.5 3.5L13.5 4.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
