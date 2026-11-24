import assert from "node:assert/strict";
import { test } from "node:test";
import { interpretarQR, ordenDelQR } from "./qr";
import { ORDEN_DEMO } from "./orden";

test("lee el numero de orden en los tres formatos que puede traer un QR", () => {
  // El portamenus imprime una URL; el host cambia entre produccion y pruebas.
  assert.equal(interpretarQR("https://divieat.mx/orden/2471"), "2471");
  assert.equal(interpretarQR("http://192.168.1.71:3000/orden/2471"), "2471");
  // Esquema propio, por si el QR se genera fuera de la web.
  assert.equal(interpretarQR("divieat:2471"), "2471");
  // Numero pelado, que es lo que se teclea a mano.
  assert.equal(interpretarQR("2471"), "2471");
});

test("normaliza mayusculas y espacios", () => {
  assert.equal(interpretarQR("  7a2k  "), "7A2K");
});

test("rechaza lo que no puede ser un numero de orden", () => {
  assert.equal(interpretarQR(""), null);
  assert.equal(interpretarQR("   "), null);
  assert.equal(interpretarQR("ab"), null, "demasiado corto");
  assert.equal(interpretarQR("12345678901"), null, "demasiado largo");
  assert.equal(interpretarQR("247-1"), null, "trae un caracter que no va");
  assert.equal(
    interpretarQR("https://divieat.mx/acerca"),
    null,
    "una URL nuestra que no apunta a una orden",
  );
});

test("un QR bien formado no basta: la orden tiene que existir", () => {
  assert.equal(ordenDelQR(`https://divieat.mx/orden/${ORDEN_DEMO.numero}`), ORDEN_DEMO.numero);
  assert.equal(ordenDelQR("9999"), null, "formato valido, orden inexistente");
});
