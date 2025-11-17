from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from lxml import html
import json

app = Flask(__name__)

# Flipkart: CSS selectors + fallback XPaths (for dynamic/templates)
SELECTORS = {
    "price": ["div.Nx9bqj.CxhGGd", '//*[@class="Nx9bqj CxhGGd"]'],
    "mrp": ["div.yRaY8j.A6\\+E6v", '//*[@class="yRaY8j A6+E6v"]'],
    "discount":
    ["div.UkUFwK.WW8yVX > span", '//*[@class="UkUFwK WW8yVX dB67CR"]/span'],
    "title": [
        "span.VU-ZEz", "span.B_NuCI", '//*[@class="VU-ZEz"]',
        '//*[@class="B_NuCI"]', "title"
    ]
}
IMAGE_SELECTORS = ["img._396cs4", "img._2r_T1I", "img._0DkuPH", "img"]

AMAZON_XPATHS = {
    "title":
    '//*[@id="productTitle"]',
    "discount":
    '//*[@id="corePriceDisplay_desktop_feature_div"]/div[1]/span[2]',
    "price":
    '//*[@id="corePriceDisplay_desktop_feature_div"]/div[1]/span[3]/span[2]/span[2]',
    "mrp":
    '//*[@id="corePriceDisplay_desktop_feature_div"]/div[2]/span/span[1]/span[2]/span/span[2]'
}


def detect_platform(url):
    if not url:
        return None
    if "flipkart.com" in url:
        return "flipkart"
    elif "amazon.in" in url or "amazon.com" in url:
        return "amazon"
    return None


def get_best_image(soup):
    image_url = ""
    best_width = 0
    for selector in IMAGE_SELECTORS:
        img = soup.select_one(selector)
        if img:
            # srcset: parse all candidates, select highest width
            if img.has_attr('srcset'):
                srcset = img['srcset']
                parts = [p.strip() for p in srcset.split(',')]
                for part in parts:
                    tokens = part.split(' ')
                    if len(tokens) == 2 and tokens[1].endswith("w"):
                        width = int(tokens[1][:-1])
                        if width > best_width:
                            image_url = tokens[0]
                            best_width = width
            # fallback: check all relevant attributes
            for attr in ['data-old-hires', 'data-src', 'src']:
                if img.has_attr(attr):
                    temp_url = img[attr]
                    # prefer higher res than current
                    if ("1080x1080" in temp_url or "1500x1500" in temp_url
                            or "1280" in temp_url or ".jpg" in temp_url) and (
                                not image_url or "128x128" in image_url):
                        image_url = temp_url
                    elif not image_url:
                        image_url = temp_url
            if image_url:
                break
    # fallback upscaling if only low-res available
    if image_url and "_128x128" in image_url:
        image_url = image_url.replace("_128x128", "_1080x1080")
    if image_url and "_396x396" in image_url:
        image_url = image_url.replace("_396x396", "_1080x1080")
    return image_url


def scrape_flipkart(resp_text):
    result = {}
    soup = BeautifulSoup(resp_text, "html.parser")
    tree = html.fromstring(resp_text)

    def try_selectors(key):
        # Try all selectors (CSS/XPath) in priority order
        for sel in SELECTORS[key]:
            if sel.startswith("//"):
                # XPath
                try:
                    elems = tree.xpath(sel)
                    for el in elems:
                        val = el.text_content().strip() if hasattr(
                            el, "text_content") else str(el).strip()
                        if val:
                            return val
                except Exception:
                    continue
            else:
                # CSS selector
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    return el.get_text(strip=True)
        return ""

    # All main fields via selector fallback loop
    for field in ["price", "mrp", "discount", "title"]:
        result[field] = try_selectors(field)

    # High-res image special handling
    result["image"] = get_best_image(soup)
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
        except Exception:
            result[key] = ""
    image = ""
    try:
        img_src = tree.xpath("//img[@id='landingImage']/@src")
        if img_src:
            image = img_src[0]
    except Exception:
        pass
    if not image:
        try:
            data_old_hi = tree.xpath(
                "//div[@id='imgTagWrapperId']/img/@data-old-hires")
            if data_old_hi:
                image = data_old_hi[0]
        except Exception:
            pass
    if not image:
        try:
            dynamic_image_json = tree.xpath(
                "string(//div[@id='imgTagWrapperId']/img/@data-a-dynamic-image)"
            )
            if dynamic_image_json:
                data = json.loads(dynamic_image_json)
                if isinstance(data, dict) and data.keys():
                    image = list(data.keys())[0]
        except Exception:
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
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return jsonify({
                "error":
                f"Failed to fetch page, status code {resp.status_code}"
            }), 500
        if platform == "flipkart":
            data = scrape_flipkart(resp.text)
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
