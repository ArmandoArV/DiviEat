import Link from "next/link";
import { Button } from "@/components/Button/Button";
import { MESA_7 } from "@/dominio/mesa";
import estilos from "./page.module.css";

export default function Inicio() {
  return (
    <main className={estilos.entrada}>
      <p className={estilos.marca}>DiviEat</p>
      <h1 className={estilos.titulo}>Divide la cuenta sin pelearte</h1>
      <p className={estilos.texto}>
        Escanea el QR de tu mesa, elige lo que consumiste y paga solo tu parte
        con CoDi. Sin descargar nada y sin registro.
      </p>

      <div className={estilos.boton}>
        <Link href={`/mesa/${MESA_7.codigo}`}>
          <Button>Entrar a la Mesa {MESA_7.numero}</Button>
        </Link>
      </div>

      <p className={estilos.nota}>
        Atajo de demo: las pantallas de cámara y de lectura del ticket son el
        camino B y todavía no están construidas, así que esto entra directo a la
        mesa como si ya hubieras escaneado el QR.
      </p>
    </main>
  );
}
