import requests
import pandas as pd
import os
import re
import shutil
import subprocess
import time
import random
import threading
from datetime import datetime

from concurrent.futures import ThreadPoolExecutor

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from bs4 import BeautifulSoup

# =====================================
# KHÓA TOÀN CỤC (GLOBAL LOCK)
# =====================================
# Khi chạy Đa luồng (Multithreading), nhiều tiến trình có thể giành nhau
# khởi động Chromedriver cùng một lúc gây ra lỗi xung đột (Conflict).
# Lock này giúp các luồng xếp hàng, khởi động Chrome từng cái một cho an toàn.
driver_lock = threading.Lock()


def detect_chrome_binary_and_version():
    """
    [QUAN TRỌNG] TỰ ĐỘNG DÒ TÌM TRÌNH DUYỆT CHROME
    -------------------------------------------------------------------------
    Vì script chạy trên nhiều máy khác nhau (Windows, Linux, Mac), hàm này có nhiệm vụ
    "lục lọi" tất cả các thư mục hệ thống mặc định để tìm đường dẫn file Chrome.exe.
    Mục đích: Nạp đúng cấu hình Chrome thật của người dùng (thay vì dùng Chromium ảo)
    để qua mặt hệ thống chống Bot (Cloudflare) dễ dàng hơn.
    """
    candidates = [
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        shutil.which("google-chrome"),
        os.path.join(
            os.environ.get("ProgramFiles", ""),
            "Google", "Chrome", "Application", "chrome.exe"
        ),
        os.path.join(
            os.environ.get("ProgramFiles(x86)", ""),
            "Google", "Chrome", "Application", "chrome.exe"
        ),
        os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Google", "Chrome", "Application", "chrome.exe"
        )
    ]

    for candidate in candidates:
        if not candidate or not os.path.exists(candidate):
            continue

        try:
            # Chạy lệnh CMD "chrome --version" để lấy phiên bản (VD: "Google Chrome 114.0.5735")
            output = subprocess.check_output(
                [candidate, "--version"],
                text=True,
                stderr=subprocess.STDOUT
            ).strip()

            # Dùng Regex móc lấy con số Major Version (VD: 114)
            match = re.search(r"(\d+)\.", output)
            if match:
                return candidate, int(match.group(1))

        except Exception:
            continue

    return None, None


def safe_quit_driver(driver):
    """
    [QUAN TRỌNG] DỌN DẸP TRÌNH DUYỆT / CHỐNG TRÀN RAM (Memory Leak)
    -------------------------------------------------------------------------
    Mỗi tab Selenium mở ra ngốn ~500MB RAM. Nếu mạng lag làm code sập giữa chừng 
    mà không tắt tab cũ đi, RAM sẽ bị nhồi đến sập máy tính (Memory Leak).
    Hàm này đảm bảo dù có báo lỗi "cháy nhà", tab Chrome vẫn phải bị "giết" triệt để.
    """
    if not driver:
        return

    try:
        driver.quit() # Đóng tab
    except Exception as e:
        print("DRIVER QUIT WARNING:", e)
    finally:
        # Xóa tham chiếu tới hàm quit để Python tự động dọn dẹp rác (Garbage Collector)
        try:
            driver.quit = lambda *args, **kwargs: None
        except Exception:
            pass

# =====================================
# LƯU TRỮ
# =====================================

all_jobs = []

# =====================================
# LẤY URL VIỆC LÀM (API FETCHING)
# =====================================
# Khác với ITviec phải cào giao diện, VietnamWorks có một API nội bộ (REST API)
# trả về chuỗi JSON rất gọn. Việc gọi thẳng API giúp thu thập hàng ngàn URL 
# chỉ trong vài giây mà không sợ bị chặn.

job_urls = []

# Vòng lặp quét 100 trang * 20 job/trang ~= 2000 job (Đủ chuẩn mẫu Big Data)
for page in range(1, 101):

    print(f"GET PAGE {page}")

    # 1. Điểm mấu chốt (Reverse Engineering): 
    # Bằng cách mở DevTools (F12) -> Network, ta phát hiện VietnamWorks không render HTML thẳng
    # mà gọi ngầm một API GraphQL/REST để lấy dữ liệu. Bắt đúng URL này sẽ tiết kiệm 90% công sức.
    url = "https://ms.vietnamworks.com/job-search/v1.0/search"

    # 2. Payload (Dữ liệu gửi đi):
    # API yêu cầu phương thức POST. Ta gửi cục JSON giả lập hành động người dùng
    # gõ chữ "IT" vào ô tìm kiếm và chọn trang số `page`.
    payload = {
        "query": "IT",
        "page": page,
        "hitsPerPage": 20 # Số lượng việc làm mỗi trang
    }

    # 3. Giả mạo danh tính (Spoofing Headers):
    # API chặn các request đến từ code (như Python Requests). 
    # Ta phải "mặc áo khoác" User-Agent để server lầm tưởng đây là trình duyệt Chrome thật.
    headers = {
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        )
    }

    try:
        # 4. Bắn Request POST thẳng vào máy chủ VietnamWorks
        response = requests.post(
            url,
            json=payload,
            headers=headers
        )

        # 5. Phân giải (Parse) dữ liệu JSON trả về cực kỳ nhẹ và sạch
        data = response.json()

        jobs = data.get("data", [])

        # 6. Trích xuất thuộc tính jobUrl của từng công việc
        for job in jobs:

            job_url = job.get("jobUrl")

            if job_url:
                job_urls.append(job_url)

    except Exception as e:

        print("API ERROR:", e)

print("\nTOTAL URLS:", len(job_urls))

# =====================================
# TẠO DRIVER (BYPASS CLOUDFLARE ANTI-BOT)
# =====================================

def create_driver():
    """
    [QUAN TRỌNG] KỸ THUẬT VƯỢT TƯỜNG LỬA CHỐNG BOT
    VietnamWorks sử dụng Cloudflare Turnstile để chặn các công cụ cào dữ liệu thô (như Requests).
    Do đó, bắt buộc phải dùng Selenium giả lập một người dùng thật đang mở trình duyệt Chrome.
    Hàm này tinh chỉnh các thông số (Options) để xóa bỏ "dấu vân tay" của Bot.
    """

    with driver_lock:

        chrome_binary, chrome_major = detect_chrome_binary_and_version()
        chrome_major = chrome_major or 148

        print("CHROME DETECTED:", chrome_binary or "UNKNOWN")
        print("CHROME MAJOR:", chrome_major)

        options = Options()

        options.add_argument("--start-maximized")

        # KHÔNG dùng chế độ ẩn (headless = True) vì Cloudflare sẽ phát hiện ra ngay lập tức
        # Chấp nhận mở cửa sổ UI để đánh lừa hệ thống bảo mật.

        # 1. Tắt cờ báo hiệu "Tôi là Robot"
        # Mặc định Selenium bật cờ 'navigator.webdriver = true'. Cloudflare quét thấy cái này là ban ngay.
        # Dòng này tắt cờ đó đi, giả dạng thành trình duyệt bình thường.
        options.add_argument(
            "--disable-blink-features=AutomationControlled"
        )

        # 2. Vô hiệu hóa Sandbox (Môi trường cách ly an toàn)
        # Bắt buộc khi chạy trên Linux/Server (như Docker, Ubuntu) để tránh lỗi crash Chrome.
        options.add_argument("--no-sandbox")

        # 3. Tối ưu bộ nhớ chia sẻ (Shared Memory)
        # Mặc định /dev/shm trên Linux chỉ có 64MB. Cào web nặng sẽ bị tràn và crash (Trang trắng).
        # Tắt đi để Chrome dùng thẳng ổ cứng (/tmp) làm RAM ảo.
        options.add_argument("--disable-dev-shm-usage")

        # 4. Tắt phần cứng tăng tốc đồ họa (Hardware Acceleration)
        # Script chạy ngầm không cần vẽ đồ họa 3D hay render mượt. Tắt đi để tiết kiệm RAM/CPU.
        options.add_argument("--disable-gpu")

        # 5. Ghi đè chữ ký User-Agent
        # Hardcode một chuỗi User-Agent của một trình duyệt Chrome xịn đời mới nhất.
        # Chống lại việc Cloudflare nhận diện ra các bản Chrome cũ rích hay thư viện tự động.
        options.add_argument(
            "--user-agent=Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/148.0.0.0 Safari/537.36"
        )

        # 6. Ép Selenium xài đúng file Chrome.exe đã quét được ở trên (Không xài Chromium ảo)
        if chrome_binary:
            options.binary_location = chrome_binary

        service = Service()

        # 7. Khởi chạy Chrome với toàn bộ "vũ khí" ngụy trang đã nạp
        driver = webdriver.Chrome(
            service=service,
            options=options
        )

        return driver

# =====================================
# CÀO VIỆC LÀM
# =====================================

def crawl_job(job_url):

    driver = None

    try:

        driver = create_driver()

        print("OPEN:", job_url)

        driver.get(job_url)

        # nghỉ ngẫu nhiên tránh bị chặn
        time.sleep(random.uniform(3, 5))

        # giả lập cuộn trang như người dùng thật
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight/2);"
        )

        time.sleep(random.uniform(1, 2))

        html = driver.page_source

        # phát hiện bị chặn
        if "403 Forbidden" in html:

            print("BỊ CHẶN")

            return None

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        # =====================================
        # TIÊU ĐỀ
        # =====================================

        title = ""

        h1 = soup.find("h1")

        if h1:
            title = h1.get_text(strip=True)

        # =====================================
        # CÔNG TY (CSS SELECTOR FALLBACK)
        # =====================================
        # Vì VietnamWorks hay đổi tên class giao diện (kiểu mã hóa ngẫu nhiên như .sc-fqkvVR),
        # ta phải dùng chiến lược "Tìm Link trước, Tìm Class sau".

        company = ""

        # Danh sách đen: Bỏ qua các text quảng cáo bị nhận nhầm là Tên Công Ty
        company_blacklist = [
            "lưu công việc",
            "tải upzi",
            "xem thêm",
            "việc làm",
            "dành cho nhà tuyển dụng",
            "tất cả danh mục",
            "việc làm theo khu vực",
            "việc làm theo ngành nghề",
            "vietnamworks"
        ]

        # 1. Tìm thẻ <a href="/nha-tuyen-dung/..."> chứa tên công ty (Chuẩn nhất)
        company_link_candidates = soup.find_all(
            "a",
            href=re.compile(r"/nha-tuyen-dung/")
        )

        for company_element in company_link_candidates:
            text = company_element.get_text(" ", strip=True)
            # Tên công ty thường dài 3-120 ký tự
            if 3 < len(text) < 120:
                lowered_text = text.lower()
                # Kiểm tra xem có dính từ khóa cấm không
                if not any(term in lowered_text for term in company_blacklist):
                    company = text
                    break

        # 2. Nếu không có link, cào mù bằng mảng các CSS Selector phổ biến
        if not company:
            company_selectors = [
                ".company-name",
                ".sc-fqkvVR", # Tên class do React/Styled-Component sinh ra tự động
                "[class*=company]" # Bất cứ class nào có chữ "company"
            ]

            for selector in company_selectors:

                company_element = soup.select_one(selector)

                if company_element:

                    text = company_element.get_text(strip=True)

                    if 3 < len(text) < 100:

                        company = text
                        break

        # =====================================
        # LƯƠNG (REGEX EXTRACTION)
        # =====================================
        # Khác với ITviec lưu JSON-LD, Vietnamworks giấu lương chung vào HTML.
        # Ta dùng Biểu thức chính quy (Regex) để truy quét bất kỳ cụm từ nào giống mức lương.

        salary = ""

        # Mẫu Regex bắt cấu trúc: "15 - 20 Triệu", "1000 USD/tháng"
        salary_pattern = re.compile(
            r"(\$?\s?\d+[.,]?\d*\s?(triệu|VND|USD|\/tháng)?)",
            re.IGNORECASE
        )

        salary_blacklist = [
            "tuyển",
            "ứng tuyển",
            "mô tả công việc",
            "yêu cầu công việc",
            "thông tin việc làm",
            "địa điểm làm việc",
            "việc làm cùng công ty",
            "tại ",
            "để xem nhiều việc làm",
            "intern",
            "fresher",
            "dưới 3 năm kinh nghiệm",
            "tải upzi"
        ]

        salary_candidates = []

        # Quét dọn toàn bộ các thẻ văn bản trên web
        for tag in soup.find_all(["span", "div", "p"]):
            text = tag.get_text(" ", strip=True)
            
            # Lương thường là 1 đoạn text ngắn
            if not text or len(text) > 80:
                continue

            lowered_text = text.lower()
            if any(term in lowered_text for term in salary_blacklist):
                continue

            # Ưu tiên 1: Chứa chữ "thương lượng"
            if "thương lượng" in lowered_text:
                salary = "Thương lượng"
                break

            # Ưu tiên 2: Khớp Mẫu Regex (VD: 15-20 Triệu)
            if salary_pattern.search(text):
                salary = text
                break

            # Ưu tiên 3: Nếu không khớp Regex nhưng có chữ "triệu/usd", nhét tạm vào mảng dự phòng
            if any(token in lowered_text for token in ["triệu", "usd", "vnd", "/tháng", "/month"]):
                salary_candidates.append(text)

        # Trả về kết quả dự phòng nếu Ưu tiên 1, 2 thất bại
        if not salary and salary_candidates:
            salary = salary_candidates[0]

        # =====================================
        # ĐỊA ĐIỂM (DICTIONARY MAPPING & TEXT SCANNING)
        # =====================================
        # Địa chỉ tuyển dụng thường rất dài (VD: "Tầng 5, Tòa nhà X, Quận Y, Hồ Chí Minh").
        # Ta dùng một Từ điển Ánh xạ (Dictionary Mapping) để chuyển đổi cụm từ thô 
        # thành Mã chuẩn (HN, HCM, DN) phục vụ cho bước Gom cụm (Clustering) khi vẽ biểu đồ.

        location = ""

        location_mapping = {
            "Hồ Chí Minh": "HCM",
            "Hà Nội": "HN",
            "Đà Nẵng": "DN"
        }

        location_found = False

        # Quét dọn toàn bộ văn bản thuần (đã tước bỏ thẻ HTML) trên trang
        for t in soup.stripped_strings:
            if location_found:
                break

            # Nếu phát hiện bất kỳ chuỗi nào chứa tên 3 thành phố lớn, lập tức gắn mã chuẩn và dừng vòng lặp
            for source_location, normalized_location in location_mapping.items():
                if source_location in t:
                    location = normalized_location
                    location_found = True
                    break

        # =====================================
        # KỸ NĂNG (HEURISTIC EXTRACTION)
        # =====================================
        # Do không có thẻ HTML chuẩn cho kỹ năng, script quét toàn bộ các thẻ liên kết <a> và <span>.
        # Nếu chữ ngắn (dưới 25 ký tự) và không lọt vào danh sách đen (blacklist) thì được coi là Kỹ năng (Python, AWS...)

        skills = []

        # 1. Danh sách Đen (Blacklist Filtering)
        # Loại bỏ các nút bấm/liên kết hệ thống thường bị nhận nhầm là kỹ năng.
        blacklist = [
            "việc làm",
            "đăng nhập",
            "ứng tuyển",
            "trang chủ",
            "tìm kiếm",
            "upzi",
            "lưu công việc",
            "thương lượng",
            "lượt xem"
        ]

        # 2. Quét thẻ Tag
        # Kỹ năng thường được đặt trong các thẻ <a> (nhãn liên kết) hoặc <span> (badge)
        for tag in soup.find_all(["a", "span"]):
            text = tag.get_text(strip=True)

            # 3. Màng lọc Heuristic (Dựa trên suy luận)
            # - Tên kỹ năng thường từ 3 đến 24 ký tự (VD: "Python", "ReactJS", "AWS"). Quá dài thì là đoạn văn.
            # - Tên kỹ năng lập trình hiếm khi chứa số xen ngang hỗn loạn (Tuy nhiên luật chặn số ở đây
            #   khá gắt, có thể sẽ bỏ qua B2B, HTML5. Ở mức độ đơn giản thì chấp nhận được).
            if (
                2 < len(text) < 25
                and not any(char.isdigit() for char in text)
            ):

                skip = False

                # 4. Kiểm duyệt qua Blacklist
                for b in blacklist:
                    if b in text.lower():
                        skip = True
                        break

                # 5. Nếu an toàn và chưa bị trùng -> Đẩy vào giỏ Kỹ năng
                if not skip and text not in skills:
                    skills.append(text)

        # =====================================
        # MÔ TẢ (DESCRIPTION HEURISTIC)
        # =====================================
        # Rút gọn phần mô tả công việc (Job Description) để tránh làm phình to file CSV
        # và làm nặng các thuật toán Machine Learning phía sau.

        description = ""

        # Chỉ tìm trong thẻ <p> (Đoạn văn) vì JD thường được viết thành từng đoạn
        paragraphs = soup.find_all("p")

        description_texts = []

        for paragraph in paragraphs:
            text = paragraph.get_text(strip=True)

            # Lọc bỏ các dòng ngắn củn (như "Quyền lợi", "Yêu cầu")
            # Chỉ lấy các đoạn văn dài có mang thông tin ngữ nghĩa (Hơn 50 ký tự)
            if len(text) > 50:
                description_texts.append(text)

        # Chống tràn dữ liệu: Chỉ lấy tối đa 5 đoạn văn bản đầu tiên 
        # (Thường là phần tóm tắt công việc quan trọng nhất, cắt bỏ phần khoe khoang công ty phía dưới)
        description = " ".join(description_texts[:5])

        # Đóng gói kết quả cào được thành 1 DTO (Data Transfer Object) dạng Dictionary
        result = {
            "title": title,
            "company": company,
            "salary": salary,
            "location": location,
            "description": description,
            "skills": ", ".join(skills[:10]), # Chỉ lấy tối đa 10 kỹ năng đầu tiên
            "url": job_url,
            "crawl_time": datetime.now()
        }

        print("COLLECTED:", title)

        return result

    except Exception as e:

        print("CRAWL ERROR:", job_url, e)

        return None

    finally:

        safe_quit_driver(driver)

# =====================================
# ĐA LUỒNG (MULTITHREADING)
# =====================================
# Sử dụng ThreadPool để mở nhiều Tab Chrome cào cùng lúc giúp giảm thời gian chạy.
# [LƯU Ý]: max_workers=2 vì mỗi Selenium tốn khoảng 500MB RAM. Mở nhiều máy tính sẽ bị treo.

with ThreadPoolExecutor(max_workers=2) as executor:

    results = executor.map(
        crawl_job,
        job_urls
    )

    for r in results:

        if r:

            all_jobs.append(r)

            # tự động lưu
            if len(all_jobs) % 10 == 0:

                pd.DataFrame(all_jobs).to_csv(
                    "autosave.csv",
                    index=False,
                    encoding="utf-8-sig"
                )

                print("AUTOSAVED")

# =====================================
# LƯU KẾT QUẢ CUỐI (DATA EXPORT)
# =====================================

# Đẩy mảng Dictionary vào Pandas DataFrame (Thư viện chuẩn Big Data)
df = pd.DataFrame(all_jobs)

# Data Cleansing: Dọn dẹp dữ liệu trùng lặp (Có thể do mạng lag cào 2 lần)
df.drop_duplicates(inplace=True)

# Ghi ra file CSV. 
# QUAN TRỌNG: encoding="utf-8-sig" bắt buộc dùng để Excel mở tiếng Việt không bị lỗi font (lỗi ký tự ô vuông)
df.to_csv(
    "vnwork.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nDONE")
print("TOTAL:", len(df))