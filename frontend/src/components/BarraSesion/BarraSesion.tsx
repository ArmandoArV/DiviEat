"use client";

import Link from "next/link";
import { Avatar } from "@/components/Avatar/Avatar";
import { Badge } from "@/components/Badge/Badge";
import { colorAvatarPorRol, etiquetaRol } from "@/dominio/auth";
import { useAuth } from "@/hooks/useAuth";
import estilos from "./BarraSesion.module.css";

export function BarraSesion() {
  const { usuario, cargando, cerrarSesion } = useAuth();

  if (cargando) {
    return (
      <div className={estilos.tarjeta} aria-busy="true">
        <span className={estilos.invitadoTexto}>Verificando sesión...</span>
      </div>
    );
  }

  if (usuario) {
    return (
      <section className={`${estilos.tarjeta} ${estilos.tarjetaActiva}`}>
        <div className={estilos.identidad}>
          <Avatar
            nombre={usuario.name}
            medida={40}
            color={colorAvatarPorRol(usuario.role)}
          />
          <div className={estilos.datos}>
            <div className={estilos.nombreFila}>
              <span className={estilos.nombre}>{usuario.name}</span>
              <Badge color="exito">{etiquetaRol(usuario.role)}</Badge>
            </div>
            <span className={estilos.correo}>{usuario.email}</span>
          </div>
        </div>
        <button
          type="button"
          className={estilos.botonSalir}
          onClick={cerrarSesion}
        >
          Salir
        </button>
      </section>
    );
  }

  return (
    <section className={estilos.tarjeta}>
      <div className={estilos.invitado}>
        <span className={estilos.invitadoTexto}>¿Tienes cuenta?</span>
        <div className={estilos.ligas}>
          <Link href="/login" className={estilos.ligaPrimaria}>
            Iniciar sesión
          </Link>
          <Link href="/registro" className={estilos.ligaSecundaria}>
            Registro
          </Link>
        </div>
      </div>
    </section>
  );
}
