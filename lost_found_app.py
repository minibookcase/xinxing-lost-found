import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 設定頁面資訊 ---
st.set_page_config(page_title="新興國小失物招領", page_icon="🎒", layout="wide")

# --- 檔案與目錄設定 ---
DATA_FILE = 'lost_items.csv'
IMG_DIR = 'uploaded_images'

# 確保圖片資料夾存在
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

# --- 載入資料函數 ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["ID", "物品名稱", "拾獲地點", "拾獲日期", "特徵描述", "圖片路徑", "狀態"])
    return pd.read_csv(DATA_FILE)

# --- 儲存資料函數 ---
def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# --- 主程式 ---
def main():
    # 標題
    st.markdown("<h1 style='text-align: center; color: #2E86C1;'>🏫 台南市南區新興國小失物招領系統</h1>", unsafe_allow_html=True)
    st.write("---")

    # 側邊欄：新增失物功能
    with st.sidebar:
        st.header("➕ 新增拾獲物品")
        st.info("請在此處輸入拾獲物品的資訊")
        
        with st.form("add_item_form", clear_on_submit=True):
            name = st.text_input("物品名稱 (如：藍色水壺)")
            location = st.text_input("拾獲地點 (如：操場司令台)")
            date = st.date_input("拾獲日期", datetime.now())
            desc = st.text_area("特徵描述 (如：上面貼有皮卡丘貼紙)")
            uploaded_file = st.file_uploader("上傳照片", type=['png', 'jpg', 'jpeg'])
            
            submitted = st.form_submit_button("送出資料")
            
            if submitted:
                if name and location and uploaded_file:
                    # 處理圖片儲存
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_ext = uploaded_file.name.split('.')[-1]
                    img_filename = f"{timestamp}.{file_ext}"
                    img_path = os.path.join(IMG_DIR, img_filename)
                    
                    with open(img_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # 處理資料儲存
                    df = load_data()
                    new_id = len(df) + 1
                    new_data = {
                        "ID": new_id,
                        "物品名稱": name,
                        "拾獲地點": location,
                        "拾獲日期": str(date),
                        "特徵描述": desc,
                        "圖片路徑": img_path,
                        "狀態": "未領取"
                    }
                    # 使用 concat 替代 append (pandas 新版寫法)
                    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                    save_data(df)
                    st.success("✅ 物品已成功登錄！")
                else:
                    st.error("⚠️ 請填寫完整資訊並上傳照片")

    # 主畫面：顯示失物清單
    st.subheader("📋 目前失物清單")
    
    # 篩選功能
    filter_status = st.radio("顯示狀態：", ["全部", "未領取", "已領回"], horizontal=True)
    
    df = load_data()
    
    if df.empty:
        st.info("目前沒有失物資料。")
    else:
        # 根據狀態篩選
        if filter_status == "未領取":
            df = df[df["狀態"] == "未領取"]
        elif filter_status == "已領回":
            df = df[df["狀態"] == "已領回"]
            
        # 倒序排列（最新的在最上面）
        df = df.sort_values(by="ID", ascending=False)

        # 顯示卡片式清單
        for index, row in df.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([1, 2, 1])
                
                # 左欄：圖片
                with col1:
                    if os.path.exists(row["圖片路徑"]):
                        st.image(row["圖片路徑"], width=200)
                    else:
                        st.write("🚫 圖片遺失")
                
                # 中欄：詳細資訊
                with col2:
                    st.markdown(f"### {row['物品名稱']}")
                    st.write(f"📍 **拾獲地點**: {row['拾獲地點']}")
                    st.write(f"📅 **拾獲日期**: {row['拾獲日期']}")
                    st.write(f"📝 **特徵**: {row['特徵描述']}")
                    
                    # 狀態標籤顏色
                    status_color = "red" if row['狀態'] == "未領取" else "green"
                    st.markdown(f"狀態：<span style='color:{status_color}; font-weight:bold'>{row['狀態']}</span>", unsafe_allow_html=True)

                # 右欄：操作按鈕
                with col3:
                    st.write("---")
                    # 只有未領取的物品顯示領回按鈕
                    if row['狀態'] == "未領取":
                        if st.button(f"有人領走了 (編號 {row['ID']})", key=f"claim_{row['ID']}"):
                            # 更新原始資料的狀態
                            original_df = load_data()
                            original_df.loc[original_df['ID'] == row['ID'], '狀態'] = '已領回'
                            save_data(original_df)
                            st.rerun() # 重新整理頁面
                
                st.write("---") # 分隔線

if __name__ == '__main__':
    main()