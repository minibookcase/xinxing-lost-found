import streamlit as st
import pandas as pd
import os
import json
import zipfile
import io
import shutil
from datetime import datetime, timedelta

st.set_page_config(
    page_title="新興國小失物招領系統", 
    page_icon="🏫", 
    layout="wide"
)

BASE_DATA_DIR = os.environ.get("DATA_DIR", ".")
DATA_FILE = os.path.join(BASE_DATA_DIR, 'lost_items.csv')
IMG_DIR = os.path.join(BASE_DATA_DIR, 'uploaded_images')
CONFIG_FILE = os.path.join(BASE_DATA_DIR, 'config.json')

if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR, exist_ok=True)

# --- 2. 檔案與目錄設定 ---
BASE_DATA_DIR = os.environ.get("DATA_DIR", ".")
DATA_FILE = os.path.join(BASE_DATA_DIR, "lost_items.csv")
IMG_DIR = os.path.join(BASE_DATA_DIR, "uploaded_images")
CONFIG_FILE = os.path.join(BASE_DATA_DIR, "config.json")

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
        img_path = target_row.iloc[0]['圖片路徑']
        if pd.notna(img_path) and os.path.exists(str(img_path)):
            try:
                os.remove(str(img_path))
            except:
                pass
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

# --- 新增功能：建立備份 ZIP ---
def create_backup_zip():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. 加入 CSV 資料檔
        if os.path.exists(DATA_FILE):
            zf.write(DATA_FILE, arcname=DATA_FILE)
        
        # 2. 加入 Config 設定檔
        if os.path.exists(CONFIG_FILE):
            zf.write(CONFIG_FILE, arcname=CONFIG_FILE)
            
        # 3. 加入所有圖片
        if os.path.exists(IMG_DIR):
            for root, dirs, files in os.walk(IMG_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 保持資料夾結構
                    zf.write(file_path, arcname=os.path.join(IMG_DIR, file))
    
    buffer.seek(0)
    return buffer

# --- 新增功能：從 ZIP 還原資料 ---
def restore_data_from_zip(uploaded_zip):
    try:
        with zipfile.ZipFile(uploaded_zip, 'r') as zf:
            # 1. 檢查 ZIP 內容是否安全 (簡單檢查)
            file_names = zf.namelist()
            if DATA_FILE not in file_names:
                return False, "備份檔中找不到資料檔 (csv)"
            
            # 2. 清空目前的圖片資料夾，避免混亂
            if os.path.exists(IMG_DIR):
                shutil.rmtree(IMG_DIR)
            os.makedirs(IMG_DIR)
            
            # 3. 解壓縮覆蓋
            zf.extractall('.')
            return True, "還原成功！"
    except Exception as e:
        return False, f"還原失敗：{str(e)}"

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
        st.caption("輸入密碼以啟用「結案」、「刪除」與「備份」權限")
        admin_pwd = st.text_input("管理密碼", type="password", placeholder="老師請在此輸入")
        
        # 判斷是否為管理員
        ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "720720")
        is_admin = (admin_pwd == ADMIN_PASSWORD)
        
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
                    
                    # ID 生成邏輯
                    if not df.empty:
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

        # --- 管理員專屬功能區 (系統設定 & 備份還原) ---
        if is_admin:
            st.divider()
            st.subheader("⚙️ 系統設定與維護")
            
            # 1. 設定認領天數
            st.markdown("**認領期限設定**")
            new_expiry = st.number_input("天數", min_value=1, value=current_expiry_days, label_visibility="collapsed")
            if new_expiry != current_expiry_days:
                config["expiry_days"] = new_expiry
                save_config(config)
                st.rerun()
            
            st.write("---")
            
            # 2. 資料備份下載
            st.markdown("**💾 資料備份 (下載 ZIP)**")
            st.caption("下載包含 CSV 與所有圖片的備份檔")
            
            zip_buffer = create_backup_zip()
            timestamp_str = datetime.now().strftime("%Y%m%d")
            
            st.download_button(
                label="⬇️ 下載完整系統備份",
                data=zip_buffer,
                file_name=f"lost_found_backup_{timestamp_str}.zip",
                mime="application/zip",
                use_container_width=True
            )
            
            st.write("---")
            
            # 3. 資料還原上傳
            st.markdown("**📥 資料還原 (上傳 ZIP)**")
            st.caption("⚠️ 注意：此操作將覆蓋目前所有資料！")
            
            uploaded_backup = st.file_uploader("請選擇備份 ZIP 檔", type="zip")
            
            if uploaded_backup is not None:
                if st.button("🚨 確定覆蓋並還原系統", type="primary", use_container_width=True):
                    success, msg = restore_data_from_zip(uploaded_backup)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    # --- 主畫面顯示 ---
    col_filter, col_space = st.columns([2, 5])
    with col_filter:
        filter_status = st.radio("👀 篩選狀態", ["全部", "未領取", "已領回"], horizontal=True)

    st.write("") 

    df = load_data()
    
    if df.empty:
        st.info("目前沒有失物資料。")
    else:
        if filter_status == "未領取":
            df = df[df["狀態"] == "未領取"]
        elif filter_status == "已領回":
            df = df[df["狀態"] == "已領回"]
            
        df = df.sort_values(by="ID", ascending=False)

        for index, row in df.iterrows():
            with st.container(border=True):
                col1, col2, col3 = st.columns([1.5, 2.5, 1])
                
                days_left, deadline_date = get_days_left(row['拾獲日期'], current_expiry_days)
                
                with col1:
                    if pd.notna(row["圖片路徑"]) and os.path.exists(str(row["圖片路徑"])):
                        st.image(str(row["圖片路徑"]), use_container_width=True)
                    else:
                        st.warning("圖片遺失")
                
                with col2:
                    header_cols = st.columns([3, 2])
                    with header_cols[0]:
                        st.markdown(f"### {row['物品名稱']}")
                    with header_cols[1]:
                        if row['狀態'] == "未領取":
                            st.markdown('<span class="status-badge-open">🔴 等待失主</span>', unsafe_allow_html=True)
                            if days_left >= 0:
                                st.markdown(f'<span class="countdown-tag">⏳ 剩餘 {days_left} 天</span>', unsafe_allow_html=True)
                            else:
                                st.markdown(f'<span class="expired-tag">⚠️ 已過期 {abs(days_left)} 天</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('<span class="status-badge-closed">🟢 已結案</span>', unsafe_allow_html=True)

                    st.markdown("---")
                    st.markdown(f"**📍 地點：** {row['拾獲地點']}")
                    st.markdown(f"**📅 拾獲日：** {row['拾獲日期']}")
                    st.markdown(f"**🛑 截止日：** {deadline_date} (保留 {current_expiry_days} 天)")
                    st.markdown(f"**📝 描述：** {row['特徵描述']}")

                with col3:
                    st.write("") 
                    st.write("") 
                    
                    unique_key_suffix = f"{row['ID']}_{index}"

                    if row['狀態'] == "未領取":
                        if is_admin:
                            st.button(
                                "🙋‍♂️ 有人領走了", 
                                key=f"claim_{unique_key_suffix}", 
                                type="primary",
                                on_click=lambda id=row['ID']: update_status(id)
                            )
                        else:
                            st.info("ℹ️ 欲認領請洽學務處")
                    
                    if is_admin:
                        st.write("") 
                        st.button(
                            "🗑️ 刪除資料",
                            key=f"delete_{unique_key_suffix}",
                            help="此操作無法復原",
                            on_click=lambda id=row['ID']: delete_item(id)
                        )

if __name__ == '__main__':
    main()