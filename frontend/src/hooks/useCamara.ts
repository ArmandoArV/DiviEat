"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type EstadoCamara =
  | "inactiva"
  | "pidiendo"
  | "lista"
  | "denegada"
  | "sin-camara"
  | "insegura"
  | "error";

/** `torch` no esta en los typings estandar: es una extension de los navegadores. */
type Capacidades = MediaTrackCapabilities & { torch?: boolean };

/**
 * Ciclo de vida de la camara trasera. El navegador solo entrega video en un
 * contexto seguro, asi que lo detectamos antes de pedir permiso: si no, el
 * error llega como un `NotAllowedError` indistinguible de un "no permitir" y
 * manda al usuario a buscar en los ajustes algo que no esta mal.
 */
export function useCamara() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [estado, setEstado] = useState<EstadoCamara>("inactiva");
  const [tieneLinterna, setTieneLinterna] = useState(false);
  const [linterna, setLinterna] = useState(false);

  const detener = useCallback(() => {
    streamRef.current?.getTracks().forEach((pista) => pista.stop());
    streamRef.current = null;
    setLinterna(false);
  }, []);

  const pedir = useCallback(async () => {
    if (typeof window === "undefined") return;
    if (!window.isSecureContext) {
      setEstado("insegura");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setEstado("sin-camara");
      return;
    }

    setEstado("pidiendo");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      const pista = stream.getVideoTracks()[0];
      const capacidades = pista?.getCapabilities?.() as Capacidades | undefined;
      setTieneLinterna(Boolean(capacidades?.torch));
      setEstado("lista");
    } catch (error) {
      const nombre = error instanceof DOMException ? error.name : "";
      if (nombre === "NotAllowedError" || nombre === "SecurityError") setEstado("denegada");
      else if (nombre === "NotFoundError" || nombre === "OverconstrainedError") setEstado("sin-camara");
      else setEstado("error");
    }
  }, []);

  const alternarLinterna = useCallback(async () => {
    const pista = streamRef.current?.getVideoTracks()[0];
    if (!pista) return;
    const siguiente = !linterna;
    try {
      await pista.applyConstraints({
        advanced: [{ torch: siguiente } as MediaTrackConstraintSet],
      });
      setLinterna(siguiente);
    } catch {
      setTieneLinterna(false);
    }
  }, [linterna]);

  // Soltar la camara al salir: dejarla viva mantiene el indicador encendido.
  useEffect(() => detener, [detener]);

  return { videoRef, estado, pedir, detener, tieneLinterna, linterna, alternarLinterna };
}
