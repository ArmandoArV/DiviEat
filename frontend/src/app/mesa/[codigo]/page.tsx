import { notFound } from "next/navigation";
import { Unirse } from "@/components/Unirse/Unirse";
import { buscarMesa } from "@/dominio/mesa";

// La cuenta de la mesa cambia con cada pago: es dato en vivo, no algo que
// tenga sentido prerenderizar. Por eso la ruta se resuelve en cada visita.
export const instant = false;

export default async function PaginaMesa({
  params,
}: {
  params: Promise<{ codigo: string }>;
}) {
  const { codigo } = await params;
  const mesa = buscarMesa(codigo);
  // Pendiente de diseño: QR invalido y mesa cerrada merecen su propia pantalla.
  if (!mesa) notFound();
  return <Unirse mesa={mesa} />;
}
