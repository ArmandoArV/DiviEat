"""Entrenamiento de la CRNN con perdida CTC."""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader

from divieat_ticket.modelo.alfabeto import Alfabeto
from divieat_ticket.modelo.crnn import CRNN
from divieat_ticket.modelo.ctc import DecodificadorVoraz
from divieat_ticket.modelo.datos import ConfiguracionLineas, ConjuntoLineas, agrupar_lote
from divieat_ticket.modelo.metricas import TasaDeError


class FuenteDeDatos(ABC):
    """De donde salen los lotes. Permite entrenar con renglones renderizados o
    con los recortes que produce el pipeline real, sin tocar el bucle."""

    @property
    def nombre(self) -> str:
        return type(self).__name__

    @abstractmethod
    def cargadores(
        self, config: "ConfiguracionEntrenamiento", alfabeto: Alfabeto
    ) -> tuple[DataLoader, DataLoader, DataLoader]:
        """Devuelve (entrenamiento, validacion, espejo-de-entrenamiento)."""


class FuenteSintetica(FuenteDeDatos):
    """Renglones renderizados directamente, sin pasar por el preproceso."""

    def cargadores(self, config, alfabeto):
        entrenamiento = ConjuntoLineas(config.muestras_entrenamiento, alfabeto, config.datos)
        validacion = ConjuntoLineas(
            config.muestras_validacion, alfabeto, config.datos, desplazamiento=10**6
        )
        espejo = ConjuntoLineas(
            min(config.muestras_validacion, config.muestras_entrenamiento), alfabeto, config.datos
        )
        comun = dict(collate_fn=agrupar_lote, num_workers=config.trabajadores)
        return (
            DataLoader(entrenamiento, batch_size=config.tamano_lote, shuffle=True, **comun),
            DataLoader(validacion, batch_size=config.tamano_lote, **comun),
            DataLoader(espejo, batch_size=config.tamano_lote, **comun),
        )


class FuenteCorpus(FuenteDeDatos):
    """Recortes reales del pipeline, leidos del disco y partidos por fraccion."""

    def __init__(self, carpeta: str | Path, fraccion_validacion: float = 0.12) -> None:
        self.carpeta = carpeta
        self.fraccion_validacion = fraccion_validacion

    def cargadores(self, config, alfabeto):
        from divieat_ticket.modelo.corpus import CorpusDeRenglones

        corte = 1.0 - self.fraccion_validacion
        entrenamiento = CorpusDeRenglones(self.carpeta, alfabeto, hasta=corte)
        validacion = CorpusDeRenglones(self.carpeta, alfabeto, desde=corte)
        espejo = CorpusDeRenglones(
            self.carpeta, alfabeto, hasta=min(corte, len(validacion) / max(len(entrenamiento), 1))
        )
        comun = dict(collate_fn=agrupar_lote, num_workers=config.trabajadores)
        return (
            DataLoader(entrenamiento, batch_size=config.tamano_lote, shuffle=True, **comun),
            DataLoader(validacion, batch_size=config.tamano_lote, **comun),
            DataLoader(espejo, batch_size=config.tamano_lote, **comun),
        )


class FuenteMixta(FuenteDeDatos):
    """Mezcla recortes reales con sinteticos.

    Los reales son pocos (un centenar) y los sinteticos ilimitados. Entrenar
    solo con los reales sobreajustaria en dos epocas; entrenar solo con
    sinteticos es justo lo que ya se probo y no transfiere. Se repiten los
    reales para que pesen lo suficiente sin que el modelo olvide la variedad
    que aportan los sinteticos.

    La validacion es **solo real**: es la unica cifra que dice algo sobre el
    problema de verdad.
    """

    def __init__(
        self,
        carpeta_real: str | Path,
        carpeta_sintetica: str | Path,
        repeticiones: int = 8,
        sinteticos: int = 2000,
        fraccion_validacion: float = 0.18,
    ) -> None:
        self.carpeta_real = carpeta_real
        self.carpeta_sintetica = carpeta_sintetica
        self.repeticiones = repeticiones
        self.sinteticos = sinteticos
        self.fraccion_validacion = fraccion_validacion

    def cargadores(self, config, alfabeto):
        from torch.utils.data import ConcatDataset, Subset

        from divieat_ticket.modelo.corpus import CorpusDeRenglones

        corte = 1.0 - self.fraccion_validacion
        real_entrenamiento = CorpusDeRenglones(self.carpeta_real, alfabeto, hasta=corte)
        real_validacion = CorpusDeRenglones(self.carpeta_real, alfabeto, desde=corte)
        sinteticos = CorpusDeRenglones(self.carpeta_sintetica, alfabeto)
        muestra = Subset(sinteticos, range(min(self.sinteticos, len(sinteticos))))

        entrenamiento = ConcatDataset([real_entrenamiento] * self.repeticiones + [muestra])
        comun = dict(collate_fn=agrupar_lote, num_workers=config.trabajadores)
        return (
            DataLoader(entrenamiento, batch_size=config.tamano_lote, shuffle=True, **comun),
            DataLoader(real_validacion, batch_size=config.tamano_lote, **comun),
            DataLoader(real_entrenamiento, batch_size=config.tamano_lote, **comun),
        )


@dataclass
class ConfiguracionEntrenamiento:
    epocas: int = 8
    tamano_lote: int = 32
    tasa_aprendizaje: float = 3e-4
    muestras_entrenamiento: int = 8000
    muestras_validacion: int = 600
    dispositivo: str | None = None          # None = elegir solo
    trabajadores: int = 0
    recorte_gradiente: float = 5.0
    ruta_checkpoint: Path = Path("modelos/crnn.pt")
    paciencia: int = 3
    datos: "ConfiguracionLineas | None" = None


@dataclass
class RegistroEpoca:
    """Una fila de la curva de aprendizaje.

    Guardamos la perdida en *ambos* conjuntos: la de entrenamiento sola no
    revela sobreajuste. El sintoma es que la de validacion repunta mientras la
    de entrenamiento sigue bajando.
    """

    epoca: int
    perdida_entrenamiento: float
    perdida_validacion: float
    cer_entrenamiento: float
    cer_validacion: float
    segundos: float

    @property
    def brecha(self) -> float:
        """Cuanto peor le va en validacion que en entrenamiento."""
        return self.perdida_validacion - self.perdida_entrenamiento

    def __str__(self) -> str:
        return (f"epoca {self.epoca:>2} · perdida {self.perdida_entrenamiento:6.3f}"
                f"/{self.perdida_validacion:6.3f} · CER {self.cer_entrenamiento:6.4f}"
                f"/{self.cer_validacion:6.4f} · brecha {self.brecha:+6.3f} · "
                f"{self.segundos:5.1f}s")


class SelectorDeDispositivo:
    """Elige el acelerador disponible: MPS en Apple Silicon, CUDA o CPU."""

    @staticmethod
    def elegir(preferido: str | None = None) -> torch.device:
        if preferido:
            return torch.device(preferido)
        if torch.backends.mps.is_available():
            return torch.device("mps")
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")


class EntrenadorCRNN:
    """Bucle de entrenamiento, validacion por CER y guardado del mejor modelo."""

    def __init__(
        self,
        modelo: CRNN | None = None,
        alfabeto: Alfabeto | None = None,
        config: ConfiguracionEntrenamiento | None = None,
        fuente: FuenteDeDatos | None = None,
    ) -> None:
        self.config = config or ConfiguracionEntrenamiento()
        self.alfabeto = alfabeto or Alfabeto.de_tickets()
        self.fuente = fuente or FuenteSintetica()
        self.dispositivo = SelectorDeDispositivo.elegir(self.config.dispositivo)
        self.modelo = (modelo or CRNN(len(self.alfabeto))).to(self.dispositivo)
        self.criterio = nn.CTCLoss(blank=Alfabeto.BLANCO, zero_infinity=True)
        self.optimizador = torch.optim.AdamW(
            self.modelo.parameters(), lr=self.config.tasa_aprendizaje
        )
        self.decodificador = DecodificadorVoraz(self.alfabeto)
        self.metrica = TasaDeError()
        self.historial: list[RegistroEpoca] = []

    # ------------------------------------------------------------------ datos
    def cargadores(self) -> tuple[DataLoader, DataLoader, DataLoader]:
        """Delegado en la fuente de datos configurada."""
        return self.fuente.cargadores(self.config, self.alfabeto)

    # ------------------------------------------------------------ entrenamiento
    def entrenar(self) -> list[RegistroEpoca]:
        cargador_entrenamiento, cargador_validacion, cargador_espejo = self.cargadores()
        mejor_cer, sin_mejorar = float("inf"), 0

        for epoca in range(1, self.config.epocas + 1):
            inicio = time.perf_counter()
            perdida = self._una_epoca(cargador_entrenamiento)
            perdida_validacion = self.perdida_en(cargador_validacion)
            cer = self.evaluar(cargador_validacion).tasa
            cer_entrenamiento = self.evaluar(cargador_espejo).tasa
            registro = RegistroEpoca(
                epoca, perdida, perdida_validacion, cer_entrenamiento, cer,
                time.perf_counter() - inicio,
            )
            self.historial.append(registro)
            print(registro, flush=True)

            if cer < mejor_cer - 1e-4:
                mejor_cer, sin_mejorar = cer, 0
                self.guardar(self.config.ruta_checkpoint, cer)
            else:
                sin_mejorar += 1
                if sin_mejorar >= self.config.paciencia:
                    print(f"sin mejora en {sin_mejorar} epocas: detengo", flush=True)
                    break
        return self.historial

    def _una_epoca(self, cargador: DataLoader) -> float:
        self.modelo.train()
        acumulada, lotes = 0.0, 0
        for imagenes, objetivos, longitudes, _ in cargador:
            imagenes = imagenes.to(self.dispositivo)
            log_probabilidades = self.modelo(imagenes)
            pasos = log_probabilidades.size(0)
            longitudes_entrada = torch.full(
                (imagenes.size(0),), pasos, dtype=torch.long, device=self.dispositivo
            )
            perdida = self.criterio(
                log_probabilidades,
                objetivos.to(self.dispositivo),
                longitudes_entrada,
                longitudes.to(self.dispositivo),
            )
            self.optimizador.zero_grad(set_to_none=True)
            perdida.backward()
            nn.utils.clip_grad_norm_(self.modelo.parameters(), self.config.recorte_gradiente)
            self.optimizador.step()
            acumulada += perdida.item()
            lotes += 1
        return acumulada / max(lotes, 1)

    @torch.no_grad()
    def perdida_en(self, cargador: DataLoader) -> float:
        """Misma perdida CTC, sin actualizar pesos: es la mitad que falta de la curva."""
        self.modelo.eval()
        acumulada, lotes = 0.0, 0
        for imagenes, objetivos, longitudes, _ in cargador:
            imagenes = imagenes.to(self.dispositivo)
            log_probabilidades = self.modelo(imagenes)
            longitudes_entrada = torch.full(
                (imagenes.size(0),), log_probabilidades.size(0),
                dtype=torch.long, device=self.dispositivo,
            )
            acumulada += self.criterio(
                log_probabilidades, objetivos.to(self.dispositivo),
                longitudes_entrada, longitudes.to(self.dispositivo),
            ).item()
            lotes += 1
        return acumulada / max(lotes, 1)

    @torch.no_grad()
    def evaluar(self, cargador: DataLoader):
        self.modelo.eval()
        predichos: list[str] = []
        verdaderos: list[str] = []
        for imagenes, _, _, textos in cargador:
            salida = self.modelo(imagenes.to(self.dispositivo))
            predichos.extend(self.decodificador.decodificar(salida.cpu()))
            verdaderos.extend(textos)
        return self.metrica.medir(predichos, verdaderos)

    @torch.no_grad()
    def ejemplos(self, cantidad: int = 6) -> list[tuple[str, str]]:
        conjunto = ConjuntoLineas(cantidad, self.alfabeto, desplazamiento=5 * 10**6)
        lote = agrupar_lote([conjunto[i] for i in range(cantidad)])
        self.modelo.eval()
        salida = self.modelo(lote[0].to(self.dispositivo))
        return list(zip(self.decodificador.decodificar(salida.cpu()), lote[3]))

    # ----------------------------------------------------------- persistencia
    def guardar(self, ruta: Path, cer: float) -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "estado": self.modelo.state_dict(),
                "alfabeto": self.alfabeto.caracteres,
                "cer": cer,
                "historial": [vars(r) for r in self.historial],
            },
            ruta,
        )
        return ruta

    @classmethod
    def cargar_modelo(cls, ruta: str | Path, dispositivo: torch.device | None = None):
        """Devuelve (modelo listo para inferencia, alfabeto, cer_guardado)."""
        dispositivo = dispositivo or SelectorDeDispositivo.elegir()
        punto = torch.load(ruta, map_location=dispositivo, weights_only=False)
        alfabeto = Alfabeto(punto["alfabeto"])
        modelo = CRNN(len(alfabeto))
        modelo.load_state_dict(punto["estado"])
        modelo.to(dispositivo).eval()
        return modelo, alfabeto, punto.get("cer")
