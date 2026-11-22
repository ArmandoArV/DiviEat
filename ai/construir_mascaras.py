import sys
sys.path.insert(0, "src")
from divieat_ticket.modelo.segmentacion import ConstructorDeMascaras

cantidad = int(sys.argv[1]) if len(sys.argv) > 1 else 700
print(f"generando {cantidad} pares imagen/mascara", flush=True)
print(ConstructorDeMascaras("datos/corpus_mascaras").construir(cantidad))
