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
Diseñado antes del golden path, así que **asume cuenta ya cerrada**: lee "El golden path
del hackathon CoDi" para saber qué pantallas se reaprovechan y cuáles faltan.

1. Permiso de cámara · 2. Cámara / escanear QR · 3. Cámara / foto del ticket ·
4. Leyendo el ticket (OCR) · 5. Revisar lo detectado · 6. Te unes a la mesa ·
7. Cuenta de la mesa · 8. Selección de consumo · 9. Dividir un compartido ·
10. Resumen y propina · 11. Pago con CoDi · 12. Pago confirmado

## El golden path del hackathon CoDi

Define el happy path que evalua el hackathon (`HACKATHON CoDi-1.pdf`, 22/11/2026).

**Escanear QR → registrar nombre → seleccionar alimentos → guardar → ¿modificar? →
¿seleccionar mas? → actualizar el dashboard → «Se pide la cuenta» → pagar.**

El pago se bifurca: si se paga **por separado** se genera un QR CoDi por usuario; si no,
**un solo QR CoDi con el total de la mesa**. En ambas ramas se manda comprobante y la
orden se marca como completada.

Dos lecturas que cambian el plano del proyecto:

- **No hay rama de foto ni de OCR.** Ninguna de las 8 historias de usuario la menciona.
  Todo `ai/` queda fuera del camino evaluado. Sigue siendo el camino B para restaurantes
  sin menu cargado, pero no es el principal.
- **El diagrama supone pedir desde la app**, no dividir una cuenta ya cerrada: tiene pasos
  de «modificar los alimentos seleccionados» y «se pide la cuenta». Las 12 pantallas del
  Figma estan construidas sobre el supuesto contrario (la comida termino, aqui esta el
  ticket, escoge lo tuyo).

Huecos contra lo ya disenado: no existe pantalla de **«Pedir la cuenta»**, no existe la
rama de **pagar el total de la mesa con un solo QR** (DiviEat solo sabe dividir), y el
panel de restaurante no tiene el **registro de transacciones CoDi** que pide la historia 8.
La historia 7 (el mesero ve pagado/pendiente) ya la cubre «Detalle en vivo». La idea 04 del
PDF, marcada «esta si o si», es literalmente el nucleo de DiviEat.

### Pedir desde la app resuelve el problema dificil

Lo mas duro de dividir una cuenta es saber **quien pidio que**: para eso existen el OCR, la
pantalla «Revisar lo detectado» y «Seleccion de consumo». Si cada quien pide desde su
celular la atribucion viene resuelta de origen, y la app pasa a ser **la fuente de la
verdad de la mesa** — sin integrarse al POS y sin leer un ticket.

Con eso, «Seleccion de consumo» deja de ser «marca lo que te comiste» y queda solo para
**compartidos** y para lo que capturo el mesero.

**Mesas mixtas: el caso que no esta en el diagrama.** No todos van a sacar el celular, y
las jarras y los centros de mesa los pone el mesero. Si la app solo registra lo pedido por
app, la cuenta no cuadra contra la caja. El mesero puede agregar platillos desde el panel y
esos entran como **«sin asignar»**: visibles para todos, reclamables desde el celular y
divisibles si son compartidos. **«Sin asignar en $0» es la condicion para cerrar la mesa.**

## Decisiones de producto ya tomadas

- **Sin app y sin registro.** Solo se pide el nombre para que los demás te identifiquen.
- **CoDi es el diferenciador**: sin comisión por transacción. Tarjeta y billetera existen
  como alternativas, con la tarifa del procesador.
- **Dos formas de entrar, pero ya no son pares.** El **QR de la mesa es el camino
  principal** (es el golden path del hackathon y el unico con pedido desde la app). La
  **foto del ticket con OCR es el camino B**, para restaurantes sin menu cargado: abre el
  mercado chico pero introduce error, por eso la pantalla *Revisar lo detectado* es
  obligatoria ahi y cuadra la suma contra el total impreso. No elimines ese paso.
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
- Alta del restaurante: carga de menú, zonas y mesas. **Ya no es opcional**: sin menú
  cargado no hay pedido desde la app, y sin pedido desde la app no hay golden path.
- De la hoja de marca faltan: área de respeto, tamaño mínimo, tira de app icon/favicon y
  usos incorrectos.

## El modulo de IA (`ai/`)

Lectura de tickets: foto -> productos estructurados. Python 3.13 en `ai/.venv`
(PyTorch no tiene ruedas para 3.14 todavia). Todo el codigo es OOP y en espanol,
siguiendo el estilo de `Maestria-IA/RecuperacionDeInformacion`.

```
ai/src/divieat_ticket/
  dominio.py       Dinero (centavos enteros), Producto, TicketExtraido
  imagen.py        Imagen: unico punto de contacto con OpenCV
  preproceso.py    OperacionImagen (ABC) -> escalado, ruido, perspectiva,
                   enderezado, binarizacion + CadenaDePreproceso (composite)
  sintetico.py     genera tickets con verdad de referencia + 5 degradaciones
  ocr.py           MotorOCR (ABC) -> Tesseract | EasyOCR | CRNN | Referencia
                   + SegmentadorDeLineas (perfil de proyeccion)
  perfiles.py      PerfilDeTicket (ABC) -> SoftRestaurant | Miyabi | Generico
  parser.py        NormalizadorOCR, ClasificadorDeLineas (ABC),
                   ExtractorDeProductos, LectorDeMetadatos, AnalizadorDeTicket
  pipeline.py      PipelineExtraccionTicket
  evaluacion.py    ComparadorDeProductos, EvaluadorDeExtraccion
  modelo/          alfabeto, crnn (CNN+BiLSTM), ctc, datos, entrenamiento, metricas
  cli.py           motores | generar | extraer | fixtures | evaluar
```

Comandos (desde `ai/`, con `PYTHONPATH=src`):
`python -m divieat_ticket.cli fixtures` · `... evaluar` · `... extraer foto.jpg`

### Decisiones que costaron hallazgos reales

- **El cuadre va contra el TOTAL, no contra el SUBTOTAL.** En Mexico el precio
  de carta ya incluye IVA: en los tickets reales `SUBTOTAL + IVA = TOTAL` y la
  suma de los renglones da el TOTAL. El SUBTOTAL es la base gravable. Si la
  propina viene dentro del total, se descuenta.
- **SOFT RESTAURANT es el POS mas comun de Mexico.** Por eso `perfiles.py`
  detecta la plantilla y toma como productos solo lo que esta entre el
  encabezado `CANT. DESCRIPCION` y la linea `TOTAL:`. Esa regla estructural
  elimina los falsos positivos (`EXICO CP 97302`, `MESA:2Y7`, `ORDEN NO. 29`
  y, sobre todo, `IVA: $219.31`, que sumado rompia el total).
- **La normalizacion del OCR depende del contexto**: en un numero `S`->5, en una
  palabra `0`->O. Los tokens `CLAVE:valor` (`MESA:2Y7`) se dejan intactos.
- **El dinero son centavos enteros.** Nunca float: el cuadre es lo que decide
  si la pantalla «Revisar lo detectado» sale en verde o en ambar.

### Segmentacion de renglones: lo que costo descubrir

El reconocedor dejo de ser el cuello de botella muy pronto. Medido:

| | |
|---|---|
| CRNN en renglones renderizados limpios | CER 0.0090 |
| CRNN base sobre recortes del pipeline | CER 0.2718 (salto de dominio 30x) |
| CRNN tras ajuste fino en recortes del pipeline | CER 0.0154 · 94.8% renglones exactos · 97.4% importes |

Con 95% de renglones correctos el sistema completo daba F1 0.47, y la razon
era la **segmentacion**: solo el 47% de los tickets quedaba con el numero
exacto de renglones. Diagnostico por pasos:

1. La hipotesis inicial (fusion de renglones) era **falsa**: 2/30 tickets
   fusionaban, 15/30 **partian**. Mirar la imagen con las cajas dibujadas fue
   lo que lo revelo; las cifras solas apuntaban al lado contrario.
2. La causa era geometrica: ~1.5 grados de inclinacion residual separaban la
   descripcion de su importe en bandas distintas. `Enderezado` estimaba el
   angulo con `minAreaRect` sobre toda la tinta y el borde del papel lo
   arruinaba. Se reemplazo por `EnderezadoPorProyeccion`, que busca el angulo
   que maximiza la varianza del perfil de proyeccion (metodo clasico de
   documentos, inmune al borde).
3. Las reglas de guiones se contaban como renglones: `+2` sistematico.
   `SegmentadorMorfologico._descartar_reglas` las filtra por altura relativa.

Eso llevo 47% -> 55%. De ahi en adelante la via clasica da rendimientos
decrecientes y entra la U-Net (`modelo/segmentacion.py`).

**Por que U-Net normal y no Attention U-Net**: las compuertas de atencion de
Oktay existen para suprimir un fondo grande e irrelevante (imagen medica).
Aqui el texto es de alto contraste y ocupa toda la hoja: no hay nada que
suprimir, y el costo extra de parametros no compra nada. Lo que decide el
resultado no es la arquitectura sino **que predice la red**: mascaras del
*nucleo* del renglon, encogidas al 50% vertical y de ancho completo. Asi dos
renglones contiguos nunca se tocan (no hay fusion) y descripcion e importe
caen en la misma componente aunque medien 600 px (no hay particion). Los dos
modos de falla desaparecen por construccion.

La supervision es gratis y exacta: `sintetico.mascara_de_renglones` pinta las
bandas y las degradaciones geometricas las transportan con la **misma**
homografia que la imagen.

### Estilo de importes

Los nueve tickets reales imprimen `$` en todos los importes y el generador no
lo hacia: la CRNN se entreno un tiempo con una distribucion inexistente.
`EstiloDeImporte` lo corrige con tres variantes (pegado `$160.00`, columna
`$     75.00`, sin simbolo) constantes dentro de un mismo ticket, como hace un
POS real.

### El salto de dominio sintetico -> real: tres causas medidas

La CRNN propia leia renglones sinteticos limpios con CER 0.009 y recortes de
fotos reales con CER 0.9986: habia aprendido una distribucion que no existe
fuera del generador. Tres causas, cada una medida por separado:

| Arreglo | CER real |
|---|---|
| Modelo v2 (sintetico liso) | 1.12 |
| `textura_termica`: rejilla de puntos ~203ppp, puntos que no queman, sangrado del calor, bandeo, grano | 0.662 |
| Margenes laterales amplios y asimetricos en los renglones de entrenamiento | 0.523 |
| `_ancho_comun` por percentiles 10-90 en vez de minimo y maximo | **0.383** |

Dos de los tres se delataron **mirando la salida, no las metricas**:

- **El `$` fantasma.** *Todas* las predicciones empezaban con espacios y un
  `$`. Los renglones sinteticos empezaban pegados al texto, pero el segmentador
  entrega el renglon con el margen del papel a los lados: la red habia
  aprendido a leer un `$` donde solo habia papel en blanco.
- **La columna oscura.** `_ancho_comun` tomaba el minimo y el maximo absolutos
  de las cajas, asi que una sola deteccion espuria en el canto del papel metia
  una banda oscura en *todos* los recortes, que el reconocedor leia como un
  caracter al inicio de cada renglon. Cambiar a percentiles bajo el CER de
  0.523 a 0.383 **con los mismos pesos, sin reentrenar**: un tercio del error
  nunca fue del modelo.

**Donde esta el techo.** El ajuste fino arranca en 0.776, toca su minimo
**0.579 en la epoca 2** y de ahi sube mientras el entrenamiento cae a 0.027
(brecha +5.1). Con 83 recortes reales de entrenamiento, `AumentadorDeRecortes`
retrasa la memorizacion pero no la evita; `FuenteMixta` los sobremuestrea 14x y
sin aumentacion la memorizacion esta garantizada. La via para romper ese techo
es **destilar EasyOCR** sobre fotos sin transcribir, no transcribir mas a mano.

**Por eso EasyOCR es el motor de produccion.** La CRNN propia paso de
inservible a legible (`***SOFT RESTAURANT V12 PRO***` -> `V12 PMO`, un caracter
de error), pero 0.38 esta lejos del <0.05 que pediria produccion. Su valor es
como ejercicio de fundamentos, y el diagnostico de arriba es el entregable.

### Datos y evaluacion

No existe corpus publico de tickets mexicanos, asi que `sintetico.py` los
fabrica con verdad exacta y `modelo/datos.py` genera renglones sueltos para
entrenar la CRNN. Los tickets reales estan transcritos en
`ai/tests/fixtures_reales.py` (nueve tickets, cuatro plantillas de POS) y son el test de
aceptacion del parser. **Las fotos originales estan en `.gitignore`**: son
tickets reales con folio y nombre de mesero.

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
