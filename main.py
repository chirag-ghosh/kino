import json
import os
import random
import threading

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8000
CACHE_LOCK = threading.Lock()
FILMS_CACHE = []
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

app = Flask(__name__, static_folder=None)


def get_all_films():
    url = "https://film-grab.com/movies-a-z/"
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching film list: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    article = soup.find("article")
    if not article:
        print("No article found on the film list page.")
        return []

    list_items = article.find_all("li")
    films = []
    for li in list_items:
        a_tag = li.find("a")
        if a_tag and a_tag.get("href"):
            films.append((a_tag.get_text(strip=True), a_tag["href"]))
    return films


def extract_field(paragraph, field_name):
    """Extract a field value from a paragraph.
    
    The field label (field_name) can be in the <p> or in a <span> child.
    The value is always in an <a> tag child of <p>.
    """
    full_text = paragraph.get_text(strip=True)
    
    # Check if the paragraph contains the field name
    if field_name not in full_text:
        return None
    
    # The value is always in an <a> tag child of <p>
    a_tag = paragraph.find("a")
    if a_tag:
        return a_tag.get_text(strip=True)
    
    return None


def get_film_featured(film_url):
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(film_url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching film page: {e}")
        return None
    
    # Get the movie details
    year = None
    director = None
    dop = None

    details_div = BeautifulSoup(response.content, "html.parser").find("div", class_="entry-content")
    if details_div:
        paragraphs = details_div.find_all("p")
        for p in paragraphs:
            if p.get_text(strip=True).startswith("Year"):
                year = extract_field(p, "Year")
            elif p.get_text(strip=True).startswith("Director of Photography"):
                dop = extract_field(p, "Director of Photography")
            elif p.get_text(strip=True).startswith("Director"):
                director = extract_field(p, "Director")

    soup = BeautifulSoup(response.content, "html.parser")
    img_tag = soup.find("img", class_="wp-post-image")
    if img_tag and img_tag.get("src"):
        return (img_tag["src"], year, director, dop)

    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return (og_image["content"], year, director, dop)

    return None


def get_random_featured():
    with CACHE_LOCK:
        global FILMS_CACHE
        if not FILMS_CACHE:
            FILMS_CACHE = get_all_films()

        if not FILMS_CACHE:
            return {
                "title": "No film available",
                "image": "https://via.placeholder.com/1600x900?text=No+Image"
            }

        random_film = random.choice(FILMS_CACHE)

    title, film_url = random_film
    image, year, director, dop = get_film_featured(film_url)
    if not image:
        image = "https://via.placeholder.com/1600x900?text=No+Image"

    return {"title": title, "image": image, "year": year, "director": director, "dop": dop}


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/favicon.svg")
def favicon_svg():
    return send_from_directory(BASE_DIR, "favicon.svg")

@app.route("/favicon.ico")
def favicon_fallback():
    return send_from_directory(BASE_DIR, "favicon.ico")

@app.route("/api/featured")
def api_featured():
    featured = get_random_featured()
    return jsonify(featured)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
