# 🕷️ ITviec Job Crawler

Script `itviec.py` tự động cào dữ liệu việc làm IT từ [itviec.com](https://itviec.com), trích xuất thông tin có cấu trúc và lưu vào CSV.

---

## 📋 Mục lục

- [Tổng quan Pipeline](#-tổng-quan-pipeline)
- [Kiến trúc](#-kiến-trúc)
- [Cài đặt](#-cài-đặt)
- [Cấu hình](#-cấu-hình)
- [Chi tiết từng bước](#-chi-tiết-từng-bước)
- [Đầu ra](#-đầu-ra)
- [Luồng dữ liệu](#-luồng-dữ-liệu)

---

## 🔄 Tổng quan Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                        PIPELINE CÀO DỮ LIỆU                    │
└─────────────────────────────────────────────────────────────────┘

  [BƯỚC 1] Khởi động & Khôi phục
       │
       ├── Kiểm tra autosave.csv (tiếp tục phiên cũ?)
       ├── Thử khôi phục session từ cookies đã lưu
       └── Nếu không có cookies → Mở trình duyệt đăng nhập thủ công
       │
       ▼
  [BƯỚC 2] Thu thập URL (URL Collection)
       │
       ├── Duyệt qua 18 truy vấn tìm kiếm:
       │    "" (ALL), developer, engineer, data, ai, devops,
       │    tester, frontend, backend, fullstack, mobile,
       │    product, manager, architect, python, java, sql, security
       │
       ├── Mỗi truy vấn → Selenium mở trang danh sách
       │    ├── Cuộn trang tự động (lazy-loading)
       │    ├── Click nút "Xem thêm" nếu có
       │    └── Trích xuất tất cả URL /it-jobs/ trên trang
       │
       ├── Dự phòng: requests HTML nếu Selenium thiếu URL
       └── Cào nhanh (quick_crawl) ngay khi tìm được URL → ghi autosave
       │
       ▼
  [BƯỚC 3] Cào chi tiết song song (Parallel Crawl)
       │
       ├── ThreadPoolExecutor (MAX_WORKERS=5 luồng đồng thời)
       │
       ├── Mỗi luồng xử lý 1 URL:
       │    ├── [Ưu tiên 1] requests.get → parse JSON-LD JobPosting
       │    ├── [Ưu tiên 2] Selenium render nếu thiếu JSON-LD
       │    └── Bỏ qua nếu trang chết (404 / Oops)
       │
       └── Tự lưu (autosave) sau mỗi 5 việc làm thành công
       │
       ▼
  [BƯỚC 4] Trích xuất & Chuẩn hóa
       │
       ├── Tiêu đề    ← JSON-LD title / <h1>
       ├── Công ty    ← hiringOrganization.name
       ├── Lương      ← DOM metadata → salary box → JSON-LD → regex fallback
       ├── Địa điểm   ← jobLocation → CITY_MAP (HN/HCM/DN) → fallback regex
       ├── Mô tả      ← jobposting.description → lọc marketing/noise
       └── Kỹ năng    ← skills field → fallback quét KNOWN_SKILLS
       │
       ▼
  [BƯỚC 5] Lưu kết quả cuối
       │
       ├── Loại bỏ trùng lặp theo URL
       ├── Làm sạch ký tự xuống dòng (1 job = 1 dòng CSV)
       └── Ghi hybrid_jobs_fixed.csv (UTF-8 BOM)
```

---

## 🏗️ Kiến trúc

```
itviec_job/
├── itviec.py              # Script chính
├── autosave.csv           # Lưu tạm - tự tạo khi chạy
├── hybrid_jobs_fixed.csv  # Kết quả cuối - tự tạo khi chạy
└── itviec_cookies.json    # Cookies phiên đăng nhập - tự tạo
```

### Thành phần chính

| Module / Hàm | Vai trò |
|---|---|
| `main()` | Điểm khởi đầu, điều phối toàn bộ pipeline |
| `collect_job_urls_itviec()` | Thu thập URL qua nhiều truy vấn |
| `get_job_urls_itviec()` | Cào danh sách 1 truy vấn, nhiều trang |
| `crawl_job()` | Cào chi tiết 1 URL việc làm |
| `quick_crawl()` | Cào nhanh chỉ dùng requests (không Selenium) |
| `fetch_page_selenium()` | Tải trang bằng Selenium (JS render) |
| `fetch_page_requests()` | Tải trang bằng requests (HTML tĩnh) |
| `normalize_salary()` | Chuẩn hóa chuỗi lương (VND/USD/Triệu) |
| `normalize_location()` | Ánh xạ địa điểm → mã thành phố |
| `normalize_skills()` | Trích xuất kỹ năng từ text |
| `extract_description()` | Làm sạch mô tả, loại marketing noise |
| `autosave_now()` | Ghi CSV tạm nguyên tử |
| `manual_login_and_export()` | Đăng nhập thủ công qua Selenium |

---

## ⚙️ Cài đặt

### Yêu cầu

- Python 3.10+
- Google Chrome (đã cài đặt)
- ChromeDriver tương thích (tự động nhận diện phiên bản)

### Cài thư viện

```bash
pip install pandas requests beautifulsoup4 selenium
```

---

## 🔧 Cấu hình

Chỉnh sửa các hằng số ở đầu file `itviec.py`:

| Hằng số | Mặc định | Mô tả |
|---|---|---|
| `TARGET_JOB_URLS` | `2000` | Số URL mục tiêu cần thu thập |
| `MAX_WORKERS` | `5` | Số luồng cào song song |
| `LISTING_PAGES` | `20` | Số trang mỗi truy vấn tìm kiếm |
| `ALL_MAX_LISTING_PAGES` | `45` | Số trang tối đa cho truy vấn "ALL" |
| `AUTOSAVE_INTERVAL` | `5` | Tự lưu sau mỗi N việc làm thành công |
| `AUTOSAVE_PATH` | `autosave.csv` | Đường dẫn file tự lưu |
| `FINAL_CSV` | `hybrid_jobs_fixed.csv` | Đường dẫn file kết quả cuối |

---

## 📖 Chi tiết từng bước

### Bước 1 – Khởi động & Xác thực

Script kiểm tra xem có phiên cào trước chưa:
- Nếu `autosave.csv` có dữ liệu → tiếp tục từ chỗ dừng, bỏ qua truy vấn "ALL"
- Thử nạp cookies từ `itviec_cookies.json` để tránh đăng nhập lại
- Nếu cookies không hợp lệ → mở Chrome, chờ người dùng đăng nhập → tự động phát hiện khi đăng nhập xong

### Bước 2 – Thu thập URL

Hàm `collect_job_urls_itviec()` duyệt tuần tự qua `LISTING_QUERIES`. Với mỗi truy vấn:

1. `get_job_urls_itviec(query, pages)` mở từng trang danh sách
2. Selenium cuộn xuống cuối, click "load more" nếu có
3. `extract_listing_job_urls()` trích URL `/it-jobs/` từ tất cả anchor, data-href, onclick handler
4. Nếu Selenium cho < 10 URL → dự phòng bằng `requests.get`
5. Ngay sau mỗi trang → `quick_crawl()` cào nhanh bằng requests để điền autosave
6. Dừng sớm nếu 3 trang liên tiếp rỗng (đã hết trang)

### Bước 3 – Cào song song

```python
with ThreadPoolExecutor(max_workers=5) as ex:
    futures = {ex.submit(crawl_job, url): url for url in unique_urls}
```

Mỗi luồng worker có **Selenium driver riêng** (thread-local), tránh xung đột.

Chiến lược trong `crawl_job()`:
1. **requests** → parse `<script type="application/ld+json">` → JobPosting schema
2. Nếu không có JSON-LD → **Selenium** render rồi parse lại
3. Nếu vẫn không có → bỏ qua (tính vào errors)

### Bước 4 – Chuẩn hóa lương

Thứ tự ưu tiên:
```
data-jobs-save-data-layer-value (DOM metadata)
    → .salary.text-success-color (CSS selector)
        → baseSalary (JSON-LD)
            → regex fallback (quét toàn trang)
```

Xử lý các định dạng: `1000-2000 USD`, `20-30 Triệu`, `Negotiable`, `Hidden`, `Competitive`

---

## 📦 Đầu ra

### 🌟 Vì sao lại chọn cào dữ liệu từ trang ITviec.com?

1. **Chuyên biệt về IT ("Ít nhưng mà chất"):** Đây là nền tảng tuyển dụng lớn nhất và chuyên sâu nhất dành riêng cho dân IT tại Việt Nam. Dữ liệu cào được sẽ không bị nhiễu bởi các ngành nghề khác.
2. **Chất lượng tin đăng cao:** Các công ty phải trả phí khá cao để đăng tin, do đó tin tuyển dụng thường rất chi tiết, ít tin rác (spam) hoặc tin ảo.
3. **Cấu trúc chuẩn SEO (JSON-LD):** Nền tảng này sử dụng cấu trúc Schema JSON-LD rất chuẩn mực, giúp bot dễ dàng bóc tách thông tin chính xác đến 99% mà không bị phụ thuộc nhiều vào giao diện HTML dễ thay đổi.

---

### `hybrid_jobs_fixed.csv`

Hệ thống cào và trích xuất các trường dữ liệu sau để phục vụ trực tiếp cho việc phân tích Big Data:

| Cột | Ý nghĩa / Vì sao phải cào trường này? |
|---|---|
| `title` | **Tiêu đề công việc:** Dùng để phân tích các vị trí/ngách công việc đang hot (vd: AI Engineer, Backend Dev). |
| `company` | **Tên công ty:** Dùng để thống kê Top công ty tuyển dụng nhiều nhất, quy mô doanh nghiệp. |
| `salary` | **Mức lương:** Trường quan trọng nhất! Dùng để vẽ biểu đồ so sánh mặt bằng lương theo cấp bậc, vị trí và công ty. |
| `location` | **Địa điểm:** Dùng để phân tích xu hướng tuyển dụng theo vùng miền (HN/HCM/ĐN) hoặc xu hướng làm việc Remote. |
| `description` | **Mô tả công việc:** Dùng cho NLP (Xử lý ngôn ngữ tự nhiên) để trích xuất thêm các yêu cầu ẩn, năm kinh nghiệm, hoặc tính toán độ khó của công việc. |
| `skills` | **Kỹ năng:** Phục vụ biểu đồ Top Kỹ Năng, mạng lưới kết nối kỹ năng (PageRank), và phân tích TF-IDF. |
| `url` | **Link gốc:** Dùng làm định danh (ID) để tránh trùng lặp dữ liệu (Deduplication) và cho phép người dùng click xem chi tiết. |
| `crawl_time` | **Thời gian cào:** Quản lý phiên bản dữ liệu (Version Control) và theo dõi biến động thị trường theo thời gian. |

---

## 🔁 Luồng dữ liệu

```
itviec.com/it-jobs
        │
        │  [Selenium + requests]
        ▼
  Danh sách URL /it-jobs/*
        │
        │  [ThreadPoolExecutor x5]
        ▼
  JSON-LD JobPosting Schema
        │
        ├── normalize_salary()    → "20-30 Triệu" / "1000 USD"
        ├── normalize_location()  → "HN,HCM"
        ├── normalize_skills()    → ["Python", "Docker", "AWS"]
        └── extract_description() → mô tả sạch (< 16000 ký tự)
        │
        ▼
  autosave.csv  ←── ghi mỗi 5 jobs (khôi phục khi crash)
        │
        ▼
  hybrid_jobs_fixed.csv  ←── kết quả cuối (đã dedupe)
```

---

## 🚀 Sử dụng

```bash
python itviec.py
```

Script sẽ tự động:
1. Mở Chrome cho đăng nhập lần đầu
2. In tiến độ cào ra console
3. Tự lưu định kỳ vào `autosave.csv`
4. Ghi kết quả cuối vào `hybrid_jobs_fixed.csv`

**Tiếp tục sau khi bị dừng:** Chỉ cần chạy lại — script tự nhận `autosave.csv` và tiếp tục từ chỗ dừng.
