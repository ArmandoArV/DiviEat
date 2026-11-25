import Link from "next/link";
import { BarraSesion } from "@/components/BarraSesion/BarraSesion";
import { Button } from "@/components/Button/Button";
import { ORDEN_DEMO } from "@/dominio/orden";
import estilos from "./page.module.css";

export default function Inicio() {
  return (
    <main className={estilos.entrada}>
      <BarraSesion />
      <p className={estilos.marca}>DiviEat</p>
      <h1 className={estilos.titulo}>Divide la cuenta sin pelearte</h1>
      <p className={estilos.texto}>
        Escanea el QR de tu mesa, elige lo que consumiste y paga solo tu parte
        con CoDi. Inicia sesión o entra directo a tu mesa.
      </p>

      <div className={estilos.boton}>
        <Link href="/escanear">
          <Button>Escanear el QR de mi mesa</Button>
        </Link>
      </div>
      <div className={estilos.boton}>
        <Link href={`/orden/${ORDEN_DEMO.numero}`}>
          <Button color="blanco">Entrar sin escanear (demo)</Button>
        </Link>
      </div>

      <p className={estilos.nota}>
        Para probar el escáner, abre{" "}
        <Link href={`/orden/${ORDEN_DEMO.numero}/qr`} className={estilos.liga}>
          el QR de la orden {ORDEN_DEMO.numero}
        </Link>{" "}
        en otra pantalla y apúntale con el teléfono.
      </p>
    </main>
  );
}
