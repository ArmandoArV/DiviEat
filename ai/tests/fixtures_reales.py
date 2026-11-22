"""Transcripcion de tickets reales de restaurantes de Merida, Yucatan.

Son la verdad de referencia del parser: el texto es el que imprime el POS, y
los totales son los que trae el papel. Sirven para medir el analisis sin
depender de que haya un motor OCR instalado.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TicketReal:
    nombre: str
    pos: str
    lineas: tuple[str, ...]
    productos_esperados: int
    total_esperado_centavos: int
    mesa_esperada: str | None = None
    comensales_esperados: int | None = None


MIYABI = TicketReal(
    nombre="miyabi",
    pos="PerfilMiyabi",
    productos_esperados=11,
    total_esperado_centavos=165000,
    mesa_esperada="42",
    comensales_esperados=4,
    lineas=(
        "MIYABI",
        "RESTAURANTES MIYABI S. DE R.L.  DE C.V.",
        "RFC RMI150915DU6",
        "CALLE 13 NUM 80 COL MEXICO MERIDA YUCATAN MER",
        "IDA YUCATAN MEXICO CP 97125 Tel. 285-3",
        "8-69",
        "=" * 44,
        "MESA: 42            FOLIO NO.      151747",
        "MESERO: 71 RICARDO",
        "24/10/2026                   05:46:23 PM",
        "PERSONAS: 4",
        "                    ORDEN NO.          29",
        "=" * 44,
        "CANT. DESCRIPCION                 IMPORTE",
        "1    AMSTEL ULTRA           $      75.00",
        "1    CALPIS                 $      70.00",
        "1    CAMARONES ROCA         $     315.00",
        "1    COCA COLA              $      60.00",
        "2    GOHAN                  $     140.00",
        "1    GYU DON                $     295.00",
        "1    LIMONADA NATURAL       $      65.00",
        "1    NIGUIRI CARACOL        $      65.00",
        "1    ROLLO NAGUISA          $     250.00",
        "1    ROLLO WAKABA           $     235.00",
        "1    TAMPICO SALAD          $      80.00",
        "                  IVA:         $219.31",
        "                  TOTAL:     $1,650.00",
        "UN MIL SEISCIENTOS CINCUENTA PESOS 00/100 M.N.",
        "FACTURACION A MIYABI.WINGS.FACTURACION@GMAIL.COM",
        "PROPINA NO INCLUIDA",
        "TIP NOT INCLUDED",
        "NO ES UN COMPROBANTE FISCAL",
    ),
)

MARCELO = TicketReal(
    nombre="marcelo",
    pos="PerfilSoftRestaurant",
    productos_esperados=9,
    total_esperado_centavos=117500,
    mesa_esperada="2Y7",
    comensales_esperados=5,
    lineas=(
        "RESTAURANTE MARCELO",
        "C. 6 400, LAS AMERICAS LOCAL 15 MERIDA YUCATAN M",
        "EXICO CP 97302",
        "LUGAR DE EXPEDICION",
        "CALLE 65 NUM 400 PLAZA AKROPOLIS LAS AMERICAS LO",
        "CAL 15 MERIDA YUCATAN",
        "=" * 44,
        "MESA:2Y7",
        "MESERO:MAHOL",
        "PERSONAS:5      ORDEN:154",
        "FOLIO:122903",
        "23/10/2026 08:34:07 PM",
        "23/10/2026 09:53:52 PM",
        "CAJERO:",
        "-" * 44,
        "CANT. DESCRIPCION                  IMPORTE",
        "1     BROCOLI A LAS BRASAS         $160.00",
        "1     LIMONADA NATURAL              $50.00",
        "1     COCA COLA                     $50.00",
        "1     FRESCA                        $50.00",
        "1     COCA  COLA LIGHT              $50.00",
        "1     AMSTEL ULTRA                  $70.00",
        "3     CHAPATA ARRACHERA            $600.00",
        "1     LATTE DE SABOR FRIO           $70.00",
        "1     DIRTY  CHAI EN LAS R          $75.00",
        "-" * 44,
        "TOTAL:          $1,175.00",
        "=" * 44,
        "SON:UN MIL CIENTO SETENTA Y CINCO PESOS 00/100 M",
        ".N.",
        "SUBTOTAL:$1,012.93   IVA:$162.07",
        "ESTE NO ES UN COMPROBANTE FISCAL",
        "Si requiere factura, escanee el codigo QR o",
        "ingrese a la siguiente pagina",
        "https://mefacturo.com/restaurantemarcelo",
        "CODIGO FACT: 33267LARAXGLF",
        "FOLIO: 122903",
        "DIAS VIGENCIA: ULTIMO DIA DEL MES",
        "***SOFT RESTAURANT V12 PRO***",
    ),
)

AVELINO = TicketReal(
    nombre="avelino",
    pos="PerfilSoftRestaurant",
    productos_esperados=4,
    total_esperado_centavos=42200,
    mesa_esperada="SALA4",
    comensales_esperados=2,
    lineas=(
        "AVELINO & MARIA",
        "OPERADORA MONTES MOLINA",
        "RFC:OMM200309S39",
        "CALLE 56 A NO.  469 ENTRE 35 Y 37 COL. CENT",
        "RO MER",
        "IDA YUCATAN MEXICO CP 97000",
        "LUGAR DE EXPEDICION",
        ". MERIDA YUCATAN",
        "TEL:9992779230",
        "=" * 44,
        "MESA:SALA4",
        "MESERO:DIEGO BRISENO",
        "PERSONAS:2      ORDEN:72",
        "FOLIO:69916",
        "23/10/2026 04:55:32 PM",
        "23/10/2026 05:11:29 PM",
        "CAJERO:",
        "-" * 44,
        "CANT. DESCRIPCION                  IMPORTE",
        "1     CHOCOLATE CHIAPANECO          $89.00",
        "1     COCA COLA LIGHT               $65.00",
        "1     HORCHATA CAFE                $129.00",
        "1     STRUDELL DE MANZANA          $139.00",
        "-" * 44,
        "TOTAL:            $422.00",
        "=" * 44,
        "SON:CUATROCIENTOS VEINTIDOS PESOS 00/100 M",
        ".N.        PROPINA NO INCLUIDA",
        "SUBTOTAL:$363.79    IVA:$58.21",
        "CUENTA CON 48HRS PARA SOLICITAR SU FACTURA",
        "LA VIGENCIA DEL TICKET ES",
        "DURANTE EL MES, POSTERIORMENTE",
        "NO SERA POSIBLE GENERAR LA FACTURA.",
        "https://mefacturo.mx/avelino",
        "CODIGO FACT: 189157LAREUL5X",
        "FOLIO: 69916",
        "DIAS VIGENCIA: 7",
        "***SOFT RESTAURANT V11 PRO***",
    ),
)

TODOS = (MIYABI, MARCELO, AVELINO)


CHILANGUITA = TicketReal(
    nombre="chilanguita",
    pos="PerfilSoftRestaurant",
    productos_esperados=2,          # las cortesias de $0.00 no cuentan como consumo
    total_esperado_centavos=136000,
    mesa_esperada="33",
    comensales_esperados=3,
    lineas=(
        "LA CHILANGUITA",
        "GRUPO GUAVOS",
        "RFC:GGU160906NK5",
        "AV. DIEGO DE ORDAZ 22 COL. REAL DE SAN",
        "JOSE JIUTEPEC MORELOS MEXICO CP 62563",
        "SUCURSAL:AUTOPISTA MEXICO-ACAPULCO S/N L-7 KM 87",
        ".5, FLORES MAGON CUERNAVACA MORELOS",
        "=" * 44,
        "MESA:33              MESERO:LETICIA ARCADEO MEJIA",
        "          FOLIO:61937",
        "       10/08/2024 09:47:01 PM",
        "PERSONAS:3                    ORDEN:76",
        "=" * 44,
        "CANT.DESCRIPCION              IMPORTE",
        "1    BARCO CHILANGUITA PR      $410.00",
        "1    B. BACARDI BLANCO 75      $950.00",
        "     COCA COLA 355 ML (5.0 X)",
        "          $0.00",
        "     SOLO REFRESCO ( 5 )        $0.00",
        "          SUBTOTAL:   $1,172.41",
        "          IVA         $187.59",
        "          TOTAL:    $1,360.00",
        "SON:UN MIL TRESCIENTOS SESENTA PESOS 00/10",
        "0 M.N.",
        "GRACIAS POR SU PREFERENCIA",
        "ESTE NO ES UN COMPROBANTE FISCAL.",
        "***SOFT RESTAURANT V10 ***",
    ),
)

BRAAIASAO = TicketReal(
    nombre="braaiasao",
    pos="PerfilSoftRestaurant",
    productos_esperados=2,
    total_esperado_centavos=179700,
    mesa_esperada="56",
    comensales_esperados=3,
    lineas=(
        "BRAAIASAO",
        "RESTAURANTES BRAAIASAO S.A. DE C.V.",
        "RFC:RBR170726943",
        "PRIVADA SINALOA NUM.1, AVENIDA SAN DIEGO, COLONI",
        "A VISTA HERMOSA CUERNAVACA MORELOS MEXICO CP 622",
        "0",
        "LUGAR DE EXPEDICION",
        "PRIV. SINALOA 1 ESQ AV. SAN DIEGO COL. VISTA HER",
        "MOSA CP. 62290 CUERNAVACA MORELOS CP 62290",
        "TEL:7773100500",
        "-" * 44,
        "MESA:56.",
        "MESERO:LUIS",
        "PERSONAS:3      ORDEN:33",
        "FOLIO:2699",
        "07/03/2026 04:23:57 PM",
        "07/03/2026 05:20:10 PM",
        "CAJERO:",
        "-" * 44,
        "CANT. DESCRIPCION                IMPORTE",
        "1     JARRA DE CLERICOT FRUTO      $330.00",
        "3     BUFFET DE CORTES ADULTO    $1,467.00",
        "-" * 44,
        "TOTAL:        $1,797.00",
    ),
)

TODOS = (MIYABI, MARCELO, AVELINO, CHILANGUITA, BRAAIASAO)
