"use client";

import Link from "next/link";
import { Button } from "@/components/Button/Button";
import type { EstadoCamara } from "@/hooks/useCamara";
import estilos from "./PermisoCamara.module.css";

/**
 * Cada motivo por el que no hay camara necesita una salida distinta. Decir
 * siempre "permite la camara" manda a buscar en los ajustes algo que, en la
 * mitad de los casos, no esta mal.
 */
const MENSAJES: Record<
  EstadoCamara,
  { titulo: string; texto: string; accion: string | null; alerta?: boolean }
> = {
  inactiva: {
    titulo: "Deja que DiviEat use tu cámara",
    texto:
      "La usamos solo para leer el QR de tu mesa o la foto de tu ticket. La imagen se procesa y se descarta: no la guardamos ni la compartimos.",
    accion: "Permitir la cámara",
  },
  pidiendo: {
    titulo: "Esperando tu permiso",
    texto: "Toca «Permitir» en el aviso que te mostró el navegador.",
    accion: null,
  },
  denegada: {
    titulo: "No tenemos acceso a tu cámara",
    texto:
      "Puedes darle permiso desde los ajustes del navegador, o entrar escribiendo el número de orden que trae tu ticket.",
    accion: "Volver a intentar",
    alerta: true,
  },
  "sin-camara": {
    titulo: "No encontramos una cámara",
    texto:
      "Este dispositivo no tiene cámara disponible. Pide al mesero el número de orden y escríbelo.",
    accion: null,
    alerta: true,
  },
  insegura: {
    titulo: "La cámara necesita una conexión segura",
    texto:
      "Los navegadores solo entregan la cámara por HTTPS. Abre la app desde https:// o desde localhost.",
    accion: null,
    alerta: true,
  },
  error: {
    titulo: "Algo salió mal con la cámara",
    texto: "Vuelve a intentarlo, o entra escribiendo el número de orden.",
    accion: "Volver a intentar",
    alerta: true,
  },
  lista: { titulo: "", texto: "", accion: null },
};

export function PermisoCamara({
  estado,
  alReintentar,
}: {
  estado: EstadoCamara;
  alReintentar: () => void;
}) {
  const { titulo, texto, accion, alerta } = MENSAJES[estado];

  return (
    <main className={estilos.pantalla}>
      <div className={estilos.centro}>
        <span className={`${estilos.icono} ${alerta ? estilos.iconoAlerta : ""}`}>
          <IconoCamara />
        </span>
        <h1 className={estilos.titulo}>{titulo}</h1>
        <p className={estilos.texto}>{texto}</p>
      </div>

      <div className={estilos.pie}>
        {accion ? <Button onClick={alReintentar}>{accion}</Button> : null}
        <p className={estilos.alterna}>
          ¿Prefieres no usar la cámara? Pide al mesero el número de orden.
        </p>
        <Link href="/codigo">
          <Button color="blanco">Escribir número de orden</Button>
        </Link>
      </div>
    </main>
  );
}

function IconoCamara() {
  return (
    <svg width="42" height="42" viewBox="0 0 42 42" aria-hidden="true">
      <rect
        x="3" y="10" width="36" height="25" rx="6"
        fill="none" stroke="currentColor" strokeWidth="3"
      />
      <path
        d="M15 10l2.5-4h7L27 10"
        fill="none" stroke="currentColor" strokeWidth="3" strokeLinejoin="round"
      />
      <circle cx="21" cy="22" r="6.5" fill="none" stroke="currentColor" strokeWidth="3" />
    </svg>
  );
}
