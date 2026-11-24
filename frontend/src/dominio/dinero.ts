/**
 * El dinero son centavos enteros, nunca float — misma regla que en `ai/`.
 * Un redondeo mal hecho aqui es la diferencia entre que la mesa cuadre o no.
 */
export type Centavos = number;

export function pesos(centavos: Centavos): string {
  const signo = centavos < 0 ? "-" : "";
  const abs = Math.abs(centavos);
  const entero = Math.floor(abs / 100);
  const decimales = abs % 100;
  const miles = entero.toLocaleString("es-MX");
  return decimales === 0
    ? `${signo}$${miles}`
    : `${signo}$${miles}.${String(decimales).padStart(2, "0")}`;
}

/** Reparte un importe entre n personas sin perder ni un centavo. */
export function repartir(centavos: Centavos, entre: number): Centavos[] {
  const base = Math.floor(centavos / entre);
  const sobrante = centavos - base * entre;
  return Array.from({ length: entre }, (_, i) => base + (i < sobrante ? 1 : 0));
}
