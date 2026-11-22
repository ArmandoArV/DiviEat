"""Segmentacion de renglones con una U-Net.

La morfologia llegaba al 55% de tickets con el numero exacto de renglones y
fallaba por geometria: inclinacion residual y huecos grandes entre descripcion
e importe. Una red entrenada con **mascaras de nucleo de renglon** resuelve
las dos cosas por construccion:

* el nucleo esta encogido verticalmente, asi que dos renglones contiguos nunca
  se tocan y no hay fusiones;
* la banda va de extremo a extremo del renglon, asi que descripcion e importe
  pertenecen a la misma componente aunque medien 600 px.

La supervision es gratis y exacta: la mascara se genera junto al ticket y viaja
por las mismas deformaciones geometricas (`sintetico.mascara_de_renglones`).

No se usa Attention U-Net a proposito: sus compuertas de atencion existen para
suprimir un fondo grande e irrelevante (su caso de origen es imagen medica).
Aqui el texto es de alto contraste y esta distribuido por toda la hoja, asi que
no hay nada que suprimir; el costo extra de parametros no compra nada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset

from divieat_ticket.imagen import Imagen
from divieat_ticket.ocr import CajaTexto, Segmentador
from divieat_ticket.sintetico import ConfiguracionSintetico, GeneradorTicketsSinteticos

ALTO_ENTRADA = 640
ANCHO_ENTRADA = 448
ENCOGIMIENTO = 0.5          # el mismo que uso `mascara_de_renglones`


# ----------------------------------------------------------------------- red
class DobleConvolucion(nn.Module):
    """Dos convoluciones 3x3 con normalizacion: el ladrillo de la U-Net."""

    def __init__(self, entradas: int, salidas: int) -> None:
        super().__init__()
        self.bloque = nn.Sequential(
            nn.Conv2d(entradas, salidas, 3, padding=1, bias=False),
            nn.BatchNorm2d(salidas),
            nn.ReLU(inplace=True),
            nn.Conv2d(salidas, salidas, 3, padding=1, bias=False),
            nn.BatchNorm2d(salidas),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.bloque(x)


class Bajada(nn.Module):
    """Reduce resolucion y gana contexto."""

    def __init__(self, entradas: int, salidas: int) -> None:
        super().__init__()
        self.bloque = nn.Sequential(nn.MaxPool2d(2), DobleConvolucion(entradas, salidas))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.bloque(x)


class Subida(nn.Module):
    """Recupera resolucion y recoge el detalle por la conexion de salto."""

    def __init__(self, entradas: int, salidas: int) -> None:
        super().__init__()
        self.ascenso = nn.ConvTranspose2d(entradas, entradas // 2, 2, stride=2)
        self.bloque = DobleConvolucion(entradas, salidas)

    def forward(self, x: torch.Tensor, salto: torch.Tensor) -> torch.Tensor:
        x = self.ascenso(x)
        if x.shape[-2:] != salto.shape[-2:]:
            x = nn.functional.interpolate(x, size=salto.shape[-2:], mode="nearest")
        return self.bloque(torch.cat([salto, x], dim=1))


class UNet(nn.Module):
    """U-Net chica para mascaras de renglon (una sola clase)."""

    def __init__(self, base: int = 16) -> None:
        super().__init__()
        self.entrada = DobleConvolucion(1, base)
        self.baja1 = Bajada(base, base * 2)
        self.baja2 = Bajada(base * 2, base * 4)
        self.baja3 = Bajada(base * 4, base * 8)
        self.fondo = Bajada(base * 8, base * 16)
        self.sube1 = Subida(base * 16, base * 8)
        self.sube2 = Subida(base * 8, base * 4)
        self.sube3 = Subida(base * 4, base * 2)
        self.sube4 = Subida(base * 2, base)
        self.salida = nn.Conv2d(base, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Devuelve logits; la sigmoide se aplica al decodificar."""
        c1 = self.entrada(x)
        c2 = self.baja1(c1)
        c3 = self.baja2(c2)
        c4 = self.baja3(c3)
        fondo = self.fondo(c4)
        x = self.sube1(fondo, c4)
        x = self.sube2(x, c3)
        x = self.sube3(x, c2)
        x = self.sube4(x, c1)
        return self.salida(x)

    @property
    def parametros_entrenables(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


class PerdidaDeSegmentacion(nn.Module):
    """BCE + Dice. La BCE sola sufre porque la mascara es mayoria fondo."""

    def __init__(self, peso_dice: float = 0.5) -> None:
        super().__init__()
        self.bce = nn.BCEWithLogitsLoss()
        self.peso_dice = peso_dice

    def forward(self, logits: torch.Tensor, objetivo: torch.Tensor) -> torch.Tensor:
        probabilidad = torch.sigmoid(logits)
        interseccion = (probabilidad * objetivo).sum(dim=(1, 2, 3))
        union = probabilidad.sum(dim=(1, 2, 3)) + objetivo.sum(dim=(1, 2, 3))
        dice = 1 - ((2 * interseccion + 1.0) / (union + 1.0)).mean()
        return self.bce(logits, objetivo) + self.peso_dice * dice


def interseccion_sobre_union(logits: torch.Tensor, objetivo: torch.Tensor, umbral: float = 0.5) -> float:
    prediccion = (torch.sigmoid(logits) > umbral).float()
    interseccion = (prediccion * objetivo).sum()
    union = prediccion.sum() + objetivo.sum() - interseccion
    return float((interseccion / union).item()) if union > 0 else 1.0


# --------------------------------------------------------------------- datos
@dataclass
class EstadisticasMascaras:
    pares: int = 0

    def __str__(self) -> str:
        return f"{self.pares} pares imagen/mascara"


class ConstructorDeMascaras:
    """Escribe pares (imagen, mascara) a disco, ya a la resolucion de la red."""

    def __init__(
        self, carpeta: str | Path, semilla: int = 31, cadena=None
    ) -> None:
        self.carpeta = Path(carpeta)
        self.generador = GeneradorTicketsSinteticos(ConfiguracionSintetico(semilla=semilla))
        # Si se pasa una cadena, la red se entrena sobre la imagen **ya
        # corregida**: es el dominio en el que va a trabajar de verdad.
        self.cadena = cadena
        self.estadisticas = EstadisticasMascaras()

    def construir(self, cantidad: int, informar_cada: int = 100) -> EstadisticasMascaras:
        (self.carpeta / "imagenes").mkdir(parents=True, exist_ok=True)
        (self.carpeta / "mascaras").mkdir(parents=True, exist_ok=True)
        indice_lineas = []
        for indice in range(cantidad):
            muestra = self.generador.generar()
            if self.cadena is None:
                base, mascara_base = muestra.imagen.a_gris(), muestra.mascara
            else:
                base, mascara_base = self.cadena.aplicar_con_mascara(muestra.imagen, muestra.mascara)
            imagen = _a_tamano(base.a_gris().matriz, cv2.INTER_AREA)
            mascara = _a_tamano(mascara_base, cv2.INTER_NEAREST)
            nombre = f"{indice:05d}.png"
            cv2.imwrite(str(self.carpeta / "imagenes" / nombre), imagen)
            cv2.imwrite(str(self.carpeta / "mascaras" / nombre), mascara)
            indice_lineas.append({"archivo": nombre, "renglones": len(muestra.renglones)})
            self.estadisticas.pares += 1
            if (indice + 1) % informar_cada == 0:
                print(f"  {self.estadisticas}", flush=True)
        (self.carpeta / "indice.jsonl").write_text(
            "\n".join(json.dumps(r) for r in indice_lineas), encoding="utf-8"
        )
        return self.estadisticas


def _a_tamano(matriz: np.ndarray, interpolacion: int) -> np.ndarray:
    return cv2.resize(matriz, (ANCHO_ENTRADA, ALTO_ENTRADA), interpolation=interpolacion)


class CorpusDeMascaras(Dataset):
    """Lee los pares del disco; particion por fraccion."""

    def __init__(self, carpeta: str | Path, desde: float = 0.0, hasta: float = 1.0) -> None:
        self.carpeta = Path(carpeta)
        registros = [
            json.loads(linea)
            for linea in (self.carpeta / "indice.jsonl").read_text(encoding="utf-8").splitlines()
            if linea.strip()
        ]
        inicio, fin = int(len(registros) * desde), int(len(registros) * hasta)
        self.registros = registros[inicio:fin]

    def __len__(self) -> int:
        return len(self.registros)

    def __getitem__(self, indice: int) -> tuple[torch.Tensor, torch.Tensor, int]:
        nombre = self.registros[indice]["archivo"]
        imagen = cv2.imread(str(self.carpeta / "imagenes" / nombre), cv2.IMREAD_GRAYSCALE)
        mascara = cv2.imread(str(self.carpeta / "mascaras" / nombre), cv2.IMREAD_GRAYSCALE)
        x = torch.from_numpy(1.0 - imagen.astype(np.float32) / 255.0).unsqueeze(0)
        y = torch.from_numpy((mascara > 127).astype(np.float32)).unsqueeze(0)
        return x, y, self.registros[indice]["renglones"]


# ---------------------------------------------------------------- segmentador
class SegmentadorNeuronal(Segmentador):
    """Segmentador que usa la U-Net en vez de morfologia."""

    def __init__(
        self,
        ruta_modelo: str = "modelos/unet.pt",
        umbral: float = 0.5,
        area_minima: int = 40,
        dispositivo: str | None = None,
        ajustar_a_tinta: bool = False,
    ) -> None:
        self.ruta_modelo = ruta_modelo
        self.umbral = umbral
        self.area_minima = area_minima
        self.dispositivo_pedido = dispositivo
        # Recorta la caja a la altura real del renglon. Mejora los recortes,
        # pero **cambia el dominio**: el modelo que use este segmentador tiene
        # que haberse entrenado con la misma opcion. Con `modelos/crnn_final.pt`
        # (entrenado sin ella) activarla baja el F1 de 0.78 a 0.70.
        self.ajustar_a_tinta = ajustar_a_tinta
        self._modelo = None

    def disponible(self) -> bool:
        return Path(self.ruta_modelo).is_file()

    def _cargar(self) -> None:
        if self._modelo is not None:
            return
        from divieat_ticket.modelo.entrenamiento import SelectorDeDispositivo

        self._dispositivo = SelectorDeDispositivo.elegir(self.dispositivo_pedido)
        punto = torch.load(self.ruta_modelo, map_location=self._dispositivo, weights_only=False)
        modelo = UNet(punto.get("base", 16))
        modelo.load_state_dict(punto["estado"])
        self._modelo = modelo.to(self._dispositivo).eval()

    def segmentar(self, imagen: Imagen) -> list[CajaTexto]:
        self._cargar()
        gris = imagen.a_gris().matriz
        alto_original, ancho_original = gris.shape
        entrada = _a_tamano(gris, cv2.INTER_AREA)
        tensor = torch.from_numpy(1.0 - entrada.astype(np.float32) / 255.0)[None, None]
        with torch.no_grad():
            logits = self._modelo(tensor.to(self._dispositivo)).cpu()
        prediccion = (torch.sigmoid(logits)[0, 0].numpy() > self.umbral).astype(np.uint8)

        escala_x = ancho_original / ANCHO_ENTRADA
        escala_y = alto_original / ALTO_ENTRADA
        cantidad, etiquetas, estadisticas, _ = cv2.connectedComponentsWithStats(prediccion, 8)
        cajas = []
        for indice in range(1, cantidad):
            x, y, ancho, alto, area = estadisticas[indice]
            if area < self.area_minima:
                continue
            caja = self._a_original(x, y, ancho, alto, escala_x, escala_y,
                                    alto_original, ancho_original)
            angulo = self._angulo_de_componente(etiquetas == indice)
            if self.ajustar_a_tinta:
                caja = self._ajustar_a_la_tinta(gris, caja)
            cajas.append(CajaTexto(caja.x, caja.y, caja.ancho, caja.alto, angulo))
        cajas.sort(key=lambda c: c.centro_y)
        return cajas

    def _ajustar_a_la_tinta(self, gris: np.ndarray, caja: CajaTexto) -> CajaTexto:
        """Recorta la caja a la altura real del renglon.

        La banda que predice la red es mas gruesa que el nucleo ideal, asi que
        devolverle su altura dividiendo por el encogimiento la infla de mas y
        el recorte acaba arrastrando el renglon vecino. El centro de la caja si
        es fiable (viene del centro de la componente), asi que se crece desde
        ahi hacia arriba y hacia abajo mientras haya tinta, y se para en el
        primer hueco. Lo que quede fuera es el renglon de al lado.
        """
        franja = gris[caja.y: caja.y + caja.alto, caja.x: caja.x + caja.ancho]
        if franja.size < 2:
            return caja
        umbral = max(60.0, float(franja.mean()) * 0.8)
        perfil = (franja < umbral).sum(axis=1)
        minimo = max(1.0, 0.015 * franja.shape[1])
        con_tinta = perfil > minimo
        if not con_tinta.any():
            return caja

        centro = len(con_tinta) // 2
        if not con_tinta[centro]:
            cercanas = np.flatnonzero(con_tinta)
            centro = int(cercanas[np.argmin(np.abs(cercanas - centro))])

        arriba = centro
        while arriba > 0 and con_tinta[arriba - 1]:
            arriba -= 1
        abajo = centro
        while abajo < len(con_tinta) - 1 and con_tinta[abajo + 1]:
            abajo += 1

        margen = 3
        y0 = caja.y + max(0, arriba - margen)
        y1 = caja.y + min(caja.alto, abajo + 1 + margen)
        return CajaTexto(caja.x, y0, caja.ancho, max(8, y1 - y0), caja.angulo)

    @staticmethod
    def _angulo_de_componente(mascara: np.ndarray, maximo: float = 12.0) -> float:
        """Orientacion del renglon, via momentos de segundo orden de su banda.

        La componente es una franja alargada: su eje principal apunta en la
        direccion del texto. Es mas estable que `minAreaRect` cuando la banda
        tiene los extremos irregulares.
        """
        ys, xs = np.nonzero(mascara)
        if xs.size < 20:
            return 0.0
        xs = xs.astype(np.float64) - xs.mean()
        ys = ys.astype(np.float64) - ys.mean()
        varianza_x = float((xs * xs).mean())
        if varianza_x < 1e-6:
            return 0.0
        pendiente = float((xs * ys).mean()) / varianza_x
        angulo = float(np.degrees(np.arctan(pendiente)))
        return angulo if abs(angulo) <= maximo else 0.0

    @staticmethod
    def _a_original(x, y, ancho, alto, escala_x, escala_y, alto_original, ancho_original) -> CajaTexto:
        """Devuelve la caja al tamano original y deshace el encogimiento vertical."""
        centro_y = (y + alto / 2) * escala_y
        alto_real = (alto * escala_y) / ENCOGIMIENTO
        y0 = max(0, int(centro_y - alto_real / 2))
        y1 = min(alto_original, int(centro_y + alto_real / 2))
        x0 = max(0, int(x * escala_x) - 4)
        x1 = min(ancho_original, int((x + ancho) * escala_x) + 4)
        return CajaTexto(x0, y0, max(1, x1 - x0), max(1, y1 - y0))


# --------------------------------------------------------------- entrenamiento
@dataclass
class ConfiguracionUNet:
    epocas: int = 20
    tamano_lote: int = 8
    tasa_aprendizaje: float = 1e-3
    fraccion_validacion: float = 0.15
    paciencia: int = 5
    base: int = 16
    carpeta_corpus: str = "datos/corpus_mascaras"
    ruta_checkpoint: Path = Path("modelos/unet.pt")


class EntrenadorUNet:
    """Entrena la U-Net de renglones y guarda el mejor IoU de validacion."""

    def __init__(self, config: ConfiguracionUNet | None = None) -> None:
        from divieat_ticket.modelo.entrenamiento import SelectorDeDispositivo

        self.config = config or ConfiguracionUNet()
        self.dispositivo = SelectorDeDispositivo.elegir()
        self.modelo = UNet(self.config.base).to(self.dispositivo)
        self.criterio = PerdidaDeSegmentacion()
        self.optimizador = torch.optim.AdamW(
            self.modelo.parameters(), lr=self.config.tasa_aprendizaje
        )
        self.historial: list = []

    def cargadores(self):
        from torch.utils.data import DataLoader

        corte = 1.0 - self.config.fraccion_validacion
        entrenamiento = CorpusDeMascaras(self.config.carpeta_corpus, hasta=corte)
        validacion = CorpusDeMascaras(self.config.carpeta_corpus, desde=corte)
        return (
            DataLoader(entrenamiento, batch_size=self.config.tamano_lote, shuffle=True),
            DataLoader(validacion, batch_size=self.config.tamano_lote),
        )

    def entrenar(self):
        import time

        from divieat_ticket.modelo.entrenamiento import RegistroEpoca

        entrenamiento, validacion = self.cargadores()
        print(f"corpus: {len(entrenamiento.dataset)} entrenamiento · "
              f"{len(validacion.dataset)} validacion", flush=True)
        mejor_iou, sin_mejorar = -1.0, 0

        for epoca in range(1, self.config.epocas + 1):
            inicio = time.perf_counter()
            perdida_entrenamiento, iou_entrenamiento = self._una_epoca(entrenamiento, entrenar=True)
            perdida_validacion, iou_validacion = self._una_epoca(validacion, entrenar=False)
            registro = RegistroEpoca(
                epoca, perdida_entrenamiento, perdida_validacion,
                1 - iou_entrenamiento, 1 - iou_validacion, time.perf_counter() - inicio,
            )
            self.historial.append(registro)
            print(f"epoca {epoca:>2} · perdida {perdida_entrenamiento:.4f}/{perdida_validacion:.4f}"
                  f" · IoU {iou_entrenamiento:.4f}/{iou_validacion:.4f} · "
                  f"{registro.segundos:5.1f}s", flush=True)

            if iou_validacion > mejor_iou + 1e-4:
                mejor_iou, sin_mejorar = iou_validacion, 0
                self.guardar(self.config.ruta_checkpoint, iou_validacion)
            else:
                sin_mejorar += 1
                if sin_mejorar >= self.config.paciencia:
                    print(f"sin mejora en {sin_mejorar} epocas: detengo", flush=True)
                    break
        return self.historial

    def _una_epoca(self, cargador, entrenar: bool) -> tuple[float, float]:
        self.modelo.train() if entrenar else self.modelo.eval()
        perdidas, ious = [], []
        contexto = torch.enable_grad() if entrenar else torch.no_grad()
        with contexto:
            for imagenes, mascaras, _ in cargador:
                imagenes = imagenes.to(self.dispositivo)
                mascaras = mascaras.to(self.dispositivo)
                logits = self.modelo(imagenes)
                perdida = self.criterio(logits, mascaras)
                if entrenar:
                    self.optimizador.zero_grad(set_to_none=True)
                    perdida.backward()
                    self.optimizador.step()
                perdidas.append(perdida.item())
                ious.append(interseccion_sobre_union(logits.detach(), mascaras))
        return float(np.mean(perdidas)), float(np.mean(ious))

    def guardar(self, ruta: Path, iou: float) -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"estado": self.modelo.state_dict(), "base": self.config.base, "iou": iou}, ruta)
        return ruta
