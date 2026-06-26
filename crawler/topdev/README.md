# 🕷️ TopDev Job Crawler

Script `topdev.py` tự động cào dữ liệu việc làm IT từ [topdev.vn](https://topdev.vn), trích xuất thông tin qua JSON-LD schema và BeautifulSoup, lưu kết quả vào CSV tương thích với định dạng `vnwork.csv`.

---

## 📋 Mục lục

- [Tổng quan Pipeline](#-tổng-quan-pipeline)
- [Kiến trúc](#-kiến-trúc)
- [Cài đặt](#-cài-đặt)
- [Cấu hình](#-cấu-hình)
- [Chi tiết từng bước](#-chi-tiết-từng-bước)
- [Đầu ra](#-đầu-ra)

---

## 🔄 Tổng quan Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                     PIPELINE CÀO TOPDEV                         │
└─────────────────────────────────────────────────────────────────┘

  [PHASE 1] Thu thập URL việc làm
       │
       ├── Duyệt tối đa 70 trang danh sách
       │    └── https://topdev.vn/jobs/search?page=N
       │
       ├── Mỗi trang: Selenium render → BeautifulSoup parse
       │    ├── Cuộn xuống cuối (kích hoạt lazy-loading)
       │    └── Trích mọi href chứa /detail-jobs/
       │
       └── Dừng sớm nếu: trang rỗng HOẶC đã đủ 1000 URL
       │
       ▼
  [PHASE 2] Cào chi tiết song song
       │
       ├── ThreadPoolExecutor (5 luồng đồng thời)
       ├── Mỗi luồng có Selenium driver riêng (thread-local)
       │
       ├── Mỗi URL → scrape_job_detail():
       │    ├── [Ưu tiên 1] JSON-LD <script type="application/ld+json">
       │    │    → JobPosting schema (title, company, salary, location, ...)
       │    └── [Ưu tiên 2] BeautifulSoup CSS selector fallback
       │
       └── Tự động lưu (autosave) sau mỗi 10 việc làm thành công
       │
       ▼
  [BƯỚC 3] Trích xuất & Chuẩn hóa
       │
       ├── Tiêu đề    ← JSON-LD title → <h1> → <title>
       ├── Công ty    ← hiringOrganization.name → CSS fallback
       ├── Lương      ← JSON-LD baseSalary (min/max/currency) → regex trang
       ├── Địa điểm   ← jobLocation.address (addressLocality/addressRegion)
       ├── Mô tả      ← JSON-LD description → CSS content area (1 dòng)
       ├── Kỹ năng    ← JSON-LD skills → quét KNOWN_SKILLS từ text
       ├── Kinh nghiệm← experienceRequirements → regex ("N-M năm/year")
       └── Cấp bậc    ← từ khóa trong tiêu đề → toàn trang
       │
       ▼
  [BƯỚC 4] Lưu kết quả cuối
       │
       ├── Ghi topdev_jobs.csv (UTF-8 BOM, quoting=ALL)
       └── Ghi topdev_autosave.csv (bản sao an toàn)
```

---

## 🏗️ Kiến trúc

```
topdev/
├── topdev.py              # Script chính
├── topdev_autosave.csv    # Lưu tạm - tự tạo khi chạy
└── topdev_jobs.csv        # Kết quả cuối - tự tạo khi chạy
```

### Thành phần chính

| Hàm | Vai trò |
|---|---|
| `main()` | Điểm khởi đầu, điều phối 2 phase |
| `get_job_urls_from_page()` | Cào 1 trang danh sách → trả về list URL |
| `scrape_job_detail()` | Cào chi tiết 1 URL → trả về dict job |
| `process_job()` | Worker: gọi scrape → ghi vào `_all_jobs` |
| `parse_jsonld()` | Trích JobPosting từ JSON-LD script tags |
| `extract_salary_from_jsonld()` | Phân tích baseSalary (min/max/currency) |
| `extract_skills_from_text()` | Quét KNOWN_SKILLS bằng regex word-boundary |
| `clean_text()` | HTML → text thuần 1 dòng (collapse whitespace) |
| `create_driver()` | Tạo Chrome headless với options chống bot |
| `get_thread_driver()` | Lấy/tạo driver theo luồng (thread-local) |
| `autosave()` | Ghi CSV tạm sau mỗi 10 job |
| `save_final()` | Ghi CSV kết quả cuối |

---

## ⚙️ Cài đặt

### Yêu cầu

- Python 3.10+
- Google Chrome (đã cài đặt)
- ChromeDriver tương thích (tự động nhận diện)

### Cài thư viện

```bash
pip install requests pandas beautifulsoup4 selenium
```

---

## 🔧 Cấu hình

Chỉnh các hằng số ở đầu file `topdev.py`:

| Hằng số | Mặc định | Mô tả |
|---|---|---|
| `MAX_WORKERS` | `5` | Số luồng Selenium song song |
| `MAX_PAGES` | `70` | Số trang danh sách tối đa cào |
| `AUTOSAVE_INTERVAL` | `10` | Tự lưu sau mỗi N job thành công |
| `LISTING_URL` | `topdev.vn/jobs/search` | URL trang danh sách |
| `AUTOSAVE_PATH` | `topdev_autosave.csv` | File lưu tạm |
| `FINAL_CSV` | `topdev_jobs.csv` | File kết quả cuối |

---

## 📖 Chi tiết từng bước

### Phase 1 – Thu thập URL

Dùng Selenium (headless) mở từng trang danh sách. Sau khi trang load:
1. Cuộn xuống cuối để kích hoạt lazy-loading
2. Parse HTML tìm tất cả `<a href>` chứa `/detail-jobs/`
3. Bỏ qua URL đã thấy (dedup theo `_seen_urls`)
4. Dừng nếu trang không có URL mới hoặc đã thu đủ **1000 URL**

### Phase 2 – Cào chi tiết song song

5 luồng worker chạy đồng thời. Mỗi luồng:
1. Dùng driver Selenium riêng (thread-local, headless)
2. Load trang, chờ 5–6 giây cho JS render
3. Parse JSON-LD → ưu tiên dữ liệu schema có cấu trúc
4. Fallback BeautifulSoup nếu JSON-LD thiếu trường

### Chuẩn hóa lương

```
baseSalary (JSON-LD dict)
    └── value.minValue - value.maxValue + currency  → "1000-2000 USD"
    └── value có chữ "Negotiable/thỏa thuận"        → "Negotiable"
baseSalary (string)                                  → giữ nguyên
Fallback: regex trang tìm số + đơn vị               → "20 triệu"
```

### Phát hiện cấp bậc (job_level)

Tìm từ khóa theo thứ tự ưu tiên: **tiêu đề trước → toàn trang sau**

| Cấp bậc | Từ khóa nhận diện |
|---|---|
| Fresher | fresher, entry, entry-level, graduate |
| Junior | junior, junior developer |
| Middle | middle, mid-level |
| Senior | senior, lead, principal |
| Architect | architect, solutions architect |

---

## 📦 Đầu ra

### `topdev_jobs.csv`

| Cột | Mô tả |
|---|---|
| `title` | Tiêu đề việc làm |
| `company` | Tên công ty |
| `salary` | Mức lương (JSON-LD hoặc regex) |
| `location` | Địa điểm làm việc |
| `description` | Mô tả công việc (1 dòng, HTML đã làm sạch) |
| `skills` | Kỹ năng từ JSON-LD + KNOWN_SKILLS scan |
| `experience` | Số năm kinh nghiệm yêu cầu |
| `job_level` | Cấp bậc: Fresher / Junior / Middle / Senior / Architect |
| `url` | URL trang việc làm gốc |
| `crawl_time` | Thời điểm cào (YYYY-MM-DD HH:MM:SS.ffffff) |

> **Lưu ý:** Schema cột tương thích với `vnwork.csv`, thêm 2 cột mới: `experience` và `job_level`.

---

## 🚀 Sử dụng

```bash
python topdev.py
```

Script sẽ tự động:
1. **Phase 1**: Thu thập URL từ tối đa 70 trang danh sách
2. **Phase 2**: Cào 5 trang song song, in tiến độ mỗi 50 job
3. Tự lưu vào `topdev_autosave.csv` sau mỗi 10 job
4. Ghi kết quả cuối vào `topdev_jobs.csv`
