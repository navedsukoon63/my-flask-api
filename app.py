from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
from lxml import html
import json
import time

app = Flask(__name__)

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)


# ---------------------------------------------
# FLIPKART (Selenium)
# ---------------------------------------------
def scrape_flipkart(url):
    d = get_driver()
    d.get(url)
    time.sleep(3)

    data = {}

    try:
        title = d.find_element(By.CSS_SELECTOR, "span.VU-ZEz").text
    except:
        title = ""
    data["title"] = title

    try:
        price = d.find_element(By.CSS_SELECTOR, "div.Nx9bqj.CxhGGd").text
    except:
        price = ""
    data["price"] = price

    try:
        mrp = d.find_element(By.CSS_SELECTOR, "div.yRaY8j.A6+E6v").text
    except:
        mrp = ""
    data["mrp"] = mrp

    try:
        discount = d.find_element(By.CSS_SELECTOR, "div.UkUFwK.WW8yVX").text
    except:
        discount = ""
    data["discount"] = discount

    # HIGH-RES IMAGE
    try:
        img = d.find_element(By.CSS_SELECTOR, "img._0DkuPH").get_attribute("src")
        img = img.replace("128", "800").replace("256", "1200")
        data["image"] = img
    except:
        data["image"] = ""

    d.quit()
    return data


# ---------------------------------------------
# AMAZON (Selenium)
# ---------------------------------------------
def scrape_amazon(url):
    d = get_driver()
    d.get(url)
    time.sleep(3)

    data = {}

    # title
    try:
        data["title"] = d.find_element(By.ID, "productTitle").text
    except:
        data["title"] = ""

    # price
    try:
        data["price"] = d.find_element(By.CSS_SELECTOR, "#corePriceDisplay_desktop_feature_div span.a-price-whole").text
    except:
        data["price"] = ""

    # MRP
    try:
        data["mrp"] = d.find_element(By.CSS_SELECTOR, ".a-price.a-text-price span.a-offscreen").text
    except:
        data["mrp"] = ""

    # discount
    try:
        data["discount"] = d.find_element(By.CSS_SELECTOR, ".savingsPercentage").text
    except:
        data["discount"] = ""

    # High resolution image
    try:
        img = d.find_element(By.ID, "landingImage").get_attribute("src")
        img = img.replace("SL1500", "SL3000").replace("SL1000", "SL3000")
        data["image"] = img
    except:
        data["image"] = ""

    d.quit()
    return data


@app.route("/scrape", methods=["GET"])
def api():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "URL missing"}), 400

    if "flipkart.com" in url:
        return jsonify(scrape_flipkart(url))

    if "amazon" in url:
        return jsonify(scrape_amazon(url))

    return jsonify({"error": "Unsupported URL"})


@app.route("/")
def home():
    return "Scraper API Running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
