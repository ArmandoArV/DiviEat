"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState, type FormEvent } from "react";
import { Avatar } from "@/components/Avatar/Avatar";
import { Badge } from "@/components/Badge/Badge";
import { Button } from "@/components/Button/Button";
import { Pantalla } from "@/components/Pantalla/Pantalla";
import {
  colorAvatarPorRol,
  etiquetaRol,
  MIN_LONGITUD_PASSWORD,
  ROLES_USUARIO,
  type RolUsuario,
} from "@/dominio/auth";
import { useAuth } from "@/hooks/useAuth";
import estilos from "./AuthForm.module.css";

export function RegistroForm() {
  const router = useRouter();
  const { usuario, autenticado, registrar, cerrarSesion } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<RolUsuario>("comensal");
  const [password, setPassword] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const idNombre = useId();
  const idEmail = useId();
  const idPassword = useId();
  const idConfirmar = useId();

  const rolActual = ROLES_USUARIO.find((r) => r.valor === role);
  const listo =
    name.trim().length > 0 &&
    email.trim().length > 0 &&
    password.length >= MIN_LONGITUD_PASSWORD &&
    confirmar.length > 0 &&
    !enviando;

  async function manejarEnvio(evento: FormEvent) {
    evento.preventDefault();
    if (enviando) return;

    if (name.trim().length === 0) {
      setError("Escribe tu nombre para continuar.");
      return;
    }
    if (password.length < MIN_LONGITUD_PASSWORD) {
      setError(`La contraseña debe tener al menos ${MIN_LONGITUD_PASSWORD} caracteres.`);
      return;
    }
    if (password !== confirmar) {
      setError("Las contraseñas no coinciden.");
      return;
    }

    setError(null);
    setEnviando(true);
    try {
      await registrar({ name, email, role, password });
      router.push("/");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "No pudimos crear tu cuenta. Intenta de nuevo.",
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
        <h1 className={estilos.titulo}>Ya tienes sesión activa</h1>
        <p className={estilos.subtitulo}>
          Cierra tu sesión actual si deseas registrar una cuenta nueva.
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
          <Button type="submit" form="form-registro" disabled={!listo}>
            {enviando ? "Creando cuenta..." : "Crear cuenta"}
          </Button>
          <p className={estilos.pieCambio}>
            ¿Ya tienes cuenta?{" "}
            <Link href="/login" className={estilos.liga}>
              Inicia sesión
            </Link>
          </p>
        </>
      }
    >
      <h1 className={estilos.titulo}>Crea tu cuenta</h1>
      <p className={estilos.subtitulo}>
        Regístrate en segundos y elige cómo usarás DiviEat.
      </p>

      <form
        id="form-registro"
        className={estilos.formulario}
        onSubmit={manejarEnvio}
      >
        {error ? (
          <div className={estilos.alertaError} role="alert">
            {error}
          </div>
        ) : null}

        <div className={estilos.campo}>
          <label className={estilos.etiqueta} htmlFor={idNombre}>
            Nombre
          </label>
          <input
            id={idNombre}
            type="text"
            className={estilos.entrada}
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setError(null);
            }}
            placeholder="Mariana López"
            autoComplete="name"
            enterKeyHint="next"
            maxLength={60}
            required
          />
        </div>

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
          <span className={estilos.etiqueta}>Rol</span>
          <div className={estilos.roles} role="radiogroup" aria-label="Rol de usuario">
            {ROLES_USUARIO.map((opcion) => {
              const seleccionado = role === opcion.valor;
              return (
                <button
                  key={opcion.valor}
                  type="button"
                  role="radio"
                  aria-checked={seleccionado}
                  className={`${estilos.rolOpcion} ${
                    seleccionado ? estilos.rolActivo : ""
                  }`}
                  onClick={() => {
                    setRole(opcion.valor);
                    setError(null);
                  }}
                >
                  <span className={estilos.rolEtiqueta}>{opcion.etiqueta}</span>
                </button>
              );
            })}
          </div>
          {rolActual ? (
            <p className={estilos.rolDescripcion}>{rolActual.descripcion}</p>
          ) : null}
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
              placeholder="Mínimo 8 caracteres"
              autoComplete="new-password"
              enterKeyHint="next"
              minLength={MIN_LONGITUD_PASSWORD}
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
          <p className={estilos.ayuda}>Usa al menos 8 caracteres.</p>
        </div>

        <div className={estilos.campo}>
          <label className={estilos.etiqueta} htmlFor={idConfirmar}>
            Confirmar contraseña
          </label>
          <input
            id={idConfirmar}
            type={mostrarPassword ? "text" : "password"}
            className={estilos.entrada}
            value={confirmar}
            onChange={(e) => {
              setConfirmar(e.target.value);
              setError(null);
            }}
            placeholder="Repite tu contraseña"
            autoComplete="new-password"
            enterKeyHint="go"
            minLength={MIN_LONGITUD_PASSWORD}
            required
          />
        </div>
      </form>
    </Pantalla>
  );
}
