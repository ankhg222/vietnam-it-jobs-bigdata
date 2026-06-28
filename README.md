# 🏢 JOB MARKET BIGDATA — Phân Tích Thị Trường Việc Làm IT Việt Nam

> Đồ án Big Data: Thu thập, xử lý, phân tích và trực quan hóa dữ liệu tuyển dụng IT Việt Nam
> **Stack:** Python · Apache Spark (PySpark) · HDFS · MongoDB · Flask · Scikit-learn · MLxtend

---

## 📋 Mục Lục

- [Tổng quan](#-tổng-quan)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
- [Dữ liệu](#-dữ-liệu)
- [Crawler](#-crawler)
- [Xử lý & Phân tích (Spark MapReduce)](#-xử-lý--phân-tích-spark-mapreduce)
- [Data Mining](#-data-mining)
- [Hệ thống CRUD & Dashboard](#-hệ-thống-crud--dashboard)
- [Machine Learning — Gợi ý Việc làm](#-machine-learning--gợi-ý-việc-làm)
- [Hướng dẫn cài đặt & chạy](#-hướng-dẫn-cài-đặt--chạy)
- [Kết quả phân tích](#-kết-quả-phân-tích)

---

## 🎯 Tổng quan

Đồ án xây dựng pipeline Big Data end-to-end để phân tích thị trường việc làm IT Việt Nam:

| Giai đoạn | Mô tả |
|-----------|-------|
| **Thu thập** | Crawl dữ liệu từ ITviec, TopDev, VietnamWorks |
| **Lưu trữ** | HDFS (phân tán) + MongoDB (NoSQL) |
| **Xử lý** | PySpark MapReduce — 15 job phân tích |
| **Mining** | Clustering, Association Rules, NLP, Salary Prediction |
| **Ứng dụng** | Flask CRUD app + Dashboard trực quan |
| **ML** | Hệ thống gợi ý việc làm bằng NLP embeddings |

---

## 🏗 Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                         │
│         ITviec · TopDev · VietnamWorks                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ Crawler (Selenium / Requests)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                           │
│   HDFS  →  hdfs://localhost:9000/project/jobs               │
│   MongoDB Atlas  →  BigDataJobMarket.Jobs                   │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
           ▼                              ▼
┌──────────────────┐            ┌──────────────────────┐
│  SPARK ENGINE    │            │    DATA MINING        │
│  15 MapReduce    │            │  Clustering / NLP     │
│  jobs (spark/)   │            │  AssocRules / Predict │
└────────┬─────────┘            └──────────┬───────────┘
         │                                 │
         ▼                                 ▼
┌─────────────────────────────────────────────────────────────┐
│               OUTPUT / VISUALIZATION                        │
│  Parquet files · TXT reports · MongoDB collections          │
│  Flask CRUD (itjob_crud/) · Dashboard (bieudo.py)           │
│  Job Recommendation System (ML)                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Cấu trúc thư mục

```
/
│
├── crawler/                         # Thu thập dữ liệu
│   ├── itviec_job/itviec.py         #   Crawler ITviec (Selenium + Cookie)
│   ├── topdev/                      #   Crawler TopDev
│   ├── vietnamwork/                 #   Crawler VietnamWorks
│ 
│
├── data/
│   ├── raw/                         # Dữ liệu thô từ crawler
│   ├── processed/
│   │   └── Data_ITJOB_Cleaned.csv  # Dataset đã làm sạch (~3.5 MB, ~2k rows)
│   ├── parquet/                     # Output Parquet + TXT từ Spark jobs
│   └── mining_results/             # Kết quả Data Mining
│
├── spark/                           # PySpark MapReduce jobs
│   ├── mr_top_skills.py             #  Job 01: Top 20 kỹ năng
│   ├── mr_salary_by_level.py        #  Job 02: Lương theo cấp bậc
│   ├── mr_salary_by_skill.py        #  Job 03: Lương theo kỹ năng
│   ├── mr_yoe_salary_correlation.py #  Job 04: YOE vs Lương
│   ├── mr_company_hiring.py         #  Job 05: Top công ty tuyển dụng
│   ├── mr_remote_analysis.py        #  Job 06: Remote vs On-site
│   ├── mr_job_level_distribution.py #  Job 07: Phân bố cấp bậc
│   ├── mr_top_paying_jobs.py        #  Job 08: Jobs lương cao nhất
│   ├── mr_salary_bracketing.py      #  Job 09: Histogram lương
│   ├── mr_salary_outliers.py        #  Job 10: Lương bất thường (IQR)
│   ├── mr_skill_cooccurrence.py     #  Job 11: Cặp kỹ năng xuất hiện cùng
│   ├── mr_skill_rarity.py           #  Job 12: Kỹ năng hiếm (IDF)
│   ├── mr_olap_cube.py              #  Job 13: OLAP Cube 3 chiều
│   ├── mr_cross_tabulation.py       #  Job 14: Bảng chéo đa chiều
│   └── mr_location.py              #  Job 15: Phân bố theo địa điểm
│
├── ml/                              # Data Mining & Machine Learning
│   ├── dm_salary_prediction.py      # Dự đoán lương (XGBoost/RF)
│   ├── dm_job_clustering.py         # Phân cụm việc làm (K-Means)
│   ├── dm_association_rules.py      # Luật kết hợp kỹ năng (Apriori)
│   ├── dm_text_mining.py            # Khai phá văn bản JD (TF-IDF)
│   ├── dm_information_extraction.py # Trích xuất YOE, kỹ năng từ JD
│   ├── dm_network_analysis.py       # Đồ thị quan hệ kỹ năng (NetworkX)
│   ├── dm_complexity_scoring.py     # Đánh giá độ phức tạp JD
│   ├── dm_level_classification.py   # Phân loại cấp bậc tự động
│   ├── dm_level_profiling.py        # Hồ sơ thống kê theo cấp bậc
│   └── dm_role_classification.py   # Phân loại vai trò IT
│
├── itjob_crud/                      # Flask Web App (CRUD + Dashboard)
│   ├── app.py                       #   Entry point Flask
│   ├── config.py                    #   Cấu hình MongoDB / Spark
│   ├── src/                         #   Routes, models, templates
│   └── requirements.txt
│
├── Job_Recommendation_Train.ipynb   # Notebook huấn luyện gợi ý việc làm
├── job_embeddings.npy               # Vector embeddings đã lưu (~3.2 MB)
├── job_data.csv                     # Dữ liệu raw tổng hợp
├── bieudo.py                        # Sinh toàn bộ biểu đồ phân tích
├── app.py                           # Flask app root
├── requirements.txt                 # Python dependencies
└── docs/
    └── bigdata_NPKhang.docx         # Báo cáo đồ án
```

---

## 💾 Dữ liệu

### Schema chính: `Data_ITJOB_Cleaned.csv`

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `title_clean` | string | Tên công việc đã chuẩn hóa |
| `company` | string | Tên công ty |
| `job_level` | string | Fresher / Junior / Senior / Manager |
| `salary_final_vnd` | double | Mức lương quy đổi VNĐ |
| `yoe_extracted` | double | Năm kinh nghiệm (trích xuất từ JD) |
| `skills_clean` | string | Kỹ năng phân cách bởi dấu phẩy |
| `location_clean` | string | Địa điểm làm việc |
| `is_remote` | int | 0 = On-site, 1 = Remote |
| `source` | string | itviec / topdev / vietnamworks |
| `skill_count` | int | Tổng số kỹ năng yêu cầu |

### HDFS Paths

```
hdfs://localhost:9000/project/jobs/       ← input CSV
hdfs://localhost:9000/project/output/     ← output TXT reports
```

---

## 🕷 Crawler

| Thư mục | Nguồn | Kỹ thuật |
|---------|-------|----------|
| `crawler/itviec_job/` | ITviec.com | Selenium + Cookie authentication |
| `crawler/topdev/` | TopDev.vn | Requests + BeautifulSoup |
| `crawler/vietnamwork/` | VietnamWorks.com | Requests REST API |

```bash
# Chạy crawler ITviec
cd crawler/itviec_job
python itviec.py
```

---

## ⚡ Xử lý & Phân tích — Spark MapReduce

Tất cả jobs đọc từ **HDFS** (`hdfs://localhost:9000/project/jobs`),  
ghi output ra **Parquet + TXT** local và **MongoDB** collections.

### Bảng 15 MapReduce Jobs

| # | Script | Phân tích | MAP | REDUCE |
|---|--------|-----------|-----|--------|
| 01 | `mr_top_skills.py` | Top 20 kỹ năng IT | Explode skills → (skill, 1) | groupBy(skill).count() |
| 02 | `mr_salary_by_level.py` | Lương theo cấp bậc | (job_level, salary) | min/avg/median/max |
| 03 | `mr_salary_by_skill.py` | Lương theo kỹ năng | Explode → (skill, salary) | avg/median (≥10 jobs) |
| 04 | `mr_yoe_salary_correlation.py` | YOE vs Lương | Bucket YOE 0-1/2/3-4/5-6/7-9/10+ | avg_salary + LAG window |
| 05 | `mr_company_hiring.py` | Top 20 công ty tuyển | (company, salary) | count + market_share% |
| 06 | `mr_remote_analysis.py` | Remote vs On-site | Gán nhãn work_type | stats + pivot by level |
| 07 | `mr_job_level_distribution.py` | Phân bố cấp bậc | (source, job_level) | count + pivot |
| 08 | `mr_top_paying_jobs.py` | Top 3 jobs lương cao/level | (level, salary) | Window rank() per level |
| 09 | `mr_salary_bracketing.py` | Histogram mức lương | salary → bucket (<15/15-30/30-50/50-80/>80 M) | count per bucket |
| 10 | `mr_salary_outliers.py` | Lương bất thường | IQR per job_level | join + filter > Upper Bound |
| 11 | `mr_skill_cooccurrence.py` | Cặp kỹ năng đi cùng | UDF combinations() per job | groupBy(pair).count() |
| 12 | `mr_skill_rarity.py` | Độ hiếm kỹ năng (IDF) | Explode + dedupe per job | IDF = log(N / DF) |
| 13 | `mr_olap_cube.py` | OLAP Cube 3 chiều | — | .cube(location, level, remote) |
| 14 | `mr_cross_tabulation.py` | Bảng chéo đa chiều | — | crosstab multi-dimension |
| 15 | `mr_location.py` | Phân bố việc làm theo tỉnh/thành | (location, salary) | count + avg per city |

### Chạy Spark jobs

```bash
# Upload data lên HDFS trước
hdfs dfs -mkdir -p /project/jobs
hdfs dfs -put data/processed/Data_ITJOB_Cleaned.csv /project/jobs/
hdfs dfs -mkdir -p /project/output

# Submit một job
spark-submit spark/mr_top_skills.py

# Chạy local (không cần Spark cluster)
python spark/mr_top_skills.py
```

---

## 🔬 Data Mining

| Script | Kỹ thuật | Mục tiêu |
|--------|----------|----------|
| `dm_salary_prediction.py` | XGBoost / Random Forest | Dự đoán mức lương từ skills + level + yoe |
| `dm_job_clustering.py` | K-Means (sklearn) | Phân cụm việc làm theo đặc trưng |
| `dm_association_rules.py` | Apriori (MLxtend) | Luật kết hợp: kỹ năng A → kỹ năng B |
| `dm_text_mining.py` | TF-IDF + WordCloud | Phân tích ngôn ngữ trong Job Description |
| `dm_information_extraction.py` | Regex + NLP | Trích xuất YOE, kỹ năng từ JD thô |
| `dm_network_analysis.py` | NetworkX + Graph | Đồ thị quan hệ kỹ năng co-occurrence |
| `dm_complexity_scoring.py` | Scoring model | Điểm độ phức tạp yêu cầu của JD |
| `dm_level_classification.py` | Classifier | Phân loại cấp bậc tự động từ JD |
| `dm_level_profiling.py` | Statistical | Hồ sơ thống kê chi tiết theo cấp bậc |
| `dm_role_classification.py` | Text classifier | Phân loại vai trò (Dev/QA/DevOps/...) |

```bash
python ml/dm_association_rules.py
python ml/dm_salary_prediction.py
python ml/dm_job_clustering.py
```

---

## 🌐 Hệ thống CRUD & Dashboard

Flask app tại `itjob_crud/` cung cấp:
- **CRUD** đầy đủ trên collection Jobs (MongoDB backend)
- **Dashboard** thống kê tổng quan
- **REST API** phục vụ frontend queries

```bash
cd itjob_crud
pip install -r requirements.txt
python app.py
# Truy cập: http://localhost:5000
```

**Sinh biểu đồ phân tích:**
```bash
python bieudo.py
```

---

## 🤖 Machine Learning — Gợi ý Việc làm

**File:** `Job_Recommendation_Train.ipynb` + `job_embeddings.npy`

**Phương pháp:**
1. Encode mô tả công việc → dense vector embeddings (Sentence Transformers / TF-IDF)
2. Cosine similarity để tìm jobs tương đồng
3. Embeddings lưu sẵn: `job_embeddings.npy` (~3.2 MB, tránh re-compute)

```bash
jupyter notebook Job_Recommendation_Train.ipynb
```

---

## 🚀 Hướng dẫn cài đặt & chạy

### Yêu cầu hệ thống

| Thành phần | Phiên bản |
|------------|-----------|
| Python | 3.8+ |
| Apache Spark | 3.x |
| Hadoop HDFS | 3.x |
| Java JDK | 8 hoặc 11 |
| MongoDB | Atlas (cloud) hoặc local |

### 1. Cài Python packages

```bash
pip install -r requirements.txt
pip install pyspark pymongo[srv]
```

### 2. Khởi động HDFS

```bash
# Linux / WSL
start-dfs.sh

# Windows
%HADOOP_HOME%\sbin\start-dfs.cmd
```

### 3. Upload dữ liệu lên HDFS

```bash
hdfs dfs -mkdir -p /project/jobs
hdfs dfs -mkdir -p /project/output
hdfs dfs -put data/processed/Data_ITJOB_Cleaned.csv /project/jobs/
# Kiểm tra
hdfs dfs -ls /project/jobs/
```

### 4. Chạy Spark analysis jobs

```bash
spark-submit spark/mr_top_skills.py
spark-submit spark/mr_salary_by_level.py
# ... các jobs còn lại
```

### 5. Chạy Data Mining

```bash
python ml/dm_association_rules.py
python ml/dm_salary_prediction.py
```

### 6. Khởi động Web App

```bash
python app.py
# hoặc
cd itjob_crud && python app.py
```

---

## 📊 Kết quả phân tích

Output sau khi chạy Spark jobs lưu tại `data/parquet/`:

| File | Nội dung |
|------|----------|
| `top_skills.txt` | Top 20 kỹ năng IT được yêu cầu nhiều nhất |
| `salary_by_level.txt` | Min/Avg/Median/Max lương theo cấp bậc |
| `salary_by_skill.txt` | Top 15 kỹ năng có mức lương cao nhất |
| `yoe_salary_correlation.txt` | Lương tăng theo năm kinh nghiệm (LAG) |
| `company_hiring.txt` | Top 20 công ty tuyển dụng + market share |
| `remote_analysis.txt` | So sánh Remote vs On-site (lương + kỹ năng) |
| `job_level_distribution.txt` | Phân bố cấp bậc theo từng nguồn tuyển dụng |
| `top_paying_jobs.txt` | Top 3 jobs lương cao nhất mỗi cấp bậc |
| `salary_bracketing.txt` | Histogram phân bổ mức lương (<15M đến >80M) |
| `salary_outliers.txt` | Jobs có lương bất thường (IQR method) |
| `skill_cooccurrence.txt` | Top 50 cặp kỹ năng thường xuất hiện cùng |
| `skill_rarity.txt` | Top 50 kỹ năng hiếm nhất (IDF score) |
| `olap_cube.txt` | OLAP 3 chiều: Location × Level × Remote |

> Kết quả cũng được đồng bộ lên **MongoDB** collections tương ứng  
> và **upload lên HDFS** tại `/project/output/`.

---

## 👤 Tác giả
| | |
|---|---|
| **Họ và tên** | Nguyễn Phước Khang |
| **📧 Email** | khangnguyen2x0@gmail.com |
| **📚 Môn học** | Hệ thống Dữ liệu Lớn (Big Data Systems) |
