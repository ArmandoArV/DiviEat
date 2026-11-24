import { buscarOrden } from "./orden";

/**
 * El QR apunta a una ORDEN. Puede llegar de tres formas y todas deben
 * funcionar: el portamenus imprime una URL, un ticket puede traer solo el
 * numero, y en pruebas se pega pelado. Devuelve el numero normalizado o null.
 */
export function interpretarQR(texto: string): string | null {
  const limpio = texto.trim();
  if (!limpio) return null;

  // 1. URL completa: https://divieat.mx/orden/2471
  try {
    const url = new URL(limpio);
    const partes = url.pathname.split("/").filter(Boolean);
    const indice = partes.indexOf("orden");
    if (indice !== -1 && partes[indice + 1]) return normalizar(partes[indice + 1]);
  } catch {
    // no era URL; seguimos con los otros formatos
  }

  // 2. Esquema propio: divieat:2471
  if (limpio.toLowerCase().startsWith("divieat:")) {
    return normalizar(limpio.slice("divieat:".length));
  }

  // 3. Numero pelado
  return normalizar(limpio);
}

function normalizar(codigo: string): string | null {
  const limpio = codigo.trim().toUpperCase();
  return /^[A-Z0-9]{4,10}$/.test(limpio) ? limpio : null;
}

/** Un QR bien formado no basta: la orden tiene que existir y estar abierta. */
export function ordenDelQR(texto: string): string | null {
  const numero = interpretarQR(texto);
  return numero && buscarOrden(numero) ? numero : null;
}
