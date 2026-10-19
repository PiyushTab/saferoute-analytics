"""
SafeRoute Analytics - Visualization Engine
Generates all charts: histograms, box plots, bar charts, pie/donut charts
using Seaborn, Matplotlib, and Plotly
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
import io
import base64

# ─── Color Palette ────────────────────────────────────────────────────────────
COLORS = {
    'Fatal': '#C94F43',
    'Serious': '#D9822B',
    'Minor': '#5D9568',
    'Property Damage Only': '#4F8B9B',
}
SEVERITY_ORDER = ['Property Damage Only', 'Minor', 'Serious', 'Fatal']

PALETTE = ['#39785B', '#6B9B78', '#D49A42', '#C96D4B', '#4F8B9B',
           '#8A9B63', '#A87958', '#5D7892', '#B7A16A', '#6E8B80']

PLOTLY_TEMPLATE = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='#FBFCF8',
    font=dict(color='#26352B', family='Inter, sans-serif', size=12),
    xaxis=dict(gridcolor='#E5EAE1', tickfont=dict(color='#617064')),
    yaxis=dict(gridcolor='#E5EAE1', tickfont=dict(color='#617064')),
    colorway=PALETTE,
    margin=dict(l=50, r=30, t=50, b=50),
)


def fig_to_base64(fig):
    """Convert matplotlib figure to base64 PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight',
                facecolor='#FFFFFF', edgecolor='none', dpi=120)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


def plotly_to_json(fig):
    """Convert plotly figure to JSON."""
    return json.loads(fig.to_json())


def apply_dark_style():
    sns.set_theme(style="whitegrid", palette=PALETTE)
    plt.rcParams.update({
        'figure.facecolor': '#FFFFFF',
        'axes.facecolor': '#FBFCF8',
        'axes.edgecolor': '#DCE4DA',
        'axes.labelcolor': '#26352B',
        'xtick.color': '#617064',
        'ytick.color': '#617064',
        'text.color': '#26352B',
        'grid.color': '#E5EAE1',
        'grid.alpha': 0.8,
    })



# ═══════════════════════════════════════════════════════════════════════════════
#  1. HISTOGRAMS (Seaborn + Matplotlib)
# ═══════════════════════════════════════════════════════════════════════════════

def histogram_speed(df):
    apply_dark_style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor('#0F172A')

    # Overall speed distribution
    sns.histplot(df['speed_kmh'], bins=40, kde=True, color='#6366F1',
                 ax=axes[0], edgecolor='#312E81', linewidth=0.5, alpha=0.8)
    axes[0].set_title('Speed Distribution at Accident Sites', color='#E2E8F0', fontsize=13, pad=12)
    axes[0].set_xlabel('Speed (km/h)', color='#94A3B8')
    axes[0].set_ylabel('Count', color='#94A3B8')

    # Speed by severity
    colors = [COLORS[s] for s in SEVERITY_ORDER]
    for i, sev in enumerate(SEVERITY_ORDER):
        subset = df[df['severity'] == sev]['speed_kmh']
        sns.histplot(subset, bins=30, kde=True, color=colors[i],
                     ax=axes[1], alpha=0.55, label=sev, edgecolor='none')
    axes[1].set_title('Speed by Accident Severity', color='#E2E8F0', fontsize=13, pad=12)
    axes[1].set_xlabel('Speed (km/h)', color='#94A3B8')
    axes[1].set_ylabel('Count', color='#94A3B8')
    axes[1].legend(facecolor='#1E293B', edgecolor='#334155', labelcolor='#CBD5E1', fontsize=9)

    fig.suptitle('Histogram Analysis — Vehicle Speed', color='#F1F5F9', fontsize=15, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig_to_base64(fig)


def histogram_hour(df):
    apply_dark_style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor('#0F172A')

    hourly = df.groupby('hour').size().reset_index(name='count')
    axes[0].bar(hourly['hour'], hourly['count'], color='#8B5CF6', edgecolor='#4C1D95',
                linewidth=0.5, alpha=0.85)
    axes[0].set_title('Accidents by Hour of Day', color='#E2E8F0', fontsize=13, pad=12)
    axes[0].set_xlabel('Hour', color='#94A3B8')
    axes[0].set_ylabel('Accident Count', color='#94A3B8')
    axes[0].set_xticks(range(0, 24))

    # Histogram of injuries
    sns.histplot(df['injuries'], bins=20, kde=True, color='#EC4899',
                 ax=axes[1], edgecolor='#831843', linewidth=0.5, alpha=0.8)
    axes[1].set_title('Distribution of Injuries per Accident', color='#E2E8F0', fontsize=13, pad=12)
    axes[1].set_xlabel('Number of Injuries', color='#94A3B8')
    axes[1].set_ylabel('Count', color='#94A3B8')

    fig.suptitle('Histogram Analysis — Temporal & Casualty Patterns', color='#F1F5F9', fontsize=15, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig_to_base64(fig)


# ═══════════════════════════════════════════════════════════════════════════════
#  2. BOX & WHISKER PLOTS (Seaborn + Matplotlib)
# ═══════════════════════════════════════════════════════════════════════════════

def boxplot_speed_severity(df):
    apply_dark_style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    fig.patch.set_facecolor('#0F172A')

    palette = {s: COLORS[s] for s in SEVERITY_ORDER}

    sns.boxplot(data=df, x='severity', y='speed_kmh', order=SEVERITY_ORDER,
                palette=palette, ax=axes[0], linewidth=1.2,
                flierprops=dict(marker='o', color='#64748B', alpha=0.3, markersize=3))
    axes[0].set_title('Speed vs Severity', color='#E2E8F0', fontsize=13, pad=12)
    axes[0].set_xlabel('Severity', color='#94A3B8')
    axes[0].set_ylabel('Speed (km/h)', color='#94A3B8')
    axes[0].tick_params(axis='x', rotation=15)

    sns.boxplot(data=df, x='severity', y='injuries', order=SEVERITY_ORDER,
                palette=palette, ax=axes[1], linewidth=1.2,
                flierprops=dict(marker='o', color='#64748B', alpha=0.3, markersize=3))
    axes[1].set_title('Injuries vs Severity', color='#E2E8F0', fontsize=13, pad=12)
    axes[1].set_xlabel('Severity', color='#94A3B8')
    axes[1].set_ylabel('Injuries', color='#94A3B8')
    axes[1].tick_params(axis='x', rotation=15)

    fig.suptitle('Box & Whisker — Speed & Injuries by Severity', color='#F1F5F9', fontsize=15, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig_to_base64(fig)


def boxplot_road_speed(df):
    apply_dark_style()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    fig.patch.set_facecolor('#0F172A')

    road_order = df.groupby('road_type')['speed_kmh'].median().sort_values(ascending=False).index

    sns.boxplot(data=df, x='road_type', y='speed_kmh', order=road_order,
                palette=PALETTE[:6], ax=axes[0], linewidth=1.2,
                flierprops=dict(marker='o', color='#64748B', alpha=0.3, markersize=3))
    axes[0].set_title('Speed Distribution by Road Type', color='#E2E8F0', fontsize=13, pad=12)
    axes[0].set_xlabel('Road Type', color='#94A3B8')
    axes[0].set_ylabel('Speed (km/h)', color='#94A3B8')
    axes[0].tick_params(axis='x', rotation=20)

    city_order = df.groupby('city')['injuries'].median().sort_values(ascending=False).index
    sns.boxplot(data=df, x='city', y='injuries', order=city_order,
                palette=PALETTE, ax=axes[1], linewidth=1.2,
                flierprops=dict(marker='o', color='#64748B', alpha=0.3, markersize=3))
    axes[1].set_title('Injuries by City', color='#E2E8F0', fontsize=13, pad=12)
    axes[1].set_xlabel('City', color='#94A3B8')
    axes[1].set_ylabel('Injuries', color='#94A3B8')
    axes[1].tick_params(axis='x', rotation=20)

    fig.suptitle('Box & Whisker — Road Type & City Analysis', color='#F1F5F9', fontsize=15, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig_to_base64(fig)


# ═══════════════════════════════════════════════════════════════════════════════
#  3. BAR CHARTS (Matplotlib + Plotly)
# ═══════════════════════════════════════════════════════════════════════════════

def bar_cause_matplotlib(df):
    apply_dark_style()
    cause_counts = df['cause'].value_counts().head(10)
    fig, ax = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor('#0F172A')

    bars = ax.barh(cause_counts.index[::-1], cause_counts.values[::-1],
                   color=PALETTE, edgecolor='#1E293B', linewidth=0.5, alpha=0.9)

    for bar, val in zip(bars, cause_counts.values[::-1]):
        ax.text(bar.get_width() + 8, bar.get_y() + bar.get_height() / 2,
                f'{val:,}', va='center', ha='left', color='#94A3B8', fontsize=10)

    ax.set_title('Top 10 Accident Causes (Matplotlib)', color='#F1F5F9', fontsize=14, pad=14)
    ax.set_xlabel('Number of Accidents', color='#94A3B8')
    ax.set_xlim(0, cause_counts.max() * 1.15)
    plt.tight_layout()
    return fig_to_base64(fig)


def bar_city_plotly(df):
    city_sev = df.groupby(['city', 'severity']).size().reset_index(name='count')
    fig = go.Figure()
    colors_map = {s: COLORS[s] for s in SEVERITY_ORDER}

    for sev in SEVERITY_ORDER:
        subset = city_sev[city_sev['severity'] == sev]
        fig.add_trace(go.Bar(
            name=sev, x=subset['city'], y=subset['count'],
            marker_color=colors_map[sev], opacity=0.85,
            hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
        ))

    fig.update_layout(
        barmode='group', title='Accidents by City & Severity (Plotly)',
        title_font=dict(size=15, color='#F1F5F9'),
        legend=dict(bgcolor='rgba(30,41,59,0.8)', bordercolor='#334155',
                    font=dict(color='#CBD5E1')),
        **PLOTLY_TEMPLATE
    )
    return plotly_to_json(fig)


def bar_monthly_plotly(df):
    monthly = df.groupby(['year', 'month']).size().reset_index(name='count')
    monthly['date'] = pd.to_datetime(monthly[['year', 'month']].assign(day=1))

    fig = go.Figure()
    for yr in sorted(df['year'].unique()):
        subset = monthly[monthly['year'] == yr]
        fig.add_trace(go.Bar(
            name=str(yr), x=subset['month'].apply(
                lambda m: ['Jan','Feb','Mar','Apr','May','Jun',
                           'Jul','Aug','Sep','Oct','Nov','Dec'][m-1]),
            y=subset['count'],
            hovertemplate=f'<b>{yr}</b> — %{{x}}<br>Accidents: %{{y}}<extra></extra>',
            opacity=0.85
        ))

    fig.update_layout(
        barmode='group', title='Monthly Accident Trends by Year (Plotly)',
        title_font=dict(size=15, color='#F1F5F9'),
        xaxis_title='Month', yaxis_title='Accidents',
        legend=dict(bgcolor='rgba(30,41,59,0.8)', bordercolor='#334155',
                    font=dict(color='#CBD5E1')),
        **PLOTLY_TEMPLATE
    )
    return plotly_to_json(fig)


# ═══════════════════════════════════════════════════════════════════════════════
#  4. PIE & DONUT CHARTS (Matplotlib + Plotly)
# ═══════════════════════════════════════════════════════════════════════════════

def pie_severity_matplotlib(df):
    apply_dark_style()
    counts = df['severity'].value_counts().reindex(SEVERITY_ORDER)
    colors = [COLORS[s] for s in SEVERITY_ORDER]
    explode = [0.02, 0.02, 0.04, 0.06]

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    fig.patch.set_facecolor('#0F172A')

    # Pie
    wedges, texts, autotexts = axes[0].pie(
        counts, labels=SEVERITY_ORDER, colors=colors, explode=explode,
        autopct='%1.1f%%', startangle=140, pctdistance=0.75,
        wedgeprops=dict(edgecolor='#0F172A', linewidth=2, alpha=0.9)
    )
    for text in texts: text.set_color('#CBD5E1')
    for at in autotexts: at.set_color('#F1F5F9'); at.set_fontsize(10); at.set_fontweight('bold')
    axes[0].set_title('Severity Distribution — Pie (Matplotlib)', color='#E2E8F0', fontsize=12, pad=15)

    # Donut
    wedges2, texts2, autotexts2 = axes[1].pie(
        counts, labels=None, colors=colors, explode=explode,
        autopct='%1.1f%%', startangle=140, pctdistance=0.78,
        wedgeprops=dict(edgecolor='#0F172A', linewidth=2, width=0.55, alpha=0.9)
    )
    for at in autotexts2: at.set_color('#F1F5F9'); at.set_fontsize(10); at.set_fontweight('bold')
    centre_circle = plt.Circle((0, 0), 0.40, color='#0F172A')
    axes[1].add_patch(centre_circle)
    axes[1].text(0, 0, f'Total\n{counts.sum():,}', ha='center', va='center',
                 color='#E2E8F0', fontsize=13, fontweight='bold')
    axes[1].legend(SEVERITY_ORDER, loc='lower left', facecolor='#1E293B',
                   edgecolor='#334155', labelcolor='#CBD5E1', fontsize=9,
                   bbox_to_anchor=(-0.2, -0.05))
    axes[1].set_title('Severity Distribution — Donut (Matplotlib)', color='#E2E8F0', fontsize=12, pad=15)

    fig.suptitle('Accident Severity — Pie & Donut Charts', color='#F1F5F9', fontsize=15, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig_to_base64(fig)


def donut_weather_plotly(df):
    weather_counts = df['weather_condition'].value_counts().reset_index()
    weather_counts.columns = ['condition', 'count']

    fig = go.Figure(go.Pie(
        labels=weather_counts['condition'],
        values=weather_counts['count'],
        hole=0.52,
        marker=dict(colors=PALETTE[:len(weather_counts)],
                    line=dict(color='#0F172A', width=2)),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>',
        textinfo='label+percent',
        textfont=dict(color='#F1F5F9', size=11),
    ))
    fig.add_annotation(text=f"Weather<br>Analysis", x=0.5, y=0.5,
                       font_size=14, font_color='#E2E8F0', showarrow=False)
    fig.update_layout(
        title='Accidents by Weather Condition — Donut (Plotly)',
        title_font=dict(size=15, color='#F1F5F9'),
        showlegend=True,
        legend=dict(bgcolor='rgba(30,41,59,0.8)', bordercolor='#334155',
                    font=dict(color='#CBD5E1')),
        **PLOTLY_TEMPLATE
    )
    return plotly_to_json(fig)


def donut_road_plotly(df):
    road_counts = df['road_type'].value_counts().reset_index()
    road_counts.columns = ['road', 'count']

    fig = go.Figure(go.Pie(
        labels=road_counts['road'],
        values=road_counts['count'],
        hole=0.52,
        marker=dict(colors=PALETTE[:len(road_counts)],
                    line=dict(color='#0F172A', width=2)),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>',
        textinfo='label+percent',
        textfont=dict(color='#F1F5F9', size=11),
    ))
    fig.add_annotation(text=f"Road Type<br>Breakdown", x=0.5, y=0.5,
                       font_size=13, font_color='#E2E8F0', showarrow=False)
    fig.update_layout(
        title='Accidents by Road Type — Donut (Plotly)',
        title_font=dict(size=15, color='#F1F5F9'),
        showlegend=True,
        legend=dict(bgcolor='rgba(30,41,59,0.8)', bordercolor='#334155',
                    font=dict(color='#CBD5E1')),
        **PLOTLY_TEMPLATE
    )
    return plotly_to_json(fig)


# ═══════════════════════════════════════════════════════════════════════════════
#  5. ADDITIONAL CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

def heatmap_hour_day(df):
    pivot = df.pivot_table(index='day_of_week', columns='hour', values='accident_id',
                           aggfunc='count', fill_value=0)
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    apply_dark_style()
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor('#0F172A')

    sns.heatmap(pivot, ax=ax, cmap='YlOrRd', linewidths=0.3, linecolor='#0F172A',
                cbar_kws={'label': 'Accidents', 'shrink': 0.8},
                annot=True, fmt='d', annot_kws={'size': 8, 'color': '#1E293B'})
    ax.set_title('Accident Heatmap: Hour of Day × Day of Week', color='#F1F5F9', fontsize=14, pad=14)
    ax.set_xlabel('Hour of Day', color='#94A3B8')
    ax.set_ylabel('', color='#94A3B8')
    ax.tick_params(colors='#94A3B8')
    plt.tight_layout()
    return fig_to_base64(fig)


def scatter_speed_injuries_plotly(df):
    sample = df.sample(min(800, len(df)), random_state=42)
    colors_list = [COLORS.get(s, '#6366F1') for s in sample['severity']]

    fig = go.Figure()
    for sev in SEVERITY_ORDER:
        sub = sample[sample['severity'] == sev]
        fig.add_trace(go.Scatter(
            x=sub['speed_kmh'], y=sub['injuries'],
            mode='markers', name=sev,
            marker=dict(color=COLORS[sev], size=6, opacity=0.65,
                        line=dict(color='#0F172A', width=0.5)),
            hovertemplate='<b>Speed:</b> %{x} km/h<br><b>Injuries:</b> %{y}<extra></extra>'
        ))

    fig.update_layout(
        title='Speed vs Injuries — Scatter Plot (Plotly)',
        title_font=dict(size=15, color='#F1F5F9'),
        xaxis_title='Speed (km/h)', yaxis_title='Injuries',
        legend=dict(bgcolor='rgba(30,41,59,0.8)', bordercolor='#334155',
                    font=dict(color='#CBD5E1')),
        **PLOTLY_TEMPLATE
    )
    return plotly_to_json(fig)


def line_trend_plotly(df):
    df['date_parsed'] = pd.to_datetime(df['date'])
    monthly = df.resample('ME', on='date_parsed').agg(
        accidents=('accident_id', 'count'),
        fatalities=('fatalities', 'sum'),
        injuries=('injuries', 'sum')
    ).reset_index()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=monthly['date_parsed'], y=monthly['accidents'],
        name='Accidents', line=dict(color='#6366F1', width=2.5),
        fill='tozeroy', fillcolor='rgba(99,102,241,0.12)'
    ))
    fig.add_trace(go.Scatter(
        x=monthly['date_parsed'], y=monthly['injuries'],
        name='Injuries', line=dict(color='#F97316', width=2, dash='dot')
    ), secondary_y=True)
    fig.add_trace(go.Scatter(
        x=monthly['date_parsed'], y=monthly['fatalities'],
        name='Fatalities', line=dict(color='#EF4444', width=2.5)
    ), secondary_y=True)

    fig.update_layout(
        title='Monthly Trend: Accidents, Injuries & Fatalities',
        title_font=dict(size=15, color='#F1F5F9'),
        legend=dict(bgcolor='rgba(30,41,59,0.8)', bordercolor='#334155',
                    font=dict(color='#CBD5E1')),
        **PLOTLY_TEMPLATE
    )
    fig.update_yaxes(title_text="Accidents", secondary_y=False, gridcolor='rgba(148,163,184,0.1)')
    fig.update_yaxes(title_text="Casualties", secondary_y=True, gridcolor='rgba(148,163,184,0.05)')
    return plotly_to_json(fig)


def generate_all_charts(df):
    """Generate and return all chart data."""
    charts = {}
    # Matplotlib/Seaborn (base64 PNG)
    charts['hist_speed'] = histogram_speed(df)
    charts['hist_hour'] = histogram_hour(df)
    charts['box_speed_severity'] = boxplot_speed_severity(df)
    charts['box_road_speed'] = boxplot_road_speed(df)
    charts['bar_cause'] = bar_cause_matplotlib(df)
    charts['pie_severity'] = pie_severity_matplotlib(df)
    charts['heatmap_hour_day'] = heatmap_hour_day(df)

    # Plotly (JSON)
    charts['bar_city'] = bar_city_plotly(df)
    charts['bar_monthly'] = bar_monthly_plotly(df)
    charts['donut_weather'] = donut_weather_plotly(df)
    charts['donut_road'] = donut_road_plotly(df)
    charts['scatter_speed'] = scatter_speed_injuries_plotly(df)
    charts['line_trend'] = line_trend_plotly(df)

    return charts
