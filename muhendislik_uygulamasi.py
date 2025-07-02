import streamlit as st
import pandas as pd
import fluids
import chemicals
from fluids.fittings import K_fittings_dict, K_fittings_T_junction

# --- Sayfa Ayarları ve Başlık ---
st.set_page_config(layout="wide", page_title="Kimya Mühendisliği Hesaplayıcısı")

st.title("🧮 Fluids Kütüphanesi ile Mühendislik Hesaplayıcısı")
st.write("Bu interaktif web uygulaması, `CalebBell/fluids` ve `chemicals` kütüphanelerini kullanarak çeşitli akışkanlar dinamiği hesaplamaları yapar.")

# --- Navigasyon Menüsü ---
st.sidebar.title("Hesaplama Modülleri")
secim = st.sidebar.radio("Lütfen bir modül seçin:", 
                         ('Akışkan Özellikleri', 'Boru Basınç Düşüşü', 'Vana ve Ek Parça Kayıpları'))

# ==============================================================================
# --- MODÜL 1: AKIŞKAN ÖZELLİKLERİ ---
# ==============================================================================
if secim == 'Akışkan Özellikleri':
    st.header("💧 Akışkan Özellikleri Görüntüleyici")
    st.info("Seçilen bir akışkanın, belirtilen sıcaklıktaki temel fiziksel özelliklerini hesaplar.")

    col1, col2 = st.columns(2)

    with col1:
        # Kullanıcıdan akışkan ve sıcaklık bilgilerini al
        fluid_name = st.selectbox("Akışkan Seçin:", 
                                  ('water', 'air', 'ethanol', 'methanol', 'acetone', 'benzene', 'toluene'), 
                                  key='fluid_prop_fluid')
        temperature_c = st.slider("Sıcaklık (°C)", min_value=-50, max_value=200, value=25, key='fluid_prop_temp')
        T_kelvin = temperature_c + 273.15

    if st.button("Özellikleri Hesapla", key='fluid_prop_button'):
        try:
            # chemicals kütüphanesinden özellikleri çek (Doğru fonksiyon adı 'lookup')
            density = chemicals.lookup(fluid_name, 'rho', T=T_kelvin)
            viscosity = chemicals.lookup(fluid_name, 'mu', T=T_kelvin)
            heat_capacity = chemicals.lookup(fluid_name, 'Cp', T=T_kelvin)
            surface_tension = chemicals.lookup(fluid_name, 'sigma', T=T_kelvin)
            vapor_pressure = chemicals.lookup(fluid_name, 'Psat', T=T_kelvin)

            # Sonuçları bir DataFrame'de göster
            data = {
                "Özellik": ["Yoğunluk (ρ)", "Viskozite (μ)", "Özgül Isı (Cp)", "Yüzey Gerilimi (σ)", "Buhar Basıncı (P_sat)"],
                "Değer": [f"{density:.2f}", f"{viscosity:.6f}", f"{heat_capacity:.2f}", f"{surface_tension:.4f}", f"{vapor_pressure:.2f}"],
                "Birim": ["kg/m³", "Pa·s", "J/kg·K", "N/m", "Pa"]
            }
            df = pd.DataFrame(data)
            
            with col2:
                st.subheader(f"{fluid_name.capitalize()} @ {temperature_c}°C")
                st.table(df)

        except Exception as e:
            st.error(f"Hesaplama sırasında bir hata oluştu: {e}. Lütfen farklı bir sıcaklık deneyin.")


# ==============================================================================
# --- MODÜL 2: BORU BASINÇ DÜŞÜŞÜ ---
# ==============================================================================
elif secim == 'Boru Basınç Düşüşü':
    st.header("📉 Boru Hattı Basınç Düşüşü Hesaplayıcısı")
    st.info("Düz bir boru hattındaki sürtünme kaynaklı basınç kaybını Darcy-Weisbach denklemi ile hesaplar.")

    # Girdi ve Çıktı için kolonlar oluştur
    input_col, result_col = st.columns([1, 2])

    with input_col:
        st.subheader("Girdi Parametreleri")
        # Akışkan Bilgileri
        fluid_name_pd = st.selectbox("Akışkan:", ('water', 'air', 'ethanol'), key='pd_fluid')
        temp_c_pd = st.slider("Sıcaklık (°C)", 0, 100, 25, key='pd_temp')
        mass_flow_pd = st.number_input("Kütlesel Debi (kg/s)", min_value=0.01, value=1.0, step=0.1, key='pd_flow')
        
        # Boru Bilgileri
        st.markdown("---")
        pipe_length_pd = st.number_input("Boru Uzunluğu (m)", min_value=1.0, value=100.0, step=1.0, key='pd_length')
        nominal_diameter_pd = st.selectbox("Nominal Boru Çapı (inç)", (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0), index=3, key='pd_nps')
        
        # Statik olarak yaygın Schedule listesi
        schedules = ['5', '10', '20', '30', '40', '60', '80', '100', '120', '140', '160', 'STD', 'XS', 'XXS']
        schedule_pd = st.selectbox("Boru Çizelgesi (Schedule)", schedules, index=4, key='pd_schedule') # index=4 -> '40'
        
        pipe_material_pd = st.selectbox("Boru Malzemesi", ('steel', 'stainless steel', 'PVC', 'cast iron'), index=0, key='pd_material')

    if st.button("Basınç Düşüşünü Hesapla", key='pd_button'):
        try:
            # --- Hesaplama Bloğu ---
            T_kelvin = temp_c_pd + 273.15
            density = chemicals.lookup(fluid_name_pd, 'rho', T=T_kelvin)
            viscosity = chemicals.lookup(fluid_name_pd, 'mu', T=T_kelvin)
            
            # Boru özelliklerini al
            ID, _, _, roughness = fluids.nearest_pipe(NPS=nominal_diameter_pd, schedule=schedule_pd, material=pipe_material_pd)
            
            area = (3.14159 * ID**2) / 4.0
            velocity = mass_flow_pd / (density * area)
            Re = fluids.Reynolds(D=ID, rho=density, V=velocity, mu=viscosity)
            ff = fluids.friction_factor(Re=Re, eD=roughness/ID)
            pressure_drop_Pa = fluids.P_drop(D=ID, L=pipe_length_pd, rho=density, V=velocity, fd=ff)
            pressure_drop_bar = pressure_drop_Pa / 100000.0

            # --- Sonuçları Gösterme Bloğu ---
            with result_col:
                st.subheader("Hesaplama Sonuçları")
                
                st.success(f"### Toplam Basınç Düşüşü: {pressure_drop_bar:.4f} bar")
                
                st.markdown("---")
                
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric("Akışkan Hızı", f"{velocity:.3f} m/s")
                    st.metric("Boru İç Çapı (ID)", f"{ID*1000:.2f} mm")
                    st.metric("Sürtünme Faktörü (f)", f"{ff:.5f}")
                
                with res_col2:
                    st.metric("Reynolds Sayısı", f"{Re:,.0f}")
                    st.metric("Boru Pürüzlülüğü (ε)", f"{roughness*1000:.5f} mm")
                    st.metric("Basınç Düşüşü (Pa)", f"{pressure_drop_Pa:,.2f} Pa")
                
                # Akış Rejimi Bilgisi
                flow_regime = "Laminer" if Re < 2100 else "Geçiş Bölgesi" if Re < 4000 else "Türbülanslı"
                st.info(f"**Akış Rejimi:** {flow_regime} (Re = {Re:,.0f})")

        except Exception as e:
            with result_col:
                st.error(f"Hesaplama hatası: {e}")

# ==============================================================================
# --- MODÜL 3: VANA VE EK PARÇA KAYIPLARI ---
# ==============================================================================
elif secim == 'Vana ve Ek Parça Kayıpları':
    st.header("🔧 Vana ve Ek Parça Kayıp Katsayısı (K)")
    st.info("Standart vana ve boru bağlantı parçaları için kayıp katsayısını (K) hesaplar. Bu katsayı, yerel basınç kayıplarını bulmak için kullanılır.")

    # Mevcut ek parçaların listesini al
    available_fittings = list(K_fittings_dict.keys())

    fitting_type = st.selectbox("Ek Parça Tipini Seçin:", available_fittings, index=available_fittings.index('gate valve, full open'))
    
    # Gerekli girdileri göster
    if fitting_type in ['T, through-flow', 'T, branch-flow']:
        q_branch = st.slider("Dallanan Akış Oranı (q_dal / q_toplam)", 0.0, 1.0, 0.5, 0.05)
        q_main = 1.0 - q_branch
        K = K_fittings_T_junction(Di=1, Qo_main=q_main, Qo_branch=q_branch, flow_main=1, flow_branch=1 if fitting_type == 'T, branch-flow' else 0)
    else:
        # Diğer ek parçalar için doğrudan K değerini al
        K = K_fittings_dict[fitting_type]

    st.success(f"### Seçilen Ek Parça İçin Kayıp Katsayısı (K) = {K:.3f}")
    
    st.markdown("---")
    st.subheader("Bu Değer Ne İşe Yarar?")
    st.latex(r''' \Delta P_{yerel} = K \cdot \frac{\rho V^2}{2} ''')
    st.markdown(r"""
    - $\Delta P_{yerel}$: Vana veya ek parçadaki basınç düşüşü (Pa)
    - $K$: Yukarıda hesaplanan boyutsuz kayıp katsayısı
    - $\rho$: Akışkan yoğunluğu (kg/m³)
    - $V$: Borudaki akışkan hızı (m/s)
    
    Toplam basınç kaybını bulmak için bu yerel kayıpları, düz borudaki sürtünme kaybına eklemeniz gerekir.
    """)
