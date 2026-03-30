import streamlit as st
import google.generativeai as genai
import time
import zipfile
import io
import re
import math
import os

st.set_page_config(page_title="Veo 3 Prompt Generator VIP", page_icon="🎬", layout="wide")

st.title("🎬 Trình Tạo Prompt Veo 3 - Tự Động Hóa (Smart API)")

with st.sidebar:
    st.header("⚙️ Nạp Năng Lượng (API Key)")
    api_keys_input = st.text_area("Danh sách Gemini API Key (Mỗi dòng 1 key):", height=150)
    api_keys = [key.strip() for key in api_keys_input.split('\n') if key.strip()]
    if api_keys:
        st.success(f"🔋 Đã nạp {len(api_keys)} API Key!")

def calculate_duration(chunk_text):
    timestamps = re.findall(r'(\d{2}):(\d{2}):(\d{2})', chunk_text)
    if len(timestamps) < 2: return 30
    def to_sec(t): return int(t[0])*3600 + int(t[1])*60 + int(t[2])
    duration = to_sec(timestamps[-1]) - to_sec(timestamps[0])
    return duration if duration > 0 else 30

# HÀM GỌI AI THÔNG MINH - TỰ ĐỘNG CHUYỂN KEY KHI HẾT LƯỢT
def call_gemini_smart(prompt, current_keys, model_name='gemini-1.5-pro'):
    for i in range(len(current_keys)):
        key = current_keys[0] # Luôn lấy key đầu tiên trong hàng đợi
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text, current_keys
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "quota" in error_msg:
                st.warning(f"⚠️ Key hiện tại đã hết lượt hoặc quá nhanh. Đang đổi sang key dự phòng...")
                current_keys.pop(0) # Loại bỏ key đã hết lượt
                if not current_keys:
                    raise Exception("🛑 TẤT CẢ API KEY ĐÃ HẾT LƯỢT DÙNG TRONG NGÀY!")
                time.sleep(2) # Nghỉ 2 giây trước khi thử key mới
            else:
                raise e # Nếu là lỗi khác thì dừng lại báo lỗi
    return None, current_keys

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("1. Nạp Dữ Liệu")
    uploaded_files = st.file_uploader("Chọn file phụ đề .srt", type=['srt'], accept_multiple_files=True)
    video_style = st.text_area("Yêu cầu đặc biệt (Gợi ý: cinematic, horror, psychology...):", height=80)

with col2:
    st.subheader("2. Bảng Điều Khiển")
    if st.button("🚀 KÍCH HOẠT HỆ THỐNG AI", use_container_width=True, type="primary"):
        if not api_keys or not uploaded_files:
            st.error("❌ Vui lòng nạp đủ API Key và tải file SRT lên!")
        else:
            working_keys = api_keys.copy()
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_box = st.empty()
            zip_buffer = io.BytesIO()
            log_messages = ""
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for file_idx, file in enumerate(uploaded_files):
                    try:
                        srt_content = file.read().decode("utf-8")
                        log_messages = f"⏳ Đang xử lý: {file.name}\n" + log_messages
                        log_box.text_area("Nhật ký:", value=log_messages, height=200)
                        
                        # Bước 1: Phân tích bối cảnh
                        p1 = f"Phân tích kịch bản sau về bối cảnh, tâm lý, ánh sáng. Style: {video_style}\nKịch bản: {srt_content}"
                        director_vision, working_keys = call_gemini_smart(p1, working_keys)
                        time.sleep(15)

                        # Bước 2: Tạo prompt chi tiết
                        blocks = srt_content.strip().split('\n\n')
                        chunk_size = 25 
                        final_prompts = []
                        
                        for i in range(0, len(blocks), chunk_size):
                            chunk_text = '\n\n'.join(blocks[i:i+chunk_size])
                            duration = calculate_duration(chunk_text)
                            target_prompts = math.ceil(duration / 6.5)
                            
                            p2 = f"Director Vision: {director_vision}\n\nWrite EXACTLY {target_prompts} English video prompts for Veo 3. One per line. Only text.\n\nSubtitles:\n{chunk_text}"
                            p_result, working_keys = call_gemini_smart(p2, working_keys)
                            final_prompts.append(p_result)
                            time.sleep(15)
                        
                        zip_file.writestr(file.name.replace(".srt", "_prompts.txt"), '\n'.join(final_prompts))
                        log_messages = f"✅ Thành công: {file.name}\n" + log_messages
                    except Exception as e:
                        log_messages = f"❌ Lỗi: {str(e)}\n" + log_messages
                    
                    progress_bar.progress((file_idx + 1) / len(uploaded_files))
                    log_box.text_area("Nhật ký:", value=log_messages, height=200)

            st.success("🎉 Hoàn tất quy trình!")
            st.download_button(label="📦 TẢI VỀ KẾT QUẢ (.ZIP)", data=zip_buffer.getvalue(), file_name="Veo3_Prompts.zip", mime="application/zip")
