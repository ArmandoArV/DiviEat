"""Reconocimiento de texto propio: CNN + BiLSTM + CTC entrenado con datos sinteticos."""

from divieat_ticket.modelo.alfabeto import Alfabeto
from divieat_ticket.modelo.crnn import CRNN
from divieat_ticket.modelo.ctc import DecodificadorCTC

__all__ = ["Alfabeto", "CRNN", "DecodificadorCTC"]
