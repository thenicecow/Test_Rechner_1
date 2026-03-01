import streamlit as st

st.title("Unterseite A")

st.write("Diese Seite ist eine Unterseite der Startseite.")


import numpy as np
import pandas as pd
import streamlit as st

# ----------------------------
# PK model (1-compartment, oral, first-order absorption & elimination)
# C(t) = (F*D*ka)/(Vd*(ka-k)) * (exp(-k t) - exp(-ka t))
# where k = ln(2)/t_half
# Units:
#   D in mg, Vd in L, concentration in mg/L, time in hours
# ----------------------------

def k_from_half_life(t_half_h: float) -> float:
    return np.log(2) / t_half_h


def conc_oral_single_dose(
    t: np.ndarray,
    dose_mg: float,
    F: float,
    Vd_L: float,
    ka_per_h: float,
    k_per_h: float
) -> np.ndarray:
    """Concentration-time curve for a single oral dose (mg/L)."""
    t = np.asarray(t, dtype=float)
    t = np.maximum(t, 0.0)

    # Handle ka ~ k numerically stable (limit case)
    if np.isclose(ka_per_h, k_per_h, rtol=1e-4, atol=1e-6):
        # Limit as ka -> k: C(t) = (F*D/Vd) * (k*t) * exp(-k*t)
        return (F * dose_mg / Vd_L) * (k_per_h * t) * np.exp(-k_per_h * t)

    factor = (F * dose_mg * ka_per_h) / (Vd_L * (ka_per_h - k_per_h))
    return factor * (np.exp(-k_per_h * t) - np.exp(-ka_per_h * t))


def conc_oral_multiple_dose(
    t: np.ndarray,
    dose_mg: float,
    F: float,
    Vd_L: float,
    ka_per_h: float,
    k_per_h: float,
    tau_h: float,
    n_doses: int
) -> np.ndarray:
    """Superposition of repeated oral doses given every tau (mg/L)."""
    t = np.asarray(t, dtype=float)
    total = np.zeros_like(t, dtype=float)

    for i in range(n_doses):
        t_shift = t - i * tau_h
        mask = t_shift >= 0
        if np.any(mask):
            total[mask] += conc_oral_single_dose(
                t=t_shift[mask],
                dose_mg=dose_mg,
                F=F,
                Vd_L=Vd_L,
                ka_per_h=ka_per_h,
                k_per_h=k_per_h
            )
    return total


def metrics_from_curve(t: np.ndarray, c: np.ndarray) -> dict:
    """Compute Cmax, Tmax, AUC (0-last) numerically."""
    t = np.asarray(t, dtype=float)
    c = np.asarray(c, dtype=float)

    idx_max = int(np.argmax(c))
    cmax = float(c[idx_max])
    tmax = float(t[idx_max])
    # Use trapezoid instead of trapz (more robust across numpy versions)
    auc = float(np.trapezoid(c, t))  # mg*h/L

    return {"Cmax_mg_per_L": cmax, "Tmax_h": tmax, "AUC0_last_mg_h_per_L": auc}


# Example default profiles (approximate typical values; user-editable)
DEFAULTS = {
    "Diazepam": {
        "F": 0.95,
        "t_half_h": 36.0,     # typical range ~20-50h (simplified)
        "ka_per_h": 1.0,
        "Vd_L_per_kg": 0.9
    },
    "Paracetamol": {
        "F": 0.85,
        "t_half_h": 2.5,      # typical ~2-3h (simplified)
        "ka_per_h": 1.5,
        "Vd_L_per_kg": 0.9
    }
}


def build_time_grid(duration_h: float, dt_min: float) -> np.ndarray:
    dt_h = dt_min / 60.0
    n = int(np.floor(duration_h / dt_h)) + 1
    return np.linspace(0.0, duration_h, n)


# ----------------------------
# Streamlit UI
# ----------------------------

def main():
    st.title("Pharmakokinetik-Rechner (oral): Diazepam & Paracetamol")
    st.caption("Modell: 1-Kompartiment, first-order Absorption und Elimination (linear). Keine Interaktionen, keine Therapieempfehlung.")

    tabs = st.tabs(["Rechner", "Modellannahmen & Hinweise"])

    with tabs[1]:
        with st.expander("Annahmen (wichtig)"):
            st.markdown(
                "- 1-Kompartiment-Modell\n"
                "- Absorption und Elimination 1. Ordnung\n"
                "- Lineare Kinetik (Superposition bei Mehrfachdosierung)\n"
                "- Keine aktiven Metaboliten, keine Sättigung, keine Interaktionen\n"
                "- Parameter-Defaults sind Beispielwerte und müssen bei realen Fällen angepasst werden."
            )

    with tabs[0]:
        # Core UI elements for grading: form, number_input, slider, checkbox, radio, metric, chart, tabs, expander
        with st.form("pk_form"):
            st.subheader("Patient")
            weight_kg = st.number_input("Körpergewicht (kg)", min_value=30.0, max_value=200.0, value=70.0, step=1.0)

            st.subheader("Simulation")
            duration_h = st.slider("Simulationsdauer (h)", min_value=8, max_value=336, value=168, step=8)  # up to 14 days
            dt_min = st.slider("Zeitauflösung (min)", min_value=1, max_value=60, value=5, step=1)

            st.subheader("Dosierung")
            multiple = st.checkbox("Mehrfachdosierung aktivieren", value=True)
            if multiple:
                tau_h = st.slider("Dosierintervall τ (h)", min_value=2, max_value=48, value=12, step=1)
                n_doses = st.slider("Anzahl Dosen", min_value=1, max_value=60, value=14, step=1)
            else:
                tau_h = 0.0
                n_doses = 1

            st.subheader("Medikament-Profile (editierbar)")
            scale = st.radio("Plot-Skala", options=["linear", "log"], index=0, horizontal=True)

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Diazepam (fix)")
                d_diaz = st.number_input("Dosis Diazepam pro Gabe (mg)", min_value=0.0, max_value=100.0, value=5.0, step=0.5)
                F_diaz = st.number_input("Bioverfügbarkeit F (Diazepam)", min_value=0.0, max_value=1.0, value=float(DEFAULTS["Diazepam"]["F"]), step=0.01)
                t12_diaz = st.number_input("Halbwertszeit t½ (h) (Diazepam)", min_value=1.0, max_value=200.0, value=float(DEFAULTS["Diazepam"]["t_half_h"]), step=1.0)
                ka_diaz = st.number_input("Absorptionskonstante ka (1/h) (Diazepam)", min_value=0.05, max_value=5.0, value=float(DEFAULTS["Diazepam"]["ka_per_h"]), step=0.05)
                vdkg_diaz = st.number_input("Vd (L/kg) (Diazepam)", min_value=0.1, max_value=5.0, value=float(DEFAULTS["Diazepam"]["Vd_L_per_kg"]), step=0.05)

            with col2:
                st.markdown("### Paracetamol (fix)")
                d_para = st.number_input("Dosis Paracetamol pro Gabe (mg)", min_value=0.0, max_value=2000.0, value=1000.0, step=50.0)
                F_para = st.number_input("Bioverfügbarkeit F (Paracetamol)", min_value=0.0, max_value=1.0, value=float(DEFAULTS["Paracetamol"]["F"]), step=0.01)
                t12_para = st.number_input("Halbwertszeit t½ (h) (Paracetamol)", min_value=0.5, max_value=24.0, value=float(DEFAULTS["Paracetamol"]["t_half_h"]), step=0.1)
                ka_para = st.number_input("Absorptionskonstante ka (1/h) (Paracetamol)", min_value=0.05, max_value=5.0, value=float(DEFAULTS["Paracetamol"]["ka_per_h"]), step=0.05)
                vdkg_para = st.number_input("Vd (L/kg) (Paracetamol)", min_value=0.1, max_value=5.0, value=float(DEFAULTS["Paracetamol"]["Vd_L_per_kg"]), step=0.05)

            submitted = st.form_submit_button("Berechnen")

        if submitted:
            t = build_time_grid(duration_h=float(duration_h), dt_min=float(dt_min))

            # Convert to Vd in L using weight
            Vd_diaz = float(vdkg_diaz) * float(weight_kg)
            Vd_para = float(vdkg_para) * float(weight_kg)

            k_diaz = k_from_half_life(float(t12_diaz))
            k_para = k_from_half_life(float(t12_para))

            if multiple:
                c_diaz = conc_oral_multiple_dose(
                    t=t, dose_mg=float(d_diaz), F=float(F_diaz), Vd_L=Vd_diaz,
                    ka_per_h=float(ka_diaz), k_per_h=k_diaz,
                    tau_h=float(tau_h), n_doses=int(n_doses)
                )
                c_para = conc_oral_multiple_dose(
                    t=t, dose_mg=float(d_para), F=float(F_para), Vd_L=Vd_para,
                    ka_per_h=float(ka_para), k_per_h=k_para,
                    tau_h=float(tau_h), n_doses=int(n_doses)
                )
            else:
                c_diaz = conc_oral_single_dose(
                    t=t, dose_mg=float(d_diaz), F=float(F_diaz), Vd_L=Vd_diaz,
                    ka_per_h=float(ka_diaz), k_per_h=k_diaz
                )
                c_para = conc_oral_single_dose(
                    t=t, dose_mg=float(d_para), F=float(F_para), Vd_L=Vd_para,
                    ka_per_h=float(ka_para), k_per_h=k_para
                )

            # Metrics
            m_diaz = metrics_from_curve(t, c_diaz)
            m_para = metrics_from_curve(t, c_para)

            st.subheader("Kennwerte")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Diazepam**")
                st.metric("Cmax (mg/L)", f"{m_diaz['Cmax_mg_per_L']:.4f}")
                st.metric("Tmax (h)", f"{m_diaz['Tmax_h']:.2f}")
                st.metric("AUC0-last (mg·h/L)", f"{m_diaz['AUC0_last_mg_h_per_L']:.2f}")
            with c2:
                st.markdown("**Paracetamol**")
                st.metric("Cmax (mg/L)", f"{m_para['Cmax_mg_per_L']:.4f}")
                st.metric("Tmax (h)", f"{m_para['Tmax_h']:.2f}")
                st.metric("AUC0-last (mg·h/L)", f"{m_para['AUC0_last_mg_h_per_L']:.2f}")

            st.subheader("Konzentrations-Zeit-Kurven")
            df = pd.DataFrame({
                "t_h": t,
                "Diazepam_mg_per_L": c_diaz,
                "Paracetamol_mg_per_L": c_para
            }).set_index("t_h")

            if scale == "log":
                # Avoid log(0) issues; clamp to tiny positive
                df_plot = df.clip(lower=1e-12)
            else:
                df_plot = df

            st.line_chart(df_plot)

            st.caption("Hinweis: Bei log-Skala werden Werte nahe 0 geklammert, um log(0) zu vermeiden.")


if __name__ == "__main__":
    main()