
import csv
import random
import shutil
from pathlib import Path

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_DIR / "data" / "fashion-dataset"
SOURCE_IMAGES = DATASET_DIR / "images"

OUTPUT_DIR = PROJECT_DIR / "data" / "fashion-1000-new"
OUTPUT_IMAGES = OUTPUT_DIR / "images"
OUTPUT_CSV = OUTPUT_DIR / "products.csv"
SOURCE_CSV = DATASET_DIR / "styles.csv"

TARGET_COUNT = 1000
RANDOM_SEED = 42

# Categories useful for our fashion store
ALLOWED_CATEGORIES = {
    "Apparel",
    "Footwear",
}

ALLOWED_ARTICLE_TYPES = {
    "Shirts",
    "Tshirts",
    "Jeans",
    "Trousers",
    "Shorts",
    "Jackets",
    "Blazers",
    "Sweatshirts",
    "Sweaters",
    "Kurtas",
    "Dresses",
    "Skirts",
    "Casual Shoes",
    "Formal Shoes",
    "Sports Shoes",
    "Heels",
    "Flats",
}

def main():
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(f"Missing CSV: {SOURCE_CSV}")

    if not SOURCE_IMAGES.exists():
        raise FileNotFoundError(f"Missing images folder: {SOURCE_IMAGES}")

    OUTPUT_IMAGES.mkdir(parents=True, exist_ok=True)

    # Read the metadata
    with SOURCE_CSV.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        products = list(reader)

    # Keep useful products with images that exist
    eligible = []

    for product in products:
        product_id = product.get("id", "").strip()
        category = product.get("masterCategory", "").strip()
        article_type = product.get("articleType", "").strip()

        if category not in ALLOWED_CATEGORIES:
            continue

        if article_type not in ALLOWED_ARTICLE_TYPES:
            continue

        image_path = SOURCE_IMAGES / f"{product_id}.jpg"

        if not image_path.is_file():
            continue

        eligible.append(product)

    if len(eligible) < TARGET_COUNT:
        raise RuntimeError(
            f"Only {len(eligible)} eligible products found. "
            "Adjust the category filters."
        )

    # Select a reproducible sample
    random.seed(RANDOM_SEED)
    selected = random.sample(eligible, TARGET_COUNT)

    output_fields = [
        "id",
        "gender",
        "masterCategory",
        "subCategory",
        "articleType",
        "baseColour",
        "season",
        "year",
        "usage",
        "productDisplayName",
        "image",
    ]

    # Write metadata and copy matching images
    with OUTPUT_CSV.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=output_fields)
        writer.writeheader()

        for product in selected:
            product_id = product["id"].strip()
            filename = f"{product_id}.jpg"

            shutil.copy2(
                SOURCE_IMAGES / filename,
                OUTPUT_IMAGES / filename,
            )

            row = {
                field: product.get(field, "")
                for field in output_fields
                if field != "image"
            }
            row["image"] = f"/images/{filename}"
            writer.writerow(row)

    print("Dataset preparation complete!")
    print(f"Eligible products: {len(eligible)}")
    print(f"Selected products: {TARGET_COUNT}")
    print(f"CSV created: {OUTPUT_CSV}")
    print(f"Images copied to: {OUTPUT_IMAGES}")


if __name__ == "__main__":
    main()
