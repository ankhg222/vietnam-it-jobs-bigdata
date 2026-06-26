import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

app = FastAPI(title="Job Recommendation API")

# Mount thư mục static
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Cấu trúc request
class RecommendRequest(BaseModel):
    user_profile: str
    top_k: int = 5

# Global variables
model = None
df = None
job_embeddings = None

# ==============================================================================
# BƯỚC 1: KHỞI TẠO TÀI NGUYÊN (RESOURCE INITIALIZATION)
# ==============================================================================
# Dùng sự kiện `startup` của FastAPI để nạp Model và Data lên RAM duy nhất 1 lần lúc bật Server.
# Nếu không nạp sẵn mà để mỗi lần User request mới nạp thì API sẽ cực kỳ chậm (lag).
# Kỹ thuật này gọi là Singleton Pattern trong triển khai AI.
@app.on_event("startup")
def load_resources():
    global model, df, job_embeddings
    print("Loading data and model...")
    try:
        # Load dữ liệu công việc (Đã clean)
        df = pd.read_csv("job_data.csv")
        # Load ma trận Vector (Embeddings) của tất cả công việc đã tính toán từ trước (Tiết kiệm thời gian)
        job_embeddings = np.load("job_embeddings.npy")
        
        # Load mô hình NLP đa ngôn ngữ (Hỗ trợ cả Tiếng Anh lẫn Tiếng Việt)
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print(f"Data loaded: {df.shape[0]} jobs")
    except Exception as e:
        print(f"Error loading resources: {e}")

@app.get("/")
def read_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.post("/api/recommend")
def recommend_jobs(request: RecommendRequest):
    if df is None or job_embeddings is None or model is None:
        raise HTTPException(status_code=500, detail="Mô hình hoặc dữ liệu chưa được tải.")
    
    try:
        # ==============================================================================
        # BƯỚC 2: HỆ THỐNG GỢI Ý (CONTENT-BASED RECOMMENDER SYSTEM)
        # ==============================================================================
        
        # 2.1 Băm đoạn văn bản hồ sơ của User thành một Vector số (User Embedding)
        user_embedding = model.encode([request.user_profile])
        
        # 2.2 Tính Độ Tương Đồng Cosine (Cosine Similarity)
        # So sánh Vector của User với HÀNG NGÀN Vector của Job cùng một lúc (Phép toán Ma Trận).
        # Cosine Similarity = 1 (Giống hệt nhau), = 0 (Khác hoàn toàn).
        similarities = cosine_similarity(user_embedding, job_embeddings)[0]
        
        # 2.3 Lấy Top K công việc phù hợp nhất (Sorting)
        top_k = min(request.top_k, len(df))
        # np.argsort sắp xếp vị trí các phần tử từ bé đến lớn. 
        # Thêm [::-1] để lật ngược lại thành Lớn (Giống nhất) -> Bé.
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Build response
        results = []
        for idx in top_indices:
            if idx >= len(df):
                continue
            row = df.iloc[idx]
            
            # Xử lý các cột NaN nếu có
            def safe_get(val):
                return str(val) if pd.notna(val) else ""
            
            original_salary = safe_get(row.get('salary', ''))
            
            if "Y-u'll l-ve i-USD" in original_salary or not original_salary or original_salary.lower() == 'nan':
                display_salary = "Thương lượng"
            else:
                display_salary = original_salary
                if "đ" in display_salary.lower() or "vnd" in display_salary.lower():
                    display_salary = display_salary.replace(" USD", "").replace("USD", "").strip()

            results.append({
                "title": safe_get(row.get('title_clean', row.get('title', 'Unknown'))),
                "company": safe_get(row.get('company', 'Unknown Company'))[:50], # Truncate long names
                "skills": safe_get(row.get('skills_clean', row.get('skills', 'No skills listed'))),
                "salary": display_salary,
                "url": safe_get(row.get('url', '#')),
                "similarity_score": round(float(similarities[idx]), 4)
            })
            
        return {"recommendations": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("Khởi động server trên http://localhost:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
