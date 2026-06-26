# Kiến Trúc Giao Diện (Streamlit UI Architecture)

Tài liệu này giải thích cách hoạt động của mảng Frontend (Web UI) trong hệ thống CRUD IT Job Market. Giao diện được xây dựng hoàn toàn bằng **Python (Streamlit)**, không cần viết HTML/CSS/JS thủ công.

## 1. `config.py` (Cấu Hình Lõi)
- **Biến môi trường (`os.getenv`)**: Tuyệt đối không Hardcode (viết cứng) địa chỉ IP (`HDFS_HOST`). Giúp dễ dàng mang source code sang máy tính khác, Server Linux hoặc Docker chạy trực tiếp mà không văng lỗi "File Not Found".
- **Dropdown List**: Streamlit bắt buộc Selectbox phải nhận đầu vào là mảng (List). Ép cứng các danh sách `JOB_LEVELS` (Fresher, Junior...) và `LOCATIONS` để user không gõ bậy làm rác Database.

## 2. `app.py` (Khung Xương & Điều Hướng)
- **Lazy Loading (`@st.cache_resource`)**: PySpark siêu nặng, ngốn nhiều RAM. Kỹ thuật này ép Server chỉ load Spark đúng 1 lần duy nhất lúc khởi động (Singleton). Click qua lại giữa các trang sẽ lấy thẳng từ bộ nhớ Cache ra xài -> Giao diện web mượt mà, không bị sập.
- **Sidebar Navigation**: Vẽ thanh Menu bên trái (`st.sidebar`). Dùng biến `nav = st.radio()` để bắt sự kiện click và điều hướng hiển thị nội dung từng trang.

## 3. `src/pages/dashboard.py` (Trực Quan Hóa)
- **Grid Layout (`st.columns`)**: Chia cắt màn hình thành các lưới ngang bằng nhau để nhét các thẻ thống kê KPI (Tổng Job, Công Ty, Lương Trung Bình).
- **Plotly Integration (`st.plotly_chart`)**: Nhúng biểu đồ phân tích dữ liệu tương tác cao. Kích hoạt `use_container_width=True` để biểu đồ tự động co giãn (Responsive) vừa khít với màn hình điện thoại lẫn Desktop.

## 4. `src/pages/crud_page.py` (Quản Lý Thêm/Sửa/Xóa)
- **Giao diện 1 trang (`st.tabs`)**: Gom tất cả tính năng Thêm, Sửa, Xóa vào chung 1 giao diện duy nhất thay vì tạo nhiều trang rườm rà. Bấm qua lại mượt mà, không giật lag.
- **Bộ Nhớ Tạm (`st.session_state`)**: Giải quyết bài toán phân trang (Pagination). Streamlit bị hội chứng "Stateless" (mất trí nhớ), hễ bấm nút là reset script từ đầu. Phải lưu số trang (`list_page`) vào biến `session_state` thì bấm Next Page nó mới không bị văng về trang 1.

## 5. `src/pages/backup_page.py` (Sao Lưu Dữ Liệu)
- **Tối ưu Reload (`st.form`)**: Nếu không bọc Input vào Form, User gõ 1 chữ cái hệ thống sẽ chạy lại từ đầu 1 lần. Bọc bằng `with st.form("name"):` giúp gõ chữ thoải mái, chỉ khi bấm nút "Submit" thì code mới chạy.
- **Ép tải lại trang (`st.rerun()`)**: Sau khi ấn nút tạo Backup thành công, gọi lệnh này để giao diện tự động làm mới, móc danh sách Backup vừa tạo lên màn hình ngay lập tức. Không bắt người dùng phải bấm F5 thủ công.

## 6. `src/pages/settings_page.py` (Cài Đặt Hệ Thống)
- **Loading Indicator (`st.spinner`)**: Tạo hiệu ứng vòng xoay đang tải khi bấm nút "Kiểm Tra Kết Nối HDFS/Spark". Báo hiệu cho User biết hệ thống đang rặn ngầm, xin đừng bấm bậy bạ.
- **Accordion (`st.expander`)**: Hộp thoại xổ xuống. Dùng để giấu bớt những đoạn text hướng dẫn fix lỗi dài ngoằng, trả lại sự gọn gàng cho giao diện.
