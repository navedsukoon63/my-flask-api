from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from lxml import html
import json

app = Flask(__name__)

# Updated Flipkart CSS selectors
FLIPKART_SELECTORS = {
    "title": "span._32l7gU",
    "price": "div._30jeq3._16Jk6d",
    "mrp": "div._3I9_wc._2p6-al",
    "discount": "div._3Ay6Sb",
    "image": "img._396cs4"
}

# Amazon XPath selectors (unchanged)
AMAZON_XPATHS = {
    "title": '//*[@id="productTitle"]',
    "discount": '//*[@id="corePriceDisplay_desktop_feature_div"]/div[1]/span[2]',
    "price": '//*[@id="priceblock_ourprice"]',
    "mrp": '//*[@id="priceblock_saleprice"]'
}

def detect_platform(url):
    if not url:
        return None
    if "flipkart.com" in url:
        return "flipkart"
    elif "amazon.in" in url or "amazon.com" in url:
        return "amazon"
    else:
        return None

def scrape_flipkart(soup):
    result = {}
    for key, selector in FLIPKART_SELECTORS.items():
        el = soup.select_one(selector)
        if el:
            if key == "image":
                for attr in ['src', 'data-src', 'data-old-hires', 'srcset']:
                    if el.has_attr(attr):
                        result[key] = el[attr]
                        break
                else:
                    result[key] = ""
            else:
                result[key] = el.get_text(strip=True)
        else:
            result[key] = ""
    return result

def scrape_amazon(tree):
    result = {}
    for key in ["title", "discount", "price", "mrp"]:
        try:
            vals = tree.xpath(AMAZON_XPATHS[key])
            if vals:
                elem = vals[0]
                if hasattr(elem, "text_content"):
                    result[key] = elem.text_content().strip()
                else:
                    result[key] = str(elem).strip()
            else:
                result[key] = ""
        except:
            result[key] = ""

    image = ""
    try:
        img_src = tree.xpath("//img[@id='landingImage']/@src")
        if img_src:
            image = img_src[0]
    except:
        pass

    if not image:
        try:
            data_old_hi = tree.xpath("//div[@id='imgTagWrapperId']/img/@data-old-hires")
            if data_old_hi:
                image = data_old_hi[0]
        except:
            pass

    if not image:
        try:
            dynamic_image_json = tree.xpath("string(//div[@id='imgTagWrapperId']/img/@data-a-dynamic-image)")
            if dynamic_image_json:
                data = json.loads(dynamic_image_json)
                if isinstance(data, dict) and data.keys():
                    image = list(data.keys())[0]
        except:
            pass

    result["image"] = image or ""
    return result

@app.route('/')
def home():
    return "API running!"

@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL missing"}), 400

    platform = detect_platform(url)
    if not platform:
        return jsonify({"error": "Unsupported platform"}), 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return jsonify({"error": f"Failed to fetch page, status code {resp.status_code}"}), 500

        if platform == "flipkart":
            soup = BeautifulSoup(resp.text, "html.parser")
            data = scrape_flipkart(soup)
        elif platform == "amazon":
            tree = html.fromstring(resp.content)
            data = scrape_amazon(tree)
        else:
            return jsonify({"error": "Platform not supported"}), 400

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
