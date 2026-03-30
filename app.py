import streamlit as st
import google.generativeai as genai
import time
import zipfile
import io
import re
import math

st.set_page_config(
    page_title="Veo 3 Prompt Generator VIP", page_icon="🎬", layout="wide"
)

st.title("🎬 Trình Tạo Prompt Veo 3 - Tự Động Hóa (VIP Pro)")
st.markdown(
    "Quy trình 2 bước: AI tự phân tích bối cảnh toàn bài -> Cắt nhỏ SRT -> Tính toán thời lượng -> Xuất prompt tiếng Anh thuần khiết (1 prompt / 6.5 giây)."
)

# Cột bên trái: Nạp API Key
with st.sidebar:
    st.header("⚙️ Nạp Năng Lượng (API Key)")
    api_keys_input = st.text_area(
        "Danh sách Google Gemini API Key:",
        height=150,
        help="Mỗi dòng 1 key. Đổi key sau mỗi 19 lần gọi.",
    )
    api_keys = [key.strip() for key in api_keys_input.split("\n") if key.strip()]
    if api_keys:
        st.success(f"🔋 Đã nạp {len(api_keys)} API Key!")


# Hàm tính toán thời lượng của 1 cụm SRT (giây)
def calculate_duration(chunk_text):
    timestamps = re.findall(r"(\d{2}):(\d{2}):(\d{2})", chunk_text)
    if len(timestamps) < 2:
        return 30  # Mặc định 30s nếu lỗi format

    def to_sec(t):
        return int(t[0]) * 3600 + int(t[1]) * 60 + int(t[2])

    duration = to_sec(timestamps[-1]) - to_sec(timestamps[0])
    return duration if duration > 0 else 30


col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("1. Nạp Dữ Liệu")
    uploaded_files = st.file_uploader(
        "Chọn file phụ đề .srt", type=["srt"], accept_multiple_files=True
    )

    st.subheader("2. Ghi chú thêm (Tùy chọn)")
    video_style = st.text_area(
        "Bạn có yêu cầu gì đặc biệt thêm không? (Để trống cũng được vì AI sẽ tự phân tích):",
        height=80,
    )

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
            api_call_count = 0  # Đếm số lần gọi API để xoay vòng

            with zipfile.ZipFile(
                zip_buffer, "a", zipfile.ZIP_DEFLATED, False
            ) as zip_file:
                for file_idx, file in enumerate(uploaded_files):
                    file_name = file.name
                    status_text.markdown(f"**Đang xử lý:** `{file_name}`...")

                    try:
                        srt_content = file.read().decode("utf-8")

                        # Cấu hình API Key xoay vòng
                        current_key = api_keys[(api_call_count // 19) % len(api_keys)]
                        genai.configure(api_key=current_key)
                        model = genai.GenerativeModel('gemini-2.5-flash')

                        # --- BƯỚC 1: PHÂN TÍCH TOÀN CẢNH ---
                        log_messages = (
                            f"⏳ Đang phân tích kịch bản tổng thể: {file_name}\n"
                            + log_messages
                        )
                        log_box.text_area("Nhật ký:", value=log_messages, height=200)

                        prompt_step_1 = f"""Bạn là Đạo diễn điện ảnh và Chuyên gia tâm lý. Hãy đọc toàn bộ kịch bản phụ đề sau.
Hãy phân tích cực kỳ ngắn gọn (bằng tiếng Việt) về: 1. Bối cảnh không gian. 2. Tâm lý chủ đạo. 3. Màu sắc & Ánh sáng.
Ghi chú thêm từ người dùng: {video_style}
Kịch bản:
{srt_content}"""

                        response_step_1 = model.generate_content(prompt_step_1)
                        director_vision = response_step_1.text
                        api_call_count += 1
                        time.sleep(2)  # Nghỉ lấy hơi

                        # --- BƯỚC 2: CẮT CỤM VÀ TẠO PROMPT ---
                        blocks = srt_content.strip().split("\n\n")
                        chunk_size = 40  # Khoảng 40 block thoại cho 1 cụm (~3 phút)
                        final_prompts = []

                        for i in range(0, len(blocks), chunk_size):
                            chunk_blocks = blocks[i : i + chunk_size]
                            chunk_text = "\n\n".join(chunk_blocks)

                            # Tính toán số lượng prompt cần thiết (1 prompt / 6.5s)
                            duration = calculate_duration(chunk_text)
                            target_prompts = math.ceil(duration / 6.5)
                            if target_prompts < 1:
                                target_prompts = 1

                            # Xoay vòng API nếu cần thiết giữa các cụm
                            current_key = api_keys[
                                (api_call_count // 19) % len(api_keys)
                            ]
                            genai.configure(api_key=current_key)

                            prompt_step_2 = f"""Đây là Bản Chỉ Đạo Nghệ Thuật chung cho toàn bộ video:
{director_vision}

Dựa vào bản chỉ đạo trên, hãy đọc cụm phụ đề sau và viết các lệnh (prompt) tạo video cho Veo 3.
YÊU CẦU TỐI THƯỢNG:
1. Bạn PHẢI trả về chính xác {target_prompts} dòng. Mỗi dòng là 1 prompt cảnh quay.
2. Chỉ dùng TIẾNG ANH.
3. Tuyệt đối KHÔNG có tiêu đề, KHÔNG đánh số thứ tự, KHÔNG giải thích, KHÔNG có dấu gạch đầu dòng. CHỈ LÀ PROMPT THUẦN KHIẾT.

Cụm phụ đề:
{chunk_text}"""

                            response_step_2 = model.generate_content(prompt_step_2)
                            final_prompts.append(response_step_2.text.strip())
                            api_call_count += 1
                            time.sleep(2)  # Chống spam API

                        # --- HOÀN THÀNH FILE ---
                        # Lưu kết quả vào file txt
                        full_result = "\n".join(final_prompts)
                        # Dọn dẹp các dòng trống lặp lại
                        full_result = os.linesep.join(
                            [s for s in full_result.splitlines() if s]
                        )

                        txt_filename = file_name.replace(".srt", "_veo3_prompts.txt")
                        zip_file.writestr(txt_filename, full_result)

                        success_count += 1
                        log_messages = (
                            f"✅ Xong: {file_name} (Đã tạo {len(full_result.splitlines())} prompts)\n"
                            + log_messages
                        )

                    except Exception as e:
                        error_count += 1
                        log_messages = (
                            f"❌ Lỗi ở {file_name}: {str(e)}\n" + log_messages
                        )

                    progress_bar.progress((file_idx + 1) / len(uploaded_files))
                    log_box.text_area("Nhật ký:", value=log_messages, height=200)

            status_text.success(
                f"🎉 Hoàn thành! Thành công: {success_count} | Lỗi: {error_count}."
            )
            st.download_button(
                label="📦 TẢI VỀ KẾT QUẢ (.ZIP)",
                data=zip_buffer.getvalue(),
                file_name="Veo3_Prompts_Result.zip",
                mime="application/zip",
                type="primary",
            )
