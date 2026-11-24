import { notFound } from "next/navigation";
import { Cuenta } from "@/components/Cuenta/Cuenta";
import { buscarOrden } from "@/dominio/orden";

export const instant = false;

export default async function PaginaCuenta({
  params,
}: {
  params: Promise<{ numero: string }>;
}) {
  const { numero } = await params;
  const orden = buscarOrden(numero);
  if (!orden) notFound();
  return <Cuenta orden={orden} />;
}
