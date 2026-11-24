import assert from "node:assert/strict";
import { test } from "node:test";
import { pesos, repartir } from "./dinero";
import { cobrado, ORDEN_DEMO, porCobrar } from "./orden";

test("formatea centavos como pesos mexicanos", () => {
  assert.equal(pesos(124000), "$1,240");
  assert.equal(pesos(27600), "$276");
  assert.equal(pesos(12050), "$120.50");
  assert.equal(pesos(0), "$0");
  assert.equal(pesos(-5500), "-$55");
});

test("repartir no pierde ni un centavo", () => {
  // $120 entre 3 cae exacto; el guacamole del demo depende de esto.
  assert.deepEqual(repartir(12000, 3), [4000, 4000, 4000]);
  // 100 centavos entre 3 no cae exacto: alguien paga un centavo mas, pero la
  // suma tiene que seguir dando 100.
  const partes = repartir(100, 3);
  assert.deepEqual(partes, [34, 33, 33]);
  assert.equal(partes.reduce((a, b) => a + b, 0), 100);
});

test("los datos canonicos del demo cuadran", () => {
  const sumaRenglones = ORDEN_DEMO.productos.reduce((a, p) => a + p.importe, 0);
  assert.equal(sumaRenglones, ORDEN_DEMO.total, "los renglones deben dar el total");

  const sumaConsumos = ORDEN_DEMO.comensales.reduce((a, c) => a + c.consumo, 0);
  assert.equal(sumaConsumos, ORDEN_DEMO.total, "los consumos deben dar el total");

  assert.equal(cobrado(ORDEN_DEMO), 39000, "solo Ana ha pagado");
  assert.equal(porCobrar(ORDEN_DEMO), 85000);
});
