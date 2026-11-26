# Supermercado Santa María – Reglas de asociación

Despliegue (Fase 6 de CRISP-DM) del análisis de canasta de mercado sobre el Groceries Dataset.

- 14.963 canastas (cliente + fecha) y 167 productos
- FP-Growth / Apriori con soporte mínimo 0,001, confianza mínima 0,10 y lift > 1
- 37 reglas de asociación positivas

## Secciones de la aplicación
- **Resumen:** indicadores y gráficos de las reglas
- **Recomendador:** sugiere productos según el carrito del cliente
- **Explorar reglas:** tabla filtrable y descargable
- **Estrategias comerciales:** acciones propuestas en la Fase 5
- **Monitoreo:** plan de seguimiento del KPI de negocio

## Ejecutar en local
```
pip install -r requirements.txt
streamlit run app.py
```
