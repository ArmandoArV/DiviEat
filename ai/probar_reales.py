"""La tuberia sobre fotos reales, contra la verdad transcrita a mano."""
import sys, time
from pathlib import Path
sys.path.insert(0, "src"); sys.path.insert(0, "tests")

from divieat_ticket.dominio import Dinero
from divieat_ticket.modelo.segmentacion import SegmentadorNeuronal
from divieat_ticket.ocr import MotorCRNN, MotorEasyOCR
from divieat_ticket.pipeline import PipelineExtraccionTicket
from divieat_ticket.preproceso import CadenaDePreproceso
from fixtures_reales import MARCELO, AVELINO

VERDAD = {"marcelo": MARCELO, "avelino": AVELINO}
motores = [
    ("CRNN+U-Net v2", MotorCRNN("modelos/crnn_v2_final.pt",
                             segmentador=SegmentadorNeuronal("modelos/unet_v2.pt"))),
    ("EasyOCR", MotorEasyOCR()),
]

for nombre, caso in VERDAD.items():
    ruta = Path("datos/reales") / f"{nombre}.png"
    if not ruta.is_file():
        print(f"{nombre}: falta {ruta}"); continue
    print("=" * 64)
    print(f"{nombre.upper()}  ·  verdad: {caso.productos_esperados} productos · "
          f"{Dinero(caso.total_esperado_centavos)} · mesa {caso.mesa_esperada}")
    print("=" * 64)
    for etiqueta, motor in motores:
        if not motor.disponible():
            print(f"  {etiqueta}: no disponible"); continue
        pipeline = PipelineExtraccionTicket(motor, CadenaDePreproceso.por_defecto())
        t0 = time.perf_counter()
        r = pipeline.procesar_con_trazas(ruta)
        t = r.ticket
        ok_total = t.total_impreso and t.total_impreso.centavos == caso.total_esperado_centavos
        print(f"\n  --- {etiqueta} ({time.perf_counter()-t0:.1f}s) · perfil {r.perfil} · "
              f"{len(r.ocr)} renglones leidos ---")
        print(f"  productos {len(t.productos)}/{caso.productos_esperados} · "
              f"suma {t.suma_productos} · total {t.total_impreso} {'OK' if ok_total else 'MAL'} · "
              f"cuadra {t.cuadra()}")
        print(f"  mesa {t.mesa!r} · comensales {t.comensales} · folio {t.folio!r}")
        for p in t.productos[:12]:
            print(f"     {p}")
    print()
