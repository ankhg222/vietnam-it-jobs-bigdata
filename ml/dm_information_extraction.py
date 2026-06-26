import os
import pandas as pd
import re
from collections import Counter
import matplotlib.pyplot as plt

def main():
    # ==============================================================================
    # TRÍCH XUẤT THÔNG TIN (INFORMATION EXTRACTION - IE)
    # Kỹ thuật: Rule-based Named Entity Recognition (NER) bằng Biểu thức chính quy (Regex)
    # ==============================================================================
    # Bài toán: Đọc hàng ngàn văn bản thô (Mô tả công việc) và nhặt ra các từ khóa cụ thể.
    # So với LDA (Học không giám sát tự gom cụm), thì IE ở đây là Học có giám sát (Supervised) 
    # bằng cách lập trình sẵn bộ luật (Rules) để tìm đích danh thứ mình cần.
    print("[INFO] Bắt đầu mô hình Trích xuất thông tin (Information Extraction)...")
    
    # ==============================================================================
    # CẤU HÌNH ĐƯỜNG DẪN TƯƠNG ĐỐI (RELATIVE PATH CONFIGURATION)
    # ==============================================================================
    # Dùng `__file__` để lấy thư mục chứa file script hiện tại.
    # Tuyệt đối không dùng đường dẫn cứng (Hardcode tuyệt đối kiểu "C:/khang/...") 
    # để lỡ mang sang máy thầy cô hoặc lên Server Linux chạy vẫn không bị lỗi Not Found.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "..", "data", "processed", "Data_ITJOB_Cleaned.csv")
    results_dir = os.path.join(current_dir, "..", "data", "mining_results")
    
    # Tự động tạo thư mục output nếu nó chưa tồn tại (chống lỗi thư mục)
    os.makedirs(results_dir, exist_ok=True)
    
    report_path = os.path.join(results_dir, "information_extraction_report.txt")
    plot_path = os.path.join(results_dir, "top_benefits.png")
    
    # Bẫy lỗi (Error Handling): Kiểm tra xem file Data có tồn tại không trước khi đọc
    if not os.path.exists(data_path):
        print(f"[ERROR] Không tìm thấy file: {data_path}")
        return

    df = pd.read_csv(data_path)
    df['description_clean'] = df['description_clean'].fillna('')
    
    # ==============================================================================
    # TỪ ĐIỂN CÁC MẪU REGEX (REGEX PATTERNS DICTIONARY)
    # ==============================================================================
    # Dùng regex để xử lý các biến thể chính tả. 
    # Ví dụ: Người ghi "tháng 13", người ghi "13th month" -> Gom chung về 1 cục "13th_month"
    benefits_dict = {
        "13th_month": r"(13th\s*month|tháng\s*13)",
        "healthcare_insurance": r"(health\s*care|health\s*insurance|bảo\s*hiểm|bao\s*hiem|medical)",
        "bonus_performance": r"(performance\s*bonus|thưởng|thuong|incentive)",
        "hybrid_remote": r"(hybrid|remote|work\s*from\s*home|wfh|flexible)",
        "laptop_macbook": r"(macbook|laptop|device)",
        "annual_leave": r"(annual\s*leave|paid\s*leave|phép\s*năm|nghỉ\s*phép)",
        "team_building": r"(team\s*building|company\s*trip|outing)",
        "training_certificate": r"(training|certificate|sponsorship|đào\s*tạo)"
    }
    
    # Tương tự cho Kỹ năng mềm / Ngoại ngữ
    soft_skills_dict = {
        "communication": r"(communication|giao\s*tiếp)",
        "teamwork": r"(teamwork|team\s*work|làm\s*việc\s*nhóm)",
        "problem_solving": r"(problem\s*solving|giải\s*quyết\s*vấn\s*đề)",
        "english": r"(english|tiếng\s*anh)",
        "japanese": r"(japanese|tiếng\s*nhật)"
    }
    
    # Dùng `Counter` của Python (như một bảng băm Hash Table) để đếm tần suất siêu tốc
    benefit_counts = Counter()
    soft_skill_counts = Counter()
    
    print("[INFO] Đang quét mô tả công việc (Rule-based NER)...")
    for desc in df['description_clean']:
        desc_lower = desc.lower() # Chuẩn hóa chữ thường (Case Insensitive) để quét regex không bị sót
        
        # Check benefits
        for b_name, b_pattern in benefits_dict.items():
            if re.search(b_pattern, desc_lower):
                benefit_counts[b_name] += 1
                
        # ==============================================================================
        # QUÉT VĂN BẢN (TEXT SCANNING)
        # ==============================================================================
        # Tại sao dùng `re.search` chứ không dùng `re.match`?
        # - `re.match`: Chỉ tìm xem từ khóa có nằm ở ĐẦU câu hay không.
        # - `re.search`: Lục lọi toàn bộ ngóc ngách của văn bản, thấy ở đâu là báo ở đó.
        # Phù hợp với JD vì phúc lợi có thể nằm ở bất kỳ đâu (đầu, giữa, hoặc cuối bài).
        for b_name, b_pattern in benefits_dict.items():
            if re.search(b_pattern, desc_lower):
                benefit_counts[b_name] += 1
                
        # Tương tự cho kỹ năng mềm
        for s_name, s_pattern in soft_skills_dict.items():
            if re.search(s_pattern, desc_lower):
                soft_skill_counts[s_name] += 1
                
    total_jobs = len(df)
    
    # Plot Benefits
    benefits_df = pd.DataFrame(benefit_counts.items(), columns=['Benefit', 'Count']).sort_values(by='Count', ascending=True)
    
    plt.figure(figsize=(10, 6))
    plt.barh(benefits_df['Benefit'], benefits_df['Count'], color='coral')
    plt.title("Top Phúc lợi (Benefits) được đề cập trong JD")
    plt.xlabel("Số lượng tin tuyển dụng")
    plt.tight_layout()
    plt.savefig(plot_path, dpi=300)
    plt.close()
    
    print("[INFO] Đang lưu báo cáo...")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=== BÁO CÁO TRÍCH XUẤT THÔNG TIN (INFORMATION EXTRACTION) ===\n\n")
        f.write(f"Tổng số job quét: {total_jobs}\n\n")
        
        f.write("--- PHÚC LỢI PHỔ BIẾN (BENEFITS) ---\n")
        # `most_common()` tự động sắp xếp từ cao xuống thấp, không cần viết code sort mệt mỏi
        for b_name, count in benefit_counts.most_common():
            pct = (count / total_jobs) * 100
            f.write(f"{b_name:<25}: {count:4d} jobs ({pct:.1f}%)\n")
            
        f.write("\n--- KỸ NĂNG MỀM / NGOẠI NGỮ (SOFT SKILLS / LANGUAGES) ---\n")
        for s_name, count in soft_skill_counts.most_common():
            pct = (count / total_jobs) * 100
            f.write(f"{s_name:<25}: {count:4d} jobs ({pct:.1f}%)\n")
            
    print(f"[OK] Đã lưu báo cáo: {report_path}")
    print(f"[OK] Đã lưu biểu đồ: {plot_path}")

if __name__ == "__main__":
    main()
