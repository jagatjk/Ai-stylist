
from pathlib import Path
import csv
import json
import mimetypes
import os
import secrets
import urllib.error
import urllib.request
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

BACKEND_DIR = Path(__file__).resolve().parent
LOCAL_ENV_FILE = BACKEND_DIR / ".env"
CATVTON_ENV_KEYS = {"CATVTON_API_URL", "CATVTON_API_KEY"}

if LOCAL_ENV_FILE.is_file():
    for line in LOCAL_ENV_FILE.read_text(encoding="utf-8").splitlines():
        name, separator, value = line.partition("=")
        name = name.strip()
        if separator and name in CATVTON_ENV_KEYS and not os.environ.get(name):
            os.environ[name] = value.strip().strip('"').strip("'")

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
CATALOGUE_DIR = PROJECT_DIR / "data" / "fashion-1000-new"
PRODUCTS_CSV = CATALOGUE_DIR / "products.csv"
IMAGES_DIR = CATALOGUE_DIR / "images"

app = FastAPI(title="AI Personal Stylist API")

# Allow our React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve product images
if IMAGES_DIR.exists():
    app.mount(
        "/images",
        StaticFiles(directory=str(IMAGES_DIR)),
        name="images",
    )

# Load the catalogue
def load_products():
    if not PRODUCTS_CSV.exists():
        return []

    with PRODUCTS_CSV.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        return list(csv.DictReader(file))


@app.get("/")
def home():
    return {
        "message": "AI Personal Stylist backend is running!"
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "project": "AI Personal Stylist",
    }


@app.get("/api/products")
def get_products(
    search: str = Query(default="", max_length=100),
    category: str = Query(default="", max_length=100),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    products = load_products()

    # Search product names, colours and clothing types
    if search.strip():
        term = search.strip().casefold()
        products = [
            product for product in products
            if term in product.get(
                "productDisplayName", ""
            ).casefold()
            or term in product.get(
                "articleType", ""
            ).casefold()
            or term in product.get(
                "baseColour", ""
            ).casefold()
        ]

    # Filter by master category
    if category.strip():
        selected_category = category.strip().casefold()
        products = [
            product for product in products
            if product.get(
                "masterCategory", ""
            ).casefold() == selected_category
        ]

    total = len(products)
    results = products[offset:offset + limit]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "products": results,
    }


@app.post("/api/try-on/{product_id}")
async def try_on_product(product_id: str, request: Request):
    catvton_url = os.environ.get("CATVTON_API_URL", "").rstrip("/")
    catvton_api_key = os.environ.get("CATVTON_API_KEY", "")

    if not catvton_url or not catvton_api_key:
        raise HTTPException(
            status_code=503,
            detail="CatVTON is not configured. Set CATVTON_API_URL and CATVTON_API_KEY on the backend.",
        )

    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    image_extensions = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    if content_type not in image_extensions:
        raise HTTPException(
            status_code=415,
            detail="Upload a JPEG, PNG, or WebP photo.",
        )

    max_photo_size = 10 * 1024 * 1024
    photo = bytearray()
    async for chunk in request.stream():
        photo.extend(chunk)
        if len(photo) > max_photo_size:
            raise HTTPException(
                status_code=413,
                detail="The uploaded photo must be 10 MB or smaller.",
            )
    if not photo:
        raise HTTPException(status_code=400, detail="The photo is empty.")

    product = next(
        (item for item in load_products() if item.get("id") == product_id),
        None,
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found.")

    image_name = Path(product.get("image", "")).name
    image_path = (IMAGES_DIR / image_name).resolve()
    if image_path.parent != IMAGES_DIR.resolve() or not image_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="The selected product image is unavailable.",
        )

    article_type = product.get("articleType", "").strip().casefold()
    cloth_types = {
        "shirts": "upper",
        "tshirts": "upper",
        "sweatshirts": "upper",
        "sweaters": "upper",
        "jackets": "upper",
        "blazers": "upper",
        "jeans": "lower",
        "trousers": "lower",
        "shorts": "lower",
        "skirts": "lower",
        "dresses": "overall",
        "kurtas": "overall",
    }
    cloth_type = cloth_types.get(article_type)
    if cloth_type is None:
        raise HTTPException(
            status_code=400,
            detail="CatVTON supports tops, bottoms, and full-body clothing, but not footwear or accessories.",
        )

    boundary = f"----StylistAI{secrets.token_hex(16)}"
    body = bytearray()

    def add_field(name: str, value: str):
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        )
        body.extend(value.encode())
        body.extend(b"\r\n")

    def add_file(name: str, filename: str, mime_type: str, data: bytes):
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            (
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"\r\n'
                f"Content-Type: {mime_type}\r\n\r\n"
            ).encode()
        )
        body.extend(data)
        body.extend(b"\r\n")

    add_field("cloth_type", cloth_type)
    add_file(
        "person_image",
        f"person{image_extensions[content_type]}",
        content_type,
        bytes(photo),
    )
    add_file(
        "cloth_image",
        image_path.name,
        mimetypes.guess_type(image_path.name)[0] or "application/octet-stream",
        image_path.read_bytes(),
    )
    body.extend(f"--{boundary}--\r\n".encode())

    upstream_request = urllib.request.Request(
        f"{catvton_url}/try-on",
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {catvton_api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    def request_catvton():
        try:
            with urllib.request.urlopen(upstream_request, timeout=300) as response:
                result = response.read()
                result_type = response.headers.get_content_type()
        except urllib.error.HTTPError as error:
            detail = error.read(2000).decode("utf-8", errors="replace")
            try:
                detail = json.loads(detail).get("detail", detail)
            except json.JSONDecodeError:
                pass
            raise HTTPException(
                status_code=502,
                detail=f"CatVTON request failed ({error.code}): {detail}",
            ) from error
        except urllib.error.URLError as error:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach the Colab CatVTON service: {error.reason}",
            ) from error

        if result_type != "image/png":
            raise HTTPException(
                status_code=502,
                detail="CatVTON returned an unexpected response instead of an image.",
            )
        return result

    result_image = await run_in_threadpool(request_catvton)
    return Response(content=result_image, media_type="image/png")


# Request format for outfit recommendations
class RecommendationRequest(BaseModel):
    prompt: str
    gender: str = ""
    limit: int = 8



@app.post("/api/recommendations")
def recommend_products(request: RecommendationRequest):
    products = load_products()
    prompt = request.prompt.strip().casefold()

    if not prompt:
        return {
            "total": 0,
            "recommendations": [],
            "outfits": [],
        }

    # Detect the occasion
    occasion_keywords = {
        "Formal": [
            "interview", "presentation", "office",
            "formal", "professional", "meeting",
        ],
        "Casual": [
            "college", "casual", "everyday",
            "daily", "outing", "hangout",
        ],
        "Sports": [
            "gym", "sport", "sports", "workout",
            "running", "athletic",
        ],
        "Ethnic": [
            "ethnic", "traditional", "festival",
            "wedding", "kurta",
        ],
    }

    requested_occasions = [
        occasion
        for occasion, words in occasion_keywords.items()
        if any(word in prompt for word in words)
    ]

    occasion = requested_occasions[0] if requested_occasions else ""

    # Detect requested colour
    colours = [
        "navy blue", "black", "white", "blue", "red",
        "green", "grey", "gray", "brown", "pink",
        "yellow", "beige", "purple", "orange", "maroon",
    ]

    requested_colour = next(
        (colour for colour in colours if colour in prompt),
        "",
    )

    gender = request.gender.strip().casefold()

    if not gender:
        if any(word in prompt.split() for word in ["women", "woman", "female", "ladies"]):
            gender = "women"
        elif any(word in prompt.split() for word in ["men", "man", "male", "mens"]):
            gender = "men"

    # Match product metadata against the request
    def score_product(product):
        score = 0

        name = product.get("productDisplayName", "").casefold()
        article = product.get("articleType", "").casefold()
        usage = product.get("usage", "").casefold()
        colour = product.get("baseColour", "").casefold()
        product_gender = product.get("gender", "").casefold()

        if gender:
            if gender not in product_gender:
                return -1
            score += 2

        if requested_colour and requested_colour in colour:
            score += 3

        if occasion:
            if usage == occasion.casefold():
                score += 4

        prompt_words = set(prompt.split())
        for word in prompt_words:
            if len(word) > 3 and (word in name or word in article):
                score += 1

        return score

    # Group products into outfit-friendly categories
    category_map = {
        "tops": {"shirts", "tshirts", "sweatshirts", "sweaters"},
        "bottoms": {"jeans", "trousers", "shorts", "skirts"},
        "shoes": {"casual shoes", "formal shoes", "sports shoes", "heels", "flats"},
        "one_piece": {"dresses", "kurtas"},
        "outerwear": {"jackets", "blazers"},
    }

    pools = {category: [] for category in category_map}

    for product in products:
        article = product.get("articleType", "").strip().casefold()
        score = score_product(product)

        if score < 0:
            continue

        for category, article_types in category_map.items():
            if article in article_types:
                pools[category].append((score, product))
                break

    for category in pools:
        pools[category].sort(key=lambda item: item[0], reverse=True)

    def top_products(category, limit=5):
        return [product for score, product in pools[category][:limit]]

    # Assemble outfits from matching products
    outfits = []

    if occasion == "Ethnic":
        outfit_types = ["one_piece", "shoes"]
    elif occasion == "Sports":
        outfit_types = ["tops", "bottoms", "shoes"]
    else:
        outfit_types = ["tops", "bottoms", "shoes"]

    first_category = outfit_types[0]

    # Start with the best-ranked products in the first category
    for top in top_products(first_category, 4):
        items = [top]
        for category in outfit_types[1:]:
            candidates = top_products(category, 5)
            if candidates:
                items.append(candidates[0])

        if len(items) >= 2:
            outfits.append({
                "occasion": occasion or "Everyday",
                "items": items,
                "explanation": (
                    f"Selected for your {occasion.lower()} style."
                    if occasion
                    else "A suggested outfit based on your preferences."
                ),
            })

    # Keep the existing response field for compatibility with React
    recommendations = []
    seen_ids = set()

    for outfit in outfits:
        for product in outfit["items"]:
            product_id = product.get("id", "")
            if product_id not in seen_ids:
                seen_ids.add(product_id)
                recommendations.append(product)

    return {
        "total": len(recommendations),
        "recommendations": recommendations[:request.limit],
        "outfits": outfits,
    }
