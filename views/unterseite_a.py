import streamlit as st

st.title("Unterseite A")

st.write("Diese Seite ist eine Unterseite der Startseite.")


import streamlit as st
import pandas as pd


def resistance_rate(resistant: int, total: int) -> float:
    """Return resistance rate in percent. If total==0, return 0.0."""
    if total <= 0:
        return 0.0
    return (resistant / total) * 100.0


def classify_rate(rate_pct: float) -> str:
    """
    Simple traffic-light classification.
    You can change the thresholds if your course/hospital uses different cutoffs.
    """
    if rate_pct < 10:
        return "🟢 niedrig (<10%)"
    if rate_pct <= 25:
        return "🟠 mittel (10–25%)"
    return "🔴 hoch (>25%)"


def main():
    st.title("Antibiotika-Resistenz-Monitor")
    st.write(
        "Ein einfacher Rechner zur Überwachung von Resistenzraten im Krankenhaus. "
        "Eingaben: Anzahl getesteter Isolate und Anzahl resistenter Isolate. "
        "Ausgabe: Resistenzrate (%) + Trendvergleich + einfache Risiko-Einstufung."
    )

    # Optional: helps meet the 'API elements' requirement and keeps UI tidy
    tabs = st.tabs(["Rechner", "Erklärung"])

    with tabs[1]:
        with st.expander("Formel & Interpretation"):
            st.markdown(
                r"""
**Formel (Resistenzrate):**  
\[
\text{Resistenzrate} = \frac{\text{resistente Isolate}}{\text{Gesamtisolate}} \times 100
\]

**Interpretation (Beispiel-Ampel):**
- < 10% → niedrig
- 10–25% → mittel
- > 25% → hoch

Hinweis: Diese Schwellenwerte sind didaktisch gewählt und können je nach Setting variieren.
"""
            )

    with tabs[0]:
        # Inputs in a form (as recommended in the assignment)
        with st.form("resistance_form"):
            st.subheader("Eingaben")

            col1, col2 = st.columns(2)

            with col1:
                organism = st.selectbox(
                    "Erreger (Beispiel)",
                    ["E. coli", "Klebsiella pneumoniae", "Staphylococcus aureus", "Pseudomonas aeruginosa", "Enterococcus faecium"],
                )
                antibiotic = st.selectbox(
                    "Antibiotikum (Beispiel)",
                    ["Ciprofloxacin", "Ceftriaxon", "Piperacillin/Tazobactam", "Meropenem", "Vancomycin"],
                )

            with col2:
                period = st.selectbox(
                    "Zeitraum",
                    ["letzter Monat", "letzte 3 Monate", "letztes Halbjahr", "letztes Jahr"],
                )
                compare_prev = st.checkbox("Mit Vorperiode vergleichen", value=True)

            st.markdown("### Aktuelle Periode")
            total_now = st.number_input("Gesamtzahl getesteter Isolate", min_value=0, value=100, step=1)
            resistant_now = st.number_input("Anzahl resistenter Isolate", min_value=0, value=18, step=1)

            # Optional comparison inputs
            if compare_prev:
                st.markdown("### Vorperiode (Vergleich)")
                total_prev = st.number_input("Gesamtzahl getesteter Isolate (Vorperiode)", min_value=0, value=120, step=1)
                resistant_prev = st.number_input("Anzahl resistenter Isolate (Vorperiode)", min_value=0, value=15, step=1)
            else:
                total_prev = 0
                resistant_prev = 0

            submitted = st.form_submit_button("Berechnen")

        if submitted:
            # Basic sanity checks
            if resistant_now > total_now:
                st.error("Fehler: 'resistente Isolate' darf nicht größer sein als 'Gesamtzahl getesteter Isolate' (aktuelle Periode).")
                return
            if compare_prev and resistant_prev > total_prev:
                st.error("Fehler: 'resistente Isolate' darf nicht größer sein als 'Gesamtzahl getesteter Isolate' (Vorperiode).")
                return

            # Calculate rates
            rate_now = resistance_rate(int(resistant_now), int(total_now))
            label_now = classify_rate(rate_now)

            # Show key results
            st.subheader("Resultate")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Resistenzrate (aktuell)", f"{rate_now:.1f}%")
            with c2:
                st.metric("Einstufung", label_now)
            with c3:
                st.metric("Datengrundlage", f"{int(resistant_now)}/{int(total_now)} Isolate")

            # Optional comparison
            if compare_prev and total_prev > 0:
                rate_prev = resistance_rate(int(resistant_prev), int(total_prev))
                delta_abs = rate_now - rate_prev  # percentage points
                delta_rel = 0.0 if rate_prev == 0 else (delta_abs / rate_prev) * 100.0

                st.markdown("### Vergleich mit Vorperiode")
                c4, c5, c6 = st.columns(3)
                with c4:
                    st.metric("Resistenzrate (Vorperiode)", f"{rate_prev:.1f}%")
                with c5:
                    st.metric("Änderung (Prozentpunkte)", f"{delta_abs:+.1f} pp")
                with c6:
                    st.metric("Relative Änderung", f"{delta_rel:+.1f}%")

            # Build a small dataframe for plotting
            data = {
                "Kategorie": ["Sensible", "Resistent"],
                "Aktuelle Periode": [int(total_now - resistant_now), int(resistant_now)],
            }
            if compare_prev and total_prev > 0:
                data["Vorperiode"] = [int(total_prev - resistant_prev), int(resistant_prev)]

            df = pd.DataFrame(data).set_index("Kategorie")

            st.subheader("Visualisierung")
            chart_choice = st.radio("Diagrammtyp", ["Balken (Anteile)", "Balken (Absolut)"], horizontal=True)

            if chart_choice == "Balken (Absolut)":
                st.bar_chart(df)
            else:
                # Convert to percentages for "share" chart
                df_pct = df.copy()
                for col in df_pct.columns:
                    col_sum = df_pct[col].sum()
                    df_pct[col] = (df_pct[col] / col_sum * 100.0) if col_sum > 0 else 0.0
                st.bar_chart(df_pct)

            # A short summary sentence (useful for interpretation)
            st.info(
                f"{organism} – {antibiotic} ({period}): Resistenzrate {rate_now:.1f}% ({label_now}). "
                "Bitte beachten: Schwellenwerte sind didaktisch und können lokal abweichen."
            )


if __name__ == "__main__":
    main()