# DiviEat · frontend

Next.js (App Router) + TypeScript + **CSS Modules**. Sin Tailwind: los estilos
salen de los tokens del sistema de diseño, declarados como variables CSS en
`src/app/globals.css` y leídos del Figma, no transcritos a ojo.

```
src/
  app/                 rutas
    escanear/          cámara: QR de la orden o foto del ticket
    codigo/            entrada manual del número de orden
    orden/[numero]/    unirse, cuenta, y el QR imprimible
  components/          primitivas (nombres iguales a los del Figma) y pantallas
  dominio/             dinero, orden, lectura del QR — con sus pruebas
  hooks/               useCamara, useLectorQR
```

## Correr

```bash
npm run dev        # http://localhost:3000
npm test           # pruebas de dominio
npm run build
```

## Probar el escáner

La cámara necesita **contexto seguro**. En la laptop basta `localhost`, pero el
teléfono entra por la IP de la red local y ahí el navegador **no** entrega la
cámara por HTTP. Para probar desde el celular:

```bash
npm run dev:https          # genera un certificado local
```

Luego abre `https://<ip-de-tu-laptop>:3000` en el teléfono y acepta el aviso del
certificado. La IP aparece en la salida de `next dev` como *Network*.

Para tener un QR que apuntar, abre **`/orden/2471/qr`** en la laptop: imprime el
QR de la orden del demo, apuntando al host desde el que se está sirviendo. El
teléfono lo escanea y entra a la cuenta.

Si no hay cámara a la mano, `/codigo` acepta el número de orden a mano (`2471`).

## Qué falta

La foto del ticket se toma y se previsualiza, pero **la lectura (OCR) todavía no
está conectada** con el módulo `ai/`. El QR es el camino principal; el ticket es
el camino B.
