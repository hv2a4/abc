import google.generativeai as genai
from PIL import Image
import io
import base64
import requests

def setup_gemini(api_key):
    """Setup Gemini model with API key"""
    try:
        genai.configure(api_key=api_key)
        # Update to use latest model version
        model = genai.GenerativeModel('gemini-1.5-pro-vision')
        return model
    except Exception as e:
        print(f"Error setting up Gemini: {str(e)}")
        return None

def get_image_from_url(image_url):
    """Download image from URL and return as bytes"""
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Failed to download image: {response.status_code}")
    except Exception as e:
        print(f"Error downloading image: {str(e)}")
    return None

def extract_phone_from_url(model, image_url):
    """Extract phone number from image URL using Gemini Vision"""
    image_bytes = get_image_from_url(image_url)
    if image_bytes:
        return extract_phone_from_image(model, image_bytes)
    return None

def decode_base64_to_image(base64_string):
    """Convert base64 string to PIL Image"""
    try:
        # Remove data URI scheme if present
        if 'data:image' in base64_string:
            base64_string = base64_string.split(',')[1]
            
        # Add padding if needed
        padding = len(base64_string) % 4
        if padding:
            base64_string += '=' * (4 - padding)
            
        # Decode base64 to bytes
        image_bytes = base64.b64decode(base64_string)
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        return image
    except Exception as e:
        print(f"Error decoding base64: {str(e)}")
        return None

def extract_phone_from_image(model, image_bytes):
    """Extract phone number from image using Gemini Vision"""
    try:
        if not model:
            print("Gemini model not initialized")
            return None
            
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Ensure image is in RGB mode
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Ask Gemini to extract phone number with more specific prompt
        prompt = "This image contains a phone number. Please extract and return only the digits of the phone number, with no other text or characters."
        response = model.generate_content([prompt, image])
        
        if not response or not response.text:
            print("No response from Gemini")
            return None
            
        # Clean up response to get only digits
        phone = ''.join(filter(str.isdigit, response.text))
        
        # Validate phone number length
        if 9 <= len(phone) <= 11:
            print(f"Successfully extracted phone number: {phone}")
            return phone
        else:
            print(f"Invalid phone number length: {len(phone)} digits")
            
    except Exception as e:
        print(f"Error extracting phone number: {str(e)}")
    
    return None

def extract_phone_from_base64(model, base64_string):
    """Trích xuất số điện thoại từ ảnh base64"""
    try:
        image = decode_base64_to_image(base64_string)
        if image:
            # Đảm bảo ảnh ở chế độ RGB
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            # Tạo prompt cụ thể hơn bằng tiếng Việt
            prompt = """
            Đây là ảnh chứa một số điện thoại.
            Hãy trích xuất và trả về CHỈ các chữ số của số điện thoại.
            Không trả về bất kỳ ký tự hoặc từ nào khác.
            VD: nếu thấy số "0919 204789" thì chỉ trả về "0919204789"
            """
            
            # Gọi Gemini API
            response = model.generate_content([prompt, image])
            
            if not response or not response.text:
                print("Không nhận được phản hồi từ Gemini")
                return None
                
            # Lọc lấy chữ số
            phone = ''.join(filter(str.isdigit, response.text))
            
            # Kiểm tra độ dài số điện thoại
            if 9 <= len(phone) <= 11:
                print(f"Đã tìm thấy số điện thoại: {phone}")
                return phone
            else:
                print(f"Số điện thoại không hợp lệ, độ dài: {len(phone)} chữ số")
                
    except Exception as e:
        print(f"Lỗi khi xử lý ảnh base64: {str(e)}")
    return None

def extract_phone_from_screenshot(model, screenshot_bytes):
    """Extract phone number from screenshot bytes using Gemini Vision"""
    try:
        # Convert screenshot bytes to PIL Image
        image = Image.open(io.BytesIO(screenshot_bytes))
        
        # Ensure image is in RGB mode
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        # Specific prompt for phone number extraction
        prompt = """
        Đây là ảnh chụp màn hình chứa số điện thoại.
        Hãy đọc và trích xuất CHỈ các chữ số của số điện thoại.
        Không trả về bất kỳ ký tự hoặc từ nào khác.
        """
        
        response = model.generate_content([prompt, image])
        
        if response and response.text:
            phone = ''.join(filter(str.isdigit, response.text))
            if 9 <= len(phone) <= 11:
                return phone
                
    except Exception as e:
        print(f"Lỗi khi xử lý ảnh screenshot: {str(e)}")
        
    return None

# Code test
if __name__ == "__main__":
    API_KEY = "AIzaSyCtofong2JGfdyXWRrGyBG-KO5u8t9GFoQ"
    print("Đang khởi tạo Gemini model...")
    model = setup_gemini(API_KEY)
    
    if not model:
        print("Khởi tạo model thất bại")
        exit(1)
    
    # Test với chuỗi base64
    print("\nĐang test xử lý ảnh base64...")
    test_base64 = "iVBORw0KGgoAAAANSUhEUgAAAFMAAAAOCAIAAADcwLd+AAADHUlEQVRIieWXy0sqURzHf16dxgdRNhm9lFrUxh4Lo8SNQo9VRBQ9iCCIFq3GTQm1D4Y2hYyLFiWkq7DogbbJFv0DUTFgtNDVpEJHXPQCg7s4MvfiPO7p3gst+q7O+frx+z0/GY+oQwjBt9SPrz7Al+nPk8/PzzMMMzIykkql/h377+/9a/2aPJFItLS0TE1NXVxcSGY0Gk0kEltbW1ardWZmplQqFQqFpaWlzs5Om83m9/vVMMUywgoNmDCzVCr5fD673c4wzOrqqqIDCCGEkCiK9fX1g4OD4XBYr9eHw2Hs9/X1dXV1IYSSySQAxGKxfD4/Pj6+s7MTjUYBIBQKKWJIJvIKDZgwM5PJUBRlsViGh4c5jlN0ypPzPK/T6QRBQAh5vV6v14t9mqYXFhYQQtlsFgA2Njak1rGxMQDgeV4bk/SpCjWYMJPjOJPJlE6nJVLulJ/2k5OT3t7epqYmAOju7r67u8O+xWKx2WwAUFVVBQBvb28A8PLysri4eHp62tPTMzExoYZV6FMVajBhZiQScTgcxWJRIuVOefLr62un04nXBoNBIubm5lKpVLFY3NvbAwCHw5HL5fr7+4+Pj/V6Pc/zRqNREZOfkrxCAybMpCjq/v7e5XJxHKfmlCcvFAr4gweAXC5nNpvxen19/fn5ub29fWVlhaIon8/3+voqiiJN0x8fH7Ozs09PT4qY/JTkFRowYebl5WU6nfb7/Zubm/jmkzvlyWtqaqRL9fb2tqOjA6+NRuPh4WEymaytrZ2cnGQYpq2t7ebm5vHx8erqShTFg4MDRUx+SvIKDZgwE7/EsiwASF+BCqc8+cDAgCAIAJDJZARBGBoa+r1gf3///f19bW0Nb+12OwCcn58DQENDgxpWoU9VaMOEmfjBdrvdyg6+6OLxOEVRPM97PB6apvFtibW7uwsA29vbePvw8HB0dDQ9PQ0AHo8nn88rYnKRV2jDJJnxeByfkGVZNQeklGAw2NjYWFdXV/HjGQgElpeXpe3Z2Vl1dXVra2sgEMhms2qYoggrtGESbHR0tLm5ORgMajg69F3/sfwEoOATqqZzw/AAAAAASUVORK5CYII="
    print("Bắt đầu trích xuất số điện thoại từ ảnh...")
    phone = extract_phone_from_base64(model, test_base64)
    if phone:
        print(f"Đã tìm thấy số điện thoại: {phone}")
    else:
        print("Không tìm thấy số điện thoại hợp lệ trong ảnh")
