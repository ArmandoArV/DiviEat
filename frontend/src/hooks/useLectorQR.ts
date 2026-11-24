"use client";

import jsQR from "jsqr";
import { useEffect, useRef } from "react";

/**
 * `BarcodeDetector` es nativo y mucho mas rapido, pero Safari no lo trae — y
 * medio Mexico escanea desde un iPhone. Por eso hay respaldo en JS: se intenta
 * el nativo y, si no existe, jsQR sobre el canvas.
 */
type DetectorNativo = {
  detect(fuente: CanvasImageSource): Promise<{ rawValue: string }[]>;
};
type ConstructorDetector = new (opciones: { formats: string[] }) => DetectorNativo;

const MS_ENTRE_INTENTOS = 160;

function crearDetectorNativo(): DetectorNativo | null {
  const Detector = (globalThis as { BarcodeDetector?: ConstructorDetector })
    .BarcodeDetector;
  if (!Detector) return null;
  try {
    return new Detector({ formats: ["qr_code"] });
  } catch {
    return null;
  }
}

export function useLectorQR(
  videoRef: React.RefObject<HTMLVideoElement | null>,
  activo: boolean,
  alLeer: (texto: string) => void,
) {
  // El callback cambia en cada render; guardarlo en una ref evita reiniciar
  // el bucle de escaneo cada vez. La asignacion va en un efecto, no en el
  // render: mutar una ref mientras se renderiza rompe la pureza del render.
  const alLeerRef = useRef(alLeer);
  useEffect(() => {
    alLeerRef.current = alLeer;
  }, [alLeer]);

  useEffect(() => {
    if (!activo) return;

    const video = videoRef.current;
    if (!video) return;

    const lienzo = document.createElement("canvas");
    const pincel = lienzo.getContext("2d", { willReadFrequently: true });
    const nativo = crearDetectorNativo();
    let vivo = true;
    let temporizador: number | undefined;

    async function intentar() {
      if (!vivo || !video || !pincel) return;

      if (video.readyState >= video.HAVE_CURRENT_DATA && video.videoWidth > 0) {
        let texto: string | null = null;

        if (nativo) {
          try {
            const encontrados = await nativo.detect(video);
            texto = encontrados[0]?.rawValue ?? null;
          } catch {
            // un fallo puntual del detector no debe matar el bucle
          }
        } else {
          lienzo.width = video.videoWidth;
          lienzo.height = video.videoHeight;
          pincel.drawImage(video, 0, 0, lienzo.width, lienzo.height);
          const pixeles = pincel.getImageData(0, 0, lienzo.width, lienzo.height);
          texto =
            jsQR(pixeles.data, pixeles.width, pixeles.height, {
              inversionAttempts: "dontInvert",
            })?.data ?? null;
        }

        if (texto && vivo) {
          alLeerRef.current(texto);
          return; // quien escucha decide si seguimos; no insistimos solos
        }
      }

      if (vivo) temporizador = window.setTimeout(intentar, MS_ENTRE_INTENTOS);
    }

    intentar();

    return () => {
      vivo = false;
      if (temporizador) window.clearTimeout(temporizador);
    };
  }, [activo, videoRef]);
}
