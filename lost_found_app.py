import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta

# --- 1. 頁面基本設定 ---
st.set_page_config(
    page_title="新興國小失物招領系統", 
    page_icon="🏫", 
    layout="wide"
)

# --- 2. 檔案與目錄設定 ---
DATA_FILE = 'lost_items.csv'
IMG_DIR = 'uploaded_images'
CONFIG_FILE = 'config.json'

# 確保圖片資料夾存在
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

# --- 3. 自訂 CSS 美化樣式 ---
st.markdown("""
    <style>
    /* 頂部大標題區塊 */
    .header-container {
        background-color: #1E3A8A;
        padding: 30px;
        border-radius: 15px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main-title {
        font-size: 3rem;
        color: #FFFFFF;
        font-weight: 900;
        margin: 0;
        letter-spacing: 2px;
        font-family: "Microsoft JhengHei", sans-serif;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #E0E7FF;
        margin-top: 10px;
    }
    
    /* 狀態標籤樣式 */
    .status-badge-open {
        background-color: #EF4444;
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
    }
    .status-badge-closed {
        background-color: #10B981;
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: bold;
    }
    
    /* 倒數計時樣式 */
    .countdown-tag {
        background-color: #F59E0B;
        color: white;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: bold;
        margin-left: 10px;
    }
    .expired-tag {
        background-color: #6B7280;
        color: white;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: bold;
        margin-left: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. 輔助函數 ---

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"expiry_days": 60}
    return {"expiry_days": 60}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["ID", "物品名稱", "拾獲地點", "拾獲日期", "特徵描述", "圖片路徑", "狀態"])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def delete_item(item_id):
    df = load_data()
    target_row = df[df['ID'] == item_id]
    if not target_row.empty:
        # 取得圖片路徑並刪除檔案
        img_path = target_row.iloc[0]['圖片路徑']
        if pd.notna(img_path) and os.path.exists(str(img_path)):
            try:
                os.remove(str(img_path))
            except:
                pass
        # 刪除資料行
        df = df[df['ID'] != item_id]
        save_data(df)

def update_status(item_id):
    df = load_data()
    df.loc[df['ID'] == item_id, '狀態'] = '已領回'
    save_data(df)

def get_days_left(found_date_str, expiry_days):
    try:
        found_date = datetime.strptime(str(found_date_str), "%Y-%m-%d").date()
        deadline = found_date + timedelta(days=expiry_days)
        today = datetime.now().date()
        days_left = (deadline - today).days
        return days_left, deadline
    except:
        return 0, datetime.now().date()

# --- 5. 主程式 ---
def main():
    config = load_config()
    current_expiry_days = config.get("expiry_days", 60)

    # 顯示美化後的大標題區塊
    st.markdown(f"""
        <div class="header-container">
            <p class="main-title">🏫 台南市南區新興國小失物招領系統</p>
            <p class="sub-title">物品認領期限：{current_expiry_days} 天｜請同學們把握時間領回</p>
        </div>
    """, unsafe_allow_html=True)
    
    # --- 側邊欄 ---
    with st.sidebar:
        # 管理員登入區塊
        st.markdown("### 🔐 管理員登入")
        st.caption("輸入密碼以啟用「結案」與「刪除」權限")
        admin_pwd = st.text_input("管理密碼", type="password", placeholder="老師請在此輸入")
        
        # 判斷是否為管理員
        is_admin = (admin_pwd == "720720")
        
        if is_admin:
            st.success("🔓 管理員模式已啟用")
        elif admin_pwd:
            st.error("密碼錯誤")
            
        st.divider()

        # 新增物品
        st.header("➕ 新增拾獲物品")
        
        with st.form("add_item_form", clear_on_submit=True):
            name = st.text_input("🏷️ 物品名稱 (必填)")
            uploaded_file = st.file_uploader("📷 上傳照片 (必填)", type=['png', 'jpg', 'jpeg'])
            st.divider()
            location = st.text_input("📍 拾獲地點 (選填)")
            date = st.date_input("📅 拾獲日期", datetime.now())
            desc = st.text_area("📝 特徵描述 (選填)")
            
            submitted = st.form_submit_button("🚀 發布失物招領", use_container_width=True)
            
            if submitted:
                if name and uploaded_file:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_ext = uploaded_file.name.split('.')[-1]
                    img_filename = f"{timestamp}.{file_ext}"
                    img_path = os.path.join(IMG_DIR, img_filename)
                    
                    with open(img_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    final_location = location if location else "未提供"
                    final_desc = desc if desc else "無特殊描述"
                    
                    df = load_data()
                    
                    # --- [修正點1] 更安全的 ID 生成邏輯 ---
                    if not df.empty:
                        # 找出目前最大的 ID 並 +1，確保不重複
                        new_id = df["ID"].max() + 1
                    else:
                        new_id = 1
                    
                    new_data = {
                        "ID": new_id,
                        "物品名稱": name,
                        "拾獲地點": final_location,
                        "拾獲日期": str(date),
                        "特徵描述": final_desc,
                        "圖片路徑": img_path,
                        "狀態": "未領取"
                    }
                    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                    save_data(df)
                    st.success("✅ 發布成功！")
                else:
                    st.error("⚠️ 缺漏必填項目")

        # 系統設定
        if is_admin:
            st.divider()
            st.subheader("⚙️ 系統設定")
            new_expiry = st.number_input("設定認領期限