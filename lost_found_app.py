import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. 頁面基本設定 ---
st.set_page_config(
    page_title="新興國小失物招領系統", 
    page_icon="🏫", 
    layout="wide"
)

# --- 2. 自訂 CSS 美化樣式 ---
st.markdown("""
    <style>
    .main-title {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 30px;
    }
    .status-badge-open {
        background-color: #FF4B4B;
        color: white;
        padding: 4px 12px;
        border-radius: 15px;
        font-size: 0.9rem;
        font-weight: bold;
    }
    .status-badge-closed {
        background-color: #28a745;
        color: white;
        padding: 4px 12px;
        border-radius: 15px;
        font-size: 0.9rem;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 檔案與目錄設定 ---
DATA_FILE = 'lost_items.csv'
IMG_DIR = 'uploaded_images'

if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

# --- 4. 資料處理函數 ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["ID", "物品名稱", "拾獲地點", "拾獲日期", "特徵描述", "圖片路徑", "狀態"])
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# 刪除功能：同時刪除資料與圖片
def delete_item(item_id):
    df = load_data()
    # 找出該筆資料以獲取圖片路徑
    target_row = df[df['ID'] == item_id]
    if not target_row.empty:
        img_path = target_row.iloc[0]['圖片路徑']
        # 刪除實體圖片檔案
        if os.path.exists(img_path):
            try:
                os.remove(img_path)
            except:
                pass # 如果圖檔本來就不在，忽略錯誤
        
        # 刪除 CSV 中的該行
        df = df[df['ID'] != item_id]
        save_data(df)

# 更新狀態功能
def update_status(item_id):
    df = load_data()
    df.loc[df['ID'] == item_id, '狀態'] = '已領回'
    save_data(df)

# --- 5. 主程式 ---
def main():
    st.markdown('<p class="main-title">🏫 台南市南區新興國小失物招領系統</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">請老師與同學們協助留意，讓物品早日回家 ✨</p>', unsafe_allow_html=True)
    
    # --- 側邊欄 ---
    with st.sidebar:
        st.header("➕ 新增拾獲物品")
        st.caption("只需填寫名稱並上傳照片即可")
        
        with st.form("add_item_form", clear_on_submit=True):
            name = st.text_input("🏷️ 物品名稱 (必填)")
            uploaded_file = st.file_uploader("📷 上傳照片 (必填)", type=['png', 'jpg', 'jpeg'])
            st.divider()
            location = st.text_input("📍 拾獲地點 (選填)")
            date = st.date_input("📅 拾獲日期", datetime.now())
            desc = st.text_area("📝 特徵描述 (選填)", placeholder="例如：上面有貼姓名貼...")
            
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
                    new_id = len(df) + 1 if not df.empty else 1
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
                    st.error("⚠️ 「物品名稱」與「照片」為必填項目！")

        st.divider()
        
        # --- 管理員專區 (密碼保護) ---
        st.markdown("### 🔐 管理員專區")
        admin_pwd = st.text_input("輸入密碼啟用刪除功能", type="password", placeholder="請輸入管理密碼")
        is_admin = (admin_pwd == "720720")
        
        if is_admin:
            st.success("🔓 管理員模式已啟用")
        elif admin_pwd:
            st.error("密碼錯誤")

    # --- 主畫面 ---
    col_filter, col_space = st.columns([2, 5])
    with col_filter:
        filter_status = st.radio("👀 篩選狀態", ["全部", "未領取", "已領回"], horizontal=True)

    st.write("") 

    df = load_data()
    
    if df.empty:
        st.info("目前沒有失物資料，太棒了！🎉")
    else:
        if filter_status == "未領取":
            df = df[df["狀態"] == "未領取"]
        elif filter_status == "已領回":
            df = df[df["狀態"] == "已領回"]
            
        df = df.sort_values(by="ID", ascending=False)

        for index, row in df.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([1.5, 2.5, 1])
                
                with col1:
                    if os.path.exists(row["圖片路徑"]):
                        st.image(row["圖片路徑"], use_container_width=True)
                    else:
                        st.warning("🚫 圖片遺失")
                
                with col2:
                    st.markdown(f"### {row['物品名稱']}")
                    if row['狀態'] == "未領取":
                        st.markdown('<span class="status-badge-open">🔴 等待失主</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="status-badge-closed">🟢 已結案</span>', unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.markdown(f"**📍 地點：** {row['拾獲地點']}")
                    st.markdown(f"**📅 日期：** {row['拾獲日期']}")
                    st.markdown(f"**📝 描述：** {row['特徵描述']}")

                with col3:
                    st.write("") 
                    st.write("") 
                    
                    # 1. 領回按鈕 (所有人可見，僅限未領取)
                    if row['狀態'] == "未領取":
                        st.button(
                            "🙋‍♂️ 有人領走了", 
                            key=f"claim_{row['ID']}", 
                            type="primary",
                            on_click=lambda id=row['ID']: update_status(id)
                        )
                    
                    # 2. 刪除按鈕 (僅管理員可見)
                    if is_admin:
                        st.write("") # 間距
                        st.button(
                            "🗑️ 刪除資料",
                            key=f"delete_{row['ID']}",
                            help="此操作無法復原",
                            on_click=lambda id=row['ID']: delete_item(id)
                        )

if __name__ == '__main__':
    main()