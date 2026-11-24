"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/Button/Button";
import { buscarOrden } from "@/dominio/orden";
import estilos from "./CodigoManual.module.css";

/**
 * La salida cuando la camara no es opcion: sin permiso, sin camara, o sencillo
 * que alguien prefiera teclear. El numero de orden viene impreso en el ticket.
 */
export function CodigoManual() {
  const router = useRouter();
  const [valor, setValor] = useState("");
  const [error, setError] = useState<string | null>(null);

  function entrar() {
    const numero = valor.trim().toUpperCase();
    if (!numero) return;
    if (!buscarOrden(numero)) {
      setError("No encontramos una orden abierta con ese número");
      return;
    }
    router.push(`/orden/${numero}`);
  }

  return (
    <form
      className={estilos.pantalla}
      onSubmit={(evento) => {
        evento.preventDefault();
        entrar();
      }}
    >
      <div className={estilos.cuerpo}>
        <h1 className={estilos.titulo}>Escribe el número de orden</h1>
        <p className={estilos.texto}>
          Viene impreso en tu ticket, o puedes pedírselo al mesero.
        </p>
        <input
          className={estilos.entrada}
          value={valor}
          onChange={(evento) => {
            setValor(evento.target.value);
            setError(null);
          }}
          placeholder="0000"
          inputMode="text"
          autoCapitalize="characters"
          autoComplete="off"
          enterKeyHint="go"
          maxLength={10}
          aria-label="Número de orden"
          aria-invalid={error !== null}
        />
        {error ? (
          <p className={estilos.error} role="alert">
            {error}
          </p>
        ) : null}
      </div>

      <div className={estilos.pie}>
        <Button type="submit" disabled={valor.trim().length === 0}>
          Ver la cuenta
        </Button>
        <Button color="blanco" type="button" onClick={() => router.push("/escanear")}>
          Mejor escanear el QR
        </Button>
      </div>
    </form>
  );
}
