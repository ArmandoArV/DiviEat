"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState, type FormEvent } from "react";
import { Avatar } from "@/components/Avatar/Avatar";
import { Badge } from "@/components/Badge/Badge";
import { Button } from "@/components/Button/Button";
import { Pantalla } from "@/components/Pantalla/Pantalla";
import { colorAvatarPorRol, etiquetaRol } from "@/dominio/auth";
import { useAuth } from "@/hooks/useAuth";
import estilos from "./AuthForm.module.css";

export function LoginForm() {
  const router = useRouter();
  const { usuario, autenticado, iniciarSesion, cerrarSesion } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const idEmail = useId();
  const idPassword = useId();

  const listo = email.trim().length > 0 && password.length > 0 && !enviando;

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    if (!listo) return;

    setError(null);
    setEnviando(true);
    try {
      await iniciarSesion({ email, password });
      router.push("/");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No pudimos iniciar sesión. Intenta de nuevo.",
      );
    } finally {
      setEnviando(false);
    }
  }

  if (autenticado && usuario) {
    return (
      <Pantalla
        encabezado={
          <>
            <Link href="/" className={estilos.regresar}>
              ← Inicio
            </Link>
            <span className={estilos.marca}>DiviEat</span>
          </>
        }
      >
        <h1 className={estilos.titulo}>Ya iniciaste sesión</h1>
        <p className={estilos.subtitulo}>
          Tu cuenta está activa en este dispositivo.
        </p>

        <section className={estilos.sesionActivaCard}>
          <div className={estilos.sesionActivaFila}>
            <Avatar
              nombre={usuario.name}
              medida={44}
              color={colorAvatarPorRol(usuario.role)}
            />
            <div className={estilos.sesionActivaDatos}>
              <span className={estilos.sesionActivaNombre}>{usuario.name}</span>
              <span className={estilos.sesionActivaCorreo}>{usuario.email}</span>
            </div>
            <Badge color="exito">{etiquetaRol(usuario.role)}</Badge>
          </div>

          <div className={estilos.acciones}>
            <Link href="/">
              <Button>Ir al inicio</Button>
            </Link>
            <Button color="blanco" type="button" onClick={cerrarSesion}>
              Cerrar sesión
            </Button>
          </div>
        </section>
      </Pantalla>
    );
  }

  return (
    <Pantalla
      encabezado={
        <>
          <Link href="/" className={estilos.regresar}>
            ← Inicio
          </Link>
          <span className={estilos.marca}>DiviEat</span>
        </>
      }
      barraInferior={
        <>
          <Button
            type="submit"
            form="form-login"
            disabled={!listo}
          >
            {enviando ? "Entrando..." : "Iniciar sesión"}
          </Button>
          <p className={estilos.pieCambio}>
            ¿Aún no tienes cuenta?{" "}
            <Link href="/registro" className={estilos.liga}>
              Regístrate
            </Link>
          </p>
        </>
      }
    >
      <h1 className={estilos.titulo}>Inicia sesión</h1>
      <p className={estilos.subtitulo}>
        Entra con tu correo y contraseña para usar tu perfil en DiviEat.
      </p>

      <form id="form-login" className={estilos.formulario} onSubmit={manejarEnvio}>
        {error ? (
          <div className={estilos.alertaError} role="alert">
            {error}
          </div>
        ) : null}

        <div className={estilos.campo}>
          <label className={estilos.etiqueta} htmlFor={idEmail}>
            Correo electrónico
          </label>
          <input
            id={idEmail}
            type="email"
            className={estilos.entrada}
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setError(null);
            }}
            placeholder="mariana@ejemplo.com"
            autoComplete="email"
            enterKeyHint="next"
            required
          />
        </div>

        <div className={estilos.campo}>
          <label className={estilos.etiqueta} htmlFor={idPassword}>
            Contraseña
          </label>
          <div className={estilos.entradaContrasena}>
            <input
              id={idPassword}
              type={mostrarPassword ? "text" : "password"}
              className={estilos.entrada}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError(null);
              }}
              placeholder="Tu contraseña"
              autoComplete="current-password"
              enterKeyHint="go"
              required
            />
            <button
              type="button"
              className={estilos.botonVer}
              onClick={() => setMostrarPassword((prev) => !prev)}
            >
              {mostrarPassword ? "Ocultar" : "Ver"}
            </button>
          </div>
        </div>
      </form>
    </Pantalla>
  );
}
