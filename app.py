"""
app.py
-------------------------------------------------------------------
Monitor de Salud Financiera — Dashboard conductual de finanzas personales.

Filosofía: el ahorro es un MÚSCULO que se entrena a diario. El dashboard
sigue una narrativa (data storytelling) en cuatro actos:

  1. EL GANCHO    -> tu racha y el dinero que ya te ahorró.
  2. DÓNDE ESTÁS  -> KPIs con el "gasto hormiga" como protagonista.
  3. TRAYECTORIA  -> cómo evolucionó tu saldo en el tiempo.
  4. EVIDENCIA    -> tabla auditable de movimientos.

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
# PALETA "QUIET WEALTH"
# --------------------------------------------------------------------------- #
NAVY = "#1B2A4A"          # Azul marino — ancla sobria
NAVY_SUAVE = "#3A4D6E"
OLIVO = "#6B7B3A"         # Verde olivo — el "logro" (día invicto)
OLIVO_CLARO = "#9CAA6E"
BEIGE = "#EDE8DC"
BEIGE_OSCURO = "#D9D2C2"
CLAY_CLARO = "#EAE0CE"    # Arena cálida — fuga pequeña
CLAY = "#A8703C"          # Terracota apagada (NO roja) — fuga grande
BLANCO = "#FFFFFF"
TINTA = "#33373D"

# Supuestos de proyección (fijos y transparentes; ya no son sliders sueltos).
ANIOS_PROYECCION = 10
TASA_ANUAL = 0.10

# --------------------------------------------------------------------------- #
# CONFIGURACIÓN DE PÁGINA + CSS
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Monitor de Salud Financiera",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp { background-color: #FBFAF6; color: #33373D; }
        html, body, [class*="css"] { font-family: 'Inter', 'Helvetica Neue', sans-serif; }
        h1, h2, h3 { color: #1B2A4A; font-weight: 700; }

        /* Tarjetas de métrica */
        div[data-testid="stMetric"] {
            background-color: #FFFFFF; border: 1px solid #E4DFD2;
            border-radius: 14px; padding: 16px 18px;
            box-shadow: 0 1px 3px rgba(27,42,74,0.05);
        }
        div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] p {
            color: #6E6A5E !important; opacity: 1 !important;
            font-weight: 600; letter-spacing: .3px;
            text-transform: uppercase; font-size: .70rem;
        }
        div[data-testid="stMetricValue"] { color: #1B2A4A !important; font-weight: 700; }

        /* Contenedores con borde = "paneles" que agrupan la narrativa */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF; border-radius: 18px;
            border: 1px solid #E7E1D3 !important;
        }
        section[data-testid="stSidebar"] { background-color: #F3F0E8; }
        section[data-testid="stSidebar"] * { color: #33373D; }
        button[data-baseweb="tab"] { font-weight: 600; }
        .stTabs [aria-selected="true"] { color: #6B7B3A; }

        /* Cápsula de "insight" para el storytelling */
        .insight {
            background: #F4F1E8; border-left: 5px solid #6B7B3A;
            border-radius: 12px; padding: 16px 20px; margin: 4px 0 2px 0;
            font-size: 1rem; line-height: 1.6; color: #33373D;
        }
        .seccion-intro { color: #7A7567; font-size: .98rem; margin: -6px 0 14px 0; }
        .legend-row { display: flex; gap: 22px; align-items: center;
                      flex-wrap: wrap; margin-top: 6px; font-size: .82rem; color:#5F5B50; }
        .swatch { width: 14px; height: 14px; border-radius: 3px;
                  display: inline-block; vertical-align: middle; margin-right: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# DATOS
# --------------------------------------------------------------------------- #
@st.cache_data
def cargar_datos():
    if not os.path.exists(DB_PATH):
        generar_base_datos(DB_PATH)
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql("SELECT * FROM transacciones", conn, parse_dates=["fecha"])
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.normalize()
    return df.sort_values("fecha").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# LÓGICA DE RACHAS + GASTO HORMIGA DIARIO (para el heatmap por intensidad)
# --------------------------------------------------------------------------- #
def construir_calendario_dias(df, hoy):
    """
    Calendario continuo día a día con: invicto (sin gasto hormiga) y el monto
    de gasto hormiga de ese día (para colorear el heatmap por intensidad).
    'hoy' se ancla al último día de los datos (demo estable).
    """
    inicio = df["fecha"].min()
    rango = pd.date_range(inicio, hoy, freq="D")

    hormiga = df[df["categoria"] == "Gasto Hormiga"]
    gasto_por_dia = hormiga.groupby("fecha")["monto"].sum()

    cal = pd.DataFrame({"fecha": rango})
    cal["gasto"] = cal["fecha"].map(gasto_por_dia).fillna(0.0)
    cal["invicto"] = cal["gasto"] == 0
    return cal


def calcular_rachas(cal):
    invictos = cal["invicto"].tolist()
    actual = 0
    for inv in reversed(invictos):
        if inv:
            actual += 1
        else:
            break
    maxima = mejor = 0
    for inv in invictos:
        mejor = mejor + 1 if inv else 0
        maxima = max(maxima, mejor)
    return actual, maxima


def mensaje_motivacion(racha_actual, racha_maxima):
    if racha_actual == 0:
        return ("🌱 Hoy es el día 1. Cada músculo se construye con la primera "
                "repetición. Mantente invicto y arranca tu racha.")
    if racha_actual < 4:
        return (f"💪 Llevas {racha_actual} días entrenando tu disciplina. "
                "Las primeras repeticiones son las que más cuestan: sigue firme.")
    if racha_actual < 8:
        return (f"🔥 {racha_actual} días invicto. Tu autocontrol ya es un hábito "
                "en formación. La constancia es el verdadero interés compuesto.")
    if racha_actual >= racha_maxima and racha_maxima > 0:
        return (f"🏆 ¡{racha_actual} días! Estás en tu mejor racha histórica. "
                "Tu yo del futuro te lo va a agradecer.")
    return (f"🌿 {racha_actual} días de calma financiera. Tu récord es {racha_maxima}; "
            "el músculo está fuerte. Vas por buen camino.")


# --------------------------------------------------------------------------- #
# MÉTRICAS Y COSTO DE OPORTUNIDAD
# --------------------------------------------------------------------------- #
def calcular_metricas(df):
    ingresos = df.loc[df["tipo"] == "Ingreso", "monto"].sum()
    egresos = df.loc[df["tipo"] == "Egreso", "monto"].sum()
    hormiga = df.loc[df["categoria"] == "Gasto Hormiga", "monto"].sum()
    return ingresos, egresos, ingresos - egresos, hormiga


def costo_oportunidad(df, racha_actual):
    """Traduce la racha en impacto: dinero evitado hoy y su valor invertido."""
    hormiga = df.loc[df["categoria"] == "Gasto Hormiga"]
    dias = hormiga["fecha"].nunique()
    prom_diario = (hormiga["monto"].sum() / dias) if dias else 0.0
    y_evitado = prom_diario * racha_actual
    ahorro_mensual = prom_diario * 30

    i, n = TASA_ANUAL / 12, ANIOS_PROYECCION * 12
    z = ahorro_mensual * (((1 + i) ** n - 1) / i) if i > 0 else ahorro_mensual * n
    return prom_diario, y_evitado, ahorro_mensual, z


# --------------------------------------------------------------------------- #
# VISUALIZACIONES
# --------------------------------------------------------------------------- #
def crear_heatmap(cal):
    """
    Calendario tipo GitHub donde el COLOR codifica la fuga diaria:
      - Verde olivo  = día invicto ($0 de gasto hormiga).
      - Arena→terracota = gasto hormiga, más oscuro = más fuga.
    """
    cal = cal.copy()
    inicio_grid = cal["fecha"].min() - pd.Timedelta(days=cal["fecha"].min().weekday())
    cal["semana"] = ((cal["fecha"] - inicio_grid).dt.days // 7).astype(int)
    cal["dia_sem"] = cal["fecha"].dt.weekday

    n_sem = int(cal["semana"].max()) + 1
    z = [[None] * n_sem for _ in range(7)]
    hover = [[""] * n_sem for _ in range(7)]

    for _, r in cal.iterrows():
        fila, col = int(r["dia_sem"]), int(r["semana"])
        z[fila][col] = float(r["gasto"])
        if r["invicto"]:
            estado = "✅ Invicto · $0 de fuga"
        else:
            estado = f"🐜 Gasto hormiga · ${r['gasto']:,.0f}"
        hover[fila][col] = f"{r['fecha'].strftime('%d %b %Y')}<br>{estado}"

    zmax = max(float(cal["gasto"].max()), 1.0)
    # Verde exacto en 0; a partir de ahí, rampa cálida (arena -> terracota).
    colorscale = [[0.0, OLIVO], [1e-6, CLAY_CLARO], [1.0, CLAY]]

    fig = go.Figure(
        go.Heatmap(
            z=z, customdata=hover,
            hovertemplate="%{customdata}<extra></extra>",
            colorscale=colorscale, zmin=0, zmax=zmax,
            xgap=4, ygap=4, showscale=False,
        )
    )

    tickvals, ticktext = [], []
    for _, g in cal.groupby(cal["fecha"].dt.to_period("M")):
        col = int(g["semana"].min())
        if col not in tickvals:
            tickvals.append(col)
            ticktext.append(g["fecha"].min().strftime("%b"))

    fig.update_layout(
        height=220, margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(tickmode="array", tickvals=list(range(7)),
                   ticktext=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
                   autorange="reversed", showgrid=False, zeroline=False),
        xaxis=dict(tickmode="array", tickvals=tickvals, ticktext=ticktext,
                   showgrid=False, zeroline=False, side="top"),
        font=dict(color=TINTA, size=12),
    )
    return fig


def leyenda_heatmap_html():
    """Leyenda explícita para que el heatmap se interprete sin adivinar."""
    return (
        f'<div class="legend-row">'
        f'<span><span class="swatch" style="background:{OLIVO};"></span>'
        f'Día invicto (sin fuga)</span>'
        f'<span><span class="swatch" style="background:{CLAY_CLARO};"></span>'
        f'<span class="swatch" style="background:#C9925C;"></span>'
        f'<span class="swatch" style="background:{CLAY};"></span>'
        f'Gasto hormiga: menos → más</span>'
        f'<span style="color:#8A8576;">Cada cuadro es un día.</span>'
        f'</div>'
    )


def crear_donut(df):
    """Dona de egresos por categoría, con el Gasto Hormiga destacado."""
    eg = (df[df["tipo"] == "Egreso"].groupby("categoria")["monto"].sum()
          .reset_index().sort_values("monto", ascending=False))
    mapa = {"Gastos Fijos": NAVY, "Deudas": NAVY_SUAVE, "Gasto Hormiga": OLIVO}
    # Resaltamos la rebanada protagonista (gasto hormiga) separándola.
    pull = [0.10 if c == "Gasto Hormiga" else 0 for c in eg["categoria"]]

    fig = px.pie(eg, names="categoria", values="monto", hole=0.62,
                 color="categoria", color_discrete_map=mapa)
    fig.update_traces(
        textposition="outside", textinfo="percent+label", pull=pull,
        marker=dict(line=dict(color=BLANCO, width=2)),
        hovertemplate="%{label}<br>$%{value:,.0f} · %{percent}<extra></extra>",
    )
    fig.update_layout(
        height=350, showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color=TINTA),
        annotations=[dict(text="Egresos", x=0.5, y=0.5,
                          font=dict(size=15, color=NAVY), showarrow=False)],
    )
    return fig


def crear_trayectoria_saldo(df):
    """
    Saldo acumulado en el tiempo: sube con ingresos, baja con egresos.
    Anotamos el saldo final y el punto más bajo para dar storytelling.
    """
    diario = (df.assign(neto=df.apply(
                  lambda r: r["monto"] if r["tipo"] == "Ingreso" else -r["monto"], axis=1))
              .groupby("fecha")["neto"].sum().reset_index())
    diario["saldo"] = diario["neto"].cumsum()

    fig = go.Figure(go.Scatter(
        x=diario["fecha"], y=diario["saldo"], mode="lines",
        line=dict(color=NAVY, width=2.6, shape="spline"),
        fill="tozeroy", fillcolor="rgba(107,123,58,0.13)",
        hovertemplate="%{x|%d %b}<br>Saldo: $%{y:,.0f}<extra></extra>",
    ))
    # Línea base en cero.
    fig.add_hline(y=0, line=dict(color="#B9B2A0", width=1, dash="dot"))

    # Anotación: saldo final.
    f_x, f_y = diario["fecha"].iloc[-1], diario["saldo"].iloc[-1]
    fig.add_annotation(x=f_x, y=f_y, text=f"<b>Saldo: ${f_y:,.0f}</b>",
                       showarrow=True, arrowhead=0, ax=-45, ay=-30,
                       font=dict(color=NAVY, size=12),
                       bgcolor="rgba(255,255,255,0.85)",
                       bordercolor=NAVY, borderwidth=1, borderpad=4)
    # Anotación: punto más ajustado (si llegó a estar en negativo).
    idx_min = diario["saldo"].idxmin()
    m_x, m_y = diario["fecha"].iloc[idx_min], diario["saldo"].iloc[idx_min]
    if m_y < 0:
        fig.add_annotation(x=m_x, y=m_y, text=f"Punto más ajustado: ${m_y:,.0f}",
                           showarrow=True, arrowhead=0, ax=30, ay=34,
                           font=dict(color=CLAY, size=11))

    fig.update_layout(
        height=360, margin=dict(l=10, r=10, t=14, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTA),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#ECE7DA", zeroline=False,
                   tickprefix="$", tickformat=",.0f"),
    )
    return fig


# --------------------------------------------------------------------------- #
# APP
# --------------------------------------------------------------------------- #
def main():
    df = cargar_datos()
    hoy = df["fecha"].max()
    min_d, max_d = df["fecha"].min().date(), hoy.date()

    # ---- Sidebar minimalista: solo el periodo, con Desde / Hasta ----
    st.sidebar.title("📅 Periodo")
    st.sidebar.caption("Define el rango del análisis financiero.")
    desde = st.sidebar.date_input("Desde", value=min_d, min_value=min_d, max_value=max_d)
    hasta = st.sidebar.date_input("Hasta", value=max_d, min_value=min_d, max_value=max_d)
    if desde > hasta:
        st.sidebar.error("'Desde' no puede ser posterior a 'Hasta'. Ajusté el rango.")
        desde, hasta = hasta, desde
    ini, fin = pd.Timestamp(desde), pd.Timestamp(hasta)
    df_periodo = df[(df["fecha"] >= ini) & (df["fecha"] <= fin)]

    st.sidebar.divider()
    st.sidebar.caption("La racha se mide sobre tu historial completo "
                       "(necesita continuidad); el periodo afecta solo al "
                       "análisis financiero.")

    # ---- Cálculos ----
    cal = construir_calendario_dias(df, hoy)              # racha: historial completo
    racha_actual, racha_maxima = calcular_rachas(cal)
    prom_diario, y_evitado, ahorro_mensual, z = costo_oportunidad(df, racha_actual)
    ingresos, egresos, saldo, hormiga = calcular_metricas(df_periodo)
    pct_hormiga = (hormiga / egresos * 100) if egresos else 0

    # ====================================================================== #
    # ENCABEZADO
    # ====================================================================== #
    st.title("🌿 Monitor de Salud Financiera")
    st.markdown("<p class='seccion-intro'>El ahorro es un músculo. "
                "Aquí lo entrenas todos los días.</p>", unsafe_allow_html=True)

    # ====================================================================== #
    # ACTO 1 — EL GANCHO: tu racha y lo que te ahorró (un solo panel)
    # ====================================================================== #
    with st.container(border=True):
        st.markdown("### Tu Racha Financiera")
        st.markdown("<p class='seccion-intro'>Cada día sin gasto hormiga es una "
                    "repetición. Esta es tu constancia, hecha visible.</p>",
                    unsafe_allow_html=True)

        col_izq, col_der = st.columns([1, 2.4], gap="large")
        with col_izq:
            st.metric("Racha actual", f"{racha_actual} días",
                      help="Días consecutivos sin registrar gasto hormiga.")
            st.metric("Récord histórico", f"{racha_maxima} días")
            st.success(mensaje_motivacion(racha_actual, racha_maxima))
        with col_der:
            st.markdown("**Tu calendario de constancia**")
            st.plotly_chart(crear_heatmap(cal), use_container_width=True,
                            config={"displayModeBar": False})
            st.markdown(leyenda_heatmap_html(), unsafe_allow_html=True)

        # Impacto: el cálculo vive AQUÍ, junto a su causa (la racha).
        st.markdown(
            f"""
            <div class="insight">
              💡 <b>El interés compuesto de tu disciplina.</b>
              Tu racha de <b>{racha_actual} días</b> ya evitó la fuga de
              <b style="color:{OLIVO};">${y_evitado:,.0f}</b>
              (≈ ${prom_diario:,.0f}/día de gasto hormiga). Si convirtieras ese
              hábito en inversión constante, en {ANIOS_PROYECCION} años valdría
              <b style="color:{NAVY};">${z:,.0f}</b>.
            </div>
            """, unsafe_allow_html=True)
        with st.expander("¿Cómo se calcula esa proyección?"):
            st.markdown(
                f"""
                - **Evitado hoy:** ${prom_diario:,.0f} (tu gasto hormiga promedio
                  diario) × {racha_actual} días de racha = **${y_evitado:,.0f}**.
                - **Si lo sostienes:** ese hábito equivale a ahorrar
                  ≈ **${ahorro_mensual:,.0f} al mes**.
                - **Invertido:** aportando esa cantidad cada mes durante
                  **{ANIOS_PROYECCION} años** a una tasa anual de
                  **{TASA_ANUAL*100:.0f}%** (valor futuro de una anualidad) → **${z:,.0f}**.
                - Es una proyección motivacional con supuestos fijos, no una promesa.
                """)

    # ====================================================================== #
    # ACTO 2 — DÓNDE ESTÁS: KPIs con el gasto hormiga como protagonista
    # ====================================================================== #
    with st.container(border=True):
        st.markdown("### 📊 Dónde estás este periodo")
        rango_txt = f"{ini.strftime('%d %b')} – {fin.strftime('%d %b %Y')}"
        st.markdown(f"<p class='seccion-intro'>{rango_txt}</p>", unsafe_allow_html=True)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Ingresos", f"${ingresos:,.0f}")
        k2.metric("Egresos", f"${egresos:,.0f}")
        k3.metric("Saldo", f"${saldo:,.0f}",
                  delta=f"{(saldo/ingresos*100 if ingresos else 0):.0f}% de ingresos",
                  delta_color="off")
        k4.metric("🐜 Gasto hormiga", f"${hormiga:,.0f}",
                  delta=f"{pct_hormiga:.0f}% de tus egresos", delta_color="off")

        st.markdown(
            f"""
            <div class="insight">
              🐜 El <b>gasto hormiga</b> fue el <b>{pct_hormiga:.0f}%</b> de todo lo
              que gastaste: <b>${hormiga:,.0f}</b> en pequeños movimientos.
              Individualmente parecen inofensivos; juntos, son la fuga que tu racha
              está cerrando.
            </div>
            """, unsafe_allow_html=True)

    # ====================================================================== #
    # ACTO 3 y 4 — ANÁLISIS Y EVIDENCIA
    # ====================================================================== #
    with st.container(border=True):
        st.markdown("### 🔍 A dónde va tu dinero")
        tab_dona, tab_saldo, tab_tabla = st.tabs(
            ["🍩 En qué se va", "📈 Trayectoria de tu saldo", "📋 Movimientos"])

        with tab_dona:
            c1, c2 = st.columns([3, 2], gap="large")
            with c1:
                st.plotly_chart(crear_donut(df_periodo), use_container_width=True,
                                config={"displayModeBar": False})
            with c2:
                st.markdown("#### Lectura rápida")
                resumen = (df_periodo[df_periodo["tipo"] == "Egreso"]
                           .groupby("categoria")["monto"].sum()
                           .sort_values(ascending=False))
                total = resumen.sum()
                for cat, val in resumen.items():
                    st.markdown(f"- **{cat}** — ${val:,.0f} · {val/total*100:.1f}%")
                st.caption("El gasto hormiga suele ser chico por movimiento, "
                           "pero revelador en el agregado.")

        with tab_saldo:
            st.plotly_chart(crear_trayectoria_saldo(df_periodo),
                            use_container_width=True, config={"displayModeBar": False})
            st.markdown(
                "<p class='seccion-intro'>Tu saldo <b>sube</b> con cada ingreso "
                "(nómina, freelance) y <b>baja</b> con cada egreso (gastos, deudas, "
                "gasto hormiga). Es el dinero que te va quedando disponible: arriba "
                "de la línea punteada estás en positivo; por debajo, en números "
                "ajustados.</p>", unsafe_allow_html=True)

        with tab_tabla:
            f1, f2, f3 = st.columns([2, 2, 3])
            cats = sorted(df_periodo["categoria"].unique())
            sel_cat = f1.multiselect("Categoría", cats, default=cats)
            sel_tipo = f2.multiselect("Tipo", ["Ingreso", "Egreso"],
                                      default=["Ingreso", "Egreso"])
            busca = f3.text_input("Buscar concepto", "")

            tabla = df_periodo[df_periodo["categoria"].isin(sel_cat)
                               & df_periodo["tipo"].isin(sel_tipo)].copy()
            if busca:
                tabla = tabla[tabla["concepto"].str.contains(busca, case=False, na=False)]
            tabla = tabla.sort_values("fecha", ascending=False)
            tabla["fecha"] = tabla["fecha"].dt.strftime("%Y-%m-%d")

            st.dataframe(
                tabla, use_container_width=True, hide_index=True,
                column_config={
                    "fecha": st.column_config.TextColumn("Fecha"),
                    "concepto": st.column_config.TextColumn("Concepto"),
                    "categoria": st.column_config.TextColumn("Categoría"),
                    "monto": st.column_config.NumberColumn("Monto", format="$%.2f"),
                    "tipo": st.column_config.TextColumn("Tipo"),
                },
            )
            st.caption(f"{len(tabla)} movimientos · Total: ${tabla['monto'].sum():,.2f}")

    st.caption("Monitor de Salud Financiera · Datos simulados · "
               "Streamlit + Plotly + SQLite.")


if __name__ == "__main__":
    main()
