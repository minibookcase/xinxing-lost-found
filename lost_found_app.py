from PIL import Image, ImageOps
import streamlit as st
import pandas as pd
import os
import json
import zipfile
import io
import shutil
from datetime import datetime, timedelta

# --- 1. 頁面基本設定 ---
st.set_page_config(
    page_title="新興國小失物招領系統",
    page_icon="🏫",
    layout="wide"
)

# --- 2. 路徑設定（支援 Railway Volume） ---
BASE_DATA_DIR = os.environ.get("DATA_DIR", ".")
DATA_FILE = os.path.join(BASE_DATA_DIR, "lost_items.csv")
IMG_DIR = os.path.join(BASE_DATA_DIR, "uploaded_images")
CONFIG_FILE = os.path.join(BASE_DATA_DIR, "config.json")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "720720")

DATA_COLUMNS = ["ID", "物品名稱", "拾獲地點", "拾獲日期", "特徵描述", "圖片路徑", "狀態"]

os.makedirs(BASE_DATA_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

if not os.path.exists(DATA_FILE):
    pd.DataFrame(columns=DATA_COLUMNS).to_csv(DATA_FILE, index=False)

# --- 3. 自訂 CSS 美化樣式 ---
st.markdown("""
    <style>
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
def process_uploaded_image(uploaded_file):
    """讀取上傳圖片，先做 EXIF 自動轉正，回傳 Pillow Image"""
    try:
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        return img, None
    except Exception as e:
        return None, str(e)


def save_processed_image(img, save_path, max_size=(1600, 1600), quality=75):
    """將使用者確認後的圖片壓縮儲存成 JPG"""
    try:
        img = img.copy()
        img.thumbnail(max_size)
        img.save(save_path, format="JPEG", quality=quality, optimize=True)
        return True, None
    except Exception as e:
        return False, str(e)


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"expiry_days": 60}
    return {"expiry_days": 60}


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=DATA_COLUMNS)

    try:
        df = pd.read_csv(DATA_FILE)
        for col in DATA_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[DATA_COLUMNS]
    except Exception:
        return pd.DataFrame(columns=DATA_COLUMNS)


def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


def delete_item(item_id):
    df = load_data()
    target_row = df[df["ID"] == item_id]

    if not target_row.empty:
        img_path = str(target_row.iloc[0]["圖片路徑"])
        if pd.notna(img_path) and img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except Exception:
                pass

        df = df[df["ID"] != item_id]
        save_data(df)


def update_status(item_id):
    df = load_data()
    df.loc[df["ID"] == item_id, "狀態"] = "已領回"
    save_data(df)


def get_days_left(found_date_str, expiry_days):
    try:
        found_date = datetime.strptime(str(found_date_str), "%Y-%m-%d").date()
        deadline = found_date + timedelta(days=expiry_days)
        today = datetime.now().date()
        days_left = (deadline - today).days
        return days_left, deadline
    except Exception:
        return 0, datetime.now().date()


def create_backup_zip():
    """建立結構乾淨的備份 ZIP"""
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(DATA_FILE):
            zf.write(DATA_FILE, arcname="lost_items.csv")

        if os.path.exists(CONFIG_FILE):
            zf.write(CONFIG_FILE, arcname="config.json")

        if os.path.exists(IMG_DIR):
            for root, dirs, files in os.walk(IMG_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, BASE_DATA_DIR)
                    zf.write(file_path, arcname=rel_path)

    buffer.seek(0)
    return buffer


def restore_data_from_zip(uploaded_zip):
    """將備份還原到 BASE_DATA_DIR"""
    try:
        with zipfile.ZipFile(uploaded_zip, "r") as zf:
            file_names = zf.namelist()

            if "lost_items.csv" not in file_names:
                return False, "備份檔中找不到 lost_items.csv"

            for member in file_names:
                normalized = os.path.normpath(member)
                if normalized.startswith("..") or os.path.isabs(normalized):
                    return False, f"備份檔含不安全路徑：{member}"

            os.makedirs(BASE_DATA_DIR, exist_ok=True)

            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)
            if os.path.exists(IMG_DIR):
                shutil.rmtree(IMG_DIR)

            os.makedirs(IMG_DIR, exist_ok=True)
            zf.extractall(BASE_DATA_DIR)

            if not os.path.exists(CONFIG_FILE):
                save_config({"expiry_days": 60})

            os.makedirs(IMG_DIR, exist_ok=True)
            return True, "還原成功！"

    except Exception as e:
        return False, f"還原失敗：{str(e)}"


def build_excel_report(export_df):
    """建立含圖片的 Excel 報表（已優化：圖片不重疊）"""
    excel_buffer = io.BytesIO()

    report_df = export_df.copy()

    if "圖片路徑" not in report_df.columns:
        report_df["圖片路徑"] = ""

    # 顯示欄位（不含圖片路徑）
    display_df = report_df[[
        "物品名稱",
        "拾獲日期",
        "拾獲地點",
        "狀態",
        "特徵描述"
    ]].copy()

    display_df["圖片"] = ""

    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        display_df.to_excel(writer, index=False, sheet_name="失物清單", startrow=3)

        workbook = writer.book
        worksheet = writer.sheets["失物清單"]

        # ===== 樣式 =====
        title_format = workbook.add_format({
            "bold": True,
            "font_size": 16,
            "align": "center",
            "valign": "vcenter"
        })

        subtitle_format = workbook.add_format({
            "font_size": 10,
            "align": "center"
        })

        header_format = workbook.add_format({
            "bold": True,
            "align": "center",
            "border": 1
        })

        cell_format = workbook.add_format({
            "border": 1,
            "valign": "vcenter"
        })

        # ===== 標題 =====
        worksheet.merge_range("A1:F1", "台南市南區新興國小 失物招領清單", title_format)

        today_str = datetime.now().strftime("%Y-%m-%d")
        worksheet.merge_range("A2:F2", f"報表日期：{today_str}", subtitle_format)

        # ===== 表頭 =====
        for col_num, col_name in enumerate(display_df.columns):
            worksheet.write(3, col_num, col_name, header_format)

        # ===== 內容 =====
        for row_num in range(len(display_df)):
            for col_num in range(len(display_df.columns)):
                worksheet.write(row_num + 4, col_num, display_df.iloc[row_num, col_num], cell_format)

        # ===== 欄寬（文字欄）=====
        for col_num, column in enumerate(display_df.columns[:-1]):
            col_width = max(display_df[column].astype(str).map(len).max(), len(column))
            worksheet.set_column(col_num, col_num, min(col_width + 4, 30))

        # ===== 圖片欄設定 =====
        image_col_index = len(display_df.columns) - 1
        worksheet.set_column(image_col_index, image_col_index, 20)

        # ===== 插入圖片（關鍵修正）=====
        for row_num, img_path in enumerate(report_df["圖片路徑"]):
            excel_row = row_num + 4

            # 固定列高（避免重疊）
            worksheet.set_row(excel_row, 110)

            if pd.notna(img_path) and str(img_path).strip() and os.path.exists(str(img_path)):
                try:
                    img = Image.open(str(img_path))
                    img = ImageOps.exif_transpose(img)

                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    elif img.mode != "RGB":
                        img = img.convert("RGB")

                    max_size = 120
                    ratio = min(max_size / img.width, max_size / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size)

                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="JPEG", quality=80)
                    img_bytes.seek(0)

                    worksheet.insert_image(
                        excel_row,
                        image_col_index,
                        "img.jpg",
                        {
                            "image_data": img_bytes,
                            "x_offset": 4,
                            "y_offset": 4,
                            "object_position": 1
                        }
                    )

                except Exception:
                    worksheet.write(excel_row, image_col_index, "圖片錯誤", cell_format)
            else:
                worksheet.write(excel_row, image_col_index, "無圖片", cell_format)

    excel_buffer.seek(0)
    return excel_buffer


# --- 5. 主程式 ---
def main():
    if "preview_rotation" not in st.session_state:
        st.session_state.preview_rotation = 0

    config = load_config()
    current_expiry_days = config.get("expiry_days", 60)

    st.markdown(f"""
        <div class="header-container">
            <p class="main-title">🏫 台南市南區新興國小失物招領系統</p>
            <p class="sub-title">物品認領期限：{current_expiry_days} 天｜請同學們把握時間領回</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 側邊欄 ---
    with st.sidebar:
        st.markdown("### 🔐 管理員登入")
        st.caption("輸入密碼以啟用「結案」、「刪除」、「備份」與「報表」權限")
        admin_pwd = st.text_input("管理密碼", type="password", placeholder="老師請在此輸入")

        is_admin = (admin_pwd == ADMIN_PASSWORD)

        if is_admin:
            st.success("🔓 管理員模式已啟用")
        elif admin_pwd:
            st.error("密碼錯誤")

        st.divider()

        # 新增物品
        st.header("➕ 新增拾獲物品")

        with st.form("add_item_form", clear_on_submit=False):
            name = st.text_input("🏷️ 物品名稱 (必填)")
            uploaded_file = st.file_uploader("📷 上傳照片 (必填)", type=["png", "jpg", "jpeg"])

            st.divider()
            location = st.text_input("📍 拾獲地點 (選填)")
            date = st.date_input("📅 拾獲日期", datetime.now())
            desc = st.text_area("📝 特徵描述 (選填)")

            preview_img = None
            if uploaded_file is not None:
                temp_img, error_msg = process_uploaded_image(uploaded_file)
                if temp_img is not None:
                    preview_img = temp_img.rotate(
                        -st.session_state.preview_rotation,
                        expand=True
                    )
                    st.image(preview_img, caption="照片預覽", use_container_width=True)
                else:
                    st.error(f"圖片讀取失敗：{error_msg}")

            col_left, col_right = st.columns(2)
            with col_left:
                rotate_left = st.form_submit_button("↺ 向左轉 90°", use_container_width=True)
            with col_right:
                rotate_right = st.form_submit_button("↻ 向右轉 90°", use_container_width=True)

            if rotate_left:
                st.session_state.preview_rotation = (st.session_state.preview_rotation - 90) % 360
                st.rerun()

            if rotate_right:
                st.session_state.preview_rotation = (st.session_state.preview_rotation + 90) % 360
                st.rerun()

            submitted = st.form_submit_button("🚀 發布失物招領", use_container_width=True)

            if submitted:
                if name and uploaded_file:
                    original_img, error_msg = process_uploaded_image(uploaded_file)
                    if original_img is None:
                        st.error(f"圖片處理失敗：{error_msg}")
                        st.stop()

                    final_img = original_img.rotate(
                        -st.session_state.preview_rotation,
                        expand=True
                    )

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    img_filename = f"{timestamp}.jpg"
                    img_path = os.path.join(IMG_DIR, img_filename)

                    success, save_error = save_processed_image(final_img, img_path)

                    if not success:
                        st.error(f"圖片儲存失敗：{save_error}")
                        st.stop()

                    final_location = location if location else "未提供"
                    final_desc = desc if desc else "無特殊描述"

                    df = load_data()

                    if not df.empty and pd.api.types.is_numeric_dtype(df["ID"]):
                        new_id = int(df["ID"].max()) + 1
                    elif not df.empty:
                        try:
                            new_id = int(pd.to_numeric(df["ID"], errors="coerce").max()) + 1
                        except Exception:
                            new_id = 1
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

                    st.session_state.preview_rotation = 0
                    st.success("✅ 發布成功！")
                    st.rerun()
                else:
                    st.error("⚠️ 缺漏必填項目")

        # --- 管理員專屬功能區 ---
        if is_admin:
            st.divider()
            st.subheader("⚙️ 系統設定與維護")

            st.markdown("**認領期限設定**")
            new_expiry = st.number_input(
                "天數",
                min_value=1,
                value=int(current_expiry_days),
                label_visibility="collapsed"
            )
            if new_expiry != current_expiry_days:
                config["expiry_days"] = int(new_expiry)
                save_config(config)
                st.rerun()

            st.write("---")

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

            st.markdown("**📥 資料還原 (上傳 ZIP)**")
            st.caption("⚠️ 注意：此操作將覆蓋目前所有資料！")

            uploaded_backup = st.file_uploader("請選擇備份 ZIP 檔", type="zip", key="restore_zip")

            if uploaded_backup is not None:
                if st.button("🚨 確定覆蓋並還原系統", type="primary", use_container_width=True):
                    success, msg = restore_data_from_zip(uploaded_backup)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            st.write("---")

            st.markdown("**📄 報表匯出**")
            st.caption("可依日期與狀態篩選，下載提供老師使用的失物清單")

            report_df = load_data().copy()

            if not report_df.empty:
                report_df["拾獲日期"] = pd.to_datetime(report_df["拾獲日期"], errors="coerce")

                default_start = datetime.now().date() - timedelta(days=30)
                default_end = datetime.now().date()

                report_start = st.date_input(
                    "報表開始日期",
                    value=default_start,
                    key="report_start"
                )

                report_end = st.date_input(
                    "報表結束日期",
                    value=default_end,
                    key="report_end"
                )

                report_status = st.selectbox(
                    "報表狀態篩選",
                    ["全部", "未領取", "已領回"],
                    index=1,
                    key="report_status"
                )

                filtered_df = report_df[
                    (report_df["拾獲日期"] >= pd.to_datetime(report_start)) &
                    (report_df["拾獲日期"] <= pd.to_datetime(report_end))
                ].copy()

                if report_status != "全部":
                    filtered_df = filtered_df[filtered_df["狀態"] == report_status].copy()

                export_df = filtered_df[[
                    "物品名稱",
                    "拾獲日期",
                    "拾獲地點",
                    "狀態",
                    "特徵描述",
                    "圖片路徑"
                ]].copy()

                export_df["拾獲日期"] = export_df["拾獲日期"].dt.strftime("%Y-%m-%d")

                st.markdown("**報表預覽**")

                # 畫面預覽用：不顯示圖片路徑
                preview_df = export_df[[
                    "物品名稱",
                    "拾獲日期",
                    "拾獲地點",
                    "狀態",
                    "特徵描述"
                ]].copy()

                if preview_df.empty:
                    st.info("目前查無符合條件的資料。")
                else:
                    st.dataframe(preview_df, use_container_width=True, hide_index=True)

                    # Excel 匯出用：保留完整欄位（包含圖片路徑）
                    excel_buffer = build_excel_report(export_df)

                    st.download_button(
                        label="⬇️ 下載失物報表（Excel）",
                        data=excel_buffer,
                        file_name=f"新興國小失物報表_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            else:
                st.info("目前沒有可匯出的失物資料。")

    # --- 主畫面顯示 ---
    col_filter, col_search = st.columns([2, 3])

    with col_filter:
        filter_status = st.radio("👀 篩選狀態", ["全部", "未領取", "已領回"], horizontal=True)

    with col_search:
        keyword = st.text_input("🔎 搜尋物品名稱", placeholder="例如：水壺、外套、跳繩")

    st.write("")

    df = load_data()

    if df.empty:
        st.info("目前沒有失物資料。")
    else:
        # 狀態篩選
        if filter_status == "未領取":
            df = df[df["狀態"] == "未領取"]
        elif filter_status == "已領回":
            df = df[df["狀態"] == "已領回"]

        # 關鍵字搜尋（只搜尋物品名稱）
        if keyword.strip():
            df = df[df["物品名稱"].astype(str).str.contains(keyword.strip(), case=False, na=False)]

        # 排序
        df = df.sort_values(by="ID", ascending=False)

        # 篩完後沒資料
        if df.empty:
            st.info("查無符合條件的失物資料。")
        else:
            for index, row in df.iterrows():
                with st.container(border=True):
                    col1, col2, col3 = st.columns([1.5, 2.5, 1])

                    days_left, deadline_date = get_days_left(row["拾獲日期"], current_expiry_days)

                    with col1:
                        img_path = str(row["圖片路徑"]) if pd.notna(row["圖片路徑"]) else ""
                        if img_path and os.path.exists(img_path):
                            st.image(img_path, use_container_width=True)
                        else:
                            st.warning("圖片遺失")

                    with col2:
                        header_cols = st.columns([3, 2])

                        with header_cols[0]:
                            st.markdown(f"### {row['物品名稱']}")

                        with header_cols[1]:
                            if row["狀態"] == "未領取":
                                st.markdown(
                                    '<span class="status-badge-open">🔴 等待失主</span>',
                                    unsafe_allow_html=True
                                )
                                if days_left >= 0:
                                    st.markdown(
                                        f'<span class="countdown-tag">⏳ 剩餘 {days_left} 天</span>',
                                        unsafe_allow_html=True
                                    )
                                else:
                                    st.markdown(
                                        f'<span class="expired-tag">⚠️ 已過期 {abs(days_left)} 天</span>',
                                        unsafe_allow_html=True
                                    )
                            else:
                                st.markdown(
                                    '<span class="status-badge-closed">🟢 已結案</span>',
                                    unsafe_allow_html=True
                                )

                        st.markdown("---")
                        st.markdown(f"**📍 地點：** {row['拾獲地點']}")
                        st.markdown(f"**📅 拾獲日：** {row['拾獲日期']}")
                        st.markdown(f"**🛑 截止日：** {deadline_date} (保留 {current_expiry_days} 天)")
                        st.markdown(f"**📝 描述：** {row['特徵描述']}")

                    with col3:
                        st.write("")
                        st.write("")

                        unique_key_suffix = f"{row['ID']}_{index}"

                        if row["狀態"] == "未領取":
                            if is_admin:
                                st.button(
                                    "🙋‍♂️ 有人領走了",
                                    key=f"claim_{unique_key_suffix}",
                                    type="primary",
                                    on_click=lambda id=row["ID"]: update_status(id)
                                )
                            else:
                                st.info("ℹ️ 欲認領請洽學務處")

                        if is_admin:
                            st.write("")
                            st.button(
                                "🗑️ 刪除資料",
                                key=f"delete_{unique_key_suffix}",
                                help="此操作無法復原",
                                on_click=lambda id=row["ID"]: delete_item(id)
                            )
if __name__ == "__main__":
    main()