"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";
import { Avatar } from "@/components/Avatar/Avatar";
import { Badge } from "@/components/Badge/Badge";
import { Button } from "@/components/Button/Button";
import { Pantalla } from "@/components/Pantalla/Pantalla";
import type { Orden } from "@/dominio/orden";
import estilos from "./Unirse.module.css";

/**
 * El campo y el boton de la barra inferior comparten estado, asi que la
 * pantalla entera vive en el cliente. Lo unico que pedimos para entrar es el
 * nombre: sin correo, sin contraseña y sin descargar nada.
 */
export function Unirse({ orden }: { orden: Orden }) {
  const router = useRouter();
  const [nombre, setNombre] = useState("");
  const id = useId();
  const listo = nombre.trim().length > 0;
  const dentro = orden.comensales.filter((c) => c.id !== "mariana");

  function entrar() {
    if (listo) router.push(`/orden/${orden.numero}/cuenta`);
  }

  return (
    <Pantalla
      barraInferior={
        <>
          <Button onClick={entrar} disabled={!listo}>
            Ver la cuenta
          </Button>
          <p className={estilos.pie}>
            No necesitas descargar nada. Tu pago se procesa con tu banco.
          </p>
        </>
      }
    >
      <p className={estilos.marca}>DiviEat</p>

      <h1 className={estilos.titulo}>Estás en la Mesa {orden.mesa}</h1>
      <p className={estilos.lugar}>
        {orden.restaurante} · {orden.direccion}
      </p>

      <section className={estilos.tarjeta}>
        <div className={estilos.tarjetaTop}>
          <div>
            <p className={estilos.estado}>Cuenta abierta</p>
            <p className={estilos.desde}>Se abrió a las {orden.abiertaDesde}</p>
          </div>
          <Badge color="exito">En vivo</Badge>
        </div>
        <div className={estilos.dentro}>
          <div className={estilos.avatares}>
            {dentro.map((comensal) => (
              <Avatar
                key={comensal.id}
                nombre={comensal.nombre}
                color={comensal.color}
              />
            ))}
          </div>
          <p className={estilos.cuantos}>
            {dentro.length} personas ya están dentro
          </p>
        </div>
      </section>

      <form
        onSubmit={(evento) => {
          evento.preventDefault();
          entrar();
        }}
      >
        <label className={estilos.etiqueta} htmlFor={id}>
          ¿Cómo te llamas?
        </label>
        <input
          id={id}
          className={estilos.entrada}
          value={nombre}
          onChange={(evento) => setNombre(evento.target.value)}
          placeholder="Tu nombre"
          autoComplete="given-name"
          enterKeyHint="go"
          maxLength={24}
        />
        <p className={estilos.ayuda}>
          Así te verán los demás en la mesa. No pedimos correo ni contraseña.
        </p>
      </form>
    </Pantalla>
  );
}
