import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from config.settings import FRT_HISTOGRAM_MAX_MINUTES


def _daily_date_axis(fig, date_series):
    """Clamp x-axis to actual data dates (avoids spurious ticks before min date)."""
    dates = pd.to_datetime(date_series).dropna()
    if len(dates) == 0:
        return fig
    fig.update_xaxes(
        type='date',
        range=[dates.min(), dates.max()],
    )
    return fig


def plot_daily_volume(df):
    """
    Line chart: Volume tiket per hari.
    """
    if 'created_date_only' not in df.columns or df['created_date_only'].isna().all():
        return None
    daily = df.groupby('created_date_only').size().reset_index(name='Volume')
    daily = daily.sort_values('created_date_only')
    daily['created_date_only'] = pd.to_datetime(daily['created_date_only'])

    fig = px.line(
        daily,
        x='created_date_only',
        y='Volume',
        markers=True,
        title="Tren Volume Tiket Harian",
        color_discrete_sequence=['#3498db']
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Tanggal",
        yaxis_title="Jumlah Tiket",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=40)
    )
    return _daily_date_axis(fig, daily['created_date_only'])

def plot_site_distribution(df):
    """
    Pie chart: Distribusi per Site.
    """
    if 'Site Name' not in df.columns or df['Site Name'].isna().all():
        return None
    site_counts = df['Site Name'].value_counts().reset_index()
    site_counts.columns = ['Site', 'Volume']
    
    fig = px.pie(
        site_counts,
        names='Site',
        values='Volume',
        hole=0.4,
        title="Distribusi Tiket per Site",
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=40)
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig


def plot_sentiment_distribution(df):
    """
    Bar chart: Distribusi sentimen pelanggan.
    """
    if 'sentiment' not in df.columns:
        return None

    sentiment_series = df['sentiment'].fillna('neutral').astype(str).str.lower()
    sentiment_counts = sentiment_series.value_counts().reset_index()
    sentiment_counts.columns = ['Sentimen', 'Jumlah']

    label_map = {
        'negative': 'Negatif',
        'neutral': 'Netral',
        'positive': 'Positif'
    }
    sentiment_counts['Sentimen Label'] = sentiment_counts['Sentimen'].map(label_map).fillna(sentiment_counts['Sentimen'].str.title())

    # Preserve a stable order for readability.
    order = ['negative', 'neutral', 'positive']
    sentiment_counts['order'] = sentiment_counts['Sentimen'].map({k: i for i, k in enumerate(order)})
    sentiment_counts = sentiment_counts.sort_values(['order', 'Jumlah'], ascending=[True, False]).drop(columns=['order'])

    total = sentiment_counts['Jumlah'].sum()
    if total == 0:
        return None

    sentiment_counts['Persentase'] = (sentiment_counts['Jumlah'] / total * 100).round(1)

    color_map = {
        'Negatif': '#e74c3c',
        'Netral': '#f1c40f',
        'Positif': '#2ecc71'
    }

    fig = px.bar(
        sentiment_counts,
        x='Sentimen Label',
        y='Jumlah',
        text='Persentase',
        title='Distribusi Sentimen Pelanggan (hasil analisis sentimen)',
        color='Sentimen Label',
        color_discrete_map=color_map
    )
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(
        template='plotly_white',
        xaxis_title='Sentimen',
        yaxis_title='Jumlah Tiket',
        margin=dict(l=20, r=20, t=40, b=40),
        showlegend=False,
        yaxis=dict(range=[0, max(sentiment_counts['Jumlah']) * 1.15])
    )
    return fig

def plot_hour_day_heatmap(df):
    """
    Heatmap: Hari × Jam (for forecasting staffing).
    """
    if 'hour' not in df.columns or 'day_of_week' not in df.columns:
        return None
        
    # Pivot table to count hours vs days
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    # Filter valid non-null rows
    clean_df = df.dropna(subset=['hour', 'day_of_week'])
    if len(clean_df) == 0:
        return None
        
    pivot = pd.crosstab(
        clean_df['day_name'],
        clean_df['hour']
    )
    
    # Reindex days
    pivot = pivot.reindex(days).fillna(0)
    
    # Format X columns to 'HH:00'
    hours_labels = [f"{str(h).zfill(2)}:00" for h in pivot.columns]
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=hours_labels,
        y=pivot.index,
        colorscale='Viridis',
        hoverongaps=False,
        hovertemplate="Hari: %{y}<br>Jam: %{x}<br>Volume: %{z}<extra></extra>"
    ))
    fig.update_layout(
        title="Heatmap Kepadatan Tiket: Hari vs Jam Masuk",
        template="plotly_white",
        xaxis_title="Jam Masuk (WIB)",
        yaxis_title="Hari",
        margin=dict(l=20, r=20, t=40, b=40)
    )
    return fig

def plot_volume_by_category(df):
    """
    Bar chart: Volume per Kategori.
    """
    if 'Category' not in df.columns or df['Category'].isna().all():
        return None
    cat_counts = df['Category'].value_counts().reset_index()
    cat_counts.columns = ['Kategori', 'Volume']
    
    fig = px.bar(
        cat_counts.head(10),
        x='Volume',
        y='Kategori',
        orientation='h',
        title="Top 10 Volume Kategori Layanan",
        color_discrete_sequence=['#2c3e50'],
        text_auto=True
    )
    fig.update_layout(
        template="plotly_white",
        yaxis={'categoryorder': 'total ascending'},
        margin=dict(l=20, r=20, t=40, b=40)
    )
    return fig


def plot_negative_category_distribution(df):
    """
    Bar chart: Top 10 kategori dengan jumlah sentimen negatif terbanyak.
    """
    if 'Category' not in df.columns or 'sentiment' not in df.columns:
        return None

    negative_df = df[df['sentiment'].astype(str).str.lower() == 'negative']
    if negative_df.empty:
        return None

    neg_counts = negative_df['Category'].value_counts().head(10).reset_index()
    neg_counts.columns = ['Kategori', 'Jumlah Negatif']

    fig = px.bar(
        neg_counts,
        x='Jumlah Negatif',
        y='Kategori',
        orientation='h',
        title='Top 10 Kategori dengan Sentimen Negatif Terbanyak',
        color='Jumlah Negatif',
        color_continuous_scale='Reds',
        text_auto=True
    )
    fig.update_layout(
        template='plotly_white',
        xaxis_title='Jumlah Tiket Negatif',
        yaxis_title='Kategori',
        yaxis={'categoryorder': 'total ascending'},
        margin=dict(l=20, r=20, t=40, b=40),
        coloraxis_showscale=False
    )
    return fig


def plot_volume_by_day_of_week(df):
    """
    Bar chart: Volume per Hari dalam Seminggu.
    """
    if 'day_name' not in df.columns or df['day_name'].isna().all():
        return None
        
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_counts = df['day_name'].value_counts().reindex(days).fillna(0).reset_index()
    day_counts.columns = ['Hari', 'Volume']
    
    fig = px.bar(
        day_counts,
        x='Hari',
        y='Volume',
        title="Volume Tiket per Hari dalam Seminggu",
        color_discrete_sequence=['#16a085'],
        text_auto=True
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=40)
    )
    return fig

def plot_frt_histogram(df):
    """
    Histogram: Distribusi FRT (sumbu X dibatasi 0–150 menit).
    """
    if 'frt_seconds' not in df.columns or df['frt_seconds'].isna().all():
        return None
    frt_minutes = df['frt_seconds'].dropna() / 60
    frt_display = frt_minutes[frt_minutes <= FRT_HISTOGRAM_MAX_MINUTES]

    fig = px.histogram(
        x=frt_display,
        nbins=30,
        title=f"Distribusi First Response Time (FRT) — 0–{FRT_HISTOGRAM_MAX_MINUTES} menit",
        color_discrete_sequence=['#9b59b6'],
        labels={'x': 'FRT (Menit)'}
    )
    fig.update_layout(
        template="plotly_white",
        yaxis_title="Jumlah Tiket",
        margin=dict(l=20, r=20, t=40, b=40)
    )
    fig.update_xaxes(range=[0, FRT_HISTOGRAM_MAX_MINUTES], tick0=0, dtick=10)
    return fig

def plot_daily_average_frt(df):
    """
    Line chart: FRT rata-rata per hari.
    """
    if 'created_date_only' not in df.columns or 'frt_seconds' not in df.columns or df['frt_seconds'].isna().all():
        return None
        
    daily_frt = df.groupby('created_date_only')['frt_seconds'].mean().reset_index()
    daily_frt['frt_min'] = daily_frt['frt_seconds'] / 60
    daily_frt = daily_frt.sort_values('created_date_only')
    daily_frt['created_date_only'] = pd.to_datetime(daily_frt['created_date_only'])

    fig = px.line(
        daily_frt,
        x='created_date_only',
        y='frt_min',
        markers=True,
        title="Rata-rata FRT per Hari (Menit)",
        color_discrete_sequence=['#e67e22']
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Tanggal",
        yaxis_title="Rata-rata FRT (Menit)",
        margin=dict(l=20, r=20, t=40, b=40)
    )
    fig.update_yaxes(range=[0, FRT_HISTOGRAM_MAX_MINUTES])
    return _daily_date_axis(fig, daily_frt['created_date_only'])

def plot_frt_by_site(df):
    """
    Bar chart: FRT per Site.
    """
    if 'Site Name' not in df.columns or 'frt_seconds' not in df.columns or df['frt_seconds'].isna().all():
        return None
        
    site_frt = df.groupby('Site Name')['frt_seconds'].mean().reset_index()
    site_frt['frt_min'] = site_frt['frt_seconds'] / 60
    
    fig = px.bar(
        site_frt,
        x='Site Name',
        y='frt_min',
        title="Rata-Rata Kecepatan Respon (FRT) per Site",
        color='Site Name',
        color_discrete_sequence=px.colors.qualitative.Safe,
        text_auto='.2f'
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Site Name",
        yaxis_title="Rata-rata FRT (Menit)",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=40)
    )
    fig.update_yaxes(range=[0, FRT_HISTOGRAM_MAX_MINUTES])
    return fig

def plot_frt_by_category(df):
    """
    Bar chart: FRT per Kategori.
    """
    if 'Category' not in df.columns or 'frt_seconds' not in df.columns or df['frt_seconds'].isna().all():
        return None
        
    cat_frt = df.groupby('Category')['frt_seconds'].mean().reset_index()
    cat_frt['frt_min'] = cat_frt['frt_seconds'] / 60
    cat_frt = cat_frt.sort_values('frt_min', ascending=False).head(10)
    
    fig = px.bar(
        cat_frt,
        x='frt_min',
        y='Category',
        orientation='h',
        title="Top 10 Kategori Layanan dengan FRT Terlama",
        color_discrete_sequence=['#e74c3c'],
        text_auto='.2f'
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title="Rata-rata FRT (Menit)",
        yaxis_title="Kategori",
        yaxis={'categoryorder': 'total ascending'},
        margin=dict(l=20, r=20, t=40, b=40)
    )
    fig.update_xaxes(range=[0, FRT_HISTOGRAM_MAX_MINUTES])
    return fig

def plot_site_category_distribution(df, site_name):
    """
    Pie chart: Distribusi kategori per site.
    """
    site_df = df[df['Site Name'] == site_name] if site_name != 'Semua Site' else df
    if 'Category' not in site_df.columns or site_df['Category'].isna().all():
        return None
        
    cat_counts = site_df['Category'].value_counts().head(8).reset_index()
    cat_counts.columns = ['Kategori', 'Volume']
    
    fig = px.pie(
        cat_counts,
        names='Kategori',
        values='Volume',
        title=f"Top 8 Kategori Layanan di {site_name}",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=40)
    )
    return fig

def plot_category_matrix(df):
    """
    Treemap or Matrix table visualization of Category vs Sub Category.
    """
    if 'Category' not in df.columns or 'Sub Category' not in df.columns:
        return None
        
    matrix_df = df.groupby(['Category', 'Sub Category']).size().reset_index(name='Volume')
    matrix_df = matrix_df.sort_values('Volume', ascending=False).head(30)
    
    fig = px.treemap(
        matrix_df,
        path=['Category', 'Sub Category'],
        values='Volume',
        title="Top 30 Distribusi Hirarki: Kategori & Sub-Kategori",
        color='Volume',
        color_continuous_scale='Blues'
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=40, b=40)
    )
    return fig
