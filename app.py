import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
import os

# Konfigurasi Halaman Utama
st.set_page_config(page_title="Product QA & Revenue Protection 2026", layout="wide", page_icon="📊")
st.title("📊 Enterprise Quality Intelligence & Revenue Protection")
st.markdown("Dasbor ini menyelaraskan data kualitas produk (QA) dengan dampak finansial secara real-time.")

@st.cache_data
def load_and_sync_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    files = os.listdir(base_dir)
    
    # Identifikasi file sumber utama
    qa_file = next((f for f in files if "Dashboard_QA" in f and f.endswith('.xlsx')), None)
    kip_file = next((f for f in files if "KIP April" in f and f.endswith('.xlsx')), None)
    
    if not qa_file:
        st.error("File 'Dashboard_QA_Product_Q1_2026.xlsx' tidak ditemukan di folder kerja.")
        st.stop()
        
    # --- 1. PROSES SHEET DISA (REVENUE & SUBS) ---
    # Membaca mentah untuk menentukan batas data harian vs tabel summary di bawah
    df_disa_raw = pd.read_excel(os.path.join(base_dir, qa_file), sheet_name="Disa", header=None)
    
    # Cari baris di mana tabel harian berakhir (biasanya ditandai kata 'Month' atau 'TOTAL')
    stop_idx = df_disa_raw[df_disa_raw[0].astype(str).str.contains("Month|TOTAL|Product", na=False)].index.min()
    if pd.isna(stop_idx): stop_idx = len(df_disa_raw)
        
    # Ambil data harian (mulai dari baris index 2)
    df_disa = df_disa_raw.iloc[2:stop_idx].copy()
    df_disa.columns = [
        'Date', 'ChatGPT_Subs', 'ChatGPT_Rev', 'ProtekSi_Subs', 'ProtekSi_Rev', 
        'TikTok_Subs', 'TikTok_Rev', 'Travel_Subs', 'Travel_Rev', 
        'VNSP_Subs', 'VNSP_Rev', 'FTTR_Subs', 'FTTR_Rev', 
        'Smart_Subs', 'Smart_Rev', 'Prioritas_Subs', 'Prioritas_Rev', 'Total_Subs', 'Total_Rev'
    ]
    df_disa['Date'] = pd.to_datetime(df_disa['Date'], errors='coerce')
    df_disa = df_disa.dropna(subset=['Date'])
    
    # Bersihkan data numerik
    for col in df_disa.columns[1:]:
        df_disa[col] = pd.to_numeric(df_disa[col], errors='coerce').fillna(0)

    # --- 2. PROSES REGIONAL & TOP K ---
    df_regional = pd.read_excel(os.path.join(base_dir, qa_file), sheet_name="Regional Analysis")
    df_top_k = pd.read_excel(os.path.join(base_dir, qa_file), sheet_name="Top K")
    
    # --- 3. PROSES KIP APRIL (DETAIL KELUHAN) ---
    df_kip = pd.DataFrame()
    if kip_file:
        df_kip = pd.read_excel(os.path.join(base_dir, kip_file), sheet_name="Apr")
        df_kip['Date'] = pd.to_datetime(df_kip['Date'], errors='coerce')

    return df_disa, df_regional, df_top_k, df_kip

# Inisialisasi Data
df_disa, df_regional, df_top_k, df_kip = load_and_sync_data()

# Penyelarasan Nama Produk Lintas Sheet
product_map = {
    "ChatGPT Go": {"rev": "ChatGPT_Rev", "reg": "CHATGPT Go", "key": "ChatGPT"},
    "FTTR": {"rev": "FTTR_Rev", "reg": "FTTR", "key": "FTTR"},
    "ProtekSi Kecil": {"rev": "ProtekSi_Rev", "reg": "Proteksi Kecil", "key": "Proteksi"},
    "Travel Assistant": {"rev": "Travel_Rev", "reg": "Travel Assistant", "key": "Travel"},
    "Jaringan Prioritas": {"rev": "Prioritas_Rev", "reg": "Jaringan Prioritas", "key": "Prioritas"},
    "SIMPATI TikTok": {"rev": "TikTok_Rev", "reg": "SIMPATI TikTok", "search": "TikTok"},
    "IndiHome Smart": {"rev": "Smart_Rev", "reg": "Indihome Smart", "key": "Smart"},
    "V-NSP": {"rev": "VNSP_Rev", "reg": "VNSP", "key": "VNSP"}
}

st.sidebar.header("🕹️ Control Center")
selected_p = st.sidebar.selectbox("Pilih Produk untuk Dianalisis", list(product_map.keys()))
p_info = product_map[selected_p]

# --- KPI SECTION ---
st.subheader(f"Ringkasan Performa: {selected_p}")
total_complaints = df_regional[p_info['reg']].sum()
total_revenue = df_disa[p_info['rev']].sum()
avg_subs = df_disa[p_info['rev'].replace('Rev', 'Subs')].mean()

kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("Total Tiket (Regional)", f"{total_complaints:,.0f}")
kpi2.metric("Total Revenue (Q1)", f"Rp {total_revenue:,.0f}")
kpi3.metric("Rerata Subs Harian", f"{avg_subs:,.1f}")

st.divider()

# --- ANALISIS VISUAL ---
tab_reg, tab_rev, tab_voc = st.tabs(["📍 Sebaran Regional & Isu", "📈 Recovery Tracking", "🔍 VoC Raw Logs"])

with tab_reg:
    c_left, c_right = st.columns(2)
    with c_left:
        st.write("**Top 10 Wilayah Terdampak**")
        reg_plot = df_regional[['regional', p_info['reg']]].sort_values(by=p_info['reg'], ascending=False).head(10)
        fig_bar = px.bar(reg_plot, x=p_info['reg'], y='regional', orientation='h', color=p_info['reg'], color_continuous_scale='OrRd')
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with c_right:
        st.write("**Akar Masalah Terdeteksi (Top K)**")
        search_key = p_info.get('key', selected_p)
        isu_plot = df_top_k[df_top_k['product'].str.contains(search_key, case=False, na=False)]
        if not isu_plot.empty:
            fig_pie = px.pie(isu_plot.head(5), values='Volume', names='type_3', hole=0.5)
            st.plotly_chart(fig_pie, use_container_width=True)

with tab_rev:
    st.write("**Dampak Perbaikan terhadap Pendapatan**")
    fix_date = st.date_input("Pilih Tanggal Implementasi Fix", value=pd.to_datetime("2026-04-15"))
    fix_date_ts = pd.Timestamp(fix_date)
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(x=df_disa['Date'], y=df_disa[p_info['rev']], name="Revenue", line=dict(color='#1f77b4', width=3)))
    
    # PERBAIKAN FINAL: Konversi tanggal menjadi Milidetik (Unix Timestamp) 
    # agar Plotly bisa menghitung posisi teks tanpa memicu error matematika.
    fix_date_ms = fix_date_ts.timestamp() * 1000
    
    fig_trend.add_vline(
        x=fix_date_ms, 
        line_dash="dash", 
        line_color="red", 
        annotation_text="Fix Implemented",
        annotation_position="top right"
    )
    
    fig_trend.update_layout(xaxis_title="Tanggal", yaxis_title="Revenue (Rp)", hovermode="x unified")
    st.plotly_chart(fig_trend, use_container_width=True)
with tab_voc:
    st.write("**Detail Keluhan Pelanggan (VoC)**")
    if not df_kip.empty:
        search_key = p_info.get('key', selected_p)
        kip_filt = df_kip[df_kip['product_name'].str.contains(search_key, case=False, na=False)]
        st.dataframe(kip_filt[['Date', 'type_3', 'notes']].sort_values(by='Date', ascending=False), use_container_width=True)
    else:
        st.warning("Data KIP April tidak ditemukan untuk analisis VoC.")