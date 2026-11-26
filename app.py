"""
Supermercado Santa María – Reglas de asociación (CRISP-DM, Fase 6: Despliegue)

Aplicación web que pone a disposición del negocio las 37 reglas obtenidas
en la Fase 4 (FP-Growth, soporte >= 0,001, confianza >= 0,10, lift > 1).

Ejecutar en local:  streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Santa María · Productos que se compran juntos",
    page_icon="🛒",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Carga de datos (se guarda en caché para que la app sea rápida)
# ---------------------------------------------------------------------------
@st.cache_data
def cargar_reglas():
    reglas = pd.read_csv("data/reglas.csv")
    reglas["regla"] = reglas["antecedente"].str.replace(", ", " + ") + "  →  " + reglas["consecuente"]
    reglas["ant_set"] = reglas["antecedente"].str.split(", ").apply(frozenset)
    reglas["n_antecedentes"] = reglas["ant_set"].apply(len)
    reglas["fuerza"] = pd.cut(
        reglas["lift"], [1, 1.2, 1.5, float("inf")],
        labels=["Débil (1,0–1,2)", "Moderada (1,2–1,5)", "Fuerte (> 1,5)"], right=False,
    )
    return reglas


@st.cache_data
def cargar_transacciones():
    return pd.read_csv("data/transacciones_limpias.csv", parse_dates=["Date"])


reglas = cargar_reglas()
trans = cargar_transacciones()
n_canastas = trans["id_canasta"].nunique()
productos_catalogo = sorted(trans["itemDescription"].unique())
productos_en_reglas = sorted(set(reglas["antecedente"].str.split(", ").explode()) | set(reglas["consecuente"]))


def recomendar(carrito):
    """Reglas cuyo antecedente está completo dentro del carrito y cuyo consecuente aún no está en él."""
    carrito = set(carrito)
    aplicables = reglas[
        reglas["ant_set"].apply(lambda a: a <= carrito) & ~reglas["consecuente"].isin(carrito)
    ]
    if aplicables.empty:
        return aplicables
    # Si un producto se sugiere por varias reglas, se queda la de mayor lift
    return (aplicables.sort_values("lift", ascending=False)
            .drop_duplicates("consecuente")
            .reset_index(drop=True))


# ---------------------------------------------------------------------------
# Menú lateral
# ---------------------------------------------------------------------------
st.sidebar.title("🛒 Santa María")
st.sidebar.caption("Análisis de canasta de mercado · CRISP-DM")
pagina = st.sidebar.radio(
    "Secciones",
    ["Resumen", "Recomendador", "Explorar reglas", "Estrategias comerciales", "Monitoreo"],
)
st.sidebar.divider()
st.sidebar.markdown(
    "**Parámetros del modelo**  \n"
    "Algoritmo: FP-Growth (= Apriori)  \n"
    "Soporte mínimo: 0,001  \n"
    "Confianza mínima: 0,10  \n"
    "Lift: > 1"
)

# ---------------------------------------------------------------------------
# 1. Resumen
# ---------------------------------------------------------------------------
if pagina == "Resumen":
    st.title("Productos que los clientes compran juntos")
    st.write(
        "Esta aplicación pone a disposición del Supermercado Santa María las reglas de asociación "
        "obtenidas a partir del historial de compras 2014–2015, para apoyar la venta cruzada, "
        "las recomendaciones y los paquetes promocionales."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Canastas analizadas", f"{n_canastas:,}".replace(",", "."))
    c2.metric("Productos", len(productos_catalogo))
    c3.metric("Reglas con lift > 1", len(reglas))
    c4.metric("Productos en las reglas", len(productos_en_reglas))

    st.subheader("Soporte, confianza y lift de las reglas")
    fig = px.scatter(
        reglas, x="soporte", y="confianza", color="lift", size="canastas",
        hover_name="regla", color_continuous_scale="Viridis",
        labels={"soporte": "Soporte", "confianza": "Confianza", "lift": "Lift"},
    )
    fig.update_layout(height=430, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Cada punto es una regla; el tamaño indica en cuántas canastas aparece. "
        "Las reglas de mayor lift son poco frecuentes y las más frecuentes tienen asociación débil."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Reglas según su fuerza")
        fuerza = reglas["fuerza"].value_counts().reindex(reglas["fuerza"].cat.categories)
        fig2 = px.bar(x=fuerza.index.astype(str), y=fuerza.values,
                      labels={"x": "", "y": "Número de reglas"})
        fig2.update_layout(height=320, margin=dict(t=10))
        st.plotly_chart(fig2, width="stretch")
    with col_b:
        st.subheader("Productos más presentes en las reglas")
        apar = pd.concat([reglas["antecedente"].str.split(", ").explode(), reglas["consecuente"]])
        apar = apar.value_counts().head(10).sort_values()
        fig3 = px.bar(x=apar.values, y=apar.index, orientation="h",
                      labels={"x": "Número de reglas", "y": ""})
        fig3.update_layout(height=320, margin=dict(t=10))
        st.plotly_chart(fig3, width="stretch")

# ---------------------------------------------------------------------------
# 2. Recomendador
# ---------------------------------------------------------------------------
elif pagina == "Recomendador":
    st.title("Recomendador de productos")
    st.write(
        "Elija los productos que lleva un cliente. La aplicación sugiere qué ofrecerle, "
        "según las reglas encontradas. Úselo en caja, en la app o para planear exhibiciones."
    )

    # --- Combinaciones que sí tienen sugerencias (antecedentes de las reglas) ---
    combos = (reglas.groupby("antecedente")
              .agg(lift_max=("lift", "max"), sugiere=("consecuente", lambda x: ", ".join(x)))
              .sort_values("lift_max", ascending=False).reset_index())
    productos_con_sugerencia = set(reglas["antecedente"].str.split(", ").explode())

    if "carrito" not in st.session_state:
        st.session_state.carrito = ["whole milk", "yogurt"]

    def cargar_combo(antecedente):
        st.session_state.carrito = antecedente.split(", ")

    def boton_combo(fila, col, clave):
        etiqueta = f"{fila['antecedente'].replace(', ', ' + ')}  →  {fila['sugiere']}"
        col.button(
            etiqueta, key=f"{clave}_{fila.name}", width="stretch",
            on_click=cargar_combo, args=(fila["antecedente"],),
            help=f"Lift máximo {fila['lift_max']:.2f}",
        )

    st.subheader("1. Selección rápida")
    st.caption("Combinaciones que generan una sugerencia. Haga clic para cargarlas en el carrito.")

    grupos = [
        ("Asociación fuerte (lift > 1,5)", combos[combos["lift_max"] > 1.5], True),
        ("Asociación moderada (lift 1,2 – 1,5)", combos[(combos["lift_max"] >= 1.2) & (combos["lift_max"] <= 1.5)], True),
        ("Asociación débil (lift 1,0 – 1,2)", combos[combos["lift_max"] < 1.2], False),
    ]
    for titulo, grupo, abierto in grupos:
        with st.expander(f"{titulo} · {len(grupo)} combinaciones", expanded=abierto):
            cols = st.columns(2)
            for i, (_, fila) in enumerate(grupo.iterrows()):
                boton_combo(fila, cols[i % 2], titulo[:6])

    # --- Todos los productos (primero los que generan sugerencias) ---
    st.subheader("2. Carrito del cliente")
    opciones = (sorted(productos_con_sugerencia)
                + [p for p in productos_catalogo if p not in productos_con_sugerencia])
    carrito = st.multiselect(
        "Productos en el carrito (⭐ = participa en alguna regla)",
        options=opciones,
        key="carrito",
        format_func=lambda p: f"⭐ {p}" if p in productos_con_sugerencia else p,
        help=f"Los {len(productos_con_sugerencia)} productos con ⭐ aparecen primero. "
             "Algunos solo generan sugerencias en pareja (por ejemplo, whole milk + yogurt).",
    )

    st.subheader("3. Sugerencias")
    if not carrito:
        st.info("Agregue al menos un producto al carrito o use la selección rápida.")
    else:
        sugerencias = recomendar(carrito)
        if sugerencias.empty:
            st.warning(
                "No hay reglas para esta combinación. Use la selección rápida o agregue "
                "un producto marcado con ⭐."
            )
        else:
            st.write(f"**{len(sugerencias)}** producto(s) para ofrecer:")
            for _, r in sugerencias.iterrows():
                with st.container(border=True):
                    a, b, c = st.columns([3, 1, 1])
                    a.markdown(f"### {r['consecuente']}")
                    a.caption(f"Porque el cliente lleva: {r['antecedente']}")
                    b.metric("Confianza", f"{r['confianza']:.1%}")
                    c.metric("Lift", f"{r['lift']:.2f}")
                    nivel = "Fuerte" if r["lift"] > 1.5 else "Moderada" if r["lift"] >= 1.2 else "Débil"
                    a.caption(f"Asociación {nivel.lower()}")
            st.caption(
                "Confianza: proporción de canastas con esos productos que también incluyeron el sugerido. "
                "Lift: cuántas veces más probable es la compra frente a lo esperado por azar."
            )

# ---------------------------------------------------------------------------
# 3. Explorar reglas
# ---------------------------------------------------------------------------
elif pagina == "Explorar reglas":
    st.title("Explorar las reglas de asociación")

    f1, f2, f3 = st.columns(3)
    lift_min = f1.slider("Lift mínimo", 1.0, float(reglas["lift"].max()), 1.0, 0.05)
    conf_min = f2.slider("Confianza mínima", 0.10, float(reglas["confianza"].max()), 0.10, 0.01)
    producto = f3.selectbox("Producto (antecedente o consecuente)", ["Todos"] + productos_en_reglas)

    vista = reglas[(reglas["lift"] >= lift_min) & (reglas["confianza"] >= conf_min)]
    if producto != "Todos":
        vista = vista[vista["ant_set"].apply(lambda a: producto in a) | (vista["consecuente"] == producto)]

    st.write(f"**{len(vista)}** reglas cumplen los filtros.")
    st.dataframe(
        vista[["regla", "canastas", "soporte", "confianza", "lift", "fuerza"]],
        width="stretch", hide_index=True,
        column_config={
            "regla": "Regla (si compra… → también compra)",
            "canastas": st.column_config.NumberColumn("Canastas"),
            "soporte": st.column_config.NumberColumn("Soporte", format="%.4f"),
            "confianza": st.column_config.ProgressColumn("Confianza", format="%.3f", min_value=0, max_value=0.3),
            "lift": st.column_config.NumberColumn("Lift", format="%.2f"),
            "fuerza": "Fuerza",
        },
    )
    st.download_button(
        "Descargar reglas filtradas (CSV)",
        vista[["antecedente", "consecuente", "canastas", "soporte", "confianza", "lift"]].to_csv(index=False),
        file_name="reglas_filtradas.csv", mime="text/csv",
    )

# ---------------------------------------------------------------------------
# 4. Estrategias comerciales (Fase 5, paso 5.6)
# ---------------------------------------------------------------------------
elif pagina == "Estrategias comerciales":
    st.title("Estrategias comerciales propuestas")
    st.write("Acciones derivadas de las reglas con mayor lift y respaldo, alineadas con el objetivo de negocio.")

    estrategias = pd.DataFrame([
        ["Paquete promocional",
         "whole milk + yogurt → sausage (lift 2,18); sausage + whole milk → yogurt (1,91); sausage + yogurt → whole milk (1,62); 22 canastas",
         "Combo leche entera + yogurt + salchicha con precio conjunto"],
        ["Recomendación de yogurt",
         "soft cheese, detergent, chewing gum, herbs → yogurt (lift 1,25 a 1,47)",
         "Sugerir yogurt al cliente que lleva esos productos, en caja o en la aplicación"],
        ["Venta cruzada con pan",
         "processed cheese, packaged fruit/vegetables, seasonal products, red/blush wine → rolls/buns (lift 1,16 a 1,32)",
         "Ubicar panecillos cerca de quesos, vinos y productos de temporada"],
        ["Verduras y embutidos",
         "frankfurter → other vegetables (77 canastas, lift 1,12)",
         "Promoción conjunta; es la regla con más respaldo, aunque con asociación débil"],
        ["Productos de nicho",
         "processed cheese → root vegetables (1,51); flour → tropical fruit (1,62)",
         "Probar cupones cruzados en pequeña escala (16 canastas cada una)"],
    ], columns=["Estrategia", "Reglas que la respaldan", "Acción propuesta"])
    st.dataframe(estrategias, width="stretch", hide_index=True)

    st.warning(
        "Las reglas se apoyan en pocas compras (entre 15 y 77 canastas). Conviene tratarlas como "
        "hipótesis y validarlas con pilotos antes de extenderlas a toda la cadena."
    )

# ---------------------------------------------------------------------------
# 5. Monitoreo (plan de seguimiento del KPI de negocio)
# ---------------------------------------------------------------------------
elif pagina == "Monitoreo":
    st.title("Plan de monitoreo y mantenimiento")
    st.write(
        "El dataset no incluye precios ni cantidades, por lo que el KPI de negocio (+10 % en ingresos en 12 meses) "
        "debe medirse durante la implementación."
    )
    plan = pd.DataFrame([
        ["Ingresos totales", "Mensual", "Comparar sucursales piloto vs. sucursales de control y vs. el mismo periodo del año anterior", "≥ +10 % a los 12 meses"],
        ["Ventas de los combos promocionales", "Mensual", "Unidades y monto vendido de cada paquete", "Crecimiento sostenido"],
        ["Tasa de aceptación de recomendaciones", "Mensual", "Recomendaciones aceptadas / mostradas (caja o app)", "Superior a la confianza de la regla"],
        ["Ticket promedio por canasta", "Mensual", "Monto promedio por visita", "Aumento respecto al periodo base"],
        ["Vigencia de las reglas", "Trimestral", "Volver a ejecutar FP-Growth con las transacciones nuevas y comparar reglas", "Reglas estables o actualizadas"],
    ], columns=["Indicador", "Frecuencia", "Cómo se mide", "Meta"])
    st.dataframe(plan, width="stretch", hide_index=True)

    st.subheader("Actividad histórica por mes")
    por_mes = (trans.groupby(trans["Date"].dt.to_period("M"))["id_canasta"].nunique()
               .rename("canastas").reset_index())
    por_mes["Date"] = por_mes["Date"].astype(str)
    fig = px.line(por_mes, x="Date", y="canastas", markers=True,
                  labels={"Date": "Mes", "canastas": "Canastas"})
    fig.update_layout(height=340, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
    st.caption("Línea base 2014–2015 para comparar la actividad una vez implementadas las estrategias.")