# 🤖 Hệ Tư Vấn Việc Làm IT (Job Recommendation System)

Hệ thống ứng dụng **Trí tuệ nhân tạo (AI)** và **Xử lý ngôn ngữ tự nhiên (NLP)** để tự động gợi ý các công việc IT phù hợp nhất dựa trên kỹ năng, kinh nghiệm hoặc nội dung CV của ứng viên.

Thay vì tìm kiếm theo từ khóa (keyword matching) cứng nhắc, hệ thống sử dụng **So khớp ngữ nghĩa (Semantic Matching)**. Nhờ đó, model vẫn hiểu được sự tương đồng dù ứng viên và nhà tuyển dụng dùng các từ vựng khác nhau (VD: "Artificial Intelligence" và "AI", hay "Machine Learning" và "Học máy").

---

## 📋 Mục lục
- [Kiến trúc Hệ thống](#-kiến-trúc-hệ-thống)
- [Cài đặt & Yêu cầu](#-cài-đặt--yêu-cầu)
- [Giai đoạn 1: Sinh Embedding (Feature Extraction)](#-giai-đoạn-1-sinh-embedding)
- [Giai đoạn 2: Suy luận & Gợi ý (Inference — Giao diện Web)](#-giai-đoạn-2-suy-luận--gợi-ý)
- [Ưu điểm kỹ thuật](#-ưu-điểm-kỹ-thuật)

---

## 🏗️ Kiến trúc Hệ thống

Hệ thống chia làm 2 giai đoạn tách biệt để tối ưu hiệu năng: tính toán trước các vector của việc làm (Offline) và so khớp trực tiếp với người dùng (Online).

```text
┌─────────────────────────────────────────────────────────────────┐
│                    PIPELINE HỆ TƯ VẤN VIỆC LÀM                 │
└─────────────────────────────────────────────────────────────────┘

  [GIAI ĐOẠN 1] Tính toán Offline (Train Notebook)
       │
       ├── Input: Data_ITJOB_Cleaned.csv (Dữ liệu đã làm sạch)
       ├── Gộp văn bản: title_clean + skills_clean + description_clean
       │
       ├── Model NLP: paraphrase-multilingual-MiniLM-L12-v2
       │    └── Biến đổi text thành Vector Embedding (Semantic)
       │
       └── Output lưu trữ:
            ├── job_data.csv (Thông tin text)
            └── job_embeddings.npy (Ma trận vector)
       │
       ▼
  [GIAI ĐOẠN 2] Suy luận Online (Giao diện Web — Flask/Streamlit)
       │
       ├── Input người dùng: Nhập CV hoặc danh sách kỹ năng qua Web UI
       │    └── VD: "Python Data Engineer, SQL, AWS, Airflow"
       │
       ├── Model NLP: paraphrase-multilingual-MiniLM-L12-v2
       │    └── Biến đổi Input thành Vector ứng viên
       │
       ├── So khớp (Matching):
       │    └── Tính Cosine Similarity giữa Vector ứng viên và job_embeddings
       │
       └── Output: Hiển thị Top K (VD: Top 5) việc làm phù hợp nhất trên giao diện
```

---

## ⚙️ Cài đặt & Yêu cầu

### Thư viện cần thiết
Hệ thống sử dụng các thư viện AI và xử lý dữ liệu:
```bash
pip install sentence-transformers pandas numpy scikit-learn
```

### Model NLP sử dụng
Hệ thống tải model open-source từ Hugging Face: `paraphrase-multilingual-MiniLM-L12-v2`.
- **Đa ngôn ngữ**: Hỗ trợ tốt cả tiếng Việt và tiếng Anh.
- **Nhẹ & Nhanh**: MiniLM có kích thước nhỏ, suy luận nhanh, phù hợp cho môi trường production.

---

## 🛠️ Giai đoạn 1: Sinh Embedding
**(File: `Job_Recommendation_Train.ipynb`)**

> **Lưu ý**: Dù có tên là "Train", nhưng bản chất đây là bước **Feature Extraction (Trích xuất đặc trưng)**. Chúng ta sử dụng Pre-trained model có sẵn, không huấn luyện lại (fine-tuning) tốn kém tài nguyên.

1. **Chuẩn bị dữ liệu**: Đọc file `Data_ITJOB_Cleaned.csv`.
2. **Tạo ngữ cảnh (Context)**: Ghép 3 trường thông tin quan trọng của mỗi công việc để tạo ra một đoạn văn bản đầy đủ ý nghĩa:
   - `title_clean` (Chức danh)
   - `skills_clean` (Kỹ năng yêu cầu)
   - `description_clean` (Mô tả công việc)
3. **Sinh Embedding**: Model đọc các đoạn văn bản này và mã hóa thành một ma trận số học (Vector).
4. **Lưu trữ Offline**: Lưu file `job_embeddings.npy` để không phải tính toán lại mỗi khi có người dùng truy vấn, giúp tiết kiệm thời gian đáng kể.

---

## 🎯 Giai đoạn 2: Suy luận & Gợi ý
**(Tích hợp trên Giao diện Web)**

Giai đoạn này đã được tích hợp hoàn chỉnh lên giao diện web, cho phép người dùng tương tác trực tiếp mà không cần chạy notebook:

1. **Nhận Input qua Web UI**: Ứng viên nhập đoạn text mô tả bản thân (kỹ năng, kinh nghiệm, vị trí mong muốn) ngay trên giao diện.
2. **Vector hóa**: Input được chuyển thành Vector bằng đúng model đã dùng ở Giai đoạn 1.
3. **Đo lường độ tương đồng (Cosine Similarity)**:
   - Thuật toán đo góc giữa Vector ứng viên và toàn bộ Vector việc làm trong database.
   - Điểm càng gần 1.0 (góc càng hẹp), mức độ phù hợp càng cao.
4. **Hiển thị kết quả**: Top 5 việc làm phù hợp nhất được hiển thị trực tiếp trên giao diện, sắp xếp từ cao xuống thấp.

---

## 💡 Ưu điểm kỹ thuật

- **Semantic Search (Tìm kiếm ngữ nghĩa)**: Vượt trội hơn hệ thống dựa trên từ khóa truyền thống (như SQL `LIKE` hay Elasticsearch Keyword).
- **Xử lý ngôn ngữ tự nhiên đa ngữ**: Thị trường IT Việt Nam sử dụng song song tiếng Anh và tiếng Việt (VD: "Phát triển phần mềm" = "Software Development"). Model multilingual giải quyết trọn vẹn vấn đề này.
- **Tốc độ cao**: Việc tính trước (pre-compute) Embeddings cho việc làm giúp hệ thống có thể phản hồi cho ứng viên chỉ trong vài phần nghìn giây.
