# ไฟล์: processing.py
import pandas as pd
import numpy as np

# เราจะห่อโค้ดทั้งหมดไว้ในฟังก์ชัน
# @st.cache_data (นี่คือ "ตัวเร่งความเร็ว" ของ Streamlit)
# บอกให้ Streamlit จำผลลัพธ์ไว้ ไม่ต้องโหลดไฟล์ CSV ใหม่ทุกครั้งที่คลิก
import streamlit as st

@st.cache_data
def load_and_process_data(uploaded_file): # <--- รับ File Object
    """
    ฟังก์ชันนี้จะโหลดและประมวลผลข้อมูลดิบทั้งหมด...
    """
    
    # --- 1. โหลดข้อมูล (เหมือนเดิม) ---
    try:
        df = pd.read_csv(uploaded_file, encoding='tis-620', dtype=str) # <--- ใช้ File Object
    except Exception as e:
        st.error(f"Error: ไม่สามารถอ่านไฟล์ CSV ได้: {e}")
        return pd.DataFrame()

    # --- 2. Rename คอลัมน์ (เหมือนเดิม) ---
    df = df.rename(columns={
        'Unnamed: 1': 'เวลาเข้า',
        'Unnamed: 3': 'เวลาออก'
    })

    # --- 3. การจัดการวันที่และเวลา (เหมือนเดิม) ---
    df['DateTimeIn_str'] = df['วันเข้า'].astype(str) + ' ' + df['เวลาเข้า'].astype(str)
    df['DateTimeOut_str'] = df['วันออก'].astype(str) + ' ' + df['เวลาออก'].astype(str)

    df['DateTimeIn'] = pd.to_datetime(df['DateTimeIn_str'], dayfirst=True, errors='coerce')
    df['DateTimeOut'] = pd.to_datetime(df['DateTimeOut_str'], dayfirst=True, errors='coerce')

    df = df.dropna(subset=['DateTimeIn']) # ลบแถวที่วันที่พัง

    # *** สำคัญ: เราจะใช้ 'วันเข้า' ที่เป็น Date Object จริงๆ เพื่อกรอง ***
    # เขียนทับคอลัมน์เดิมด้วยข้อมูลชนิด Date/Time ที่ถูกต้อง
    df['วันเข้า'] = df['DateTimeIn'].dt.normalize()
    df['เวลาเข้า'] = df['DateTimeIn'].dt.time
    df['วันออก'] = df['DateTimeOut'].dt.normalize()
    df['เวลาออก'] = df['DateTimeOut'].dt.time

    # --- 4. การแปลงข้อมูลและการสร้างคอลัมน์ใหม่ (เหมือนเดิม) ---
   # 4.1. กำหนดคอลัมน์ตัวเลขดิบจาก CSV (รวม 'เบิกได้' ต้นฉบับไปด้วย)
    raw_numeric_cols = ['รวม', 'เบิกได้', 'เบิกไม่ได้']
    
    for col in raw_numeric_cols:
        if col in df.columns:
            # 4.2. ทำความสะอาด Text: ลบ Commas, ลบ Space
            # เราจะ .astype(str) ก่อนเพื่อให้แน่ใจว่าใช้ .str ได้
            df[col] = df[col].astype(str).str.replace(',', '', regex=False)
            df[col] = df[col].astype(str).str.strip()
            # (ถ้ามีสัญลักษณ์อื่น เช่น '฿' ให้เพิ่ม .str.replace('฿', '') เข้าไป)
            
            # 4.3. แปลงเป็นตัวเลข (ถ้าแปลงไม่ได้ -> 0)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            st.warning(f"คำเตือน: ไม่พบคอลัมน์ตัวเลขดิบ '{col}'")

    # 4.4. สร้างคอลัมน์ใหม่ (ตอนนี้ 'รวม' เป็นตัวเลขที่ถูกต้องแล้ว)
    df['ลูกหนี้'] = np.where(df['Payer - Office'] == 'ชำระเงินเอง', 0, df['รวม'])
    df['เบิกได้.1'] = np.where(df['Payer - Office'] == 'ชำระเงินเอง', df['รวม'], 0)
    
    # 4.5. เพิ่ม 'จำนวนคน'
    df['จำนวนคน'] = 1

    # 4.6. ลบคอลัมน์ 'เบิกได้' เดิม และเปลี่ยนชื่อ 'เบิกได้.1'
    # (เราลบ 'เบิกได้' เดิมทิ้ง เพราะเราสร้าง 'เบิกได้.1' ขึ้นมาใหม่ตามเงื่อนไข)
    if 'เบิกได้' in df.columns:
        df = df.drop(columns=['เบิกได้'])
    df = df.rename(columns={'เบิกได้.1': 'เบิกได้'}) # 'เบิกได้.1' คืออันใหม่ที่เราคำนวณ

    if 'ICD-10' in df.columns:
        df = df.drop(columns=['ICD-10'])

    # 4.7. ไม่จำเป็นต้องมี final_numeric_cols loop แล้ว
    # เพราะ 'ลูกหนี้', 'เบิกได้' (ใหม่), 'เบิกไม่ได้', 'รวม' เป็นตัวเลขที่ถูกต้องแล้ว

    # 4.8. เปลี่ยนประเภท 'จำนวนคน' และจัดการ 'สิทธิ'
    df['จำนวนคน'] = df['จำนวนคน'].astype(int)
    df['สิทธิ'] = df['สิทธิ'].fillna('ไม่มีใบแจ้งหนี้').replace('', 'ไม่มีใบแจ้งหนี้')

    # --- 5. จัดเรียงคอลัมน์สุดท้าย (เหมือนเดิม) ---
    final_columns_order = [
        "วันเข้า", "เวลาเข้า", "วันออก", "เวลาออก", "HN", "VN", "AN",
        "เลขที่เอกสาร", "ชื่อผู้ป่วย", "PID", "สิทธิ", "Payer - Office",
        "จำนวนคน", "ลูกหนี้", "เบิกได้", "เบิกไม่ได้", "รวม"
    ]
    
    # เราจะเก็บคอลัมน์ที่จำเป็นอื่นๆ ไว้ด้วย เผื่อใช้ในตาราง Detail
    # เอาคอลัมน์ดั้งเดิม 'วันเข้า' (ที่เป็น text) ออกไปก่อน
    if 'วันเข้า' in final_columns_order: final_columns_order.remove('วันเข้า')
    
    # ใช้ df['วันเข้า'] (Date Object) ที่เราสร้างใหม่
    final_columns_order = ['วันเข้า'] + final_columns_order 
    
    existing_cols = [col for col in final_columns_order if col in df.columns]
    
    # *** จุดสำคัญ: เราจะ return DataFrame ที่ประมวลผลแล้ว ***
    return df[existing_cols]

# ฟังก์ชันสำหรับแปลง DataFrame เป็น CSV (เพื่อปุ่มดาวน์โหลด)
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')