# Chi Tiết File MapReduce: YOE vs Salary Correlation (Tương Quan Kinh Nghiệm & Lương)

File xử lý: `mr_yoe_salary_correlation.py`
File kết quả đầu ra: `yoe_salary_correlation.txt` & `yoe_salary_correlation.parquet`

---

## 1. Mục Đích & Quy Trình (mr_yoe_salary_correlation.py)

File `mr_yoe_salary_correlation.py` dùng để phân tích sự tương quan giữa Số năm kinh nghiệm (Years of Experience - YOE) và Mức lương trung bình trên thị trường IT. Sử dụng framework **Apache Spark** kết hợp với **Spark SQL** và **Window Functions**.

### Các bước thực thi cốt lõi:
1. **Đọc dữ liệu**:
   - Hỗ trợ chọn nguồn dữ liệu động thông qua tham số dòng lệnh `--source` (`HDFS` hoặc `MONGODB`). Mặc định đọc từ HDFS (`hdfs://localhost:9000/project/jobs`).
   - Lọc bỏ các công việc thiếu dữ liệu lương, lương <= 0, hoặc thiếu dữ liệu số năm kinh nghiệm.

2. **Map (Phân cụm - Bucketing)**:
   - Phân loại (bucket) từng tin tuyển dụng vào 6 nhóm kinh nghiệm:
     - `00-01yr (Fresher)`
     - `02yr    (Junior)`
     - `03-04yr (Mid-level)`
     - `05-06yr (Senior)`
     - `07-09yr (Lead)`
     - `10+yr   (Expert/Mgr)`
   - Cấp mã `bucket_order` để sắp xếp dữ liệu dễ dàng.

3. **Reduce & Window Functions**:
   - **Spark SQL (Group By)**: Nhóm theo `yoe_bucket` và tính:
     - Số lượng tin tuyển dụng (`job_count`)
     - Lương Min, Max, Trung bình (`avg_salary_M`), và Trung vị (`median_salary_M`) tính bằng triệu VNĐ.
     - Số lượng kỹ năng yêu cầu trung bình (`avg_skill_count`).
   - **Window Function (LAG)**: Sử dụng hàm `LAG()` để tính toán sự chênh lệch lương (`salary_increase_M`) giữa nhóm kinh nghiệm hiện tại so với nhóm liền trước (Ví dụ: Senior tăng bao nhiêu so với Mid-level).

4. **Lưu trữ Kết Quả**:
   - Ghi định dạng bảng Text (`yoe_salary_correlation.txt`) và định dạng **Parquet** (`yoe_salary_correlation.parquet`) xuống Local.
   - Ghi dữ liệu vào **MongoDB** (`BigDataJobMarket.yoe_salary_correlation`).
   - Upload toàn bộ kết quả (TXT, Parquet) lên **HDFS** (`/project/output/`).

---

## 2. Kết Quả Thống Kê (yoe_salary_correlation.txt)

```text
========================================================================================
    TUONG QUAN NAM KINH NGHIEM (YOE) VA MUC LUONG THI TRUONG IT
========================================================================================
Nhom KN                 Jobs  AvgYOE  Min(M)  Avg(M)  Median(M)  Max(M)  AvgSkills  Tang(M)
----------------------------------------------------------------------------------------
00-01yr (Fresher)        280     1.0    10.2    21.6       19.1    76.2        4.1      N/A
02yr    (Junior)         132     2.0    11.0    33.1       31.8    95.3        4.7    +11.5
03-04yr (Mid-level)      989     3.1     1.3    33.4       31.8   127.0        4.7     +0.3
05-06yr (Senior)         573     5.1    15.9    48.3       50.0   110.5        4.6    +14.9
07-09yr (Lead)            60     7.4    19.1    51.1       53.3   127.0        5.5     +2.8
10+yr   (Expert/Mgr)      30    10.5    19.1    43.5       40.6    59.7        5.2     -7.6
========================================================================================
```

---

## 3. Nhận Xét & Đánh Giá Nhanh

Dựa trên dữ liệu thu thập được:
1. **Bước Nhảy Lương (Salary Jump)**:
   - Giai đoạn chuyển từ **Fresher lên Junior** (2 năm) chứng kiến mức tăng lương mạnh nhất: **+11.5 triệu VNĐ/tháng**.
   - Giai đoạn chuyển từ **Mid-level lên Senior** (5-6 năm) cũng là một bước nhảy vọt khổng lồ: **+14.9 triệu VNĐ/tháng**.
2. **"Bẫy" Mid-level (3-4 năm)**: Mức lương trung bình của Mid-level (~33.4 triệu VNĐ) hầu như **không tăng** so với Junior (~33.1 triệu VNĐ). Tuy nhiên, phân khúc này lại chiếm số lượng việc làm áp đảo nhất (989 jobs). Điều này cho thấy sự cạnh tranh cực kỳ gay gắt và mức lương bị cào bằng ở phân khúc này.
3. **Mức Yêu Cầu Kỹ Năng (AvgSkills)**: Nhóm Lead (7-9 năm) đòi hỏi số lượng kỹ năng trung bình cao nhất (5.5 kỹ năng) để đạt được mức lương đỉnh điểm (~51.1 triệu VNĐ/tháng).
4. **Sự Sụt Giảm Ở Nhóm 10+ Năm (Expert/Mgr)**: Thống kê cho thấy mức lương trung bình giảm (-7.6 triệu) và mức Max cũng thấp hơn. Nguyên nhân có thể do ở cấp độ này, các vị trí lương cực cao (C-level, Director) thường không được niêm yết công khai (hide salary), hoặc dữ liệu thu thập đa phần là các công việc quản lý tầm trung ở doanh nghiệp truyền thống.
