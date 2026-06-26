# Chi Tiết File MapReduce: Phân Tích Địa Điểm Tuyển Dụng (Location Result)

File xử lý: `mr_location.py`
File kết quả đầu ra: `location_result.txt`

---

## 1. Mục Đích & Quy Trình (mr_location.py)

File `mr_location.py`  chịu trách nhiệm phân tích sự phân bổ số lượng việc làm IT trên khắp các tỉnh thành/hình thức làm việc. Mã nguồn ứng dụng mô hình **MapReduce** thông qua framework **Apache Spark**.

### Các bước thực thi cốt lõi:
1. **Khởi tạo Spark Session**:
   - Khởi tạo `SparkSession` với tên `MR_Location`.
   - Cấu hình số partition cho quá trình shuffle là 4 (`spark.sql.shuffle.partitions = 4`).

2. **Đọc dữ liệu (HDFS)**:
   - Dữ liệu thô (đã qua làm sạch) được đọc trực tiếp từ Hadoop Distributed File System (HDFS): `hdfs://localhost:9000/jobs_data`.

3. **MapReduce (GroupBy & Count)**:
   - **Map**: Chọn trường `location_clean` làm khóa.
   - **Reduce (`groupBy`)**: Nhóm toàn bộ các tin tuyển dụng có cùng `location_clean`.
   - **Aggregate (`count`)**: Tính tổng số lượng tin tuyển dụng cho mỗi nhóm.
   - **Sort**: Sắp xếp kết quả đếm giảm dần (`ascending=False`).

4. **Lưu trữ Kết Quả**:
   - Ghi kết quả dưới dạng bảng format text (`location_result.txt`) chuẩn UTF-8 xuống Local (thư mục `data/parquet`).
   - Ghi dữ liệu trực tiếp vào **MongoDB** (`BigDataJobMarket.location_result`).
   - Tự động thực thi lệnh Command Line (`hdfs dfs -put`) để upload file text kết quả lên **HDFS** (`/project/output/`).

---

## 2. Kết Quả Thống Kê (location_result.txt)

Sau khi chạy xong mã nguồn, bảng kết quả bên dưới thể hiện chi tiết phân bổ nhu cầu nhân lực trên thị trường IT, trích xuất nguyên bản từ `location_result.txt`:

```text
location_clean                                 count
-----------------------------------------------------
Hồ Chí Minh                                     1007
Hà Nội                                           964
Đà Nẵng                                           31
Hồ Chí Minh, Hà Nội                               31
Hồ Chí Minh, Đà Nẵng                              15
Khác                                               6
Hồ Chí Minh, Hà Nội, Remote                        3
Hồ Chí Minh, Remote                                2
Remote                                             2
Hà Nội, Đà Nẵng                                    1
Hà Nội, Đà Nẵng, Remote                            1
Hồ Chí Minh, Hà Nội, Đà Nẵng, Remote               1
```

### 💡 Phân Tích Insight Tóm Tắt:
- **Thành phố Hồ Chí Minh** dẫn đầu thị trường với số lượng job vượt mốc 1000 (1007 tin), chiếm ưu thế rõ rệt nhưng khoảng cách không quá lớn so với **Hà Nội** (964 tin).
- **Đà Nẵng** duy trì vị thế trung tâm thứ ba với 31 tin thuần tuý.
- Các tin tuyển dụng kết hợp **nhiều địa điểm** (VD: Hồ Chí Minh, Hà Nội) hoặc kết hợp làm việc **Remote** xuất hiện nhưng chiếm tỷ trọng khá nhỏ, cho thấy phần lớn các vị trí vẫn ưu tiên gắn cứng với một trụ sở chính thức.
