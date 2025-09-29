from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import os
from datetime import datetime
import pytesseract
from PIL import Image
import io
import base64
import concurrent.futures
import json
import glob
import csv
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
chromedriver_autoinstaller.install()
driver = webdriver.Chrome(options=chrome_options)

# Thêm cấu hình Tesseract
pytesseract.pytesseract.tesseract_cmd = "tesseract"
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Thiết lập Chrome options
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-dev-shm-usage")
# driver = webdriver.Chrome(service=Service("/usr/local/bin/chromedriver"), options=chrome_options)

def get_company_links(driver, url):
    driver.get(url)
    links = []
    try:
        # Get all company elements using search-results class
        companies = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "search-results"))
        )
        
        for company in companies:
            # Get link from first a tag in company element
            link = company.find_element(By.TAG_NAME, "a").get_attribute('href')
            if link:
                links.append(link)
                
    except Exception as e:
        print(f"Lỗi khi lấy links: {str(e)}")
    return links

def is_mobile_phone(phone):
    """Kiểm tra xem số điện thoại có phải là di động không"""
    if not phone or len(phone) < 9:
        return False
    # Đầu số điện thoại di động ở Việt Nam
    mobile_prefixes = ['03', '05', '07', '08', '09']
    return any(phone.startswith(prefix) for prefix in mobile_prefixes)

def get_company_detail(driver, url):
    driver.get(url)
    try:
        data = {
            'Tên công ty': '',
            'Mã số thuế': '',
            'Địa chỉ': '',
            'Đại diện pháp luật': '',
            'Trạng thái': '',
            'Ngày cấp': '',
            'Điện thoại': ''
        }
        
        # Đợi và lấy thông tin từ div class jumbotron
        company_info = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "jumbotron"))
        )
        
        # Lấy tên công ty từ thẻ h4
        name_elem = company_info.find_element(By.TAG_NAME, "h4")
        data['Tên công ty'] = name_elem.text.strip()
        
        # Lấy các thông tin khác
        text_content = company_info.text
        for line in text_content.split('\n'):
            if 'Mã số thuế:' in line:
                data['Mã số thuế'] = line.replace('Mã số thuế:', '').strip()
            elif 'Địa chỉ:' in line:
                data['Địa chỉ'] = line.replace('Địa chỉ:', '').strip()
            elif 'Đại diện pháp luật:' in line:
                data['Đại diện pháp luật'] = line.replace('Đại diện pháp luật:', '').strip()
            elif 'Trạng thái:' in line:
                data['Trạng thái'] = line.replace('Trạng thái:', '').strip()
            elif 'Ngày cấp giấy phép:' in line:
                data['Ngày cấp'] = line.replace('Ngày cấp giấy phép:', '').strip()
            elif 'Điện thoại trụ sở:' in line:
                phone = line.replace('Điện thoại trụ sở:', '').strip()
                if is_mobile_phone(phone):
                    data['Điện thoại'] = phone
        
        # Xử lý OCR số điện thoại
        try:
            phone_img = company_info.find_element(By.XPATH, ".//text()[contains(.,'Điện thoại trụ sở:')]/following-sibling::img")
            if phone_img:
                img_src = phone_img.get_attribute('src')
                if 'base64,' in img_src:
                    img_data = base64.b64decode(img_src.split(',')[1])
                    image = Image.open(io.BytesIO(img_data))
                    
                    text = pytesseract.image_to_string(
                        image,
                        config='--psm 7 -c tessedit_char_whitelist=0123456789'
                    )
                    
                    phone = ''.join(filter(str.isdigit, text))
                    if is_mobile_phone(phone):
                        data['Điện thoại'] = phone
                        print(f"Đã tìm thấy số điện thoại di động qua OCR: {phone}")
                        return data

        except Exception as e:
            print(f"Lỗi khi xử lý ảnh số điện thoại: {str(e)}")

        return data

    except Exception as e:
        print(f"Lỗi khi lấy chi tiết công ty {url}: {str(e)}")
        return None

def save_to_excel(companies, area_name, page_num=None):
    # Tạo thư mục data/ho-chi-minh/{area_name} nếu chưa có
    data_dir = f"data/ho-chi-minh/{area_name}"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # Tạo tên file với timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if page_num:
        filename = f"{data_dir}/companies_page{page_num}_{timestamp}.xlsx"
    else:
        filename = f"{data_dir}/companies_full_{timestamp}.xlsx"
    
    df = pd.DataFrame(companies)
    df.to_excel(filename, index=False)
    print(f"Đã lưu dữ liệu vào file: {filename}")
    return filename

def crawl_area(driver, area_path):
    base_url = f"https://www.tratencongty.com/thanh-pho-ho-chi-minh/{area_path}"
    # Đọc checkpoint
    start_page = get_start_page_from_files(area_path)
    print(f"Bắt đầu crawl {area_path} từ trang {start_page}")

    page = start_page
    all_companies = []

    while True:
        current_url = f"{base_url}/?page={page}" if page > 1 else base_url
        print(f"Đang xử lý trang {page}...")

        company_links = get_company_links(driver, current_url)
        if not company_links:
            print(f"Không tìm thấy công ty nào ở trang {page}")
            break

        print(f"Tìm thấy {len(company_links)} công ty trong trang {page}")
        for link in company_links:
            print(f"Đang xử lý: {link}")
            company_detail = get_company_detail(driver, link)
            if company_detail:
                company_detail['Khu vực'] = area_path
                saver.save_company(company_detail)  # 🔹 Lưu ngay vào CSV
                all_companies.append(company_detail)
                print("Đã lưu công ty vào CSV tạm!")
            time.sleep(1.5)  # Có thể giảm xuống vì đã lưu incremental

        # Xong 1 trang → export CSV sang Excel
        saver.export_to_excel(page)
        save_checkpoint(area_path, page)

        page += 1
        time.sleep(0.3)

    return all_companies

def save_checkpoint(area_name, page):
    os.makedirs("checkpoints", exist_ok=True)
    ckpt_file = f"checkpoints/{area_name.replace('/', '_')}.json"
    with open(ckpt_file, "w", encoding="utf-8") as f:
        json.dump({"last_page": page}, f)
    print(f"Đã lưu checkpoint: {area_name} - Trang {page}")

def load_checkpoint(area_name):
    ckpt_file = f"checkpoints/{area_name.replace('/', '_')}.json"
    if os.path.exists(ckpt_file):
        with open(ckpt_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("last_page", 1)
    return 1

def get_start_page_from_files(area_path):
    # Thư mục chứa file excel
    data_dir = f"data/ho-chi-minh/{area_path.replace('/', '_')}"
    if not os.path.exists(data_dir):
        return 1  # Nếu chưa có thư mục thì bắt đầu từ trang 1

    # Lấy danh sách tất cả file Excel trong thư mục
    files = glob.glob(f"{data_dir}/*.xlsx")

    if not files:
        return 1  # Nếu chưa có file thì bắt đầu từ trang 1

    # Số file hiện tại = số trang đã crawl
    return len(files) + 1  # Trang kế tiếp


def crawl_area(driver, area_path):
    base_url = f"https://www.tratencongty.com/thanh-pho-ho-chi-minh/{area_path}"
    all_companies = []

    # Đọc checkpoint
    start_page = get_start_page_from_files(area_path)
    print(f"Bắt đầu crawl {area_path} từ trang {start_page}")

    page = start_page
    while True:
        current_url = f"{base_url}/?page={page}" if page > 1 else base_url
        print(f"Đang xử lý trang {page}...")

        page_companies = []
        company_links = get_company_links(driver, current_url)
        if not company_links:
            print(f"Không tìm thấy công ty nào ở trang {page}")
            break

        print(f"Tìm thấy {len(company_links)} công ty trong trang {page}")
        for link in company_links:
            print(f"Đang xử lý: {link}")
            company_detail = get_company_detail(driver, link)
            if company_detail:
                company_detail['Khu vực'] = area_path
                page_companies.append(company_detail)
                all_companies.append(company_detail)
                print("Đã lấy thông tin thành công!")
            time.sleep(2)

        if page_companies:
            save_to_excel(page_companies, area_path.replace('/', '_'), page)
            save_checkpoint(area_path, page)  # 🔹 Lưu checkpoint sau khi xong 1 trang

        page += 1
        time.sleep(1)

    return all_companies


try:
    driver = webdriver.Chrome(options=chrome_options)

    start_time = time.time()  # Thời gian bắt đầu toàn bộ quá trình

    # Danh sách các khu vực của TP HCM, ưu tiên Quận 1
    areas_hcm = [
        # "quan-tan-binh",
        # "quan-tan-phu",
        "quan-1",  # Ưu tiên cào trước
        # "quan-3",
        "quan-binh-thanh",
        # "quan-phu-nhuan",
        "quan-go-vap",
        # "quan-7",
        "quan-10",
        # "quan-5",
        "quan-6",
        # "quan-8",
        "quan-4",
        # "quan-2",
        "quan-9",
        # "quan-12",
        "huyen-binh-chanh",
        # "huyen-hoc-mon",
        "huyen-cu-chi",
        # "huyen-nha-be",
        "huyen-can-gio"
    ]

    all_area_companies = []


    # Cào riêng Quận 1 với timeout 30 phút
    print("Bắt đầu cào dữ liệu Quận 1 (tối đa 30 phút)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future_q1 = executor.submit(crawl_area, driver, areas_hcm[0])
        try:
            quan_1_companies = future_q1.result(timeout=1800)  # 30 phút
        except concurrent.futures.TimeoutError:
            print("Quận 1: Đã hết thời gian 30 phút!")
            quan_1_companies = []
    all_area_companies.extend(quan_1_companies)

    # Lưu dữ liệu Quận 1 riêng
    if quan_1_companies:
        timestamp_q1 = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_file_q1 = f"data/ho-chi-minh/quan-1_{timestamp_q1}.xlsx"
        os.makedirs("data/ho-chi-minh", exist_ok=True)
        df_q1 = pd.DataFrame(quan_1_companies)
        df_q1.to_excel(final_file_q1, index=False)
        print(f"Đã lưu {len(quan_1_companies)} công ty của Quận 1!")

    # Các khu vực còn lại, mỗi khu vực chạy ở một luồng riêng biệt, timeout 30 phút
    print("Bắt đầu cào các khu vực còn lại của TP HCM (mỗi khu vực tối đa 30 phút)...")
    other_areas = areas_hcm[1:]
    other_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(other_areas)) as executor:
        future_map = {executor.submit(crawl_area, driver, area): area for area in other_areas}
        for future in concurrent.futures.as_completed(future_map):
            area = future_map[future]
            try:
                area_companies = future.result(timeout=1800)  # 30 phút
            except concurrent.futures.TimeoutError:
                print(f"Khu vực {area}: Đã hết thời gian 30 phút!")
                area_companies = []
            other_results.extend(area_companies)
            # Lưu từng khu vực riêng
            if area_companies:
                timestamp_area = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_file_area = f"data/ho-chi-minh/{area}_{timestamp_area}.xlsx"
                os.makedirs("data/ho-chi-minh", exist_ok=True)
                df_area = pd.DataFrame(area_companies)
                df_area.to_excel(final_file_area, index=False)
                print(f"Đã lưu {len(area_companies)} công ty của khu vực {area}!")
    all_area_companies.extend(other_results)

    # Lưu tổng hợp tất cả các khu vực
    if all_area_companies:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_file = f"data/ho-chi-minh/all_areas_companies_{timestamp}.xlsx"
        os.makedirs("data/ho-chi-minh", exist_ok=True)
        df = pd.DataFrame(all_area_companies)
        df.to_excel(final_file, index=False)
        print(f"Đã lưu tổng hợp {len(all_area_companies)} công ty của tất cả các khu vực!")

    end_time = time.time()  # Thời gian kết thúc
    elapsed = end_time - start_time  # start_time là thời điểm bắt đầu toàn bộ quá trình
    print(f"Tổng thời gian hoàn thành: {elapsed/60:.2f} phút ({elapsed:.1f} giây)")

except Exception as e:
    print(f"Lỗi: {str(e)}")
finally:
    # Không cần driver.quit() ở đây vì mỗi thread đã tự quit
    pass
