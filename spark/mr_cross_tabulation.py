import os
os.environ["PYTHONIOENCODING"] = "utf-8"

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

MONGO_URI = (
    "mongodb+srv://khangnguyen2x0_db_user:khangnguyen2x0_db_user"
    "@cluster0.yyrcrds.mongodb.net/"
)
MONGO_DB         = "BigDataJobMarket"
MONGO_COL_OUTPUT = "cross_tabulation_result"

OUTPUT_TXT = "D:/HDFS/JOB_MARKET_BIGDATA/data/parquet/cross_tabulation_result.txt"
OUTPUT_PARQUET = "D:/HDFS/JOB_MARKET_BIGDATA/data/parquet/cross_tabulation_result.parquet"

def main():
    spark = SparkSession.builder \
        .appName("JobMarket_Cross_Tabulation") \
        .config("spark.sql.shuffle.partitions", "4") \
        .config("spark.mongodb.read.connection.uri",  MONGO_URI) \
        .config("spark.mongodb.write.connection.uri", MONGO_URI) \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")

    print("[INFO] Reading from HDFS: hdfs://localhost:9000/project/jobs")
    df = spark.read.csv("hdfs://localhost:9000/project/jobs", header=True, inferSchema=True)
    df = df.withColumn("salary_final_vnd", F.col("salary_final_vnd").cast("double"))
    
 
    # tất cả về 3 siêu đô thị: HCM, HN, DN. Phần còn lại đẩy vào "Other".
    df = df.withColumn("loc", F.when(F.col("location_clean").like("%Hồ Chí Minh%"), "HCM")
                              .when(F.col("location_clean").like("%Hà Nội%"), "HN")
                              .when(F.col("location_clean").like("%Đà Nẵng%"), "DN")
                              .otherwise("Other"))
    
    # Lọc nhiễu (Filter Noise): Xóa bỏ các dòng không có Kỹ năng hoặc không có Lương.
    # Lược bỏ các tỉnh lẻ ("Other") vì dữ liệu quá thưa thớt (Sparse Data), dễ gây nhiễu biểu đồ.
    df = df.filter(F.col("skills_clean").isNotNull() & F.col("salary_final_vnd").isNotNull() & (F.col("loc") != "Other"))
    
    # ==============================================================================
    # BƯỚC 2: MAP PHASE (TRẢI PHẲNG DỮ LIỆU - EXPLODE)
    # ==============================================================================
    # Trong MongoDB, `skills` là một chuỗi phân cách dấu phẩy: "Java, Python, SQL"
    # Dùng hàm `F.explode()` để tách chuỗi này ra. 
    # [1 Dòng "Java, Python"] -> [Biến thành 2 Dòng riêng biệt: "Java" và "Python"].
    mapped_df = df.withColumn("skill", F.explode(F.split(F.lower(F.col("skills_clean")), ",")))
    # Xóa khoảng trắng thừa (ví dụ: " Java " -> "Java") để khi đếm không bị tách làm 2 kỹ năng khác nhau
    mapped_df = mapped_df.withColumn("skill", F.trim(F.col("skill")))
    # Lọc bỏ các kỹ năng rỗng (do lỗi chuỗi có dấu phẩy dư ở cuối: "Java,Python,")
    mapped_df = mapped_df.filter(F.col("skill") != "")
    
    # ==============================================================================
    # BƯỚC 3: REDUCE PHASE (BẢNG CHÉO - CROSS TABULATION / PIVOT)
    # ==============================================================================
    # Kỹ thuật Pivot (Xoay trục dữ liệu) cực kỳ phổ biến trong Big Data & Data Warehouse.
    # Mục đích: Chuyển dữ liệu DỌC thành dữ liệu NGANG để làm báo cáo so sánh.
    # 
    # Giải phẫu dòng code bên dưới:
    # 1. groupBy("skill")       : Nhóm tất cả các dòng có cùng Kỹ năng lại (VD: Gom tất cả việc làm yêu cầu "Java").
    #                             Đây là trục dọc (Trục Y) của bảng.
    # 2. pivot("loc", [...])    : Xoay trục ngang. Lấy các giá trị (HCM, HN, DN) của cột `loc` biến thành 3 CỘT MỚI.
    #                             Lưu ý: Truyền sẵn mảng ["HCM", "HN", "DN"] để Spark không phải tốn công 
    #                             quét toàn bộ dữ liệu để tìm các giá trị duy nhất (Tối ưu hiệu năng cực lớn).
    # 3. agg(...)               : Aggregate (Tổng hợp). Điền giá trị gì vào các ô trống ở giữa bảng chéo?
    #                             Ở đây ta tính Lương Trung Bình: F.avg("salary_final_vnd").
    # 4. F.round(... / 1M, 1)   : Tiền Việt Nam có quá nhiều số 0. Chia cho 1.000.000 và làm tròn 1 chữ số thập phân 
    #                             (VD: 25.500.000 -> 25.5 Triệu).
    # 5. fillna(0)              : Nếu kỹ năng "Python" không có ai tuyển ở Đà Nẵng, ô đó sẽ bị Null. 
    #                             Hàm này tự động điền số 0 vào để tránh lỗi tính toán phía sau.
    #
    # Kết quả: Ta có 1 bảng gồm 4 cột: [skill, HCM, HN, DN]. Dễ dàng trả lời câu hỏi: "Lương Java ở HCM hay HN cao hơn?".
    pivot_df = mapped_df.groupBy("skill").pivot("loc", ["HCM", "HN", "DN"]).agg(
        F.round(F.avg("salary_final_vnd") / 1000000, 1).alias("avg_sal_M")
    ).fillna(0)
    
    # ==============================================================================
    # BƯỚC 4: SORTING (TÌM TOP KỸ NĂNG TRẢ LƯƠNG CAO NHẤT)
    # ==============================================================================
    # Giải phẫu dòng code:
    # 1. withColumn("total_avg", ...) : Khởi tạo 1 cột tạm (Ảo). Cột này bằng (HCM + HN + DN) / 3.
    #                                   Ta cần cột này làm tiêu chí để xếp hạng mức độ "Giàu" chung của kỹ năng đó.
    # 2. filter(F.col("HCM") > 0)     : Lọc "Nhiễu Thống Kê" (Statistical Outliers / Bias). 
    #                                   [TẠI SAO?] Giả sử có một công nghệ cực hiếm (VD: "Cobol"), cả nước chỉ có 
    #                                   đúng 1 công ty ở Hà Nội tuyển dụng 1 người với mức lương "trên trời" 100 Triệu.
    #                                   Nếu không lọc, "Cobol" sẽ lập tức nghiễm nhiên đứng Top 1 Bảng Xếp Hạng Lương.
    #                                   Điều này gây ra sự "ảo tưởng" cho người xem báo cáo vì nó không đại diện 
    #                                   cho xu hướng chung của thị trường.
    #                                   [GIẢI PHÁP] Bắt buộc kỹ năng đó phải có giao dịch tuyển dụng ở TP.HCM 
    #                                   (Trung tâm IT lớn nhất nước, nơi có số lượng mẫu Data đủ lớn) thì mới 
    #                                   được đưa vào xếp hạng. Nếu HCM = 0 -> Loại ngay lập tức.
    # 3. orderBy(F.desc... limit(30)  : Sắp xếp giảm dần (descending) theo cột `total_avg` vừa tạo.
    #                                   Cắt lấy Top 30 kỹ năng dẫn đầu thị trường.
    final_df = pivot_df.withColumn("total_avg", (F.col("HCM") + F.col("HN") + F.col("DN")) / 3) \
                       .filter(F.col("HCM") > 0) \
                       .orderBy(F.desc("total_avg")).limit(30)
                       
    print(f"[INFO] Writing results to Parquet: {OUTPUT_PARQUET}")
    final_df.drop("total_avg").write.mode("overwrite").parquet("file:///" + OUTPUT_PARQUET)
    print(f"[OK] Da ghi ket qua Parquet vao: {OUTPUT_PARQUET}")
    
    results = final_df.collect()
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("=== CROSS-TABULATION: AVERAGE SALARY (M) BY SKILL & LOCATION ===\n\n")
        f.write(f"{'SKILL':<20} | {'HCM':<10} | {'HN':<10} | {'DN':<10}\n")
        f.write("-" * 55 + "\n")
        for row in results:
            f.write(f"{row['skill']:<20} | {row['HCM']:<10.1f} | {row['HN']:<10.1f} | {row['DN']:<10.1f}\n")
            
    print(f"[OK] Da ghi ket qua vao: {OUTPUT_TXT}")

    print(f"[INFO] Writing results to MongoDB: {MONGO_DB}.{MONGO_COL_OUTPUT}")
    final_df.drop("total_avg").write \
        .format("mongodb") \
        .option("database",   MONGO_DB) \
        .option("collection", MONGO_COL_OUTPUT) \
        .mode("overwrite") \
        .save()
    print(f"[OK] MongoDB written: {MONGO_DB}.{MONGO_COL_OUTPUT}")

    # ── Upload len HDFS ──────────────────────────────────────────────────────────
    HDFS_OUTPUT_DIR = "/project/output/"
    print(f"[INFO] Uploading TXT and Parquet to HDFS: {HDFS_OUTPUT_DIR}")
    os.system(f"hdfs dfs -mkdir -p {HDFS_OUTPUT_DIR}")
    os.system(f"hdfs dfs -rm -r -f {HDFS_OUTPUT_DIR}" + os.path.basename(OUTPUT_TXT))
    os.system(f"hdfs dfs -rm -r -f {HDFS_OUTPUT_DIR}" + os.path.basename(OUTPUT_PARQUET))
    os.system(f"hdfs dfs -put -f {OUTPUT_TXT} {HDFS_OUTPUT_DIR}")
    os.system(f"hdfs dfs -put -f {OUTPUT_PARQUET} {HDFS_OUTPUT_DIR}")
    print("[OK] HDFS upload commands executed.")

    spark.stop()

if __name__ == "__main__":
    main()
