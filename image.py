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

# Cấu hình Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Thiết lập Chrome options
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

# ========== Các hàm lưu và checkpoint ==========
def append_to_csv(data, area_name):
    data_dir = f"data/{area_name}"
    os.makedirs(data_dir, exist_ok=True)
    filepath = f"{data_dir}/companies_temp.csv"
    df = pd.DataFrame([data])
    header = not os.path.exists(filepath)
    df.to_csv(filepath, mode='a', index=False, header=header)

def save_checkpoint(area, page):
    path = f"data/{area}/checkpoint.txt"
    with open(path, 'w') as f:
        f.write(str(page))

def load_checkpoint(area):
    path = f"data/{area}/checkpoint.txt"
    try:
        with open(path, 'r') as f:
            return int(f.read().strip())
    except:
        return 1

def has_processed(link, area):
    path = f"data/{area}/processed.txt"
    if not os.path.exists(path):
        return False
    with open(path, 'r') as f:
        return link in f.read()

def mark_processed(link, area):
    path = f"data/{area}/processed.txt"
    with open(path, 'a') as f:
        f.write(link + '\n')

# ========== Các hàm chính ==========
def is_mobile_phone(phone):
    if not phone or len(phone) < 9:
        return False
    mobile_prefixes = ['03', '05', '07', '08', '09']
    return any(phone.startswith(prefix) for prefix in mobile_prefixes)

def get_company_links(driver, url):
    driver.get(url)
    links = []
    try:
        companies = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "search-results"))
        )
        for company in companies:
            link = company.find_element(By.TAG_NAME, "a").get_attribute('href')
            if link:
                links.append(link)
    except Exception as e:
        print(f"Lỗi khi lấy links: {str(e)}")
    return links

def get_company_detail(driver, url):
    driver.get(url)
    try:
        data = {'Tên công ty': '', 'Mã số thuế': '', 'Địa chỉ': '',
                'Đại diện pháp luật': '', 'Trạng thái': '', 'Ngày cấp': '', 'Điện thoại': ''}

        company_info = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "jumbotron"))
        )

        name_elem = company_info.find_element(By.TAG_NAME, "h4")
        data['Tên công ty'] = name_elem.text.strip()

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

        try:
            phone_imgs = company_info.find_elements(By.TAG_NAME, "img")
            for img in phone_imgs:
                img_src = img.get_attribute('src')
                if 'base64,' in img_src:
                    img_data = base64.b64decode(img_src.split(',')[1])
                    image = Image.open(io.BytesIO(img_data))
                    text = pytesseract.image_to_string(
                        image, config='--psm 7 -c tessedit_char_whitelist=0123456789')
                    phone = ''.join(filter(str.isdigit, text))
                    if is_mobile_phone(phone):
                        data['Điện thoại'] = phone
                        break
        except Exception as e:
            print(f"OCR lỗi: {str(e)}")

        return data

    except Exception as e:
        print(f"Lỗi khi lấy chi tiết {url}: {str(e)}")
        return None

def crawl_area(driver, area_path):
    area_name = area_path.replace('/', '_')
    base_url = f"https://www.tratencongty.com/tinh-bac-lieu/{area_path}"
    page = load_checkpoint(area_name)

    while True:
        current_url = f"{base_url}/?page={page}" if page > 1 else base_url
        print(f"Trang {page} - {current_url}")
        company_links = get_company_links(driver, current_url)

        if not company_links:
            print("Hết trang hoặc lỗi, dừng lại.")
            break

        for link in company_links:
            if has_processed(link, area_name):
                print(f"Bỏ qua đã cào: {link}")
                continue
            print(f"-> Cào: {link}")
            detail = get_company_detail(driver, link)
            if detail:
                detail['Khu vực'] = area_path
                append_to_csv(detail, area_name)
                mark_processed(link, area_name)
            time.sleep(2)

        save_checkpoint(area_name, page)
        page += 1
        time.sleep(3)

# ========== Chạy chính ==========
try:
    driver = webdriver.Chrome(options=chrome_options)

    areas = [
        "thanh-pho-bac-lieu",
        "thi-xa-gia-rai",
        "huyen-dong-hai",
        "huyen-hoa-binh",
        "huyen-hong-dan",
        "huyen-phuoc-long",
        "huyen-vinh-loi"
    ]

    for area in areas:
        crawl_area(driver, area)
        time.sleep(5)

    print("\n>>> Hoàn tất tất cả khu vực!")

except Exception as e:
    print(f"Lỗi chính: {str(e)}")

finally:
    if 'driver' in locals():
        driver.quit()
