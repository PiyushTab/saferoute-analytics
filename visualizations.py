"""
SafeRoute Analytics - static chart renderer (Matplotlib + Seaborn).

Every public function takes a DataFrame and returns PNG bytes, so the Flask
API can serve them directly at /api/viz/<name>.png.

Charts are drawn with the object-oriented Figure API (no pyplot state), and
rendering is serialised with a lock, so it is safe under Flask's threaded server.
"""

import io
import threading

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import seaborn as sns

SEVERITY_ORDER = ["Property Damage Only", "Minor", "Serious", "Fatal"]
SEVERITY_COLORS = {
    "Fatal": "#C94F43",
    "Serious": "#D9822B",
    "Minor": "#5D9568",
    "Property Damage Only": "#4F8B9B",
}
PALETTE = ["#39785B", "#6B9B78", "#D49A42", "#C96D4B", "#4F8B9B",
           "#8A9B63", "#A87958", "#5D7892", "#B7A16A", "#6E8B80"]
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

INK = "#1F2A24"
MUTED = "#6B7570"
GRID = "#E4E8E2"
ACCENT = "#39785B"

_RC = {
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED,
    "axes.titlecolor": INK,
    "axes.titlesize": 12,
    "axes.titleweight": "semibold",
    "axes.titlelocation": "left",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "text.color": INK,
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "legend.frameon": False,
}

_LOCK = threading.Lock()


def _render(draw, size=(8, 4.4)):
    """Create a Figure, let `draw(fig)` fill it, and return PNG bytes."""
    with _LOCK, plt.rc_context(_RC):
        sns.set_theme(style="whitegrid", rc=_RC, context={"axes.labelsize": 10, "xtick.labelsize": 9, "ytick.labelsize": 9,
                                                       "legend.fontsize": 9, "font.size": 10})
        fig = Figure(figsize=size, dpi=130)
        FigureCanvasAgg(fig)
        draw(fig)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor="white", bbox_inches="tight", pad_inches=0.15)
        return buf.getvalue()


def _empty(fig, message="No data for the selected filters"):
    ax = fig.add_subplot(111)
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center", color=MUTED, fontsize=11)


def _present_severities(df):
    present = set(df["severity"].unique())
    return [s for s in SEVERITY_ORDER if s in present]


# ─── Distributions (Seaborn) ──────────────────────────────────────────────────

def speed_histogram(df):
    def draw(fig):
        if df.empty:
            return _empty(fig)
        ax = fig.add_subplot(111)
        sns.histplot(data=df, x="speed_kmh", hue="severity", hue_order=_present_severities(df),
                     palette=SEVERITY_COLORS, multiple="stack", bins=30, edgecolor="white",
                     linewidth=0.4, ax=ax)
        ax.set_xlabel("Speed (km/h)")
        ax.set_ylabel("Accidents")
        ax.grid(axis="x", visible=False)
        leg = ax.get_legend()
        if leg is not None:
            leg.set_title("")
    return _render(draw)


def injuries_histogram(df):
    def draw(fig):
        if df.empty:
            return _empty(fig)
        ax = fig.add_subplot(111)
        top = int(df["injuries"].quantile(0.99)) + 1
        sns.histplot(data=df[df["injuries"] <= top], x="injuries", discrete=True,
                     color=ACCENT, edgecolor="white", linewidth=0.4, ax=ax)
        ax.set_xlabel("Injuries")
        ax.set_ylabel("Accidents")
        ax.grid(axis="x", visible=False)
    return _render(draw)


def speed_box_by_severity(df):
    def draw(fig):
        if df.empty:
            return _empty(fig)
        ax = fig.add_subplot(111)
        order = _present_severities(df)
        sns.boxplot(data=df, x="severity", y="speed_kmh", order=order, hue="severity",
                    hue_order=order, palette=SEVERITY_COLORS, legend=False, width=0.55,
                    fliersize=2, linewidth=1, ax=ax)
        ax.set_xlabel("")
        ax.set_ylabel("Speed (km/h)")
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels([o.replace("Property Damage Only", "Property\ndamage") for o in order])
        ax.grid(axis="x", visible=False)
    return _render(draw)


def speed_box_by_road(df):
    def draw(fig):
        if df.empty:
            return _empty(fig)
        ax = fig.add_subplot(111)
        order = (df.groupby("road_type")["speed_kmh"].median().sort_values().index.tolist())
        sns.boxplot(data=df, x="road_type", y="speed_kmh", order=order, hue="road_type",
                    hue_order=order, palette=PALETTE[: len(order)], legend=False, width=0.55,
                    fliersize=2, linewidth=1, ax=ax)
        ax.set_xlabel("")
        ax.set_ylabel("Speed (km/h)")
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels([o.replace(" ", "\n", 1) for o in order])
        ax.grid(axis="x", visible=False)
    return _render(draw)


# ─── Comparisons and proportions (Matplotlib) ─────────────────────────────────

def top_causes_bar(df):
    def draw(fig):
        if df.empty:
            return _empty(fig)
        ax = fig.add_subplot(111)
        counts = df["cause"].value_counts().head(10).sort_values()
        bars = ax.barh(counts.index, counts.values, color=ACCENT, height=0.62)
        ax.bar_label(bars, labels=[f"{v:,}" for v in counts.values], padding=4,
                     color=MUTED, fontsize=9)
        ax.set_xlabel("Accidents")
        ax.set_xlim(0, counts.max() * 1.14)
        ax.grid(axis="y", visible=False)
    return _render(draw)


def severity_pie(df):
    def draw(fig):
        if df.empty:
            return _empty(fig)
        ax = fig.add_subplot(111)
        counts = df["severity"].value_counts().reindex(SEVERITY_ORDER).dropna()
        colors = [SEVERITY_COLORS[s] for s in counts.index]
        wedges, _ = ax.pie(counts.values, colors=colors, startangle=90, counterclock=False,
                           wedgeprops={"width": 0.42, "edgecolor": "white", "linewidth": 2})
        total = counts.sum()
        labels = [f"{s}  {v / total:.1%}  ({int(v):,})" for s, v in zip(counts.index, counts.values)]
        ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5))
        ax.text(0, 0, f"{int(total):,}\naccidents", ha="center", va="center",
                fontsize=12, color=INK)
        ax.set_aspect("equal")
    return _render(draw, size=(8, 4.2))


# ─── Patterns (Seaborn) ───────────────────────────────────────────────────────

def hour_day_heatmap(df):
    def draw(fig):
        if df.empty:
            return _empty(fig)
        ax = fig.add_subplot(111)
        pivot = (df.pivot_table(index="day_of_week", columns="hour", values="accident_id",
                                aggfunc="count", fill_value=0)
                 .reindex(index=DAY_ORDER, columns=range(24), fill_value=0))
        sns.heatmap(pivot, ax=ax, cmap=sns.light_palette(ACCENT, as_cmap=True),
                    linewidths=0.6, linecolor="white", square=False,
                    cbar_kws={"label": "Accidents", "shrink": 0.85})
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("")
        ax.set_yticklabels([d[:3] for d in DAY_ORDER], rotation=0)
        ax.set_xticklabels([str(h) for h in range(24)], rotation=0)
        ax.grid(False)
    return _render(draw, size=(11, 3.8))


CHARTS = {
    "speed_hist": speed_histogram,
    "injuries_hist": injuries_histogram,
    "box_severity": speed_box_by_severity,
    "box_road": speed_box_by_road,
    "cause_bar": top_causes_bar,
    "severity_pie": severity_pie,
    "heatmap": hour_day_heatmap,
}
