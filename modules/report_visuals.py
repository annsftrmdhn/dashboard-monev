"""Static chart images for PDF/Excel Monev reports (matplotlib)."""
import io

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd


def _save_fig(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def daily_volume_png(df):
    if "created_date_only" not in df.columns or df["created_date_only"].isna().all():
        return None
    daily = df.groupby("created_date_only").size().reset_index(name="Volume")
    daily = daily.sort_values("created_date_only")
    daily["created_date_only"] = pd.to_datetime(daily["created_date_only"])

    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.plot(daily["created_date_only"], daily["Volume"], color="#3498db", marker="o", linewidth=2)
    ax.set_title("Tren Volume Tiket Harian", fontsize=11, fontweight="bold")
    ax.set_xlabel("Tanggal")
    ax.set_ylabel("Jumlah Tiket")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.autofmt_xdate()
    return _save_fig(fig)


def daily_frt_png(df):
    if (
        "created_date_only" not in df.columns
        or "frt_seconds" not in df.columns
        or df["frt_seconds"].isna().all()
    ):
        return None
    daily = df.groupby("created_date_only")["frt_seconds"].mean().reset_index()
    daily["frt_min"] = daily["frt_seconds"] / 60
    daily = daily.sort_values("created_date_only")
    daily["created_date_only"] = pd.to_datetime(daily["created_date_only"])

    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.plot(daily["created_date_only"], daily["frt_min"], color="#e67e22", marker="o", linewidth=2)
    ax.set_title("Rata-rata FRT per Hari (Menit)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Tanggal")
    ax.set_ylabel("FRT (menit)")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    fig.autofmt_xdate()
    return _save_fig(fig)


def sentiment_png(df):
    if "sentiment" not in df.columns or df["sentiment"].isna().all():
        return None
    counts = df["sentiment"].str.lower().value_counts()
    labels = counts.index.tolist()
    values = counts.values
    colors = {"positive": "#2ecc71", "negative": "#e74c3c", "neutral": "#95a5a6"}
    bar_colors = [colors.get(l, "#3498db") for l in labels]

    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    ax.bar(labels, values, color=bar_colors)
    ax.set_title("Distribusi Sentimen", fontsize=11, fontweight="bold")
    ax.set_ylabel("Jumlah Tiket")
    for i, v in enumerate(values):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=9)
    return _save_fig(fig)


def top_categories_png(df, top_n=10):
    if "Category" not in df.columns or df["Category"].isna().all():
        return None
    cat = df["Category"].value_counts().head(top_n).sort_values()
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.barh(cat.index.astype(str), cat.values, color="#9b59b6")
    ax.set_title(f"Top {top_n} Volume Kategori Layanan", fontsize=11, fontweight="bold")
    ax.set_xlabel("Jumlah Tiket")
    return _save_fig(fig)


def build_excel_summary_tables(df):
    """Aggregated tables for extra Excel sheets."""
    tables = {}

    if "created_date_only" in df.columns and not df["created_date_only"].isna().all():
        vol = df.groupby("created_date_only").size().reset_index(name="Volume")
        vol = vol.sort_values("created_date_only")
        vol.columns = ["Tanggal", "Volume"]
        tables["Volume Harian"] = vol

        if "frt_seconds" in df.columns and not df["frt_seconds"].isna().all():
            frt = df.groupby("created_date_only")["frt_seconds"].mean().reset_index()
            frt["Rata-rata FRT (menit)"] = (frt["frt_seconds"] / 60).round(2)
            frt = frt.sort_values("created_date_only")[["created_date_only", "Rata-rata FRT (menit)"]]
            frt.columns = ["Tanggal", "Rata-rata FRT (menit)"]
            tables["FRT Harian"] = frt

    if "sentiment" in df.columns and not df["sentiment"].isna().all():
        sent = df["sentiment"].str.lower().value_counts().reset_index()
        sent.columns = ["Sentimen", "Jumlah"]
        total = sent["Jumlah"].sum()
        sent["Persentase (%)"] = (sent["Jumlah"] / total * 100).round(1) if total else 0
        tables["Distribusi Sentimen"] = sent

    if "Category" in df.columns and not df["Category"].isna().all():
        cat = df["Category"].value_counts().head(15).reset_index()
        cat.columns = ["Kategori", "Volume"]
        tables["Top Kategori"] = cat

    if "hour" in df.columns and "day_name" in df.columns:
        pivot = df.groupby(["day_name", "hour"]).size().unstack(fill_value=0)
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        pivot = pivot.reindex([d for d in day_order if d in pivot.index])
        tables["Volume Jam x Hari"] = pivot.reset_index()

    return tables
