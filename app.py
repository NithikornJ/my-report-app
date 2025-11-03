# ไฟล์: app.py
import streamlit as st
import pandas as pd
import io 
from processing import load_and_process_data # Import ฟังก์ชันเดิม
import datetime

# --- (ฟังก์ชัน create_multisheet_excel เหมือนเดิมเป๊ะๆ) ---
@st.cache_data
def create_multisheet_excel(df_summary_total, df_all_day, list_of_rights):
    """
    สร้างไฟล์ Excel ในหน่วยความจำ (BytesIO)
    """
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        
        # Sheet 1: สรุปยอด
        df_summary_total.to_excel(writer, sheet_name='สรุปยอด (Sheet1)', index=False)
        
        # Sheet 2: ข้อมูลทั้งหมด
        df_all_day.to_excel(writer, sheet_name='ข้อมูลทั้งหมด (Sheet2)', index=False)
        worksheet2 = writer.sheets['ข้อมูลทั้งหมด (Sheet2)']
        try:
            date_col_index = df_all_day.columns.get_loc('วันเข้า')
            worksheet2.set_column(date_col_index, date_col_index, 12, date_format)
        except KeyError:
            pass # ไม่ต้องเตือน

        # Sheet 3+: วนลูปสร้างตามสิทธิ
        for right in list_of_rights:
            df_right_detail = df_all_day[df_all_day['สิทธิ'] == right].copy()
            
            if not df_right_detail.empty:
                total_row_data = {}
                for col in df_right_detail.columns:
                    if pd.api.types.is_numeric_dtype(df_right_detail[col]):
                        total_row_data[col] = df_right_detail[col].sum()
                    elif col == 'สิทธิ': 
                        total_row_data[col] = "รวม"
                    else:
                        total_row_data[col] = None 
                
                total_row_df = pd.DataFrame(total_row_data, index=[0])
                df_right_detail_with_total = pd.concat([df_right_detail, total_row_df], ignore_index=True)
            else:
                df_right_detail_with_total = df_right_detail 

            safe_sheet_name = str(right).replace('[','').replace(']','').replace('/','-')[:30]
            df_right_detail_with_total.to_excel(writer, sheet_name=safe_sheet_name, index=False)
            
            worksheet_detail = writer.sheets[safe_sheet_name]
            try:
                date_col_index_detail = df_right_detail_with_total.columns.get_loc('วันเข้า')
                worksheet_detail.set_column(date_col_index_detail, date_col_index_detail, 12, date_format)
            except KeyError:
                pass # ไม่ต้องเตือน

    processed_data = output.getvalue()
    return processed_data
# --- (จบฟังก์ชัน) ---


# --- 1. ตั้งค่าหน้าเว็บ (เหมือนเดิม) ---
st.set_page_config(layout="wide")
st.title("โปรแกรมสร้างรายงาน Excel (Multi-sheet)")

# --- 2. (ใหม่) สร้างปุ่ม File Uploader ---
st.header("1. อัปโหลดไฟล์ CSV ข้อมูลดิบ")
uploaded_file = st.file_uploader("เลือกไฟล์ CSV (Encoding TIS-620 หรือ 874)", type=["csv"])

# --- (ใหม่) ตรรกะทั้งหมดจะทำงาน "หลังจาก" อัปโหลดไฟล์แล้ว ---
if uploaded_file is not None:
    
    # --- 3. โหลดข้อมูล (ใช้ File Object ที่เพิ่งอัปโหลด) ---
    try:
        df_full = load_and_process_data(uploaded_file)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดร้ายแรงขณะโหลดข้อมูล: {e}")
        st.stop()

    if df_full.empty:
        st.warning("ไม่สามารถประมวลผลข้อมูลในไฟล์ได้ กรุณาตรวจสอบไฟล์")
        st.stop()
    
    st.success(f"อัปโหลดไฟล์ '{uploaded_file.name}' และประมวลผลสำเร็จ!")

    # --- 4. สร้าง UI รับเงื่อนไข (วันที่) ---
    st.header("2. เลือกวันที่ต้องการ")

    min_date = df_full['วันเข้า'].min()
    max_date = df_full['วันเข้า'].max()

    selected_date = st.date_input(
        "เลือกวันที่",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY"
    )

    # --- 5. กรองข้อมูลเฉพาะวันที่เลือก ---
    st.header(f"ข้อมูลประจำวันที่: {selected_date.strftime('%d/%m/%Y')}")

    df_today = df_full[df_full['วันเข้า'].dt.date == selected_date].copy()

    if df_today.empty:
        st.warning("ไม่พบข้อมูลในวันที่เลือก")
    else:
        # --- 6. สร้างและแสดงตารางสรุป (Sheet 1) ---
        st.subheader("ตัวอย่างตารางสรุป (Sheet 1)")
        df_summary = df_today.groupby('สิทธิ').agg(
            จำนวนคน=('จำนวนคน', 'sum'),
            ลูกหนี้=('ลูกหนี้', 'sum'),
            เบิกได้=('เบิกได้', 'sum'),
            เบิกไม่ได้=('เบิกไม่ได้', 'sum'),
            รวม=('รวม', 'sum')
        )
        df_summary_with_total = df_summary.copy()
        df_summary_with_total.loc['รวมทั้งหมด'] = df_summary.sum(numeric_only=True)
        df_summary_with_total = df_summary_with_total.reset_index() 
        st.dataframe(df_summary_with_total, use_container_width=True)

        # --- 7. ปุ่มดาวน์โหลดไฟล์ Excel ---
        st.header("3. ดาวน์โหลดรายงาน")
        list_of_rights = df_summary.index.unique().tolist()
        excel_data = create_multisheet_excel(df_summary_with_total, df_today, list_of_rights)
        
        st.download_button(
            label=f"📥 ดาวน์โหลดไฟล์ Excel ทั้งหมดของวันที่ {selected_date.strftime('%d-%m-%Y')}",
            data=excel_data,
            file_name=f"Report_{selected_date.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # --- 8. (ส่วนเสริม) ดูตัวอย่างข้อมูลรายตัว ---
        st.header("4. ดูตัวอย่างข้อมูลรายตัว (ในเว็บ)")
        selected_right = st.selectbox("เลือก 'สิทธิ' เพื่อดูตัวอย่าง:", list_of_rights)
        if selected_right:
            df_detail = df_today[df_today['สิทธิ'] == selected_right]
            st.subheader(f"ตัวอย่างข้อมูลของ: {selected_right} (จำนวน {len(df_detail)} รายการ)")
            
            columns_to_show = ['วันเข้า', 'เวลาเข้า', 'HN', 'ชื่อผู้ป่วย', 'ลูกหนี้', 'เบิกได้', 'เบิกไม่ได้', 'รวม']
            existing_cols_detail = [col for col in columns_to_show if col in df_detail.columns]
            
            if 'วันเข้า' in df_detail.columns:
                df_detail_display = df_detail[existing_cols_detail].copy()
                df_detail_display['วันเข้า'] = df_detail_display['วันเข้า'].dt.strftime('%Y-%m-%d') 
                st.dataframe(df_detail_display, use_container_width=True)
            else:
                st.dataframe(df_detail[existing_cols_detail], use_container_width=True)