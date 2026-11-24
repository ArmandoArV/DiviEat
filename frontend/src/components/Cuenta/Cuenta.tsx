import { Avatar } from "@/components/Avatar/Avatar";
import { Badge } from "@/components/Badge/Badge";
import { Button } from "@/components/Button/Button";
import { ItemRow, Palomita, type EstadoRenglon } from "@/components/ItemRow/ItemRow";
import { Pantalla, TituloPantalla } from "@/components/Pantalla/Pantalla";
import { pesos } from "@/dominio/dinero";
import {
  cobrado,
  colorPorEstado,
  porCobrar,
  YO,
  type Orden,
  type Producto,
} from "@/dominio/orden";
import estilos from "./Cuenta.module.css";

/**
 * Un producto hereda el estado de quien lo pidio: pagado solo cuando todos sus
 * dueños pagaron, apartado mientras alguien esta en el cobro. Sin dueños, sigue
 * disponible para que alguien lo reclame.
 */
function estadoDe(producto: Producto, orden: Orden): EstadoRenglon {
  if (producto.de.length === 0) return "disponible";
  const suyos = orden.comensales.filter((c) => producto.de.includes(c.id));
  if (suyos.every((c) => c.estado === "pagado")) return "pagado";
  if (suyos.some((c) => c.estado === "pagando")) return "apartado";
  return "disponible";
}

function metaDe(producto: Producto, orden: Orden, estado: EstadoRenglon): string {
  const nombres = orden.comensales
    .filter((c) => producto.de.includes(c.id))
    .map((c) => (c.id === YO ? "tú" : c.nombre));
  const piezas = producto.cantidad > 1 ? `${producto.cantidad} piezas` : null;

  if (estado === "pagado") {
    return [`Pagó ${nombres.join(" y ")}`, piezas].filter(Boolean).join(" · ");
  }
  if (estado === "apartado") {
    const pagando = orden.comensales.find(
      (c) => producto.de.includes(c.id) && c.estado === "pagando",
    );
    const compartido = producto.compartido
      ? ` · compartido entre ${producto.de.length}`
      : "";
    return `${pagando?.nombre} lo está pagando${compartido}`;
  }
  return [piezas, producto.compartido ? "Compartido" : null]
    .filter(Boolean)
    .join(" · ");
}

export function Cuenta({ orden }: { orden: Orden }) {
  const yaCobrado = cobrado(orden);
  const falta = porCobrar(orden);
  const avance = Math.round((yaCobrado / orden.total) * 100);

  const conEstado = orden.productos.map((producto) => ({
    producto,
    estado: estadoDe(producto, orden),
  }));
  const pagados = conEstado.filter((p) => p.estado === "pagado");
  const pendientes = conEstado.filter((p) => p.estado !== "pagado");

  return (
    <Pantalla
      encabezado={
        <>
          <TituloPantalla>Mesa {orden.mesa}</TituloPantalla>
          <Badge color="exito">En vivo</Badge>
        </>
      }
      barraInferior={<Button>Elegir lo mío</Button>}
    >
      <section className={estilos.resumen}>
        <p className={estilos.cifra}>
          <span className={estilos.cobrado}>{pesos(yaCobrado)}</span>
          <span className={estilos.deTotal}>de {pesos(orden.total)}</span>
        </p>
        <div
          className={estilos.barra}
          role="progressbar"
          aria-valuenow={avance}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Avance del cobro de la mesa"
        >
          <div className={estilos.avance} style={{ width: `${avance}%` }} />
        </div>
        <p className={estilos.faltan}>Faltan {pesos(falta)} por cobrar</p>
      </section>

      <section className={estilos.comensales}>
        {orden.comensales.map((comensal) => {
          const eresTu = comensal.id === YO;
          const comoVa = eresTu
            ? "tú"
            : { pagado: "pagó", pagando: "pagando", pendiente: "pendiente" }[
                comensal.estado
              ];
          return (
            <div key={comensal.id} className={estilos.comensal}>
              <Avatar
                nombre={comensal.nombre}
                medida={44}
                color={colorPorEstado(comensal)}
              />
              <span
                className={`${estilos.comoVa} ${eresTu ? estilos.tu : ""}`}
              >
                {comoVa}
              </span>
            </div>
          );
        })}
      </section>

      {pagados.length > 0 && (
        <>
          <h2 className={`${estilos.seccion} ${estilos.seccionPagado}`}>
            Ya pagado
          </h2>
          <div className={estilos.lista}>
            {pagados.map(({ producto, estado }) => (
              <ItemRow
                key={producto.id}
                nombre={producto.nombre}
                meta={metaDe(producto, orden, estado)}
                importe={producto.importe}
                estado={estado}
                marca={<Palomita />}
                insignia={<Badge color="exito">Pagado</Badge>}
              />
            ))}
          </div>
        </>
      )}

      <h2 className={estilos.seccion}>Sin pagar</h2>
      <div className={estilos.lista}>
        {pendientes.map(({ producto, estado }) => (
          <ItemRow
            key={producto.id}
            nombre={producto.nombre}
            meta={metaDe(producto, orden, estado)}
            importe={producto.importe}
            estado={estado}
            insignia={
              estado === "apartado" ? <Badge color="info">En curso</Badge> : undefined
            }
          />
        ))}
      </div>
    </Pantalla>
  );
}
