import type { ReactNode } from "react";
import estilos from "./Pantalla.module.css";

export function Pantalla({
  encabezado,
  children,
  barraInferior,
}: {
  encabezado?: ReactNode;
  children: ReactNode;
  barraInferior?: ReactNode;
}) {
  return (
    <main className={estilos.marco}>
      {encabezado ? <header className={estilos.encabezado}>{encabezado}</header> : null}
      <div className={estilos.cuerpo}>{children}</div>
      {barraInferior ? (
        <footer className={estilos.barraInferior}>{barraInferior}</footer>
      ) : null}
    </main>
  );
}

export function TituloPantalla({ children }: { children: ReactNode }) {
  return <h1 className={estilos.titulo}>{children}</h1>;
}
