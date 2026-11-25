import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  apiBaseUrl,
  etiquetaRol,
  traducirErrorApi,
} from "./auth";

describe("auth dominio", () => {
  it("traduce los errores conocidos del backend a espanol claro", () => {
    assert.equal(
      traducirErrorApi("email is already registered", 409),
      "Este correo ya está registrado. Intenta iniciar sesión.",
    );
    assert.equal(
      traducirErrorApi("invalid email or password", 401),
      "Correo o contraseña incorrectos.",
    );
    assert.equal(
      traducirErrorApi("password must be at least 8 characters", 400),
      "La contraseña debe tener al menos 8 caracteres.",
    );
  });

  it("usa localhost:8080 por defecto si NEXT_PUBLIC_API_URL no existe", () => {
    const anterior = process.env.NEXT_PUBLIC_API_URL;
    delete process.env.NEXT_PUBLIC_API_URL;
    try {
      assert.equal(apiBaseUrl(), "http://localhost:8080");
    } finally {
      if (anterior !== undefined) process.env.NEXT_PUBLIC_API_URL = anterior;
    }
  });

  it("elimina diagonales finales en NEXT_PUBLIC_API_URL", () => {
    const anterior = process.env.NEXT_PUBLIC_API_URL;
    process.env.NEXT_PUBLIC_API_URL = "https://api.divieat.mx///";
    try {
      assert.equal(apiBaseUrl(), "https://api.divieat.mx");
    } finally {
      if (anterior === undefined) {
        delete process.env.NEXT_PUBLIC_API_URL;
      } else {
        process.env.NEXT_PUBLIC_API_URL = anterior;
      }
    }
  });

  it("resuelve la etiqueta visible para cada rol", () => {
    assert.equal(etiquetaRol("comensal"), "Comensal");
    assert.equal(etiquetaRol("mesero"), "Mesero");
    assert.equal(etiquetaRol("admin"), "Admin");
  });
});
