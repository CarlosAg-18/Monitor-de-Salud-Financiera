"""
generar_db.py
-------------------------------------------------------------------
Genera una base de datos SQLite ('finanzas.db') con transacciones
personales simuladas de los últimos ~3 meses para el dashboard
"Monitor de Salud Financiera".

Diseño de los datos:
  - 4 categorías: Ingresos, Gastos Fijos, Deudas, Gasto Hormiga.
  - Se anclan las fechas a "hoy" para que la racha actual sea relevante.
  - Se inyectan rachas LIMPIAS intencionales (varios días seguidos sin
    "Gasto Hormiga") para poder probar el sistema de rachas:
        * Una racha actual al final del periodo.
        * Una racha máxima histórica más larga en el pasado.
        * Cortes ("breakers") deterministas que delimitan esas rachas.

Uso:
    python generar_db.py
-------------------------------------------------------------------
"""

import sqlite3
import random
from datetime import date, timedelta

import pandas as pd

# --------------------------------------------------------------------------- #
# Configuración global
# --------------------------------------------------------------------------- #
DB_PATH = "finanzas.db"
SEED = 42
DIAS_HISTORIAL = 90  # ~3 meses

random.seed(SEED)

# Catálogo de conceptos por categoría. Cada entrada: (concepto, monto_min, monto_max)
CATALOGO_HORMIGA = [
    ("Café", 45, 75),
    ("Uber", 55, 190),
    ("Tacos", 70, 160),
    ("Snacks", 25, 90),
    ("Refresco", 20, 45),
    ("App Delivery", 140, 320),
    ("Cigarros", 70, 95),
    ("Propina", 30, 60),
    ("Antojo OXXO", 35, 110),
]


def _monto(rango_min, rango_max, decimales=True):
    """Devuelve un monto realista dentro del rango dado."""
    val = random.uniform(rango_min, rango_max)
    return round(val, 2) if decimales else float(round(val))


def _rango_fechas(inicio, fin):
    """Generador de fechas día a día (inclusive)."""
    dia = inicio
    while dia <= fin:
        yield dia
        dia += timedelta(days=1)


def generar_transacciones():
    """
    Construye la lista de transacciones simuladas.

    Returns:
        pd.DataFrame con columnas: fecha, concepto, categoria, monto, tipo
    """
    fin = date.today()
    inicio = fin - timedelta(days=DIAS_HISTORIAL - 1)
    transacciones = []

    # ------------------------------------------------------------------ #
    # 1) INGRESOS Y MOVIMIENTOS FIJOS (mensuales / quincenales)
    # ------------------------------------------------------------------ #
    # Recorremos cada día y disparamos los movimientos recurrentes según
    # el día del mes en que ocurren.
    for dia in _rango_fechas(inicio, fin):
        dom = dia.day  # día del mes

        # Nómina quincenal (los días 15 y fin de mes ~30)
        if dom == 15 or dom == 30:
            transacciones.append(
                (dia, "Nómina", "Ingresos", _monto(8800, 9600), "Ingreso")
            )
        # Ingreso freelance ocasional a mitad de mes
        if dom == 22 and random.random() < 0.7:
            transacciones.append(
                (dia, "Proyecto Freelance", "Ingresos", _monto(1500, 4500), "Ingreso")
            )

        # --- Gastos fijos ---
        if dom == 2:
            transacciones.append((dia, "Renta", "Gastos Fijos", _monto(6500, 6500), "Egreso"))
        if dom == 5:
            transacciones.append((dia, "Spotify", "Gastos Fijos", 115.0, "Egreso"))
            transacciones.append((dia, "Netflix", "Gastos Fijos", 219.0, "Egreso"))
        if dom == 7:
            transacciones.append((dia, "Internet", "Gastos Fijos", 499.0, "Egreso"))
        if dom == 10:
            transacciones.append((dia, "Gimnasio", "Gastos Fijos", 450.0, "Egreso"))
        if dom == 18:
            transacciones.append((dia, "Luz (CFE)", "Gastos Fijos", _monto(280, 520), "Egreso"))

        # --- Deudas ---
        if dom == 4:
            transacciones.append((dia, "Tarjeta de Crédito", "Deudas", _monto(1400, 1900), "Egreso"))
        if dom == 12:
            transacciones.append((dia, "Pago Préstamo", "Deudas", 1200.0, "Egreso"))
        if dom == 20:
            transacciones.append((dia, "MSI Pantalla", "Deudas", 833.0, "Egreso"))

    # ------------------------------------------------------------------ #
    # 2) GASTO HORMIGA con rachas LIMPIAS intencionales
    # ------------------------------------------------------------------ #
    # Definimos conjuntos de días "limpios" forzados (sin gasto hormiga)
    # y días "rompe-racha" forzados (con al menos un gasto hormiga) para
    # que el sistema de rachas sea fácilmente verificable.
    dias_limpios_forzados = set()
    dias_breaker_forzados = set()

    # (a) Racha ACTUAL: últimos 6 días limpios -> termina "hoy".
    for offset in range(0, 6):
        dias_limpios_forzados.add(fin - timedelta(days=offset))
    # Rompemos justo antes para que la racha actual sea exactamente 6.
    dias_breaker_forzados.add(fin - timedelta(days=6))

    # (b) Racha MÁXIMA histórica: 14 días limpios en el pasado.
    racha_max_fin = fin - timedelta(days=27)
    for offset in range(0, 14):
        dias_limpios_forzados.add(racha_max_fin - timedelta(days=offset))
    # Breakers que delimitan la racha máxima por ambos lados.
    dias_breaker_forzados.add(racha_max_fin + timedelta(days=1))
    dias_breaker_forzados.add(racha_max_fin - timedelta(days=14))

    # (c) Una racha media de 4 días en otra zona del calendario.
    racha_media_fin = fin - timedelta(days=55)
    for offset in range(0, 4):
        dias_limpios_forzados.add(racha_media_fin - timedelta(days=offset))
    dias_breaker_forzados.add(racha_media_fin + timedelta(days=1))
    dias_breaker_forzados.add(racha_media_fin - timedelta(days=4))

    for dia in _rango_fechas(inicio, fin):
        if dia in dias_limpios_forzados:
            # Día invicto forzado: no se registra gasto hormiga.
            continue

        if dia in dias_breaker_forzados:
            # Día rompe-racha forzado: garantizamos al menos un gasto hormiga.
            n_gastos = random.choice([1, 2])
        else:
            # Día normal: 0-3 gastos hormiga (0 también genera días limpios
            # de forma natural y realista).
            n_gastos = random.choices([0, 1, 2, 3], weights=[0.18, 0.42, 0.28, 0.12])[0]

        for _ in range(n_gastos):
            concepto, lo, hi = random.choice(CATALOGO_HORMIGA)
            transacciones.append((dia, concepto, "Gasto Hormiga", _monto(lo, hi), "Egreso"))

    # ------------------------------------------------------------------ #
    # 2.5) Anclaje del último día
    # ------------------------------------------------------------------ #
    # Los días limpios del final del periodo pueden no tener NINGUNA
    # transacción (ni hormiga ni fija). Si eso ocurre justo en 'fin',
    # el calendario se truncaría y subestimaría la racha actual.
    # Insertamos un micro-ingreso neutral (no es gasto hormiga, así que
    # el día sigue contando como "invicto") para anclar el periodo.
    transacciones.append(
        (fin, "Cashback Tarjeta", "Ingresos", _monto(20, 60), "Ingreso")
    )

    # ------------------------------------------------------------------ #
    # 3) Armado del DataFrame
    # ------------------------------------------------------------------ #
    df = pd.DataFrame(
        transacciones, columns=["fecha", "concepto", "categoria", "monto", "tipo"]
    )
    df["fecha"] = pd.to_datetime(df["fecha"])
    df = df.sort_values("fecha").reset_index(drop=True)
    return df


def generar_base_datos(db_path=DB_PATH):
    """Genera el DataFrame y lo persiste en SQLite en la tabla 'transacciones'."""
    df = generar_transacciones()
    with sqlite3.connect(db_path) as conn:
        df.to_sql("transacciones", conn, if_exists="replace", index=False)
    return df


if __name__ == "__main__":
    df = generar_base_datos()
    print(f"✅ Base de datos '{DB_PATH}' generada con {len(df)} transacciones.")
    print(f"   Rango: {df['fecha'].min().date()} → {df['fecha'].max().date()}")
    print("\nResumen por categoría:")
    print(df.groupby("categoria")["monto"].agg(["count", "sum"]).round(2))
