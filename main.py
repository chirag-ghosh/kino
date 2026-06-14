import os
import random
import threading

import requests
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = 8000
CACHE_LOCK = threading.Lock()
FILMS_CACHE = []
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

PAGES_TO_FETCH = 1  # Number of pages to fetch for each list

FETCH_URLS = {
    "trending_movies": "https://api.themoviedb.org/3/trending/movie/week",
    "top_rated_movies": "https://api.themoviedb.org/3/movie/top_rated",
    "popular_movies": "https://api.themoviedb.org/3/movie/popular",
    "upcoming_movies": "https://api.themoviedb.org/3/movie/upcoming",
    "top_rated_tv": "https://api.themoviedb.org/3/tv/top_rated",
    "popular_tv": "https://api.themoviedb.org/3/tv/popular",
    "airing_today_tv": "https://api.themoviedb.org/3/tv/airing_today",
    "on_the_air_tv": "https://api.themoviedb.org/3/tv/on_the_air"
}

REQUESTED_FETCH_URLS = set()

app = Flask(__name__, static_folder=None)

def fetch_films():
    headers = {
        "Authorization": f"Bearer {os.getenv('TMDB_API_KEY')}",
    }
    included_lists = REQUESTED_FETCH_URLS if REQUESTED_FETCH_URLS else [
        "top_rated_movies",
        "top_rated_tv",
    ]
    for list_key in included_lists:
        list_url = FETCH_URLS.get(list_key)
        is_a_tv = "tv" in list_key
        for page in range(1, PAGES_TO_FETCH + 1):
            params = {
                "page": page,
                "language": "en-US",
            }
            response = requests.get(list_url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                # include media type for filtering later
                for item in results:
                    item["media_type"] = "tv" if is_a_tv else "movie"
                FILMS_CACHE.extend(results)
    return []

def fetch_film_images(film_id, media_type):
    backdrop_url = None
    logo_url = None

    if media_type == "movie":
        url = "https://api.themoviedb.org/3/movie/{movie_id}/images?include_image_language=en,null".format(movie_id=film_id)
    else:
        url = "https://api.themoviedb.org/3/tv/{tv_id}/images?include_image_language=en,null".format(tv_id=film_id)

    headers = {
        "Authorization": f"Bearer {os.getenv('TMDB_API_KEY')}",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        
        backdrops = data.get("backdrops", [])
        selected_backdrops = [b for b in backdrops if b.get("iso_639_1") is None]
        if not selected_backdrops:
            selected_backdrops = backdrops
        
        logos = data.get("logos", [])
        selected_logos = [l for l in logos if l.get("iso_639_1") == "en"]
        if not selected_logos:
            selected_logos = logos
        if backdrops:
            backdrop_url = "https://image.tmdb.org/t/p/original" + selected_backdrops[0].get("file_path", "")
        if logos:
            logo_url = "https://image.tmdb.org/t/p/original" + selected_logos[0].get("file_path", "")
    return backdrop_url, logo_url

def get_random_film_image():
    with CACHE_LOCK:
        if not FILMS_CACHE:
            FILMS_CACHE.extend(fetch_films())
        if FILMS_CACHE:
            film = random.choice(FILMS_CACHE)
            return fetch_film_images(film.get("id"), film.get("media_type"))
    return None, None

@app.route("/")
def index():
    included_lists = request.args.getlist("included_lists")
    included_lists = [url for url in included_lists if url in FETCH_URLS.keys()]
    if not included_lists:
        included_lists = [
            "top_rated_movies",
            "top_rated_tv",
        ]
    print(f"Included lists: {included_lists}")
    REQUESTED_FETCH_URLS.update(included_lists)
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/favicon.svg")
def favicon_svg():
    return send_from_directory(BASE_DIR, "favicon.svg")

@app.route("/favicon.ico")
def favicon_fallback():
    return send_from_directory(BASE_DIR, "favicon.ico")

@app.route("/api/featured")
def api_featured():
    backdrop_url, logo_url = get_random_film_image()
    if backdrop_url and logo_url:
        return jsonify({
            "backdrop_url": backdrop_url,
            "logo_url": logo_url
        })
    return jsonify({"error": "No films available"}), 500
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
