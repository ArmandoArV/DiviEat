import type { Centavos } from "./dinero";

export type EstadoComensal = "pagado" | "pagando" | "pendiente";

export type Comensal = {
  id: string;
  nombre: string;
  estado: EstadoComensal;
  /** Lo que le toca de consumo, sin propina. */
  consumo: Centavos;
  /** Color de identidad, el que lo distingue al entrar. */
  color: string;
};

export type Producto = {
  id: string;
  nombre: string;
  cantidad: number;
  /** Importe del renglon completo, no unitario. */
  importe: Centavos;
  /** Ids de quienes lo pidieron. Vacio = nadie lo ha reclamado todavia. */
  de: string[];
  /** Un compartido se divide entre quienes lo pidieron, no entre toda la mesa. */
  compartido?: boolean;
};

/**
 * La unidad es la ORDEN, no la mesa: una mesa se reusa varias veces en la
 * noche y la orden es lo que abre, acumula y se cierra — es tambien como la
 * numeran los POS mexicanos («ORDEN NO. 29» en SOFT RESTAURANT) y como la
 * cierra el golden path del hackathon («se marca como orden completada»).
 * La mesa pasa a ser un atributo de la orden: donde se esta sirviendo.
 */
export type Orden = {
  numero: string;
  mesa: number;
  restaurante: string;
  direccion: string;
  abiertaDesde: string;
  total: Centavos;
  comensales: Comensal[];
  productos: Producto[];
};

/**
 * Datos canonicos del demo. Las cifras estan cuadradas contra las pantallas
 * del Figma: la suma de los renglones da exactamente el total, y la suma de
 * los consumos por comensal tambien. No los cambies sueltos.
 */
export const ORDEN_DEMO: Orden = {
  numero: "2471",
  mesa: 7,
  restaurante: "La Nortestense",
  direccion: "Av. Revolución 120",
  abiertaDesde: "20:15",
  total: 124000,
  comensales: [
    { id: "ana", nombre: "Ana", estado: "pagado", consumo: 39000, color: "var(--color-rose-base)" },
    { id: "luis", nombre: "Luis", estado: "pagando", consumo: 13500, color: "var(--color-teal-base)" },
    { id: "mariana", nombre: "Mariana", estado: "pendiente", consumo: 24000, color: "var(--color-primary-base)" },
    { id: "sofia", nombre: "Sofía", estado: "pendiente", consumo: 47500, color: "var(--color-amber-base)" },
  ],
  productos: [
    { id: "tacos", nombre: "Tacos de pastor", cantidad: 4, importe: 24000, de: ["ana"] },
    { id: "cerveza", nombre: "Cerveza clara", cantidad: 2, importe: 15000, de: ["ana"] },
    { id: "guacamole", nombre: "Guacamole", cantidad: 1, importe: 12000, de: ["luis", "mariana", "sofia"], compartido: true },
    { id: "flautas", nombre: "Flautas de pollo", cantidad: 1, importe: 14500, de: [] },
    { id: "horchata", nombre: "Agua de horchata", cantidad: 1, importe: 5500, de: [] },
    { id: "michelada", nombre: "Michelada", cantidad: 1, importe: 9500, de: [] },
    { id: "quesadillas", nombre: "Quesadillas", cantidad: 3, importe: 19500, de: [] },
    { id: "flan", nombre: "Flan napolitano", cantidad: 2, importe: 24000, de: [] },
  ],
};

/** Quien eres en el demo: el flujo se cuenta desde Mariana. */
export const YO = "mariana";

export function cobrado(orden: Orden): Centavos {
  return orden.comensales
    .filter((c) => c.estado === "pagado")
    .reduce((suma, c) => suma + c.consumo, 0);
}

export function porCobrar(orden: Orden): Centavos {
  return orden.total - cobrado(orden);
}

export function buscarOrden(numero: string): Orden | null {
  return numero.trim().toUpperCase() === ORDEN_DEMO.numero ? ORDEN_DEMO : null;
}

/**
 * En la cuenta el avatar no te identifica, te dice como vas: verde pagado,
 * teal cobrandose, naranja tu, gris pendiente. Es la misma lectura que usa el
 * mesero en su panel.
 */
export function colorPorEstado(comensal: Comensal): string {
  if (comensal.id === YO) return "var(--color-primary-base)";
  return {
    pagado: "var(--color-success-base)",
    pagando: "var(--color-teal-base)",
    pendiente: "var(--color-border-strong)",
  }[comensal.estado];
}
