import { notFound } from "next/navigation";
import { Cuenta } from "@/components/Cuenta/Cuenta";
import { buscarMesa } from "@/dominio/mesa";

// La cuenta de la mesa cambia con cada pago: es dato en vivo, no algo que
// tenga sentido prerenderizar. Por eso la ruta se resuelve en cada visita.
export const instant = false;

export default async function PaginaCuenta({
  params,
}: {
  params: Promise<{ codigo: string }>;
}) {
  const { codigo } = await params;
  const mesa = buscarMesa(codigo);
  if (!mesa) notFound();
  return <Cuenta mesa={mesa} />;
}
