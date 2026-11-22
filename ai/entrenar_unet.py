import sys
sys.path.insert(0, "src")
from divieat_ticket.modelo.graficas import DiagnosticoDeSobreajuste, GraficadorDeAprendizaje
from divieat_ticket.modelo.segmentacion import ConfiguracionUNet, EntrenadorUNet

entrenador = EntrenadorUNet(ConfiguracionUNet(epocas=24, tamano_lote=8))
print(f"dispositivo: {entrenador.dispositivo} · "
      f"{entrenador.modelo.parametros_entrenables:,} parametros", flush=True)
entrenador.entrenar()
ruta = GraficadorDeAprendizaje(
    entrenador.historial, "U-Net · mascaras de renglon", nombre_metrica="Error de segmentacion (1 - IoU)",
    nombre_perdida="Perdida BCE + Dice"
).figura("figuras/curvas_unet.png")
print(f"\nfigura: {ruta}")
print(DiagnosticoDeSobreajuste(entrenador.historial).veredicto())
