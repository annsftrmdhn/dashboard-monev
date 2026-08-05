import io
import pandas as pd
from fpdf import FPDF

from modules import report_visuals

def export_to_excel(df, metrics_dict, site_scorecard, formula_table=None):
    """
    Exports clean dataset, site scorecards, and overall KPI metrics to an Excel workbook in-memory.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        kpi_data = {
            'Metrik Utama': [
                'Total Volume Tiket',
                'Average Speed of Answer (ASA) - Menit',
                'First Response Time (FRT) - Menit',
                'Service Level (SL) - %',
                'Resolution Rate - %',
                'Average Handle Time (AHT) - Menit',
                'Rata-rata Kontak per Agen',
            ],
            'Nilai': [
                metrics_dict['total_tickets'],
                round(metrics_dict['asa_minutes'], 2),
                round(metrics_dict.get('frt_minutes', metrics_dict['asa_minutes']), 2),
                round(metrics_dict['service_level'], 2),
                round(metrics_dict['resolution_rate_pct'], 2),
                round(metrics_dict['aht_minutes'], 2),
                round(metrics_dict['avg_contacts_per_agent'], 1),
            ],
        }
        pd.DataFrame(kpi_data).to_excel(writer, sheet_name='Summary KPI', index=False)

        if formula_table is not None and not formula_table.empty:
            formula_table.to_excel(writer, sheet_name='Rumus Metrik', index=False)
        
        # Write Site Scorecard sheet
        if not site_scorecard.empty:
            site_scorecard.to_excel(writer, sheet_name='Site Scorecard', index=False)
            
        for sheet_name, table_df in report_visuals.build_excel_summary_tables(df).items():
            safe_name = sheet_name[:31]
            table_df.to_excel(writer, sheet_name=safe_name, index=False)

        # Write Cleaned Data sheet (omit internal columns)
        exclude_cols = ['pertanyaan_clean', 'created_dt_wib', 'day_of_week', 'handle_seconds', 'staffing_handle_seconds']
        export_cols = [c for c in df.columns if c not in exclude_cols]
        export_df = df[export_cols].copy()

        # Excel does not support timezone-aware datetimes; convert them to naive timestamps in WIB.
        for col in export_df.columns:
            if pd.api.types.is_datetime64tz_dtype(export_df[col]):
                export_df[col] = export_df[col].dt.tz_convert('Asia/Jakarta').dt.tz_localize(None)
            elif pd.api.types.is_datetime64_dtype(export_df[col]):
                export_df[col] = export_df[col].dt.tz_localize(None) if getattr(export_df[col].dt, 'tz', None) is not None else export_df[col]

        export_df.to_excel(writer, sheet_name='Raw Data & Sentimen', index=False)
        
    output.seek(0)
    return output.getvalue()

class ExecutivePDF(FPDF):
    def header(self):
        self.set_fill_color(44, 62, 80) # Dark executive blue
        self.rect(0, 0, 210, 25, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 8, 'LAPORAN EKSEKUTIF MONITORING CONTACT CENTER', border=0, ln=True, align='C')
        self.set_font('Helvetica', 'I', 9)
        self.cell(0, 4, 'Bravo Bea Cukai - Subdirektorat Strategi Komunikasi, Monitoring dan Evaluasi DJBC', border=0, ln=True, align='C')
        self.ln(10)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(127, 127, 127)
        self.cell(0, 10, f'Halaman {self.page_no()}/{{nb}} | Rahasia Intern DJBC', align='C')

def _pdf_add_chart_page(pdf, png_bytes, section_title):
    if not png_bytes:
        return
    pdf.add_page()
    pdf.set_text_color(44, 62, 80)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, section_title, ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.image(io.BytesIO(png_bytes), x=10, w=190)


def export_to_pdf(metrics_dict, site_scorecard, df=None):
    """
    Generates a beautifully structured PDF Executive summary.
    Optional df embeds key visualization charts as PNG pages.
    """
    pdf = ExecutivePDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # 1. Executive Summary Title
    pdf.set_text_color(44, 62, 80)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, '1. Ringkasan Eksekutif Utama (KPI)', ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # KPI Grid
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(60, 60, 60)
    
    kpi_lines = [
        f"- Total Volume Tiket Terproses        : {metrics_dict['total_tickets']:,} tiket",
        f"- Average Speed of Answer (ASA)      : {metrics_dict['asa_minutes']:.2f} menit",
        f"- First Response Time (FRT)          : {metrics_dict.get('frt_minutes', metrics_dict['asa_minutes']):.2f} menit",
        f"- Service Level (SLA <= 5 Menit)       : {metrics_dict['service_level']:.2f}%",
        f"- Resolution Rate                     : {metrics_dict['resolution_rate_pct']:.2f}%",
        f"- Average Handle Time (AHT)          : {metrics_dict['aht_minutes']:.2f} menit",
        f"- Rata-rata Beban Kontak per Agen     : {metrics_dict['avg_contacts_per_agent']:.1f} tiket/agen",
    ]
    
    for line in kpi_lines:
        pdf.cell(0, 7, line, ln=True)
        
    pdf.ln(10)
    
    # 2. Performance per Site / Kantor Wilayah
    if not site_scorecard.empty:
        pdf.set_text_color(44, 62, 80)
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 10, '2. Kinerja Layanan Antar Kantor Wilayah / Site', ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # Table Header
        pdf.set_fill_color(230, 240, 250)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(38, 8, "Nama Site", border=1, fill=True, align='C')
        pdf.cell(22, 8, "Vol. Tiket", border=1, fill=True, align='C')
        pdf.cell(22, 8, "ASA (menit)", border=1, fill=True, align='C')
        pdf.cell(22, 8, "FRT (menit)", border=1, fill=True, align='C')
        pdf.cell(26, 8, "Service Level (%)", border=1, fill=True, align='C')
        pdf.cell(26, 8, "Res. Rate (%)", border=1, fill=True, align='C')
        pdf.cell(24, 8, "AHT (menit)", border=1, fill=True, align='C')
        pdf.cell(20, 8, "Neg %", border=1, fill=True, align='C')
        pdf.ln()
        
        # Table Body
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(80, 80, 80)
        for _, row in site_scorecard.iterrows():
            pdf.cell(38, 8, str(row['Site']), border=1, align='L')
            pdf.cell(22, 8, f"{row['Total Tickets']:,}", border=1, align='C')
            pdf.cell(22, 8, f"{row['ASA (min)']:.2f}", border=1, align='C')
            pdf.cell(22, 8, f"{row['FRT (min)']:.2f}", border=1, align='C')
            pdf.cell(26, 8, f"{row['Service Level (%)']:.1f}%", border=1, align='C')
            pdf.cell(26, 8, f"{row['Resolution Rate (%)']:.1f}%", border=1, align='C')
            pdf.cell(24, 8, f"{row['AHT (min)']:.2f}", border=1, align='C')
            pdf.cell(20, 8, f"{row['Neg Sentimen (%)']:.1f}%", border=1, align='C')
            pdf.ln()
            
    pdf.ln(10)
    
    # 3. Catatan & Rekomendasi Monev
    pdf.set_text_color(44, 62, 80)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, '3. Rekomendasi Operasional & Tindak Lanjut', ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 100, 100)
    
    recoms = [
        "1. Optimalkan pembagian shift agen berdasarkan Heatmap jam sibuk (terutama jam 09:00 - 11:00 WIB).",
        "2. Buat FAQ template responsif untuk Kategori/Sub-Kategori dengan frekuensi keluhan & FRT tertinggi.",
        "3. Lakukan audit performa SLA pada site dengan capaian Service Level di bawah target nasional."
    ]
    for rec in recoms:
        pdf.multi_cell(0, 6, rec)
        pdf.ln(1)

    if df is not None and len(df) > 0:
        chart_specs = [
            (report_visuals.daily_volume_png(df), '4. Visualisasi: Tren Volume Harian'),
            (report_visuals.daily_frt_png(df), '5. Visualisasi: Rata-rata FRT Harian'),
            (report_visuals.sentiment_png(df), '6. Visualisasi: Distribusi Sentimen'),
            (report_visuals.top_categories_png(df), '7. Visualisasi: Top Kategori Layanan'),
        ]
        for png_bytes, title in chart_specs:
            _pdf_add_chart_page(pdf, png_bytes, title)
        
    pdf_output = pdf.output()
    # In fpdf2, output() without file path returns a bytes object
    return bytes(pdf_output)
