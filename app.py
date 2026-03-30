import streamlit as st
import google.generativeai as genai
import time
import zipfile
import io
import re
import math
import os  # Thêm dòng này để sửa lỗi 'os' is not defined

st.set_page_config(page_title="Veo 3 Prompt Generator VIP", page_icon="🎬", layout="wide")

st.title("🎬 Trình Tạo Prompt Veo 3 - Tự Động Hóa (VIP Pro)")
st.markdown("Quy trình: Phân tích bối cảnh -> Cắt nhỏ SRT -> Xuất prompt tiếng Anh thuần khiết cho Veo 3.")

# Cột bên trái: Nạp API Key
with st.sidebar:
    st.header("⚙️ Nạp Năng Lượng (API Key)")
    api_keys_input = st.text_area("Danh sách Google Gemini API Key:", height=150, help="Mỗi dòng 1 key.")
    api_keys = [key.strip() for key in api_keys_input.split('\n') if key.strip()]
    if api_keys:
        st.success(f"🔋 Đã nạp {len(api_keys)} API Key!")

def calculate_duration(chunk_text):
    timestamps = re.findall(r'(\d{2}):(\d{2}):(\d{2})', chunk_text)
    if len(timestamps) < 2: return 30
    def to_sec(t): return int(t[0])*3600 + int(t[1])*60 + int(t[2])
    duration = to_sec(timestamps[-1]) - to_sec(timestamps[0])
    return duration if duration > 0 else 30

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("1. Nạp Dữ Liệu")
    uploaded_files = st.file_uploader("Chọn file phụ đề .srt", type=['srt'], accept_multiple_files=True)
    st.subheader("2. Ghi chú thêm")
    video_style = st.text_area("Yêu cầu đặc biệt về style:", height=80)

with col2:
    st.subheader("3. Bảng Điều Khiển")
    if st.button("🚀 KÍCH HOẠT HỆ THỐNG AI", use_container_width=True, type="primary"):
        if not api_keys or not uploaded_files:
            st.error("❌ Vui lòng nạp đủ API Key và tải file SRT lên!")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_box = st.empty()
            zip_buffer = io.BytesIO()
            success_count = 0
            error_count = 0
            log_messages = ""
            api_call_count = 0 
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for file_idx, file in enumerate(uploaded_files):
                    file_name = file.name
                    status_text.markdown(f"**Đang xử lý:** `{file_name}`...")
                    try:
                        srt_content = file.read().decode("utf-8")
                        current_key = api_keys[(api_call_count // 19) % len(api_keys)]
                        genai.configure(api_key=current_key)
                        
                        # Dùng bản Pro để có chất lượng tốt nhất
                        model = genai.GenerativeModel('gemini-2.5-pro')
                        
                        log_messages = f"⏳ Đang phân tích tổng thể: {file_name}\n" + log_messages
                        log_box.text_area("Nhật ký:", value=log_messages, height=200)
                        
                        prompt_step_1 = f"Phân tích kịch bản sau về bối cảnh, tâm lý, ánh sáng (Tiếng Việt). Style: {video_style}\nKịch bản: {srt_content}"
                        response_step_1 = model.generate_content(prompt_step_1)
                        director_vision = response_step_1.text
                        api_call_count += 1
                        time.sleep(15) # Nghỉ 15s để tránh lỗi API Miễn phí

                        blocks = srt_content.strip().split('\n\n')
                        chunk_size = 30 
                        final_prompts = []
                        
                        for i in range(0, len(blocks), chunk_size):
                            chunk_text = '\n\n'.join(blocks[i:i+chunk_size])
                            duration = calculate_duration(chunk_text)
                            target_prompts = math.ceil(duration / 6.5)
                            
                            prompt_step_2 = f"Director Vision: {director_vision}\n\nWrite EXACTLY {target_prompts} English video prompts for Veo 3 for this subtitle chunk. Each prompt on a new line. No numbers, no explanation, ONLY prompt text.\n\nSubtitles:\n{chunk_text}"
                            response_step_2 = model.generate_content(prompt_step_2)
                            final_prompts.append(response_step_2.text.strip())
                            api_call_count += 1
                            time.sleep(15) # Nghỉ 15s để tránh lỗi API Miễn phí
                        
                        full_result = '\n'.join(final_prompts)
                        txt_filename = file_name.replace(".srt", "_veo3_prompts.txt")
                        zip_file.writestr(txt_filename, full_result)
                        success_count += 1
                        log_messages = f"✅ Xong: {file_name}\n" + log_messages
                    except Exception as e:
                        error_count += 1
                        log_messages = f"❌ Lỗi ở {file_name}: {str(e)}\n" + log_messages
                    
                    progress_bar.progress((file_idx + 1) / len(uploaded_files))
                    log_box.text_area("Nhật ký:", value=log_messages, height=200)

            status_text.success(f"🎉 Hoàn thành! Thành công: {success_count} | Lỗi: {error_count}.")
            st.download_button(label="📦 TẢI VỀ KẾT QUẢ (.ZIP)", data=zip_buffer.getvalue(), file_name="Veo3_Result.zip", mime="application/zip", type="primary")
