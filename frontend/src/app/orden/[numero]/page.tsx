import { notFound } from "next/navigation";
import { Unirse } from "@/components/Unirse/Unirse";
import { buscarOrden } from "@/dominio/orden";

// La cuenta cambia con cada pago: es dato en vivo, no algo que tenga sentido
// prerenderizar. Por eso la ruta se resuelve en cada visita.
export const instant = false;

export default async function PaginaOrden({
  params,
}: {
  params: Promise<{ numero: string }>;
}) {
  const { numero } = await params;
  const orden = buscarOrden(numero);
  // Pendiente de diseño: QR invalido y orden cerrada merecen su propia pantalla.
  if (!orden) notFound();
  return <Unirse orden={orden} />;
}
