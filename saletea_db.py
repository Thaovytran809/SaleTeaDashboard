import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests # Thêm thư viện này để gửi dữ liệu HTTP
import json

# Cấu hình trang Dashboard
st.set_page_config(page_title="Tea Shop Analytics Dashboard", layout="wide")

# Bảng màu chủ đạo: Xanh lá trà (Tea Green & Forest Green)
TEA_COLORS = ["#2C5E3B", "#4E8752", "#73A96C", "#9CBF96", "#C7DCA7", "#DFEBD0"]
MAIN_TEA_COLOR = "#2C5E3B"

st.title("🍵 TEA SHOP ANALYTICS DASHBOARD")
st.markdown("---")

# --- 1. ĐỌC DỮ LIỆU TỪ GOOGLE SHEETS ---
sheet_url = "https://docs.google.com/spreadsheets/d/1zvFIMcc3SndkKUpIjkRk1Rh8VKFriwqyGKYPCnH9XzM/edit?gid=1267144830#gid=1267144830"  # Thay URL của bạn vào đây

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Đọc dữ liệu từ Sheet chính chứa data gốc
    df = conn.read(spreadsheet=sheet_url, ttl=0)
    df = df.dropna(how="all")
    
    # Chuẩn hóa cột thời gian sang định dạng datetime để xử lý cho các Chart ngày/tháng/giờ
    df['Thời gian tạo đơn'] = pd.to_datetime(df['Thời gian tạo đơn'])
    
    st.success("Tải dữ liệu từ Google Sheets thành công!")
except Exception as e:
    st.error(f"Lỗi kết nối dữ liệu: {e}")
    st.stop()

# --- Khởi tạo session state lưu trữ tạm thời các Insight người dùng nhập ---
if "insights" not in st.session_state:
    st.session_state.insights = {f"chart_{i}": "" for i in range(1, 13)}

# --- TẠO CÁC TABS PHÂN TÍCH ---
tab_sales, tab_time, tab_prob, tab_customer, tab_history = st.tabs([
    "📦 Doanh thu & Hàng hóa", 
    "⏰ Phân tích Thời gian", 
    "🎯 Xác suất & Nhóm hàng", 
    "👥 Khách hàng",
    "💾 Lưu Lịch sử Insight"
])

# ==========================================
# TAB 1: DOANH THU & HÀNG HÓA (Chart 1 & 2)
# ==========================================
with tab_sales:
    st.header("Phân tích Doanh thu theo Mặt hàng & Nhóm hàng")
    
    # --- CHART 1 ---
    st.subheader("1: Doanh thu và Số lượng theo Mặt Hàng")
    c1_df = df.groupby(['Mã mặt hàng', 'Tên mặt hàng', 'Mã nhóm hàng', 'Tên nhóm hàng']).agg(
        doanh_thu=('Thành tiền', 'sum'),
        sl=('SL', 'sum')
    ).reset_index().sort_values(by='doanh_thu', ascending=False)
    
    fig1 = px.bar(c1_df.head(20), x='Tên mặt hàng', y='doanh_thu', text='sl',
                  title="Top 20 Mặt hàng có Doanh thu cao nhất (Số hiển thị là Số lượng bán)",
                  color_discrete_sequence=[MAIN_TEA_COLOR])
    st.plotly_chart(fig1, width='stretch')
    st.session_state.insights["chart_1"] = st.text_area("Insight Chart 1:", value=st.session_state.insights["chart_1"], key="in_1")

    st.markdown("---")
    
    # --- CHART 2 ---
    st.subheader("2: Doanh thu theo Nhóm Hàng")
    df['ma_ten_NH'] = "[" + df['Mã nhóm hàng'].astype(str) + "] " + df['Tên nhóm hàng'].astype(str)
    c2_df = df.groupby('ma_ten_NH').agg(doanh_thu=('Thành tiền', 'sum')).reset_index()
    
    fig2 = px.pie(c2_df, names='ma_ten_NH', values='doanh_thu', 
                  title="Tỷ lệ Doanh thu giữa các Nhóm Hàng",
                  color_discrete_sequence=TEA_COLORS)
    st.plotly_chart(fig2, width='stretch')
    st.session_state.insights["chart_2"] = st.text_area("Insight Chart 2:", value=st.session_state.insights["chart_2"], key="in_2")


# ==========================================
# TAB 2: PHÂN TÍCH THỜI GIAN (Chart 3, 4, 5, 6)
# ==========================================
with tab_time:
    st.header("Biến động doanh thu theo chu kỳ thời gian")
    
    # --- CHART 3 ---
    st.subheader("3: Doanh thu theo Tháng")
    df['thang_num'] = df['Thời gian tạo đơn'].dt.month
    df['month'] = "Tháng " + df['thang_num'].astype(str)
    c3_df = df.groupby(['thang_num', 'month']).agg(doanh_thu=('Thành tiền', 'sum')).reset_index().sort_values('thang_num')
    
    fig3 = px.line(c3_df, x='month', y='doanh_thu', markers=True, title="Xu hướng doanh thu theo tháng", color_discrete_sequence=[MAIN_TEA_COLOR])
    st.plotly_chart(fig3, width='stretch')
    st.session_state.insights["chart_3"] = st.text_area("Insight Chart 3:", value=st.session_state.insights["chart_3"], key="in_3")
    
    st.markdown("---")
    
    # --- CHART 4 ---
    st.subheader("4: Doanh thu trung bình theo Thứ trong tuần")
    # map theo weekday của pandas (Thứ 2=0... Chủ nhật=6) thành STT mong muốn (Thứ 2=2... Chủ nhật=8)
    day_map = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ nhật"}
    stt_map = {0: 2, 1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8}
    
    df['ngay_trong_tuan'] = df['Thời gian tạo đơn'].dt.weekday.map(day_map)
    df['stt_tuan'] = df['Thời gian tạo đơn'].dt.weekday.map(stt_map)
    df['date_only'] = df['Thời gian tạo đơn'].dt.date
    
    # Nhóm tính tổng tiền và đếm số ngày duy nhất
    c4_base = df.groupby(['stt_tuan', 'ngay_trong_tuan']).agg(
        tong_tien=('Thành tiền', 'sum'),
        so_ngay=('date_only', 'nunique')
    ).reset_index()
    c4_base['dttb'] = c4_base['tong_tien'] / c4_base['so_ngay']
    c4_base = c4_base.sort_values('stt_tuan')
    
    fig4 = px.bar(c4_base, x='ngay_trong_tuan', y='dttb', title="Doanh thu trung bình theo ngày trong tuần", color_discrete_sequence=[TEA_COLORS[1]])
    st.plotly_chart(fig4, width='stretch')
    st.session_state.insights["chart_4"] = st.text_area("Insight Chart 4:", value=st.session_state.insights["chart_4"], key="in_4")
    
    st.markdown("---")

    # --- CHART 5 ---
    st.subheader("5: Doanh thu trung bình theo Ngày trong Tháng")
    df['ngay_num'] = df['Thời gian tạo đơn'].dt.day
    df['ngay'] = "Ngày " + df['ngay_num'].astype(str)
    
    c5_base = df.groupby(['ngay_num', 'ngay']).agg(
        tong_tien=('Thành tiền', 'sum'),
        so_ngay=('date_only', 'nunique')
    ).reset_index()
    c5_base['dttb'] = c5_base['tong_tien'] / c5_base['so_ngay']
    c5_base = c5_base.sort_values('ngay_num')
    
    fig5 = px.bar(c5_base, x='ngay', y='dttb', title="Doanh thu trung bình theo ngày trong tháng", color_discrete_sequence=[TEA_COLORS[2]])
    st.plotly_chart(fig5, width='stretch')
    st.session_state.insights["chart_5"] = st.text_area("Insight Chart 5:", value=st.session_state.insights["chart_5"], key="in_5")
    
    st.markdown("---")

    # --- CHART 6 ---
    st.subheader("6: Doanh thu trung bình theo Khung Giờ trong ngày")
    df['gio_num'] = df['Thời gian tạo đơn'].dt.hour
    df['gio'] = df['gio_num'].astype(str) + ":00 - " + (df['gio_num'] + 1).astype(str) + ":59"
    
    c6_base = df.groupby(['gio_num', 'gio']).agg(
        tong_tien=('Thành tiền', 'sum'),
        so_ngay=('date_only', 'nunique')
    ).reset_index().sort_values('gio_num')
    c6_base['dttb'] = c6_base['tong_tien'] / c6_base['so_ngay']
    
    fig6 = px.bar(c6_base, x='gio', y='dttb', title="Khung giờ mua sắm trà đóng gói phổ biến (DTTB)", color_discrete_sequence=[TEA_COLORS[3]])
    st.plotly_chart(fig6, width='stretch')
    st.session_state.insights["chart_6"] = st.text_area("Insight Chart 6:", value=st.session_state.insights["chart_6"], key="in_6")


# ==========================================
# TAB 3: XÁC SUẤT & NHÓM HÀNG (Chart 7, 8, 9, 10)
# ==========================================
with tab_prob:
    st.header("Phân tích tỷ lệ xuất hiện (Xác suất % đơn hàng)")
    
    total_distinct_orders = df['Mã đơn hàng'].nunique()
    
    # --- CHART 7 ---
    st.subheader("7: Xác suất xuất hiện Nhóm hàng trên tổng số đơn hàng")
    c7_df = df.groupby('ma_ten_NH').agg(so_don=('Mã đơn hàng', 'nunique')).reset_index()
    c7_df['xac_suat'] = (c7_df['so_don'] * 100) / total_distinct_orders
    
    fig7 = px.bar(c7_df, x='xac_suat', y='ma_ten_NH', orientation='h', title="Xác suất (%) một đơn hàng bất kỳ có chứa nhóm hàng này", color_discrete_sequence=[MAIN_TEA_COLOR])
    st.plotly_chart(fig7, width='stretch')
    st.session_state.insights["chart_7"] = st.text_area("Insight Chart 7:", value=st.session_state.insights["chart_7"], key="in_7")
    
    st.markdown("---")

    # --- CHART 8 ---
    st.subheader("8: Xác suất xuất hiện Nhóm hàng theo từng Tháng")
    t1_c8 = df.groupby('thang_num').agg(tong_don=('Mã đơn hàng', 'nunique')).reset_index()
    t2_c8 = df.groupby(['thang_num', 'ma_ten_NH']).agg(so_don=('Mã đơn hàng', 'nunique')).reset_index()
    c8_res = pd.merge(t2_c8, t1_c8, on='thang_num')
    c8_res['xac_suat'] = (c8_res['so_don'] * 100) / c8_res['tong_don']
    
    fig8 = px.bar(c8_res, x='thang_num', y='xac_suat', color='ma_ten_NH', barmode='group', title="Xác suất nhóm hàng xuất hiện trong đơn hàng phân rã theo từng tháng", color_discrete_sequence=TEA_COLORS)
    st.plotly_chart(fig8, width='stretch')
    st.session_state.insights["chart_8"] = st.text_area("Insight Chart 8:", value=st.session_state.insights["chart_8"], key="in_8")
    
    st.markdown("---")

    # --- CHART 9 ---
    st.subheader("9: Xác suất Mặt hàng xuất hiện trong Nhóm hàng của nó")
    df['ma_ten_MH'] = "[" + df['Mã mặt hàng'].astype(str) + "] " + df['Tên mặt hàng'].astype(str)
    t1_c9 = df.groupby('ma_ten_NH').agg(tong_don=('Mã đơn hàng', 'nunique')).reset_index()
    t2_c9 = df.groupby(['ma_ten_NH', 'ma_ten_MH']).agg(so_don=('Mã đơn hàng', 'nunique')).reset_index()
    c9_res = pd.merge(t2_c9, t1_c9, on='ma_ten_NH')
    c9_res['xac_suat'] = (c9_res['so_don'] * 100) / c9_res['tong_don']
    
    # Cho phép người dùng lọc theo Nhóm hàng để biểu đồ đỡ bị rối vì quá nhiều mặt hàng
    nhom_selected = st.selectbox("Chọn nhóm hàng để xem chi tiết Chart 9:", options=c9_res['ma_ten_NH'].unique())
    c9_filtered = c9_res[c9_res['ma_ten_NH'] == nhom_selected].sort_values('xac_suat', ascending=False)
    
    fig9 = px.bar(c9_filtered, x='ma_ten_MH', y='xac_suat', title=f"Tỷ lệ đóng góp đơn của mặt hàng trong nhóm: {nhom_selected}", color_discrete_sequence=[TEA_COLORS[1]])
    st.plotly_chart(fig9, width='stretch')
    st.session_state.insights["chart_9"] = st.text_area("Insight Chart 9:", value=st.session_state.insights["chart_9"], key="in_9")
    
    st.markdown("---")

    # --- CHART 10 ---
    st.subheader("10: Xác suất Mặt hàng trong Nhóm theo từng Tháng")
    # Tạo định dạng như SQL concat
    df['ma_ten_NH_alt'] = "[" + df['Mã nhóm hàng'].astype(str) + "]" + df['Tên nhóm hàng'].astype(str)
    df['ma_ten_MH_alt'] = "[" + df['Mã mặt hàng'].astype(str) + "]" + df['Tên mặt hàng'].astype(str)
    
    t1_c10 = df.groupby(['ma_ten_NH_alt', 'thang_num']).agg(tong_don=('Mã đơn hàng', 'nunique')).reset_index()
    t2_c10 = df.groupby(['ma_ten_NH_alt', 'ma_ten_MH_alt', 'thang_num']).agg(so_don=('Mã đơn hàng', 'nunique')).reset_index()
    c10_res = pd.merge(t2_c10, t1_c10, on=['ma_ten_NH_alt', 'thang_num'])
    c10_res['xac_suat'] = (c10_res['so_don'] * 100) / c10_res['tong_don']
    
    nhom_selected_10 = st.selectbox("Chọn nhóm hàng xem chi tiết Chart 10:", options=c10_res['ma_ten_NH_alt'].unique(), key="sb_10")
    c10_filtered = c10_res[c10_res['ma_ten_NH_alt'] == nhom_selected_10]
    
    fig10 = px.line(c10_filtered, x='thang_num', y='xac_suat', color='ma_ten_MH_alt', markers=True, title="Xu hướng thay đổi xác suất mặt hàng qua các tháng", color_discrete_sequence=TEA_COLORS)
    st.plotly_chart(fig10, width='stretch')
    st.session_state.insights["chart_10"] = st.text_area("Insight Chart 10:", value=st.session_state.insights["chart_10"], key="in_10")


# ==========================================
# TAB 4: PHÂN TÍCH KHÁCH HÀNG (Chart 11 & 12)
# ==========================================
with tab_customer:
    st.header("Phân tích hành vi Khách hàng")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # --- CHART 11 ---
        st.subheader("11: Số lượng đơn theo Khách hàng")
        c11_df = df.groupby('Mã khách hàng').agg(sl=('Mã đơn hàng', 'nunique')).reset_index()
        fig11 = px.histogram(c11_df, x='sl', title="Phân phối số lượng đơn hàng của Khách hàng", color_discrete_sequence=[TEA_COLORS[0]])
        st.plotly_chart(fig11, width='stretch')
        st.session_state.insights["chart_11"] = st.text_area("Insight Chart 11:", value=st.session_state.insights["chart_11"], key="in_11")
        
    with col2:
        # --- CHART 12 ---
        st.subheader("12: Tổng chi tiêu theo Khách hàng (Tăng dần)")
        c12_df = df.groupby('Mã khách hàng').agg(tong_tien=('Thành tiền', 'sum')).reset_index().sort_values('tong_tien', ascending=True)
        fig12 = px.box(c12_df, y='tong_tien', title="Phân bổ tổng chi tiêu khách hàng (Sắp xếp tăng dần)", color_discrete_sequence=[TEA_COLORS[2]])
        st.plotly_chart(fig12, width='stretch')
        st.session_state.insights["chart_12"] = st.text_area("Insight Chart 12:", value=st.session_state.insights["chart_12"], key="in_12")


# ==========================================
# TAB 5: LƯU LỊCH SỬ INSIGHT VÀO GG SHEETS (Qua Apps Script)
# ==========================================
with tab_history:
    st.header("Lưu lịch sử báo cáo & Insight")
    st.markdown("Hệ thống sẽ ghi nhận toàn bộ các đoạn insight bạn vừa viết ở các biểu đồ trên và lưu lại thành một dòng lịch sử mới vào tab `History_Insights` của Google Sheet thông qua Apps Script.")
    
    if st.button("🚀 Ghi nhận & Lưu Lịch sử lên Google Sheet"):
        # Tạo bản ghi dữ liệu lịch sử
        history_record = {
            "Thời_gian_lưu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        # Thêm 12 insight vào dict
        for i in range(1, 13):
            history_record[f"Insight_Chart_{i}"] = st.session_state.insights[f"chart_{i}"]
            
        # URL của Web App bạn vừa copy ở Apps Script
        APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwAwINikBVuaih6z2sp8P69rVwg4f0DaHWr1DZjSwC_K25xQdbn2oCbVxrOqKpCIUwA/exec"
        
        try:
            # Gửi dữ liệu bằng HTTP POST
            response = requests.post(APPS_SCRIPT_URL, json=history_record, allow_redirects=True, timeout=15)
            
            # Kiểm tra kết quả trả về từ Apps Script
            if response.status_code == 200:
                try:
                    res_data = response.json()
                    if res_data.get("status") == "success":
                        st.success("🎉 Đã lưu toàn bộ lịch sử phân tích và insight của bạn lên Google Sheet thành công!")
                    else:
                        st.error(f"Lỗi từ Apps Script: {res_data.get('message')}")
                except ValueError:
                    st.error("Lỗi: Apps Script không trả về định dạng JSON (Có thể do sai quyền truy cập).")
                    with st.expander("Xem chi tiết nội dung Google trả về"):
                        st.write(response.text)
            else:
                # HIỂN THỊ MÃ LỖI CỤ THỂ Ở ĐÂY
                st.error(f"Google Server từ chối kết nối! Mã lỗi: {response.status_code}")
                with st.expander("Xem chi tiết lỗi"):
                    st.write(response.text)
                
        except Exception as err:
            st.error(f"Không thể gửi dữ liệu. Chi tiết: {err}")