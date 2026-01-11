import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# --- 設定區 ---
# 請將這裡替換成你自己的 Google 試算表網址
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1nHXcZBx1st290N7VxceiS6N6B91HDJV2dY_YX4cthCo/edit?gid=0#gid=0"

# 頁面設定
st.set_page_config(page_title="雲端健身紀錄", page_icon="💪")
st.title("💪 雲端健身訓練日誌 (Google Sheets)")

# --- 連線 Google Sheets 函數 ---
def get_google_sheet_data():
    # 定義權限範圍
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 從 Streamlit Secrets 讀取憑證 (這會在部署時設定)
    # 本地測試時，如果沒有設定 secrets，會報錯
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 開啟試算表
        sheet = client.open_by_url(SPREADSHEET_URL).sheet1
        return sheet
    except Exception as e:
        st.error(f"連線失敗，請檢查 Secrets 設定: {e}")
        return None

# --- 資料處理函數 ---
def load_data(sheet):
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["日期", "動作名稱", "重量(kg)", "次數", "組數", "備註"])
    df = pd.DataFrame(data)
    # 強制轉換日期格式
    if "日期" in df.columns and not df.empty:
        df["日期"] = pd.to_datetime(df["日期"]).dt.date
    return df

# 建立連線
sheet = get_google_sheet_data()

if sheet:
    # 載入資料
    df = load_data(sheet)

    # --- 側邊欄：新增紀錄 ---
    st.sidebar.header("📝 新增訓練")
    input_date = st.sidebar.date_input("日期", date.today())
    exercise = st.sidebar.selectbox(
        "選擇動作", 
        ["深蹲 (Squat)", "臥推 (Bench Press)", "硬舉 (Deadlift)", "肩推 (Overhead Press)", "引體向上 (Pull-up)", "啞鈴划船 (Dumbbell Row)", "其他"]
    )
    if exercise == "其他":
        exercise = st.sidebar.text_input("輸入自訂動作名稱")

    weight = st.sidebar.number_input("重量 (kg)", min_value=0.0, step=0.5, format="%.1f")
    reps = st.sidebar.number_input("次數 (Reps)", min_value=1, step=1)
    sets = st.sidebar.number_input("組數 (Sets)", min_value=1, step=1)
    note = st.sidebar.text_input("備註")

    if st.sidebar.button("提交紀錄"):
        # 準備要寫入的一列資料 (轉成字串以確保寫入順利)
        new_row = [str(input_date), exercise, weight, reps, sets, note]
        
        # 1. 如果是全空的表，先寫入標題
        if df.empty:
            sheet.append_row(["日期", "動作名稱", "重量(kg)", "次數", "組數", "備註"])
            
        # 2. 寫入新資料到 Google Sheet
        sheet.append_row(new_row)
        
        st.sidebar.success("已上傳至 Google Sheets！")
        # 重新執行以顯示最新資料
        st.rerun()

    # --- 主頁面：數據儀表板 ---
    st.subheader("📋 歷史紀錄")
    if not df.empty:
        st.dataframe(df.sort_values(by="日期", ascending=False), use_container_width=True)

        st.markdown("---")
        st.subheader("📈 力量進步趨勢")
        
        unique_exercises = df["動作名稱"].unique()
        selected_exercise = st.selectbox("選擇要查看趨勢的動作", unique_exercises)
        
        if selected_exercise:
            chart_data = df[df["動作名稱"] == selected_exercise].copy()
            chart_data["日期"] = pd.to_datetime(chart_data["日期"])
            chart_data = chart_data.sort_values("日期")
            
            st.line_chart(chart_data, x="日期", y="重量(kg)")
            
            max_weight = chart_data["重量(kg)"].max()
            st.metric(label=f"{selected_exercise} PR", value=f"{max_weight} kg")
    else:
        st.info("目前試算表是空的，請新增第一筆資料。")