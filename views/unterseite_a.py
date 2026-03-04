import streamlit as st

st.title("Unterseite A")

st.write("Diese Seite ist eine Unterseite der Startseite.")


import streamlit as st
import pandas as pd


def resistance_rate(resistant: int, total: int) -> float:
    return 0.0 if total <= 0 else (resistant / total) * 100.0


def classify_rate(rate_pct: float) -> str:
    if rate_pct < 10:
        return "🟢 niedrig (<10%)"
    if rate_pct <= 25:
        return "🟠 mittel (10–25%)"
    return "🔴 hoch (>25%)"


def is_enterobacterales(organism: str) -> bool:
    return organism in {"E. coli", "Klebsiella pneumoniae"}


def main():
    st.title("Antibiotika-Resistenz-Monitor")

    tabs = st.tabs(["Rechner", "Erklärung"])
    with tabs[1]:
        with st.expander("Formel"):
            st.markdown(r"\(\text{Resistenzrate}=\frac{\text{resistent}}{\text{gesamt}}\times 100\)")

    with tabs[0]:
        with st.form("resistance_form"):
            c1, c2 = st.columns(2)
            with c1:
                organism = st.selectbox(
                    "Keim (Erreger)",
                    [
                        "E. coli",
                        "Klebsiella pneumoniae",
                        "Staphylococcus aureus",
                        "Pseudomonas aeruginosa",
                        "Enterococcus faecium",
                        "Enterococcus faecalis",
                    ],
                )
                antibiotic = st.selectbox(
                    "Antibiotikum",
                    [
                        "Penicillin",
                        "Ciprofloxacin",
                        "Ceftriaxon",
                        "Piperacillin/Tazobactam",
                        "Meropenem (Carbapenem)",
                        "Vancomycin",
                        "Flucloxacillin",
                        "Cefazolin",
                        "Cefalexin",
                        "Ampicillin-Sulbactam",
                        "Amoxicillin-Clavulansäure",
                        "Co-trimoxazol",
                        "Clindamycin",
                        "Doxycyclin",
                        "Fusidinsäure",
                        "Teicoplanin",
                        "Daptomycin",
                        "Linezolid",
                        
                    ],
                )
            with c2:
                period = st.selectbox(
                    "Zeitperiode (Pflicht)",
                    ["letzter Monat", "letzte 3 Monate", "letztes Halbjahr", "letztes Jahr"],
                )
                compare_prev = st.checkbox("Mit Vorperiode vergleichen", value=True)

            st.markdown("### Aktuelle Periode")
            total_now = st.number_input("Gesamtzahl getesteter Isolate", min_value=0, value=100, step=1)
            resistant_now = st.number_input("Anzahl resistenter Isolate", min_value=0, value=18, step=1)

            if compare_prev:
                st.markdown("### Vorperiode")
                total_prev = st.number_input("Gesamtzahl getesteter Isolate (Vorperiode)", min_value=0, value=120, step=1)
                resistant_prev = st.number_input("Anzahl resistenter Isolate (Vorperiode)", min_value=0, value=15, step=1)
            else:
                total_prev, resistant_prev = 0, 0

            submitted = st.form_submit_button("Berechnen")

        if submitted:
            if resistant_now > total_now:
                st.error("Aktuelle Periode: resistente Isolate dürfen nicht größer sein als Gesamtisolate.")
                st.stop()
            if compare_prev and resistant_prev > total_prev:
                st.error("Vorperiode: resistente Isolate dürfen nicht größer sein als Gesamtisolate.")
                st.stop()

            rate_now = resistance_rate(int(resistant_now), int(total_now))
            label_now = classify_rate(rate_now)

            data = {
                "Kategorie": ["Sensible", "Resistent"],
                "Aktuelle Periode": [int(total_now - resistant_now), int(resistant_now)],
            }
            if compare_prev and total_prev > 0:
                data["Vorperiode"] = [int(total_prev - resistant_prev), int(resistant_prev)]

            st.session_state["result"] = {
                "organism": organism,
                "antibiotic": antibiotic,
                "period": period,
                "rate_now": rate_now,
                "label_now": label_now,
                "total_now": int(total_now),
                "resistant_now": int(resistant_now),
                "compare_prev": bool(compare_prev),
                "total_prev": int(total_prev),
                "resistant_prev": int(resistant_prev),
                "df": pd.DataFrame(data).set_index("Kategorie"),
            }

        if "result" not in st.session_state:
            st.info("Werte eingeben und auf **Berechnen** klicken.")
            return

        r = st.session_state["result"]
        df = r["df"]

        # --- Warnings ---
        # Carbapenem resistance in Enterobacterales
        if is_enterobacterales(r["organism"]) and r["antibiotic"].startswith("Meropenem") and r["resistant_now"] > 0:
            st.warning(
                "Warnhinweis: Carbapenem-Resistenz bei Enterobacterales ist besonders relevant "
                "(mögliche CPE/CRE). Bestätigung/Abklärung und Hygienemassnahmen gemäss Spitalrichtlinien prüfen."
            )

        # MRSA hint: S. aureus + Penicillin resistance (simplified teaching rule)
        if r["organism"] == "Staphylococcus aureus" and r["antibiotic"] == "Penicillin" and r["resistant_now"] > 0:
            st.warning(
                "Hinweis (didaktisch): Penicillin-Resistenz bei Staphylococcus aureus ist häufig. "
                "MRSA wird jedoch über Methicillin/Oxacillin/Cefoxitin beurteilt. Die Penicillin-Resistenz allein ist kein MRSA-Nachweis, aber könnte ein Indikator sein. "
                "Für MRSA-Screening lokale Teststrategie beachten."
            )

        # VRE warning: Enterococcus + Vancomycin resistance
        if r["organism"].startswith("Enterococcus") and r["antibiotic"] == "Vancomycin" and r["resistant_now"] > 0:
            st.warning(
                "Warnhinweis: Vancomycin-Resistenz bei Enterokokken ist besonders relevant (VRE). "
                "Bestätigung/Abklärung und Hygienemassnahmen gemäss Spitalrichtlinien prüfen."
            )

        # --- Results ---
        st.subheader("Resultate")
        st.markdown(f"**Keim:** {r['organism']}  \n**Antibiotikum:** {r['antibiotic']}  \n**Zeitperiode:** {r['period']}")

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Resistenzrate (aktuell)", f"{r['rate_now']:.1f}%")
        with m2:
            st.metric("Einstufung", r["label_now"])
        with m3:
            st.metric("Datengrundlage", f"{r['resistant_now']}/{r['total_now']}")

        if r["compare_prev"] and r["total_prev"] > 0:
            rate_prev = resistance_rate(r["resistant_prev"], r["total_prev"])
            delta_abs = r["rate_now"] - rate_prev
            delta_rel = 0.0 if rate_prev == 0 else (delta_abs / rate_prev) * 100.0
            st.markdown("### Vergleich mit Vorperiode")
            v1, v2, v3 = st.columns(3)
            with v1:
                st.metric("Resistenzrate (Vorperiode)", f"{rate_prev:.1f}%")
            with v2:
                st.metric("Änderung (pp)", f"{delta_abs:+.1f}")
            with v3:
                st.metric("Relative Änderung", f"{delta_rel:+.1f}%")

        # --- Visualization ---
        st.subheader("Visualisierung")
        chart_choice = st.radio("Diagrammtyp", ["Anteile (%)", "Absolut (n)"], horizontal=True)

        if chart_choice == "Absolut (n)":
            st.bar_chart(df)
        else:
            df_pct = df.copy()
            for col in df_pct.columns:
                s = df_pct[col].sum()
                df_pct[col] = (df_pct[col] / s * 100.0) if s > 0 else 0.0
            st.bar_chart(df_pct)

        st.caption(f"Auswertung: {r['organism']} – {r['antibiotic']} ({r['period']})")


if __name__ == "__main__":
    main()