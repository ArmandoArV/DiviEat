# DiviEat

Plataforma web para que cada comensal divida y pague **solo su parte** de la cuenta en un
restaurante, desde el navegador de su celular y sin descargar una app. Se entra escaneando
un QR (o fotografiando el ticket), se eligen los productos consumidos y se paga con CoDi,
tarjeta o billetera. Conforme entran los pagos, la cuenta de la mesa se actualiza en vivo
para todos. Mercado objetivo: México.

Proyecto académico. El equipo trabaja en español: **toda la UI, el copy y los nombres de
capas en Figma están en español**. Mantén esa convención.

## Estado actual

**No hay código todavía.** El único entregable vivo es el mockup de Figma. El `.gitignore`
es de perfil Node, pero **el stack no está decidido** (ver "Decisiones abiertas").

## El mockup de Figma

`fileKey`: **`RjNdEa7jK11DdLrUrPYFcb`** — https://www.figma.com/design/RjNdEa7jK11DdLrUrPYFcb

| Página | id | Contenido |
|---|---|---|
| 01 · Landing | `0:1` | Landing desktop 1440×7306 + tablero "Guion de scroll" (especificación de movimiento) |
| 02 · Flujo comensal | `2:2` | 12 pantallas móviles 390×844, de la cámara al comprobante |
| 03 · Panel restaurante | `2:3` | 3 pantallas desktop 1440×1024: mesas, detalle en vivo, QR por mesa |
| 04 · Sistema de diseño | `2:4` | Tokens, escala tipográfica y componentes |
| 05 · Marca | `45:266` | Exploración del logo, calibración y componentes de marca |

### Flujo comensal (orden real)
1. Permiso de cámara · 2. Cámara / escanear QR · 3. Cámara / foto del ticket ·
4. Leyendo el ticket (OCR) · 5. Revisar lo detectado · 6. Te unes a la mesa ·
7. Cuenta de la mesa · 8. Selección de consumo · 9. Dividir un compartido ·
10. Resumen y propina · 11. Pago con CoDi · 12. Pago confirmado

## Decisiones de producto ya tomadas

- **Sin app y sin registro.** Solo se pide el nombre para que los demás te identifiquen.
- **CoDi es el diferenciador**: sin comisión por transacción. Tarjeta y billetera existen
  como alternativas, con la tarifa del procesador.
- **Dos formas de entrar**: QR de la mesa (restaurante integrado) o **foto del ticket con
  OCR** (restaurante no integrado). El OCR abre el mercado chico pero introduce error, por
  eso la pantalla *Revisar lo detectado* es obligatoria y cuadra la suma contra el total
  impreso. No elimines ese paso.
- **Los compartidos se dividen entre quienes los pidieron**, no entre toda la mesa.
- **La cuenta es en vivo**: cada pago actualiza la mesa al instante, sin recargar.
- La imagen del ticket **se procesa y se descarta**; eso está prometido en la UI.
- Los **precios de la landing ($299 / $599 / A medida) son placeholder**, no un modelo de
  negocio validado.

## Marca

- **Marca**: la **D** de DiviEat cortada por la **perforación de un ticket**, con el **borde
  dentado** del papel al pie. Calibrada a **2 dientes profundos** — con 3 o 4 se rellenan y
  desaparecen a 16 px.
- **Logotipo**: la marca **sustituye la D** → `[marca]iviEat`. **Nunca escribas la D además
  de la marca.**
- Se probó una **mordida en la "a"** y se descartó: se veía rara.
- El juego `Logo/Lockup` (`50:324`) tiene variantes **tamaño L (56) / M (30) / S (20)** ×
  **color Oscuro / Blanco**. **Elige el tamaño; no reescales la instancia** (el texto no
  escala al redimensionar un frame).
- `Logo/Marca` (`45:359`) es el azulejo naranja para app, favicon y avatar; existen también
  versiones sin fondo, blanca y monocroma.

## Sistema de diseño

**Tipografía: Nunito** (sustituto de una redondeada propia; Feather de Duolingo no es
licenciable). Pesos: Black para display, ExtraBold para encabezados y botones, Medium para
cuerpo. Ojo: en Figma el estilo es `"ExtraBold"` sin espacio, pero en Inter es `"Extra Bold"`.

**Identidad naranja cálida.** Se partió de un lenguaje tipo Duolingo (botones 3D, esquinas
muy redondeadas, bordes de 2 px) y se recoloreó a naranja porque el verde lima leía
demasiado a Duolingo. El verde quedó **reservado para "pagado/confirmado"**.

Colección de variables: `VariableCollectionId:2:5`, modo `2:0`.

| Rol | Token | Hex |
|---|---|---|
| Marca | `color/primary/base` · `shadow` · `soft` · `tint` | `#FF7A1A` `#D45E00` `#FFE2C2` `#FFF4E9` |
| Éxito (pagado) | `color/success/base` · `soft` | `#12A150` `#D8F3E3` |
| Acentos | `teal` `amber` `rose` `sunset` `red` | `#0FA3A3` `#FFB020` `#E8546B` `#FF9F43` `#F2484B` |
| Texto | `primary` · `secondary` · `muted` | `#3A2E26` `#7A6A5E` `#A99C92` |
| Bordes | `default` · `strong` | `#ECE4DD` `#D9CDC2` |
| Superficies | `base` · `muted` | `#FFFFFF` `#FBF6F1` |
| Oscuro | `dark` · `darkElevated` · `darkBorder` | `#1F1714` `#2B211C` `#46382F` |

**Botón 3D**: frame exterior con el color "shadow" y `paddingBottom: 4`; dentro, la cara
("face") con el color base. Al presionar, la cara baja 4 px y el labio desaparece.

### Componentes y sus propiedades

| Componente | id | Propiedades / variantes |
|---|---|---|
| Button | `3:20` | `label#5:0`; `color=Naranja\|Teal\|Blanco`, `size=L\|M` |
| Badge | `3:31` | `label#5:7`; `color=Éxito\|Info\|Neutro\|Alerta\|Error` |
| Avatar | `3:32` | `inicial#5:13` (el fill se sobreescribe por instancia) |
| Item/Row | `3:71` | `nombre#5:14`, `meta#5:19`, `precio#5:24`; `estado=Disponible\|Seleccionado\|Pagado\|Apartado` |
| Bullet | `5:31` | `texto#5:29` |
| StepCard | `6:2` | `numero#6:0`, `titulo#6:1`, `cuerpo#6:2` |
| FeatureCard | `6:7` | `titulo#6:3`, `cuerpo#6:4`, `icono#6:5` (INSTANCE_SWAP) |
| PlanCard | `6:70` | `plan#6:6`, `precio#6:9`, `periodo#6:12`; `destacado=Sí\|No` |
| Iconos | `5:2`…`5:28` | QR, Phone, Users, Bolt, Shield, Clock, Card, Store (trazo blanco, van sobre tiles de color) |

## Datos canónicos del demo

Datos sintéticos. Úsalos tal cual al construir el prototipo: las cifras están cuadradas en
las 16 pantallas.

**Mesa 7 · La Nortestense · 4 comensales · total del consumo $1,240**

| Producto | Cant. | Importe |
|---|---|---|
| Tacos de pastor | 4 | $240 |
| Cerveza clara | 2 | $150 |
| Flautas de pollo | 1 | $145 |
| Agua de horchata | 1 | $55 |
| Guacamole (compartido entre 3) | 1 | $120 |
| Michelada | 1 | $95 |
| Quesadillas | 3 | $195 |
| Flan napolitano | 2 | $240 |

- **Ana** pagó tacos + cerveza = $390 de consumo ($448 con 15% de propina).
- **Mariana** (la usuaria del flujo) paga flautas + horchata + 1/3 de guacamole = **$240**,
  propina 15% = $36, **total $276**. Folio `DIV-7A2K`, 21:43.
- **Luis**: michelada + 1/3 de guacamole = $135 ($155) — *pagando*.
- **Sofía**: quesadillas + flan + 1/3 de guacamole = $475 ($546) — *sin pagar*.
- Consumo cobrado tras el pago de Mariana: **$630 de $1,240**, faltan $610.

## Investigación de competencia

Competidores directos en México: **SimplePay TablePay**, **Tabe** (desde $499 MXN/mes +
comisiones), **Mangio**, **Que Pay**, **Pacto Pay on Demand**. Solo Tabe publica precio.

**Regla de honestidad que ya está aplicada en la tabla comparativa de la landing**: donde la
investigación no encontró el dato público se usa "—" = *no identificado*, **nunca "No"**.
Eso incluye la columna de CoDi para los competidores: no se verificó que no lo tengan.
No conviertas esos guiones en negativos.

## Decisiones abiertas

- **Stack**: sin elegir. El `.gitignore` sugiere Node/JS, nada más.
- Pantallas de error aún sin diseñar: QR inválido, mesa cerrada, ticket ilegible, sin
  conexión a media selección.
- **Pago fallido o caducado** (CoDi expira) y reintento.
- Conflicto de concurrencia: dos personas tocan el mismo platillo a la vez.
- Alguien se va sin pagar: qué ve el mesero y cómo se cierra la mesa.
- Cobro mixto en efectivo marcado por el mesero.
- **Facturación CFDI** — en México lo van a pedir en la mesa.
- Alta del restaurante: carga de menú, zonas y mesas.
- De la hoja de marca faltan: área de respeto, tamaño mínimo, tira de app icon/favicon y
  usos incorrectos.

## Trabajar el Figma desde Claude Code

El MCP de Figma está conectado. Carga la skill `figma-use` **antes** de cualquier
`use_figma`, y `figma-generate-design` además cuando el cambio sea visible. Trampas que ya
costaron tiempo en este archivo:

1. **`setBoundVariableForPaint` devuelve el color en negro** cuando el nodo ya estaba ligado
   a *esa misma* variable (pasa al sobreescribir el fill de una instancia). Construye el
   paint con el color literal de la variable y después lígalo.
2. **`FILL` dentro de un contenedor en `HUG` colapsa a los hijos.** Pon el contenedor en
   `FILL`/`FIXED` antes de poner los hijos en `FILL`.
3. Al **estirar un botón** hay que poner también su hijo `face` en `FILL`, si no se ve el
   labio 3D por detrás.
4. **`toLocaleString` no separa miles** en el sandbox: formatea a mano (`$1,240`).
5. `addComponentProperty` con `INSTANCE_SWAP` espera un **node id**, no un key.
6. Carga las fuentes antes de tocar `characters` o `textAutoResize`.
7. **El script es transaccional**: si falla a la mitad, revierte todo. Se puede reintentar
   limpio, pero no asumas que "quedó algo a medias".
8. `figma.subtract` y `figma.flatten` **consumen los nodos**: captura medidas antes.
