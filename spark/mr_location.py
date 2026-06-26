import os
# [QUAN TRỌNG] Ép kiểu mã hóa UTF-8 ở cấp độ Hệ điều hành (OS Level)
# Spark chạy trên Windows cực kỳ hay bị vỡ font tiếng Việt khi in ra console hoặc ghi file txt.
# Biến môi trường này ép toàn bộ luồng I/O của Python phải dùng UTF-8.
os.environ["PYTHONIOENCODING"] = "utf-8"

from pyspark.sql import SparkSession

MONGO_URI = (
    "mongodb+srv://khangnguyen2x0_db_user:khangnguyen2x0_db_user"
    "@cluster0.yyrcrds.mongodb.net/"
)
MONGO_DB         = "BigDataJobMarket"
MONGO_COL_INPUT  = "Jobs"
MONGO_COL_OUTPUT = "location_result"

OUTPUT_TXT = "D:/HDFS/JOB_MARKET_BIGDATA/data/parquet/location_result.txt"
OUTPUT_PARQUET = "D:/HDFS/JOB_MARKET_BIGDATA/data/parquet/location_result.parquet"

# ==============================================================================
# KHỞI TẠO SPARK SESSION (TRÁI TIM CỦA HỆ THỐNG PHÂN TÁN)
# ==============================================================================
# SparkSession là điểm vào (entry point) của mọi ứng dụng PySpark.
spark = SparkSession.builder \
    .appName("MR_Location") \
    .config("spark.sql.shuffle.partitions", "4") \
    .config("spark.mongodb.read.connection.uri",  MONGO_URI) \
    .config("spark.mongodb.write.connection.uri", MONGO_URI) \
    .getOrCreate()
    
# Giải thích cấu hình:
# 1. spark.sql.shuffle.partitions = 4: Mặc định Spark chia 200 phân vùng (partitions) khi gom nhóm (groupBy). 
#    Nhưng vì dữ liệu đồ án nhỏ, để 200 sẽ sinh ra 200 file rác rất nặng máy. Giảm xuống 4 giúp chạy cực nhanh.
# 2. spark.mongodb... : Tích hợp thẳng MongoDB Connector vào Spark để lưu kết quả trực tiếp lên Cloud.

spark.sparkContext.setLogLevel("WARN")

# ==============================================================================
# BƯỚC 1: EXTRACT (TRÍCH XUẤT TỪ HDFS)
# ==============================================================================
print("[INFO] Reading from HDFS: hdfs://localhost:9000/project/jobs")
# Spark đọc dữ liệu thô (CSV) lưu trữ trên hệ thống tệp phân tán Hadoop (HDFS).
# inferSchema=True: Spark tự động quét qua dữ liệu để đoán kiểu (String, Int, Float).
df = spark.read.csv("hdfs://localhost:9000/project/jobs", header=True, inferSchema=True)

# ==============================================================================
# BƯỚC 2: TRANSFORM (ÁP DỤNG MAP-REDUCE)
# ==============================================================================
# Đây chính là cốt lõi của tính toán phân tán. Hàm này sẽ được chia nhỏ ra cho nhiều Node cùng đếm.
# - Map: Trích xuất trường `location_clean`
# - Reduce (groupBy + count): Gom các địa điểm giống nhau lại và đếm tổng số lượng.
result = df.groupBy("location_clean") \
           .count() \
           .orderBy("count", ascending=False) # Xếp giảm dần (Top địa điểm tuyển nhiều nhất)

# ==============================================================================
# BƯỚC 3: LOAD (LƯU TRỮ ĐA NỀN TẢNG - POLYGLOT PERSISTENCE)
# ==============================================================================

# 3.1 Ghi ra File TXT (Dành cho con người đọc - Human Readable)
# Dùng hàm thuần Python open() thay vì Spark I/O để kiểm soát chặt chẽ việc xuống dòng và canh lề.
with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
    rows = result.collect() # Gom dữ liệu từ các Node về Node Master (Driver) để ghi ra file
    f.write(f"{'location_clean':<45} {'count':>6}\n")
    f.write("-" * 53 + "\n")
    for row in rows:
        f.write(f"{str(row['location_clean']):<45} {row['count']:>6}\n")

print(f"[OK] Da ghi ket qua vao: {OUTPUT_TXT}")

# 3.2 Ghi ra Parquet (Dành cho máy đọc - Machine Readable)
# Parquet là định dạng lưu trữ dạng cột (Columnar format) tiêu chuẩn của Big Data.
# Nó nén dữ liệu cực kỳ nhỏ và truy vấn cực nhanh so với CSV.
print(f"[INFO] Writing results to Parquet: {OUTPUT_PARQUET}")
result.write.mode("overwrite").parquet("file:///" + OUTPUT_PARQUET)
print(f"[OK] Da ghi ket qua Parquet vao: {OUTPUT_PARQUET}")

# 3.3 Ghi ra MongoDB (Dành cho Ứng dụng/Web)
# Đẩy thẳng dữ liệu đã thống kê lên MongoDB Atlas (Cloud Database) để
# ứng dụng Web (Streamlit/React) có thể kéo về vẽ biểu đồ (Dashboard) ngay lập tức.
print(f"[INFO] Writing results to MongoDB: {MONGO_DB}.{MONGO_COL_OUTPUT}")
result.write \
    .format("mongodb") \
    .option("database",   MONGO_DB) \
    .option("collection", MONGO_COL_OUTPUT) \
    .mode("overwrite") \
    .save()
print(f"[OK] MongoDB written: {MONGO_DB}.{MONGO_COL_OUTPUT}")

# ── Upload len HDFS ──────────────────────────────────────────────────────────
HDFS_OUTPUT_DIR = "/project/output/"
print(f"[INFO] Uploading TXT and Parquet to HDFS: {HDFS_OUTPUT_DIR}")

print("[OK] HDFS upload commands executed.")

spark.stop()