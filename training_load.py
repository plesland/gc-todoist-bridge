# training_load.py
from datetime import datetime, timedelta
from db import get_conn, init_db
import math
import pandas as pd

# ---------- CONFIG ----------

DEFAULT_HR_REST = 55
DEFAULT_HR_MAX = 166
CTL_WINDOW = 42
ATL_WINDOW = 7

# ---------- UTILITY FUNCTIONS ----------

def compute_hrTSS(duration_s, avg_hr, hr_rest=DEFAULT_HR_REST, hr_max=DEFAULT_HR_MAX):
    """Heart rate–based TSS (normalized for effort and duration)."""
    if not avg_hr:
        return None
    duration_hr = duration_s / 3600
    hr_thr = 0.9 * hr_max
    ri = (avg_hr - hr_rest) / (hr_thr - hr_rest)
    ri = max(0, min(ri, 1.2))
    return duration_hr * (ri ** 2) * 100


def compute_rTSS(duration_s, pace_s_per_km, thr_pace_s_per_km):
    """Pace-based TSS fallback when HR missing."""
    duration_hr = duration_s / 3600
    ri = thr_pace_s_per_km / pace_s_per_km
    ri = max(0, min(ri, 1.2))
    return duration_hr * (ri ** 2) * 100


def compute_ctl_atl_tsb(tss_series):
    """Compute CTL, ATL, TSB using exponential moving averages."""
    df = pd.DataFrame({"tss": tss_series}).fillna(0)
    ctl = df["tss"].ewm(span=CTL_WINDOW, adjust=False).mean()
    atl = df["tss"].ewm(span=ATL_WINDOW, adjust=False).mean()
    tsb = ctl - atl
    df["ctl"], df["atl"], df["tsb"] = ctl, atl, tsb
    return df


def estimate_threshold_pace(activities):
    """Estimate threshold pace from top-20min efforts."""
    paces = []
    for a in activities:
        if a["distance_m"] > 2000 and a["moving_time_s"] > 600:
            pace = a["moving_time_s"] / (a["distance_m"] / 1000)
            paces.append(pace)
    if not paces:
        return 300  # fallback 5:00/km
    best_pace = min(paces)
    return best_pace * 0.95


# ---------- MAIN COMPUTATION ----------

def compute_training_load(activities):
    """Compute TSS per activity and rolling load metrics."""
    if not activities:
        return {"message": "no activities provided"}

    # Estimate threshold pace from data
    thr_pace_s_per_km = estimate_threshold_pace(activities)
    daily_tss = []

    for a in activities:
        if a["type"].lower() != "run":
            continue

        tss = None
        if a.get("average_hr"):
            tss = compute_hrTSS(a["moving_time_s"], a["average_hr"])
        else:
            pace = a["moving_time_s"] / (a["distance_m"] / 1000)
            tss = compute_rTSS(a["moving_time_s"], pace, thr_pace_s_per_km)

        date = datetime.fromisoformat(a["start_date"].replace("Z", ""))
        daily_tss.append({"date": date.date(), "tss": round(tss, 1)})

    # Aggregate by date
    df = pd.DataFrame(daily_tss).groupby("date").sum().sort_index()
    metrics = compute_ctl_atl_tsb(df["tss"])
    df = pd.concat([df, metrics[["ctl", "atl", "tsb"]]], axis=1)

    latest = df.iloc[-1].to_dict()
    latest["trend"] = (
        "fatigued" if latest["tsb"] < -10 else
        "fresh" if latest["tsb"] > 10 else
        "balanced"
    )
    
        # ---------- Persist results ----------
    init_db()
    with get_conn() as conn:
        for i, row in df.iterrows():
            conn.execute("""
                INSERT OR REPLACE INTO training_load (user_id, date, tss, ctl, atl, tsb)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "default_user",  # Replace with real user_id if multi-user
                str(i),
                float(row["tss"]),
                float(row["ctl"]),
                float(row["atl"]),
                float(row["tsb"])
            ))
        conn.commit()

    return {
        "summary": {
            "ctl": round(latest["ctl"], 1),
            "atl": round(latest["atl"], 1),
            "tsb": round(latest["tsb"], 1),
            "trend": latest["trend"]
        },
        "history": df.tail(42).reset_index().to_dict(orient="records")
    }