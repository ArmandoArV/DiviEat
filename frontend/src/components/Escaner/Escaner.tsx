"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "@/components/Button/Button";
import { ordenDelQR } from "@/dominio/qr";
import { useCamara } from "@/hooks/useCamara";
import { useLectorQR } from "@/hooks/useLectorQR";
import { PermisoCamara } from "@/components/PermisoCamara/PermisoCamara";
import estilos from "./Escaner.module.css";

type Modo = "qr" | "ticket";

export function Escaner({ modoInicial = "qr" }: { modoInicial?: Modo }) {
  const router = useRouter();
  const { videoRef, estado, pedir, detener, tieneLinterna, linterna, alternarLinterna } =
    useCamara();
  const [modo, setModo] = useState<Modo>(modoInicial);
  const [aviso, setAviso] = useState<string | null>(null);
  const [foto, setFoto] = useState<string | null>(null);
  const reintento = useRef<number | undefined>(undefined);

  useEffect(() => {
    pedir();
  }, [pedir]);

  useEffect(() => () => window.clearTimeout(reintento.current), []);

  const alLeer = useCallback(
    (texto: string) => {
      const numero = ordenDelQR(texto);
      if (numero) {
        detener();
        router.push(`/orden/${numero}`);
        return;
      }
      // Un QR legible que no es de una orden abierta: lo decimos y seguimos
      // escaneando, en vez de dejar la camara muda.
      setAviso("Ese código no corresponde a una orden abierta");
      reintento.current = window.setTimeout(() => setAviso(null), 2200);
    },
    [detener, router],
  );

  useLectorQR(videoRef, modo === "qr" && estado === "lista" && aviso === null, alLeer);

  function tomarFoto() {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const lienzo = document.createElement("canvas");
    lienzo.width = video.videoWidth;
    lienzo.height = video.videoHeight;
    lienzo.getContext("2d")?.drawImage(video, 0, 0);
    setFoto(lienzo.toDataURL("image/jpeg", 0.92));
  }

  if (estado !== "lista") {
    return <PermisoCamara estado={estado} alReintentar={pedir} />;
  }

  if (foto) {
    return (
      <div className={estilos.escaner}>
        <div className={estilos.previa}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className={estilos.previaImagen} src={foto} alt="Foto de tu ticket" />
          <div className={estilos.previaPie}>
            <Button disabled>Leer este ticket</Button>
            <Button color="blanco" onClick={() => setFoto(null)}>
              Repetir la foto
            </Button>
            <p className={estilos.previaNota}>
              La foto ya se toma bien. Falta conectar la lectura del ticket con
              el módulo de OCR; mientras tanto el camino principal es el QR.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const esQR = modo === "qr";

  return (
    <div className={estilos.escaner}>
      <video ref={videoRef} className={estilos.video} playsInline muted />
      <div className={estilos.velo} />

      <div className={estilos.capa}>
        <div className={estilos.barraSuperior}>
          <button
            type="button"
            className={estilos.iconoBtn}
            onClick={() => {
              detener();
              router.push("/");
            }}
            aria-label="Cerrar la cámara"
          >
            <Equis />
          </button>
          <span className={estilos.titulo}>
            {esQR ? "Escanea el QR de tu mesa" : "Toma foto de tu ticket"}
          </span>
          <button
            type="button"
            className={`${estilos.iconoBtn} ${linterna ? estilos.iconoActivo : ""}`}
            onClick={alternarLinterna}
            disabled={!tieneLinterna}
            aria-pressed={linterna}
            aria-label="Encender la linterna"
          >
            <Rayo />
          </button>
        </div>

        <div className={estilos.centro}>
          {esQR ? (
            <div className={estilos.visorQR}>
              <span className={`${estilos.esquina} ${estilos.ne}`} />
              <span className={`${estilos.esquina} ${estilos.no}`} />
              <span className={`${estilos.esquina} ${estilos.se}`} />
              <span className={`${estilos.esquina} ${estilos.so}`} />
              <span className={estilos.linea} />
            </div>
          ) : (
            <div className={estilos.visorTicket} />
          )}

          {aviso ? (
            <p className={estilos.aviso} role="status">
              {aviso}
            </p>
          ) : (
            <p className={`${estilos.pista} ${esQR ? "" : estilos.pistaPildora}`}>
              {esQR
                ? "Apunta al código del portamenús o al QR impreso en tu ticket"
                : "Encuadra todo el ticket, incluido el total"}
            </p>
          )}
        </div>

        <div className={estilos.barraInferior}>
          <div className={estilos.modos} role="tablist">
            {(["qr", "ticket"] as const).map((valor) => (
              <button
                key={valor}
                type="button"
                role="tab"
                aria-selected={modo === valor}
                className={`${estilos.modo} ${modo === valor ? estilos.modoActivo : ""}`}
                onClick={() => {
                  setAviso(null);
                  setModo(valor);
                }}
              >
                {valor === "qr" ? "QR de la mesa" : "Foto del ticket"}
              </button>
            ))}
          </div>

          {esQR ? (
            <button
              type="button"
              className={estilos.enlace}
              onClick={() => {
                detener();
                router.push("/codigo");
              }}
            >
              Escribir número de orden
            </button>
          ) : (
            <div className={estilos.controles}>
              <span className={estilos.iconoBtn} aria-hidden="true" />
              <button
                type="button"
                className={estilos.disparador}
                onClick={tomarFoto}
                aria-label="Tomar la foto"
              />
              <span className={estilos.iconoBtn} aria-hidden="true" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Equis() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        d="M2 2l14 14M16 2L2 16"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function Rayo() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path d="M10 1L3 10h4l-1 7 7-9H9l1-7z" fill="currentColor" />
    </svg>
  );
}
