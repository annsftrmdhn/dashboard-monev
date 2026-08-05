import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os
import re

# Import modular components
from config import settings
from modules import loader, cleaner, metrics, charts, exporter

# Set page configuration
st.set_page_config(
    page_title="Bravo Bea Cukai - Contact Center Dashboard",
    page_icon="🏢",
    layout="wide"
)

# Premium executive style CSS
st.markdown("""
    <style>
    .main {
        background-color: #f4f6f9;
    }
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #fcfdfe 100%);
        border-radius: 14px;
        padding: 22px 18px;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.04);
        text-align: center;
        border-top: 5px solid #3498db;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 12px;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.08);
    }
    .kpi-val {
        font-size: 34px;
        font-weight: 800;
        color: #2c3e50;
        margin-bottom: 2px;
    }
    .kpi-label {
        font-size: 12px;
        color: #95a5a6;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 700;
    }
    .insight-box {
        background: linear-gradient(to right, #ebf8ff, #f0fff4);
        border-left: 5px solid #3182ce;
        padding: 16px 20px;
        border-radius: 8px;
        margin-top: 10px;
        margin-bottom: 20px;
        font-size: 14px;
        color: #2b6cb0;
        line-height: 1.6;
        box-shadow: 0 2px 8px rgba(49,130,206,0.08);
    }
    </style>
""", unsafe_allow_html=True)

# Cache sentiment classifier model
@st.cache_resource
def load_sentiment_model():
    import warnings
    warnings.filterwarnings('ignore', message='.*torchvision.*')
    os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'
    try:
        from transformers import pipeline
    except ImportError:
        return None
    return pipeline(
        "sentiment-analysis",
        model="w11wo/indonesian-roberta-base-sentiment-classifier"
    )

try:
    classifier = load_sentiment_model()
except Exception:
    classifier = None


# HEADER
col_logo, col_title = st.columns([1, 8])
with col_title:
    st.title("Dashboard Monitoring Contact Center Bravo Bea Cukai")
    st.markdown("##### Subdirektorat Strategi Komunikasi, Monitoring dan Evaluasi DJBC | Project MONEV")

# SIDEBAR CONFIGURATION
st.sidebar.header("Unggah Data & Parameter SLA")
# Allow both CSV and Excel uploads
uploaded_file = st.sidebar.file_uploader("Unggah File Report Ticket (CSV/XLSX)", type=["csv", "xlsx", "xls"])

# Threshold Configs
st.sidebar.markdown("---")
st.sidebar.markdown("### Threshold & SLA")
sla_threshold = st.sidebar.slider(
    "Threshold SLA (detik):",
    min_value=60,
    max_value=1200,
    value=settings.DEFAULT_SLA_THRESHOLD,
    step=30
)

target_occupancy = st.sidebar.slider(
    "Target Occupancy Rate:",
    min_value=0.50,
    max_value=0.99,
    value=settings.TARGET_OCCUPANCY,
    step=0.05
)

# Load data
raw_df = None
if uploaded_file is not None:
    df, err = loader.load_and_validate_csv(uploaded_file)
    if err:
        st.sidebar.error(err)
    else:
        raw_df = df
        st.sidebar.success("File CSV berhasil diunggah!")
else:
    # Try reading default data
    default_paths = ["output/sentiment_results.csv", "output/data_sentimen_prepared.csv"]
    for path in default_paths:
        if os.path.exists(path):
            df, err = loader.load_and_validate_csv(path)
            if not err:
                raw_df = df
                st.sidebar.info(f"Menggunakan data default: {path}")
                break

if raw_df is not None:
    # Preprocess & clean
    with st.spinner("Melakukan cleaning dan preprocessing data..."):
        clean_df = cleaner.clean_dataframe(raw_df)

    kpis = metrics.calculate_kpi_metrics(clean_df, sla_threshold)
    site_scorecard = metrics.get_site_scorecard(clean_df, sla_threshold)
    staffing = metrics.get_peak_hour_staffing(clean_df, kpis, target_occupancy)
    formula_table = metrics.get_metrics_formula_table(kpis, sla_threshold, target_occupancy, staffing)
    
    # 7 TABS
    tabs = st.tabs([
        "Overview & KPI",
        "Analisis Volume & Staffing",
        "Performa Layanan (FRT)",
        "Analisis per Site",
        "Analisis Kategori",
        "Data Mentah & Export",
        "Prediksi Sentimen Baru"
    ])
    
    # TAB 1: OVERVIEW & KPI
    with tabs[0]:
        st.subheader("Metrik Utama Kinerja (KPI)")
        
        # Display KPI cards
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f"""
                <div class="kpi-card" style="border-top: 5px solid #2980b9;">
                    <div class="kpi-val">{kpis['total_tickets']:,}</div>
                    <div class="kpi-label">Total Volume Tiket</div>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div class="kpi-card" style="border-top: 5px solid #e67e22;">
                    <div class="kpi-val">{kpis['asa_minutes']:.2f} m</div>
                    <div class="kpi-label">Rata-rata ASA</div>
                </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
                <div class="kpi-card" style="border-top: 5px solid #2ecc71;">
                    <div class="kpi-val" style="color: #27ae60;">{kpis['service_level']:.1f}%</div>
                    <div class="kpi-label">Service Level (SL)</div>
                </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
                <div class="kpi-card" style="border-top: 5px solid #9b59b6;">
                    <div class="kpi-val">{kpis['resolution_rate_pct']:.1f}%</div>
                    <div class="kpi-label">Resolution Rate</div>
                </div>
            """, unsafe_allow_html=True)
        with c5:
            st.markdown(f"""
                <div class="kpi-card" style="border-top: 5px solid #f1c40f;">
                    <div class="kpi-val">{kpis['aht_minutes']:.2f} m</div>
                    <div class="kpi-label">Rata-rata AHT</div>
                </div>
            """, unsafe_allow_html=True)
            
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            fig_daily = charts.plot_daily_volume(clean_df)
            if fig_daily:
                st.plotly_chart(fig_daily, use_container_width=True)
        with col_v2:
            fig_site_dist = charts.plot_site_distribution(clean_df)
            if fig_site_dist:
                st.plotly_chart(fig_site_dist, use_container_width=True)

        st.markdown("---")
        fig_sentiment = charts.plot_sentiment_distribution(clean_df)
        if fig_sentiment:
            st.plotly_chart(fig_sentiment, use_container_width=True)
                
        # Executive Insight Box
        st.markdown(f"""
            <div class="insight-box">
                <b>Ringkasan Kinerja Utama:</b><br>
                • Capaian <b>Service Level</b> berada pada <b>{kpis['service_level']:.1f}%</b> dengan target respon di bawah {sla_threshold} detik.<br>
                • Rata-rata <b>ASA/FRT</b> adalah <b>{kpis['asa_minutes']:.2f} menit</b>; rata-rata <b>AHT</b> (durasi penanganan) <b>{kpis['aht_minutes']:.2f} menit</b>.
            </div>
        """, unsafe_allow_html=True)

        with st.expander("Referensi Rumus Metrik Call Center"):
            st.dataframe(formula_table, use_container_width=True, hide_index=True)
        
    # TAB 2: ANALISIS VOLUME & STAFFING
    with tabs[1]:
        st.subheader("Analisis Volume Masuk & Jam Sibuk")
        
        col_vol1, col_vol2 = st.columns(2)
        with col_vol1:
            fig_dow = charts.plot_volume_by_day_of_week(clean_df)
            if fig_dow:
                st.plotly_chart(fig_dow, use_container_width=True)
        with col_vol2:
            fig_heatmap = charts.plot_hour_day_heatmap(clean_df)
            if fig_heatmap:
                st.plotly_chart(fig_heatmap, use_container_width=True)
                


        with st.expander("Referensi Rumus Metrik Call Center"):
            st.dataframe(formula_table, use_container_width=True, hide_index=True)
                
    # TAB 3: PERFORMA LAYANAN (FRT)
    with tabs[2]:
        st.subheader("Analisis First Response Time (FRT)")
        
        col_frt1, col_frt2 = st.columns(2)
        with col_frt1:
            fig_frt_hist = charts.plot_frt_histogram(clean_df)
            if fig_frt_hist:
                st.plotly_chart(fig_frt_hist, use_container_width=True)
        with col_frt2:
            fig_frt_daily = charts.plot_daily_average_frt(clean_df)
            if fig_frt_daily:
                st.plotly_chart(fig_frt_daily, use_container_width=True)
                
        col_frt3, col_frt4 = st.columns(2)
        with col_frt3:
            fig_frt_site = charts.plot_frt_by_site(clean_df)
            if fig_frt_site:
                st.plotly_chart(fig_frt_site, use_container_width=True)
        with col_frt4:
            fig_frt_cat = charts.plot_frt_by_category(clean_df)
            if fig_frt_cat:
                st.plotly_chart(fig_frt_cat, use_container_width=True)

    # TAB 4: ANALISIS PER SITE
    with tabs[3]:
        st.subheader("Scorecard dan Perbandingan Antar Kantor / Site")
        
        if not site_scorecard.empty:
            st.dataframe(site_scorecard, use_container_width=True)
            
            st.markdown("---")
            col_site_p1, col_site_p2 = st.columns(2)
            with col_site_p1:
                # Let user pick a site to show its top categories
                site_options = sorted(clean_df['Site Name'].dropna().unique().tolist())
                selected_site_spec = st.selectbox("Pilih Site untuk Distribusi Kategori:", site_options)
                fig_site_cat = charts.plot_site_category_distribution(clean_df, selected_site_spec)
                if fig_site_cat:
                    st.plotly_chart(fig_site_cat, use_container_width=True)
            with col_site_p2:
                # Sentiment negative comparison chart per site
                neg_sent_site = []
                for s in site_options:
                    s_df = clean_df[clean_df['Site Name'] == s]
                    tot = len(s_df)
                    neg = (s_df['sentiment'].str.lower() == 'negative').sum()
                    neg_sent_site.append({'Site': s, 'Persentase Negatif (%)': round(neg/tot*100, 1) if tot > 0 else 0})
                neg_site_df = pd.DataFrame(neg_sent_site).sort_values('Persentase Negatif (%)', ascending=True)
                fig_neg_site = px.bar(
                    neg_site_df,
                    x='Persentase Negatif (%)',
                    y='Site',
                    orientation='h',
                    title="Persentase Keluhan (Sentimen Negatif %) per Site",
                    color_discrete_sequence=['#e74c3c'],
                    text_auto=True
                )
                st.plotly_chart(fig_neg_site, use_container_width=True)
        else:
            st.warning("Data Site Name tidak tersedia.")
            
    # TAB 5: ANALISIS KATEGORI
    with tabs[4]:
        st.subheader("Analisis Detail Kategori & Sub-Kategori")

        top_neg_categories = metrics.get_top_negative_category_insights(clean_df, top_n=4)
        if top_neg_categories:
            st.markdown("#### 4 Kategori dengan Sentimen Negatif Terbanyak")
            cols = st.columns(len(top_neg_categories))
            for idx, insight in enumerate(top_neg_categories):
                with cols[idx]:
                    st.markdown(f"""
                        <div class="kpi-card" style="border-top: 5px solid #c0392b; padding: 18px;">
                            <div class="kpi-label" style="font-size: 12px; margin-bottom: 6px;">Kategori</div>
                            <div class="kpi-val" style="font-size: 24px; color: #c0392b;">{insight['Category']}</div>
                            <div style="font-size: 14px; margin-top: 10px;"><b>Negatif:</b> {insight['Negative Count']}</div>
                            <div style="font-size: 13px; margin-top: 10px;"><b>Kata Kunci:</b><br>{insight['Keywords']}</div>
                            <div style="font-size: 13px; margin-top: 10px;"><b>Contoh Pertanyaan:</b><br>{insight['Sample Question']}</div>
                        </div>
                    """, unsafe_allow_html=True)

            st.markdown("#### Sample Nomor Tiket Sentimen Negatif")
            negative_tickets = clean_df.loc[clean_df['sentiment'].astype(str).str.lower() == 'negative', 'Ticket Number'].dropna().astype(str).tolist()
            if negative_tickets:
                sample_tickets = negative_tickets[:20]
                st.write("Contoh nomor tiket yang terdeteksi sentimen negatif:")
                st.code("\n".join(sample_tickets), language=None)
            else:
                st.info("Tidak ada tiket dengan sentimen negatif.")
        else:
            st.info("Tidak ada kategori dengan sentimen negatif yang cukup untuk ditampilkan.")

        st.markdown('---')
        col_cat1, col_cat2 = st.columns(2)
        with col_cat1:
            fig_top_cat = charts.plot_volume_by_category(clean_df)
            if fig_top_cat:
                st.plotly_chart(fig_top_cat, use_container_width=True)
        with col_cat2:
            fig_neg_cat = charts.plot_negative_category_distribution(clean_df)
            if fig_neg_cat:
                st.plotly_chart(fig_neg_cat, use_container_width=True)
            else:
                st.info("Tidak ada data sentimen negatif yang cukup untuk ditampilkan.")

        st.markdown('---')
        fig_matrix = charts.plot_category_matrix(clean_df)
        if fig_matrix:
            st.plotly_chart(fig_matrix, use_container_width=True)

    # TAB 6: DATA MENTAH & EXPORT
    with tabs[5]:
        st.subheader("Ekspor & Unduh Laporan Monev")
        st.markdown(
            "Unduh data bersih, scorecard, **ringkasan agregat** (volume/FRT harian, sentimen, kategori), "
            "dan **PDF eksekutif** dengan grafik utama (tren volume, FRT, sentimen, top kategori)."
        )
        
        excel_data = exporter.export_to_excel(clean_df, kpis, site_scorecard, formula_table)
        pdf_data = exporter.export_to_pdf(kpis, site_scorecard, clean_df)
        
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                label="Unduh Laporan Excel (xlsx)",
                data=excel_data,
                file_name="Laporan_Monitoring_Contact_Center.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col_dl2:
            st.download_button(
                label="Unduh Laporan PDF (pdf)",
                data=pdf_data,
                file_name="Ringkasan_Monev_Contact_Center.pdf",
                mime="application/pdf"
            )
            
        st.markdown("---")
        st.subheader("Penelusuran Data Interaktif")
        
        # Display data columns
        view_cols = ['Ticket Number', 'Category', 'Sub Category', 'Priority', 'Channel', 'Ticket Status', 'Site Name', 'Created Date', 'FRT', 'sentiment']
        display_cols = [c for c in view_cols if c in clean_df.columns]
        
        # We use st.dataframe to provide high interactive features
        st.dataframe(clean_df[display_cols], use_container_width=True)
        
    # TAB 7: PREDIKSI SENTIMEN BARU
    with tabs[6]:
        st.subheader("Prediksi Sentimen Pertanyaan Pelanggan (Real-Time)")
        st.markdown("Masukkan teks pertanyaan atau keluhan pelanggan untuk menganalisis sentimen menggunakan model IndoRoBERTa.")
        
        user_input = st.text_area("Tulis atau Tempel Pertanyaan Pelanggan di Sini:", height=150, placeholder="Contoh: Mengapa barang kiriman saya dari luar negeri belum sampai juga? Statusnya tertahan di Bea Cukai.")
        
        if st.button("Prediksi Sentimen"):
            if not user_input.strip():
                st.warning("Silakan masukkan teks terlebih dahulu.")
            elif cleaner.clean_and_validate_question(user_input) is None:
                st.warning("Teks terlalu singkat atau berupa karakter acak (noise). Silakan masukkan pertanyaan atau keluhan pelanggan yang utuh.")
            elif classifier is None:
                st.error("Model NLP tidak dapat dimuat. Pastikan dependensi terinstal.")
            else:
                with st.spinner("Menganalisis teks..."):
                    pred = classifier(user_input[:512])[0]
                    label_raw = pred['label'].upper()
                    score = pred['score']
                    
                    label = cleaner.reclassify_sentiment(user_input, label_raw.lower()).upper()
                    was_reclassified = label != label_raw
                    
                    input_words = re.findall(r'\b\w+\b', user_input.lower())
                    found_neg = [w for w in input_words if w in settings.EXPLANATION_KEYWORDS['negatif']]
                    found_pos = [w for w in input_words if w in settings.EXPLANATION_KEYWORDS['positif']]
                    
                    if was_reclassified:
                        st.warning(f"Model awalnya memprediksi **{label_raw}**, tetapi direklasifikasi menjadi **{label}** berdasarkan analisis konteks kalimat.")
                    
                    if label == 'NEGATIVE':
                        st.error(f"**SENTIMEN NEGATIF** (Confidence: {score*100:.2f}%)")
                        st.markdown("**Rekomendasi Aksi**: Teruskan ke Customer Service Specialist untuk penanganan prioritas.")
                        if found_neg:
                            st.markdown(f"Kata kunci keluhan terdeteksi: **{', '.join(set(found_neg))}**.")
                    elif label == 'POSITIVE':
                        st.success(f"**SENTIMEN POSITIF** (Confidence: {score*100:.2f}%)")
                        st.markdown("**Rekomendasi Aksi**: Kirimkan jawaban informatif & ucapan terima kasih otomatis.")
                        if found_pos:
                            st.markdown(f"Kata kunci apresiasi terdeteksi: **{', '.join(set(found_pos))}**.")
                    else:
                        st.info(f"**SENTIMEN NETRAL** (Confidence: {score*100:.2f}%)")
                        st.markdown("**Rekomendasi Aksi**: Berikan jawaban template informatif standar.")

else:
    st.warning("Data belum tersedia. Silakan unggah file report CSV pada sidebar atau pastikan file output default tersimpan.")
