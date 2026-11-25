export type RolUsuario = "comensal" | "mesero" | "admin";

export type Usuario = {
  id: string;
  name: string;
  email: string;
  role: RolUsuario;
  createdAt: string;
};

export type SesionAuth = {
  token: string;
  user: Usuario;
};

export type DatosRegistro = {
  name: string;
  email: string;
  role: RolUsuario;
  password: string;
};

export type DatosLogin = {
  email: string;
  password: string;
};

export const ROLES_USUARIO: ReadonlyArray<{
  valor: RolUsuario;
  etiqueta: string;
  descripcion: string;
}> = [
  {
    valor: "comensal",
    etiqueta: "Comensal",
    descripcion: "Divide y paga tu parte en la mesa",
  },
  {
    valor: "mesero",
    etiqueta: "Mesero",
    descripcion: "Gestiona mesas y cobros en vivo",
  },
  {
    valor: "admin",
    etiqueta: "Admin",
    descripcion: "Configura el restaurante y menú",
  },
];

export const CLAVE_SESION_STORAGE = "divieat_sesion";

export const MIN_LONGITUD_PASSWORD = 8;

export function etiquetaRol(rol: RolUsuario): string {
  return ROLES_USUARIO.find((r) => r.valor === rol)?.etiqueta ?? rol;
}

export function colorAvatarPorRol(rol: RolUsuario): string {
  return {
    comensal: "var(--color-primary-base)",
    mesero: "var(--color-teal-base)",
    admin: "var(--color-rose-base)",
  }[rol];
}

export function apiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  const base = raw && raw.length > 0 ? raw : "http://localhost:8080";
  return base.replace(/\/+$/, "");
}

export class ErrorAuthApi extends Error {
  readonly status: number;

  constructor(mensaje: string, status: number) {
    super(mensaje);
    this.name = "ErrorAuthApi";
    this.status = status;
  }
}

const MENSAJES_ERROR_API: Record<string, string> = {
  "email is already registered": "Este correo ya está registrado. Intenta iniciar sesión.",
  "invalid email or password": "Correo o contraseña incorrectos.",
  "invalid or expired token": "Tu sesión venció. Inicia sesión de nuevo.",
  "user not found": "No encontramos tu cuenta.",
  "name is required": "Escribe tu nombre para continuar.",
  "invalid email address": "Escribe un correo electrónico válido.",
  "password must be at least 8 characters": "La contraseña debe tener al menos 8 caracteres.",
  "role must be comensal, mesero, or admin": "Selecciona un rol válido.",
  "malformed body": "Revisa los datos enviados e intenta de nuevo.",
};

export function traducirErrorApi(mensaje?: string, status?: number): string {
  if (mensaje) {
    const normalizado = mensaje.trim().toLowerCase();
    if (MENSAJES_ERROR_API[normalizado]) {
      return MENSAJES_ERROR_API[normalizado];
    }
  }
  if (status === 401) return "Correo o contraseña incorrectos.";
  if (status === 409) return "Este correo ya está registrado.";
  if (status && status >= 500) {
    return "El servidor tuvo un problema. Intenta de nuevo en unos segundos.";
  }
  return mensaje || "No pudimos completar la solicitud. Intenta de nuevo.";
}

async function solicitarApi<T>(
  ruta: string,
  opciones: RequestInit = {},
): Promise<T> {
  const url = `${apiBaseUrl()}${ruta}`;
  let respuesta: Response;

  try {
    respuesta = await fetch(url, {
      ...opciones,
      headers: {
        "Content-Type": "application/json",
        ...(opciones.headers ?? {}),
      },
    });
  } catch {
    throw new ErrorAuthApi(
      `No pudimos conectar con la API (${apiBaseUrl()}). Verifica que el backend esté activo.`,
      0,
    );
  }

  let cuerpo: Record<string, unknown> | null = null;
  try {
    cuerpo = (await respuesta.json()) as Record<string, unknown>;
  } catch {
    cuerpo = null;
  }

  if (!respuesta.ok) {
    const errorCrudo =
      cuerpo && typeof cuerpo.error === "string" ? cuerpo.error : undefined;
    throw new ErrorAuthApi(
      traducirErrorApi(errorCrudo, respuesta.status),
      respuesta.status,
    );
  }

  return cuerpo as T;
}

export async function registrarUsuario(datos: DatosRegistro): Promise<SesionAuth> {
  return solicitarApi<SesionAuth>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      name: datos.name.trim(),
      email: datos.email.trim().toLowerCase(),
      role: datos.role,
      password: datos.password,
    }),
  });
}

export async function iniciarSesionApi(datos: DatosLogin): Promise<SesionAuth> {
  return solicitarApi<SesionAuth>("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      email: datos.email.trim().toLowerCase(),
      password: datos.password,
    }),
  });
}

export async function obtenerPerfilApi(token: string): Promise<Usuario> {
  const data = await solicitarApi<{ user: Usuario }>("/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return data.user;
}
