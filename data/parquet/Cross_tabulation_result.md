# Chi Tiết File MapReduce: Cross-Tabulation (Phân Tích Chéo Lương Theo Kỹ Năng & Địa Điểm)

File xử lý: `mr_cross_tabulation.py`
File kết quả đầu ra: `cross_tabulation_result.txt` & `cross_tabulation_result.parquet`

---

## 1. Mục Đích & Quy Trình (mr_cross_tabulation.py)

File `mr_cross_tabulation.py` chịu trách nhiệm phân tích mức lương trung bình của các kỹ năng IT tại 3 trung tâm công nghệ lớn (Hồ Chí Minh, Hà Nội, Đà Nẵng). Sử dụng mô hình **MapReduce** và kỹ thuật **Cross-Tabulation (Pivot)** qua framework **Apache Spark**.

### Các bước thực thi cốt lõi:
1. **Đọc dữ liệu (HDFS)**:
   - Dữ liệu thô được đọc trực tiếp từ HDFS: `hdfs://localhost:9000/project/jobs`.
   - Ép kiểu cột lương (`salary_final_vnd`) sang dạng số thực (Double).

2. **Tiền xử lý (Map & Filter)**:
   - Chuẩn hóa cột địa điểm (`location_clean`) về 3 trung tâm chính: HCM, HN, DN.
   - Loại bỏ các dòng thiếu thông tin kỹ năng hoặc lương.
   - **Explode**: Tách chuỗi kỹ năng (skills) thành nhiều dòng độc lập cho mỗi kỹ năng.

3. **MapReduce (Pivot & Aggregation)**:
   - **Group By**: Nhóm theo từng kỹ năng (`skill`).
   - **Pivot**: Chuyển đổi 3 địa điểm (HCM, HN, DN) thành các cột riêng biệt (Cross-Tabulation).
   - **Aggregate (Average)**: Tính mức lương trung bình (quy đổi ra triệu VNĐ) cho từng kỹ năng tại mỗi địa điểm.
   - **Sort**: Tính tổng trung bình 3 miền (`total_avg`) và sắp xếp giảm dần, lấy top 30 kỹ năng có mức lương trung bình cao nhất.

4. **Lưu trữ Kết Quả**:
   - Ghi kết quả dưới dạng bảng format text (`cross_tabulation_result.txt`) chuẩn UTF-8 xuống Local (thư mục `data/parquet`).
   - Ghi kết quả định dạng **Parquet** (`cross_tabulation_result.parquet`) xuống Local để lưu trữ tối ưu dữ liệu phân tích.
   - Ghi dữ liệu trực tiếp vào **MongoDB** (`BigDataJobMarket.cross_tabulation_result`).
   - Tự động thực thi lệnh Command Line (`hdfs dfs -put`) để upload cả file text và file Parquet lên **HDFS** (`/project/output/`).

---

## 2. Kết Quả Thống Kê (cross_tabulation_result.txt)

Bảng kết quả bên dưới thể hiện chi tiết mức lương trung bình (triệu VNĐ) theo từng kỹ năng ở 3 khu vực chính:

```text
=== CROSS-TABULATION: AVERAGE SALARY (M) BY SKILL & LOCATION ===

SKILL                | HCM        | HN         | DN        
-------------------------------------------------------
technical architecture | 127.0      | 59.7       | 0.0       
technology management | 101.6      | 54.8       | 0.0       
golang               | 42.8       | 34.1       | 69.9      
uiux                 | 40.6       | 35.4       | 69.9      
postgresql           | 38.9       | 37.0       | 69.9      
performance management | 85.4       | 59.7       | 0.0       
brse                 | 40.6       | 50.0       | 54.0      
japanese ( n1 or n2) | 40.6       | 50.0       | 54.0      
typescript           | 36.0       | 35.7       | 69.9      
phân tích yêu cầu    | 40.6       | 63.5       | 35.6      
software architecture | 42.5       | 59.0       | 38.1      
team management      | 50.6       | 51.1       | 35.6      
reactjs              | 38.8       | 34.2       | 61.9      
leadership           | 55.3       | 51.6       | 27.3      
aws                  | 45.5       | 40.8       | 44.8      
azure                | 41.2       | 35.8       | 54.0      
redux                | 37.5       | 38.7       | 54.0      
it product           | 53.3       | 76.2       | 0.0       
japanese             | 41.9       | 47.7       | 39.5      
english              | 41.9       | 41.9       | 45.0      
giao tiếp tiếng nhật bản | 31.8       | 59.7       | 35.6      
databases            | 127.0      | 0.0        | 0.0       
change management    | 66.2       | 59.7       | 0.0       
ai                   | 39.7       | 36.3       | 48.7      
system architecture  | 51.1       | 37.6       | 35.6      
api development      | 56.5       | 31.8       | 35.6      
java                 | 37.9       | 37.8       | 47.8      
product manager      | 53.3       | 70.0       | 0.0       
collaboration        | 40.6       | 47.1       | 35.6      
mlops                | 42.0       | 43.1       | 38.1      
```

### Nhận Xét & Đánh Giá Nhanh:
Dựa trên toàn bộ kết quả phân tích:
1. **Các Vị Trí Cấp Cao (Management & Architecture)**: Mang lại mức lương cao vượt trội, đặc biệt tại TP.Hồ Chí Minh. Điển hình như `technical architecture` và `databases` đạt trung bình lên tới ~127 triệu VNĐ/tháng, gấp đôi so với Hà Nội (~59.7 triệu VNĐ). Các vị trí quản lý sản phẩm như `it product`, `product manager` lại có xu hướng trả cao hơn ở Hà Nội (~70 - 76 triệu VNĐ).
2. **Sự Đột Phá Tại Đà Nẵng**: Một số công nghệ như `golang`, `uiux`, `postgresql`, `typescript`, và `reactjs` ghi nhận mức trung bình tại Đà Nẵng rất cao (61 - 69.9 triệu VNĐ), vượt mặt cả HCM và HN.
3. **Nhóm Kỹ Năng Ngoại Ngữ & Cầu Nối (BRSE, Japanese, English)**: Phân bổ lương khá ổn định giữa 3 miền. Tuy nhiên, Hà Nội và Đà Nẵng có xu hướng trả lương cho vị trí BRSE hoặc tiếng Nhật nhỉnh hơn đôi chút (~50 - 54 triệu VNĐ) so với TP.HCM (~40.6 - 41.9 triệu VNĐ).
4. **Hạ Tầng & Đám Mây (Cloud/DevOps/AI)**: Các kỹ năng như `aws`, `azure`, `ai`, `mlops` có mức lương rất đồng đều ở cả 3 khu vực (khoảng 35 - 54 triệu VNĐ), cho thấy nhu cầu chung khá ổn định và có mặt bằng chung trên toàn quốc.
