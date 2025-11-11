from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

app = Flask(__name__)

SELECTORS: Dict[str, Dict[str, str]] = {
    "flipkart": {
        "title": "span.VU-ZEz",
        "price": "div.Nx9bqj.CxhGGd",
        "mrp": "div.yRaY8j.A6\\+E6v",
        "discount": "div.UkUFwK.WW8yVX",
        "image": "img._0DkuPH, div.Be4x5X.-PhTVc"
    }
}


def detect_platform(url: Optional[str]) -> Optional[str]:
    if url and "flipkart.com" in url:
        return "flipkart"
    return None


@app.route('/')
def home():
    return "API running!"


@app.route('/scrape', methods=['GET'])
def scrape():
    url: Optional[str] = request.args.get('url')

    if not url:
        return jsonify({"error": "URL missing"}), 400

    platform: Optional[str] = detect_platform(url)
    if not platform:
        return jsonify({"error": "Unsupported platform"}), 400

    selectors = SELECTORS.get(platform)
    if not selectors:
        return jsonify({"error": "Selectors missing"}), 400

    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        result: Dict[str, Any] = {}

        for field, selector in selectors.items():
            el = soup.select_one(selector)

            if el:
                # IMAGE handling
                if field == "image":
                    # Case 1: img tag
                    if el.name == "img":
                        src = el.get("src")
                        result[field] = src if isinstance(src, str) else ""

                    # Case 2: div background-image
                    elif el.name == "div":
                        style = el.get("style")
                        if isinstance(style,
                                      str) and "background-image" in style:
                            url_start = style.find("url(")
                            url_end = style.find(")", url_start + 4)

                            if url_start != -1 and url_end != -1:
                                result[field] = style[url_start + 4:url_end]
                            else:
                                result[field] = ""
                        else:
                            result[field] = ""
                    else:
                        result[field] = ""

                # TEXT fields
                else:
                    text = el.get_text(strip=True)
                    result[field] = text if isinstance(text, str) else ""

            else:
                result[field] = ""

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
