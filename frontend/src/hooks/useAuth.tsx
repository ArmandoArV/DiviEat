"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import {
  CLAVE_SESION_STORAGE,
  ErrorAuthApi,
  iniciarSesionApi,
  obtenerPerfilApi,
  registrarUsuario,
  type DatosLogin,
  type DatosRegistro,
  type SesionAuth,
  type Usuario,
} from "@/dominio/auth";

type ValorContextoAuth = {
  usuario: Usuario | null;
  token: string | null;
  cargando: boolean;
  autenticado: boolean;
  iniciarSesion: (datos: DatosLogin) => Promise<Usuario>;
  registrar: (datos: DatosRegistro) => Promise<Usuario>;
  cerrarSesion: () => void;
};

const ContextoAuth = createContext<ValorContextoAuth | null>(null);

// Almacen sincronizado con localStorage para evitar setState sincrono en
// useEffect y mantener consistencia entre SSR e hidratacion.
let sesionCache: SesionAuth | null = null;
let cacheInicializado = false;
const oyentes = new Set<() => void>();

function notificarOyentes(): void {
  for (const oyente of oyentes) oyente();
}

function leerSesionDesdeStorage(): SesionAuth | null {
  if (typeof window === "undefined") return null;
  try {
    const crudo = window.localStorage.getItem(CLAVE_SESION_STORAGE);
    if (!crudo) return null;
    const parsed = JSON.parse(crudo) as Partial<SesionAuth>;
    if (typeof parsed.token !== "string" || !parsed.user?.id) {
      return null;
    }
    return { token: parsed.token, user: parsed.user };
  } catch {
    return null;
  }
}

function obtenerSnapshotCliente(): SesionAuth | null {
  if (!cacheInicializado) {
    sesionCache = leerSesionDesdeStorage();
    cacheInicializado = true;
  }
  return sesionCache;
}

function obtenerSnapshotServidor(): SesionAuth | null {
  return null;
}

function escribirSesion(sesion: SesionAuth | null): void {
  sesionCache = sesion;
  cacheInicializado = true;
  if (typeof window !== "undefined") {
    try {
      if (sesion) {
        window.localStorage.setItem(CLAVE_SESION_STORAGE, JSON.stringify(sesion));
      } else {
        window.localStorage.removeItem(CLAVE_SESION_STORAGE);
      }
    } catch {
      // Storage puede fallar en modo privado estricto; la sesion sigue en memoria.
    }
  }
  notificarOyentes();
}

function suscribirSesion(oyente: () => void): () => void {
  oyentes.add(oyente);
  const alCambiarStorage = (evento: StorageEvent) => {
    if (evento.key === CLAVE_SESION_STORAGE) {
      sesionCache = leerSesionDesdeStorage();
      cacheInicializado = true;
      notificarOyentes();
    }
  };
  if (typeof window !== "undefined") {
    window.addEventListener("storage", alCambiarStorage);
  }
  return () => {
    oyentes.delete(oyente);
    if (typeof window !== "undefined") {
      window.removeEventListener("storage", alCambiarStorage);
    }
  };
}

function suscribirHidratacion(): () => void {
  return () => {};
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const sesion = useSyncExternalStore(
    suscribirSesion,
    obtenerSnapshotCliente,
    obtenerSnapshotServidor,
  );
  const hidratado = useSyncExternalStore(
    suscribirHidratacion,
    () => true,
    () => false,
  );
  const tokenVerificado = useRef<string | null>(null);

  useEffect(() => {
    const token = sesion?.token ?? null;
    if (!token || tokenVerificado.current === token) return;

    let activo = true;
    tokenVerificado.current = token;

    obtenerPerfilApi(token)
      .then((usuarioActual) => {
        if (!activo) return;
        escribirSesion({ token, user: usuarioActual });
      })
      .catch((error) => {
        if (!activo) return;
        // Si el token expiro o fue rechazado (401/404), limpiamos la sesion.
        // Si solo no hay red (status 0), conservamos la sesion local.
        if (error instanceof ErrorAuthApi && (error.status === 401 || error.status === 404)) {
          tokenVerificado.current = null;
          escribirSesion(null);
        }
      });

    return () => {
      activo = false;
    };
  }, [sesion?.token]);

  const iniciarSesion = useCallback(async (datos: DatosLogin) => {
    const nueva = await iniciarSesionApi(datos);
    tokenVerificado.current = nueva.token;
    escribirSesion(nueva);
    return nueva.user;
  }, []);

  const registrar = useCallback(async (datos: DatosRegistro) => {
    const nueva = await registrarUsuario(datos);
    tokenVerificado.current = nueva.token;
    escribirSesion(nueva);
    return nueva.user;
  }, []);

  const cerrarSesion = useCallback(() => {
    tokenVerificado.current = null;
    escribirSesion(null);
  }, []);

  const valor = useMemo<ValorContextoAuth>(
    () => ({
      usuario: sesion?.user ?? null,
      token: sesion?.token ?? null,
      cargando: !hidratado,
      autenticado: sesion !== null,
      iniciarSesion,
      registrar,
      cerrarSesion,
    }),
    [sesion, hidratado, iniciarSesion, registrar, cerrarSesion],
  );

  return <ContextoAuth.Provider value={valor}>{children}</ContextoAuth.Provider>;
}

export function useAuth(): ValorContextoAuth {
  const ctx = useContext(ContextoAuth);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }
  return ctx;
}
