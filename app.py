"""
app.py
-------------------------------------------------------------------
Monitor de Salud Financiera — Dashboard conductual de finanzas personales.

Filosofía: el ahorro es un MÚSCULO que se entrena a diario. El módulo
central, "Calistenia Financiera", mide rachas de días consecutivos sin
"Gasto Hormiga" y conecta esa disciplina con su costo de oportunidad real.

Ejecutar:
    streamlit run app.py

Requisitos:
    pip install streamlit pandas plotly
-------------------------------------------------------------------
"""

import os
import sqlite3

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from generar_db import generar_base_datos, DB_PATH

# --------------------------------------------------------------------------- #
# 1) PALETA "QUIET WEALTH" Y CONFIGURACIÓN DE PÁGINA
# --------------------------------------------------------------------------- #
NAVY = "#1B2A4A"        # Azul marino — color ancla, sobrio
NAVY_SUAVE = "#2E4063"  # Navy más claro para acentos
OLIVO = "#6B7B3A"       # Verde olivo — éxito / días invictos
OLIVO_CLARO = "#9CAA6E"
BEIGE = "#EDE8DC"       # Beige — fondos y neutros
BEIGE_OSCURO = "#D9D2C2"
BLANCO = "#FFFFFF"
TINTA = "#33373D"       # Texto principal

st.set_page_config(
    page_title="Monitor de Salud Financiera",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS para reforzar la estética minimalista (no se usa f-string por las llaves).
st.markdown(
    """
    <style>
        .stApp { background-color: #FBFAF6; color: #33373D; }
        /* Tipografía sobria */
        html, body, [class*="css"] { font-family: 'Inter', 'Helvetica Neue', sans-serif; }
        /* Tarjetas de métricas */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF;
            border: 1px solid #E4DFD2;
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: 0 1px 3px rgba(27,42,74,0.05);
        }
        div[data-testid="stMetricLabel"] p {
            color: #7A7567; font-weight: 600; letter-spacing: .3px;
            text-transform: uppercase; font-size: .72rem;
        }
        div[data-testid="stMetricValue"] { color: #1B2A4A; font-weight: 700; }
        /* Encabezados */
        h1, h2, h3 { color: #1B2A4A; font-weight: 700; }
        /* Pestañas */
        button[data-baseweb="tab"] { font-weight: 600; }
        .stTabs [aria-selected="true"] { color: #6B7B3A; }
        /* Sidebar */
        section[data-testid="stSidebar"] { background-color: #F3F0E8; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# 2) CARGA DE DATOS
# --------------------------------------------------------------------------- #
@st.cache_data
def cargar_datos():
    """Carga las transacciones desde SQLite; genera la BD si no existe."""
    if not os.path.exists(DB_PATH):
        generar_base_datos(DB_PATH)
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM transacciones", conn, parse_dates=["fecha"])
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.normalize()
    return df.sort_values("fecha").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 3) LÓGICA CONDUCTUAL: RACHAS ("CALISTENIA FINANCIERA")
# --------------------------------------------------------------------------- #
def construir_calendario_dias(df, hoy):
    """
    Construye un calendario continuo (un renglón por día) desde el primer
    movimiento hasta 'hoy', marcando cada día como invicto o no.

    Un día es INVICTO si NO registró ningún 'Gasto Hormiga'.
    (Un día sin transacciones también cuenta como invicto: no hubo fuga.)

    Nota: anclamos 'hoy' al último día de los datos para que el demo sea
    estable. En una app con datos reales usarías pd.Timestamp.today().
    """
    inicio = df["fecha"].min()
    rango = pd.date_range(inicio, hoy, freq="D")
    dias_hormiga = set(df.loc[df["categoria"] == "Gasto Hormiga", "fecha"])

    cal = pd.DataFrame({"fecha": rango})
    cal["invicto"] = ~cal["fecha"].isin(dias_hormiga)
    return cal


def calcular_rachas(cal):
    """Devuelve (racha_actual, racha_maxima) a partir del calendario de días."""
    invictos = cal["invicto"].tolist()

    # Racha actual: días invictos consecutivos terminando en 'hoy'.
    racha_actual = 0
    for inv in reversed(invictos):
        if inv:
            racha_actual += 1
        else:
            break

    # Racha máxima histórica.
    racha_maxima = mejor = 0
    for inv in invictos:
        mejor = mejor + 1 if inv else 0
        racha_maxima = max(racha_maxima, mejor)

    return racha_actual, racha_maxima


def mensaje_motivacion(racha_actual, racha_maxima):
    """Mensaje dinámico que refuerza la disciplina como entrenamiento diario."""
    if racha_actual == 0:
        return ("🌱 Hoy es el día 1. Cada músculo se construye con la primera "
                "repetición. Mantente invicto y empieza tu racha.")
    if racha_actual < 4:
        return (f"💪 Llevas {racha_actual} días entrenando tu disciplina. "
                "Las primeras repeticiones son las que más cuestan: sigue firme.")
    if racha_actual < 8:
        return (f"🔥 {racha_actual} días invicto. Tu autocontrol ya es un hábito "
                "en formación. La constancia es el verdadero interés compuesto.")
    if racha_actual >= racha_maxima and racha_maxima > 0:
        return (f"🏆 ¡{racha_actual} días! Estás en tu mejor racha histórica. "
                "Tu yo del futuro te lo va a agradecer.")
    return (f"🌿 {racha_actual} días de calma financiera. Tu récord es de "
            f"{racha_maxima}; el músculo está fuerte. Vas por buen camino.")


# --------------------------------------------------------------------------- #
# 4) MÉTRICAS Y COSTO DE OPORTUNIDAD
# --------------------------------------------------------------------------- #
def calcular_metricas(df):
    """Ingresos, egresos y saldo del periodo."""
    ingresos = df.loc[df["tipo"] == "Ingreso", "monto"].sum()
    egresos = df.loc[df["tipo"] == "Egreso", "monto"].sum()
    return ingresos, egresos, ingresos - egresos


def costo_oportunidad(df, racha_actual, anios, tasa_anual):
    """
    Traduce la racha en impacto financiero real.

    - y_evitado: dinero NO fugado durante la racha actual
      (promedio diario de gasto hormiga × días de racha).
    - z_invertido: valor futuro si ese ahorro mensual se invirtiera de forma
      recurrente durante 'anios' a 'tasa_anual' (valor futuro de una anualidad).
    """
    hormiga = df.loc[df["categoria"] == "Gasto Hormiga"]
    dias_con_hormiga = hormiga["fecha"].nunique()
    total_hormiga = hormiga["monto"].sum()

    promedio_diario = (total_hormiga / dias_con_hormiga) if dias_con_hormiga else 0.0
    y_evitado = promedio_diario * racha_actual
    ahorro_mensual = promedio_diario * 30

    # Valor futuro de una anualidad (aportaciones mensuales).
    i = tasa_anual / 12
    n = anios * 12
    if i > 0:
        z_invertido = ahorro_mensual * (((1 + i) ** n - 1) / i)
    else:
        z_invertido = ahorro_mensual * n

    return promedio_diario, y_evitado, z_invertido, ahorro_mensual


# --------------------------------------------------------------------------- #
# 5) VISUALIZACIONES
# --------------------------------------------------------------------------- #
def crear_heatmap_rachas(cal):
    """
    Mapa de calor estilo "contribuciones de GitHub":
      - Columnas = semanas, Renglones = día de la semana (Lun arriba).
      - Verde olivo = día invicto; beige = día con gasto hormiga.
    """
    cal = cal.copy()
    # Alineamos el inicio al lunes de esa semana para una cuadrícula limpia.
    inicio_grid = cal["fecha"].min() - pd.Timedelta(days=cal["fecha"].min().weekday())
    cal["semana"] = ((cal["fecha"] - inicio_grid).dt.days // 7).astype(int)
    cal["dia_sem"] = cal["fecha"].dt.weekday  # 0=Lun ... 6=Dom

    n_semanas = int(cal["semana"].max()) + 1
    z = [[None] * n_semanas for _ in range(7)]
    hover = [[""] * n_semanas for _ in range(7)]

    for _, r in cal.iterrows():
        fila, col = int(r["dia_sem"]), int(r["semana"])
        z[fila][col] = 1 if r["invicto"] else 0
        estado = "Invicto ✅" if r["invicto"] else "Gasto hormiga 🐜"
        hover[fila][col] = f"{r['fecha'].strftime('%d %b %Y')}<br>{estado}"

    dias_label = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            customdata=hover,
            hovertemplate="%{customdata}<extra></extra>",
            colorscale=[[0.0, BEIGE_OSCURO], [1.0, OLIVO]],
            zmin=0, zmax=1,
            xgap=3, ygap=3,
            showscale=False,
        )
    )

    # Etiquetas de mes en el eje X (en la columna donde cae cada día 1).
    tickvals, ticktext = [], []
    for mes, grupo in cal.groupby(cal["fecha"].dt.to_period("M")):
        col = int(grupo["semana"].min())
        if col not in tickvals:
            tickvals.append(col)
            ticktext.append(grupo["fecha"].min().strftime("%b"))

    fig.update_layout(
        height=230,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(7)),
            ticktext=dias_label,
            autorange="reversed",   # Lunes arriba
            showgrid=False, zeroline=False,
        ),
        xaxis=dict(
            tickmode="array", tickvals=tickvals, ticktext=ticktext,
            showgrid=False, zeroline=False, side="top",
        ),
        font=dict(color=TINTA, size=12),
    )
    return fig


def crear_donut_egresos(df):
    """Dona interactiva con la distribución del gasto por categoría (solo egresos)."""
    egresos = (
        df[df["tipo"] == "Egreso"]
        .groupby("categoria")["monto"].sum()
        .reset_index()
        .sort_values("monto", ascending=False)
    )
    mapa_color = {
        "Gastos Fijos": NAVY,
        "Deudas": NAVY_SUAVE,
        "Gasto Hormiga": OLIVO,
    }
    fig = px.pie(
        egresos, names="categoria", values="monto", hole=0.62,
        color="categoria", color_discrete_map=mapa_color,
    )
    fig.update_traces(
        textposition="outside",
        textinfo="percent+label",
        marker=dict(line=dict(color=BLANCO, width=2)),
        hovertemplate="%{label}<br>$%{value:,.0f}<br>%{percent}<extra></extra>",
    )
    fig.update_layout(
        height=360, showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA),
        annotations=[dict(text="Egresos", x=0.5, y=0.5,
                          font=dict(size=15, color=NAVY), showarrow=False)],
    )
    return fig


def crear_linea_liquidez(df):
    """Línea de tendencia de la liquidez (saldo acumulado) a lo largo del tiempo."""
    diario = (
        df.assign(neto=df.apply(
            lambda r: r["monto"] if r["tipo"] == "Ingreso" else -r["monto"], axis=1))
        .groupby("fecha")["neto"].sum()
        .reset_index()
    )
    diario["liquidez"] = diario["neto"].cumsum()

    fig = go.Figure(
        go.Scatter(
            x=diario["fecha"], y=diario["liquidez"],
            mode="lines", line=dict(color=NAVY, width=2.5, shape="spline"),
            fill="tozeroy", fillcolor="rgba(107,123,58,0.12)",
            hovertemplate="%{x|%d %b}<br>Liquidez: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#ECE7DA", zeroline=False,
                   tickprefix="$", tickformat=",.0f"),
    )
    return fig


# --------------------------------------------------------------------------- #
# 6) APP — LAYOUT PRINCIPAL
# --------------------------------------------------------------------------- #
def main():
    df = cargar_datos()
    hoy = df["fecha"].max()  # "Hoy" anclado a los datos (demo estable).

    # ---- Sidebar: filtros y supuestos ----
    st.sidebar.title("⚙️ Ajustes")
    st.sidebar.caption("Monitor de Salud Financiera")

    st.sidebar.subheader("Periodo a analizar")
    rango = st.sidebar.date_input(
        "Rango de fechas",
        value=(df["fecha"].min().date(), hoy.date()),
        min_value=df["fecha"].min().date(),
        max_value=hoy.date(),
    )
    if isinstance(rango, tuple) and len(rango) == 2:
        ini, fin = pd.Timestamp(rango[0]), pd.Timestamp(rango[1])
    else:
        ini, fin = df["fecha"].min(), hoy
    df_periodo = df[(df["fecha"] >= ini) & (df["fecha"] <= fin)]

    st.sidebar.subheader("Supuestos de inversión")
    anios = st.sidebar.slider("Horizonte (años)", 1, 30, 10)
    tasa = st.sidebar.slider("Rendimiento anual (%)", 4.0, 15.0, 10.0, step=0.5) / 100

    # ---- Cálculos (rachas SIEMPRE sobre historia completa para continuidad) ----
    cal = construir_calendario_dias(df, hoy)
    racha_actual, racha_maxima = calcular_rachas(cal)
    prom_diario, y_evitado, z_invertido, ahorro_mensual = costo_oportunidad(
        df, racha_actual, anios, tasa
    )
    ingresos, egresos, saldo = calcular_metricas(df_periodo)

    # ====================================================================== #
    # ENCABEZADO
    # ====================================================================== #
    st.title("🌿 Monitor de Salud Financiera")
    st.markdown(
        "<p style='color:#7A7567; font-size:1.05rem; margin-top:-10px;'>"
        "El ahorro es un músculo. Aquí lo entrenas todos los días.</p>",
        unsafe_allow_html=True,
    )

    # ====================================================================== #
    # SECCIÓN 1 — CALISTENIA FINANCIERA (RACHAS)
    # ====================================================================== #
    st.markdown("## 🏋️ Calistenia Financiera")
    col_r1, col_r2, col_cal = st.columns([1, 1, 3])

    with col_r1:
        st.metric("Racha actual", f"{racha_actual} días", help="Días consecutivos sin Gasto Hormiga.")
    with col_r2:
        st.metric("Racha máxima", f"{racha_maxima} días", help="Tu mejor racha histórica.")
    with col_cal:
        st.markdown("**Tu calendario de constancia**")
        st.plotly_chart(crear_heatmap_rachas(cal), use_container_width=True,
                        config={"displayModeBar": False})

    # Mensaje motivacional dinámico.
    st.success(mensaje_motivacion(racha_actual, racha_maxima))

    st.divider()

    # ====================================================================== #
    # SECCIÓN 2 — MÉTRICAS CLAVE Y COSTO DE OPORTUNIDAD
    # ====================================================================== #
    st.markdown("## 📊 Métricas clave")
    m1, m2, m3 = st.columns(3)
    m1.metric("Ingresos totales", f"${ingresos:,.0f}")
    m2.metric("Egresos totales", f"${egresos:,.0f}")
    m3.metric("Saldo disponible", f"${saldo:,.0f}",
              delta=f"{(saldo/ingresos*100 if ingresos else 0):.0f}% de ingresos",
              delta_color="off")  # sin rojos alarmantes

    # Costo de oportunidad conectado a la racha.
    st.markdown(
        f"""
        <div style="background:{BEIGE}; border-left:5px solid {OLIVO};
                    border-radius:12px; padding:18px 22px; margin-top:8px;">
            <div style="color:{NAVY}; font-weight:700; font-size:1.05rem;
                        margin-bottom:6px;">💡 El poder de tu constancia</div>
            <div style="color:{TINTA}; font-size:1rem; line-height:1.6;">
                Tu racha actual de <b>{racha_actual} días</b> ha evitado la fuga de
                <b style="color:{OLIVO};">${y_evitado:,.0f}</b>
                (≈ ${prom_diario:,.0f} de gasto hormiga al día).<br>
                Si reorientaras ese ahorro (~${ahorro_mensual:,.0f} al mes) y lo
                invirtieras durante <b>{anios} años</b>, este esfuerzo equivaldría a
                <b style="color:{NAVY};">${z_invertido:,.0f}</b>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ====================================================================== #
    # SECCIÓN 3 — ANÁLISIS DE EGRESOS (PESTAÑAS)
    # ====================================================================== #
    st.markdown("## 🔍 Análisis")
    tab_dist, tab_liq, tab_tabla = st.tabs(
        ["🍩 Distribución de egresos", "📈 Tendencia de liquidez", "📋 Transacciones"]
    )

    with tab_dist:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.plotly_chart(crear_donut_egresos(df_periodo), use_container_width=True,
                            config={"displayModeBar": False})
        with c2:
            st.markdown("#### Lectura rápida")
            resumen = (
                df_periodo[df_periodo["tipo"] == "Egreso"]
                .groupby("categoria")["monto"].sum().sort_values(ascending=False)
            )
            for cat, val in resumen.items():
                pct = val / resumen.sum() * 100
                st.markdown(f"- **{cat}**: ${val:,.0f}  ·  {pct:.1f}%")
            st.caption("El gasto hormiga suele ser pequeño en cada movimiento, "
                       "pero revelador en el agregado.")

    with tab_liq:
        st.plotly_chart(crear_linea_liquidez(df_periodo), use_container_width=True,
                        config={"displayModeBar": False})
        st.caption("Saldo acumulado (ingresos − egresos) a lo largo del periodo.")

    with tab_tabla:
        st.markdown("#### Auditoría de movimientos")
        f1, f2, f3 = st.columns([2, 2, 3])
        cats = sorted(df_periodo["categoria"].unique())
        sel_cat = f1.multiselect("Categoría", cats, default=cats)
        sel_tipo = f2.multiselect("Tipo", ["Ingreso", "Egreso"], default=["Ingreso", "Egreso"])
        busqueda = f3.text_input("Buscar concepto", "")

        tabla = df_periodo[
            df_periodo["categoria"].isin(sel_cat) & df_periodo["tipo"].isin(sel_tipo)
        ].copy()
        if busqueda:
            tabla = tabla[tabla["concepto"].str.contains(busqueda, case=False, na=False)]

        tabla = tabla.sort_values("fecha", ascending=False)
        tabla["fecha"] = tabla["fecha"].dt.strftime("%Y-%m-%d")

        st.dataframe(
            tabla,
            use_container_width=True,
            hide_index=True,
            column_config={
                "fecha": st.column_config.TextColumn("Fecha"),
                "concepto": st.column_config.TextColumn("Concepto"),
                "categoria": st.column_config.TextColumn("Categoría"),
                "monto": st.column_config.NumberColumn("Monto", format="$%.2f"),
                "tipo": st.column_config.TextColumn("Tipo"),
            },
        )
        st.caption(f"{len(tabla)} movimientos · "
                   f"Total: ${tabla['monto'].sum():,.2f}")

    st.divider()
    st.caption("Monitor de Salud Financiera · Datos simulados · "
               "Construido con Streamlit, Plotly y SQLite.")


if __name__ == "__main__":
    main()
