import { headers } from "next/headers";
import { notFound } from "next/navigation";
import QRCode from "qrcode";
import { buscarOrden } from "@/dominio/orden";
import estilos from "./page.module.css";

// El QR tiene que apuntar al host desde el que se sirve: en pruebas eso es la
// IP de la laptop en la red local, no localhost, porque quien escanea es el
// telefono. Por eso se arma en cada peticion a partir de las cabeceras.
export const instant = false;

export const metadata = { title: "QR de la orden · DiviEat" };

export default async function PaginaQR({
  params,
}: {
  params: Promise<{ numero: string }>;
}) {
  const { numero } = await params;
  const orden = buscarOrden(numero);
  if (!orden) notFound();

  const cabeceras = await headers();
  const host = cabeceras.get("host") ?? "localhost:3000";
  const protocolo = cabeceras.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const destino = `${protocolo}://${host}/orden/${orden.numero}`;

  const svg = await QRCode.toString(destino, {
    type: "svg",
    margin: 1,
    errorCorrectionLevel: "M",
    color: { dark: "#3A2E26", light: "#FFFFFF" },
  });

  return (
    <main className={estilos.hoja}>
      <div className={estilos.tarjeta}>
        <p className={estilos.marca}>DiviEat</p>
        <div className={estilos.codigo} dangerouslySetInnerHTML={{ __html: svg }} />
        <p className={estilos.mesa}>Mesa {orden.mesa}</p>
        <p className={estilos.orden}>Orden {orden.numero}</p>
        <p className={estilos.instruccion}>
          Escanea para ver la cuenta y pagar solo tu parte.
        </p>
      </div>
      <p className={estilos.destino}>{destino}</p>
    </main>
  );
}
