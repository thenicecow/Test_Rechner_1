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
#
# Units:
#   D in mg, Vd in L, concentration in mg/L, time in hours
#
# Notes:
# - This is a simplified teaching model (no metabolites, no interactions, linear kinetics).
# - Fixed medication parameters are illustrative defaults.
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
    auc = float(np.trapezoid(c, t))  # mg*h/L

    return {"Cmax_mg_per_L": cmax, "Tmax_h": tmax, "AUC0_last_mg_h_per_L": auc}


def build_time_grid(duration_h: float, dt_min: float) -> np.ndarray:
    dt_h = dt_min / 60.0
    n = int(np.floor(duration_h / dt_h)) + 1
    return np.linspace(0.0, duration_h, n)


def add_target_band(df: pd.DataFrame, low: float, high: float, prefix: str) -> pd.DataFrame:
    out = df.copy()
    out[f"{prefix}_Target_low"] = low
    out[f"{prefix}_Target_high"] = high
    return out


# Fixed medication profiles (dose is user input)
# Values are simplified defaults for a teaching app.
# Concentration target ranges are shown as optional reference bands (not medical advice).
PROFILES = {
    "Diazepam": {
        "F": 1.0,
        "t_half_h": 36.0,
        "ka_per_h": 1.0,
        "Vd_L_per_kg": 0.9,
        "default_tau_h": 24,
        "default_n_doses": 14,
        # Example reference band: 100–1000 ng/mL  -> 0.1–1.0 mg/L
        "target_low_mg_per_L": 0.10,
        "target_high_mg_per_L": 1.00,
        "dose_default_mg": 5.0,
        "dose_min_mg": 0.0,
        "dose_max_mg": 100.0,
        "dose_step_mg": 0.5,
    },
    "Sertralin": {
        # Absolute bioavailability is often cited as >44%; use 0.44 as a conservative default.
        "F": 0.44,
        "t_half_h": 26.0,        # typical ~22–36 h
        "ka_per_h": 0.30,        # slower absorption (Tmax commonly several hours)
        "Vd_L_per_kg": 20.0,     # very large apparent Vd reported in references
        "default_tau_h": 24,
        "default_n_doses": 28,   # longer horizon to show approach to steady state
        # Example reference band: 10–150 ng/mL -> 0.01–0.15 mg/L
        "target_low_mg_per_L": 0.010,
        "target_high_mg_per_L": 0.150,
        "dose_default_mg": 50.0,
        "dose_min_mg": 0.0,
        "dose_max_mg": 200.0,
        "dose_step_mg": 25.0,
    }
}


def main():
    st.title("Pharmakokinetik-Rechner (oral): Diazepam & Sertralin")
    st.caption(
        "Modell: 1-Kompartiment, first-order Absorption und Elimination (linear). "
        "Keine Interaktionen, keine Therapieempfehlung."
    )

    tabs = st.tabs(["Rechner", "Modellannahmen & Hinweise"])

    with tabs[1]:
        with st.expander("Annahmen (wichtig)"):
            st.markdown(
                "- 1-Kompartiment-Modell\n"
                "- Absorption und Elimination 1. Ordnung\n"
                "- Lineare Kinetik (Superposition bei Mehrfachdosierung)\n"
                "- Keine aktiven Metaboliten, keine Sättigung, keine Interaktionen\n"
                "- Medikamentenparameter sind als Beispielwerte fix hinterlegt.\n"
                "- Referenzbereiche sind optional und dienen nur zur Visualisierung (keine klinische Empfehlung)."
            )

    with tabs[0]:
        with st.form("pk_form"):
            st.subheader("Patient")
            weight_kg = st.number_input(
                "Körpergewicht (kg)", min_value=30.0, max_value=200.0, value=70.0, step=1.0
            )

            st.subheader("Simulation")
            duration_h = st.slider(
                "Simulationsdauer (h)", min_value=8, max_value=336, value=168, step=8
            )  # up to 14 days
            dt_min = st.slider("Zeitauflösung (min)", min_value=1, max_value=60, value=5, step=1)
            scale = st.radio("Plot-Skala", options=["linear", "log"], index=0, horizontal=True)
            show_targets = st.checkbox("Referenzbereiche im Plot anzeigen", value=True)

            st.subheader("Mehrfachdosierung (optional, pro Medikament separat)")
            col_reg1, col_reg2 = st.columns(2)

            with col_reg1:
                st.markdown("**Diazepam**")
                multiple_diaz = st.checkbox("Mehrfachdosierung Diazepam", value=True)
                if multiple_diaz:
                    tau_diaz = st.slider(
                        "Dosierintervall τ Diazepam (h)",
                        min_value=2, max_value=72, value=int(PROFILES["Diazepam"]["default_tau_h"]), step=1
                    )
                    n_diaz = st.slider(
                        "Anzahl Dosen Diazepam",
                        min_value=1, max_value=60, value=int(PROFILES["Diazepam"]["default_n_doses"]), step=1
                    )
                else:
                    tau_diaz = 0.0
                    n_diaz = 1

            with col_reg2:
                st.markdown("**Sertralin**")
                multiple_ser = st.checkbox("Mehrfachdosierung Sertralin", value=True)
                if multiple_ser:
                    tau_ser = st.slider(
                        "Dosierintervall τ Sertralin (h)",
                        min_value=12, max_value=48, value=int(PROFILES["Sertralin"]["default_tau_h"]), step=1
                    )
                    n_ser = st.slider(
                        "Anzahl Dosen Sertralin",
                        min_value=1, max_value=60, value=int(PROFILES["Sertralin"]["default_n_doses"]), step=1
                    )
                else:
                    tau_ser = 0.0
                    n_ser = 1

            st.subheader("Medikamentenprofile (fix) – nur Dosis eingeben")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Diazepam")
                d_diaz = st.number_input(
                    "Dosis pro Gabe (mg)",
                    min_value=float(PROFILES["Diazepam"]["dose_min_mg"]),
                    max_value=float(PROFILES["Diazepam"]["dose_max_mg"]),
                    value=float(PROFILES["Diazepam"]["dose_default_mg"]),
                    step=float(PROFILES["Diazepam"]["dose_step_mg"]),
                )

            with col2:
                st.markdown("### Sertralin")
                d_ser = st.number_input(
                    "Dosis pro Gabe (mg)",
                    min_value=float(PROFILES["Sertralin"]["dose_min_mg"]),
                    max_value=float(PROFILES["Sertralin"]["dose_max_mg"]),
                    value=float(PROFILES["Sertralin"]["dose_default_mg"]),
                    step=float(PROFILES["Sertralin"]["dose_step_mg"]),
                )

            submitted = st.form_submit_button("Berechnen")

        if submitted:
            t = build_time_grid(duration_h=float(duration_h), dt_min=float(dt_min))

            diaz = PROFILES["Diazepam"]
            ser = PROFILES["Sertralin"]

            # Convert to Vd in L using weight
            Vd_diaz = float(diaz["Vd_L_per_kg"]) * float(weight_kg)
            Vd_ser = float(ser["Vd_L_per_kg"]) * float(weight_kg)

            # Elimination rate constants
            k_diaz = k_from_half_life(float(diaz["t_half_h"]))
            k_ser = k_from_half_life(float(ser["t_half_h"]))

            # Concentration curves
            if multiple_diaz:
                c_diaz = conc_oral_multiple_dose(
                    t=t, dose_mg=float(d_diaz), F=float(diaz["F"]), Vd_L=Vd_diaz,
                    ka_per_h=float(diaz["ka_per_h"]), k_per_h=k_diaz,
                    tau_h=float(tau_diaz), n_doses=int(n_diaz)
                )
            else:
                c_diaz = conc_oral_single_dose(
                    t=t, dose_mg=float(d_diaz), F=float(diaz["F"]), Vd_L=Vd_diaz,
                    ka_per_h=float(diaz["ka_per_h"]), k_per_h=k_diaz
                )

            if multiple_ser:
                c_ser = conc_oral_multiple_dose(
                    t=t, dose_mg=float(d_ser), F=float(ser["F"]), Vd_L=Vd_ser,
                    ka_per_h=float(ser["ka_per_h"]), k_per_h=k_ser,
                    tau_h=float(tau_ser), n_doses=int(n_ser)
                )
            else:
                c_ser = conc_oral_single_dose(
                    t=t, dose_mg=float(d_ser), F=float(ser["F"]), Vd_L=Vd_ser,
                    ka_per_h=float(ser["ka_per_h"]), k_per_h=k_ser
                )

            # Metrics
            m_diaz = metrics_from_curve(t, c_diaz)
            m_ser = metrics_from_curve(t, c_ser)

            st.subheader("Kennwerte (aus Simulation)")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Diazepam**")
                st.metric("Cmax (mg/L)", f"{m_diaz['Cmax_mg_per_L']:.4f}")
                st.metric("Tmax (h)", f"{m_diaz['Tmax_h']:.2f}")
                st.metric("AUC0-last (mg·h/L)", f"{m_diaz['AUC0_last_mg_h_per_L']:.2f}")
            with c2:
                st.markdown("**Sertralin**")
                st.metric("Cmax (mg/L)", f"{m_ser['Cmax_mg_per_L']:.4f}")
                st.metric("Tmax (h)", f"{m_ser['Tmax_h']:.2f}")
                st.metric("AUC0-last (mg·h/L)", f"{m_ser['AUC0_last_mg_h_per_L']:.2f}")

            st.subheader("Konzentrations-Zeit-Kurven")
            df = pd.DataFrame(
                {
                    "t_h": t,
                    "Diazepam_mg_per_L": c_diaz,
                    "Sertralin_mg_per_L": c_ser,
                }
            ).set_index("t_h")

            if show_targets:
                df = add_target_band(
                    df,
                    float(diaz["target_low_mg_per_L"]),
                    float(diaz["target_high_mg_per_L"]),
                    "Diazepam"
                )
                df = add_target_band(
                    df,
                    float(ser["target_low_mg_per_L"]),
                    float(ser["target_high_mg_per_L"]),
                    "Sertralin"
                )

            # Apply log scaling safe-clamp if requested
            if scale == "log":
                df_plot = df.clip(lower=1e-12)
            else:
                df_plot = df

            st.line_chart(df_plot)

            if show_targets:
                st.caption(
                    "Referenzbereiche werden als horizontale Linien (min/max) dargestellt "
                    "(nur Visualisierung, keine klinische Empfehlung)."
                )
            if scale == "log":
                st.caption("Hinweis: Bei log-Skala werden Werte nahe 0 geklammert, um log(0) zu vermeiden.")


if __name__ == "__main__":
    main()