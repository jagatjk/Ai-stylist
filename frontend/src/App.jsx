
import { useEffect, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8001";

const categories = [
  "All",
  "Shirts",
  "Tshirts",
  "Jeans",
  "Trousers",
  "Jackets",
  "Dresses",
  "Casual Shoes",
  "Formal Shoes",
];

function App() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedProduct, setSelectedProduct] = useState(null);

  // AI stylist state
  const [prompt, setPrompt] = useState("");
  const [gender, setGender] = useState("");
  const [recommendations, setRecommendations] = useState([]);
  const [recommendationLoading, setRecommendationLoading] =
    useState(false);
  const [recommendationError, setRecommendationError] = useState("");
  const [showRecommendations, setShowRecommendations] =
    useState(false);
  const [showTryOnUpload, setShowTryOnUpload] = useState(false);
  const [tryOnProduct, setTryOnProduct] = useState(null);
  const [userPhoto, setUserPhoto] = useState(null);
  const [userPhotoPreview, setUserPhotoPreview] = useState("");
  const [tryOnResult, setTryOnResult] = useState("");
  const [tryOnLoading, setTryOnLoading] = useState(false);
  const [tryOnError, setTryOnError] = useState("");

  useEffect(
    () => () => {
      if (userPhotoPreview) {
        URL.revokeObjectURL(userPhotoPreview);
      }
    },
    [userPhotoPreview]
  );

  useEffect(() => {
    if (!tryOnResult) {
      return undefined;
    }

    return () => URL.revokeObjectURL(tryOnResult);
  }, [tryOnResult]);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchProducts() {
      setLoading(true);
      setError("");

      try {
        const params = new URLSearchParams({
          limit: "100",
          offset: "0",
        });

        if (search.trim()) {
          params.set("search", search.trim());
        }

        const response = await fetch(
          `${API}/api/products?${params.toString()}`,
          { signal: controller.signal }
        );

        if (!response.ok) {
          throw new Error("Could not load products.");
        }

        const data = await response.json();
        setProducts(data.products);
      } catch (err) {
        if (err.name !== "AbortError") {
          setError(
            "Couldn't load the store. Check that the backend is running."
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    fetchProducts();
    return () => controller.abort();
  }, [search]);


async function findMyStyle(event) {
  event.preventDefault();

  if (!prompt.trim()) {
    setRecommendationError("Describe the outfit you want first.");
    return;
  }

  setRecommendationLoading(true);
  setRecommendationError("");
  setShowRecommendations(true);
  setRecommendations([]);

  try {
    const response = await fetch(`${API}/api/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: prompt.trim(),
        gender,
        limit: 8,
      }),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(
        data.detail || `Recommendations failed with status ${response.status}`
      );
    }

    setRecommendations(data.recommendations || []);

    if (!data.recommendations?.length) {
      setRecommendationError("No matching products found. Try another prompt.");
    }
  } catch (err) {
    setRecommendationError(
      err.message || "Could not load recommendations."
    );
  } finally {
    setRecommendationLoading(false);
  }
}

  async function generateTryOn() {
    if (!tryOnProduct || !userPhoto) {
      setTryOnError("Choose a clothing item and upload your photo first.");
      return;
    }

    setTryOnLoading(true);
    setTryOnError("");
    setTryOnResult("");

    try {
      const response = await fetch(
        `${API}/api/try-on/${encodeURIComponent(tryOnProduct.id)}`,
        {
          method: "POST",
          headers: {
            "Content-Type": userPhoto.type,
          },
          body: userPhoto,
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(
          data.detail || `Try-on failed with status ${response.status}.`
        );
      }

      const result = await response.blob();
      if (!result.type.startsWith("image/")) {
        throw new Error("The try-on service returned an invalid image.");
      }
      setTryOnResult(URL.createObjectURL(result));
    } catch (err) {
      setTryOnError(
        err.message || "Could not connect to the CatVTON try-on service."
      );
    } finally {
      setTryOnLoading(false);
    }
  }


  const visibleProducts =
    category === "All"
      ? products
      : products.filter(
          (product) =>
            product.articleType?.toLowerCase() ===
            category.toLowerCase()
        );

  function renderProductCard(product) {
    return (
      <article className="product-card" key={product.id}>
        <div className="product-image-wrap">
          <img
            className="product-image"
            src={`${API}${product.image}`}
            alt={product.productDisplayName}
            loading="lazy"
          />
          <span className="product-tag">
            {product.articleType}
          </span>
        </div>

        <div className="product-info">
          <p className="product-colour">
            {product.baseColour || "Classic style"}
          </p>

          <h3>{product.productDisplayName}</h3>

          <p className="product-meta">
            {product.gender} · {product.usage || "Everyday"}
          </p>

          <button
            className="try-button"
            onClick={() => {
              setSelectedProduct(product);
              setTryOnResult("");
              setTryOnError("");
            }}
          >
            Try this on <span>↗</span>
          </button>
        </div>
      </article>
    );
  }

  return (
    <div className="store">
      <header className="topbar">
        <a className="brand" href="#">
          STYLIST<span>AI</span>
        </a>
        <span className="topbar-note">
          YOUR PERSONAL STYLIST
        </span>
      </header>

      <section className="hero">
        <p className="eyebrow">STYLE, REIMAGINED</p>

        <h1>
          Your style.
          <br />
          <span>Your rules.</span>
        </h1>

        <p className="hero-copy">
          Discover your next favourite outfit. Explore our
          collection, then let AI help you decide what to wear.
        </p>
      </section>

      {/* AI STYLIST */}
      <section className="catalogue">
        <div className="catalogue-heading">
          <div>
            <p className="eyebrow">YOUR PERSONAL STYLIST</p>
            <h2>What are you looking for?</h2>
          </div>
        </div>

        <form onSubmit={findMyStyle}>
          <textarea
            className="search-input"
            rows={3}
            placeholder="E.g. Smart casual blue shirt for a college presentation..."
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
          />

          <div style={{
            display: "flex",
            gap: "12px",
            alignItems: "center",
            flexWrap: "wrap",
            marginTop: "12px",
          }}>
            <select
              className="search-input"
              value={gender}
              onChange={(event) => setGender(event.target.value)}
              aria-label="Gender preference"
              style={{ width: "auto", minWidth: "150px" }}
            >
              <option value="">Any gender</option>
              <option value="Men">Men</option>
              <option value="Women">Women</option>
            </select>

            <button
              type="submit"
              className="try-button"
              disabled={recommendationLoading}
              style={{ width: "auto", minWidth: "180px" }}
            >
              {recommendationLoading
                ? "Finding outfits..."
                : "✦ Find My Style"}
            </button>
          </div>
        </form>

        {recommendationError && (
          <p className="error-message">
            {recommendationError}
          </p>
        )}

        {showRecommendations && !recommendationLoading && (
          <div style={{ marginTop: "32px" }}>
            <div className="catalogue-heading">
              <div>
                <p className="eyebrow">CURATED FOR YOU</p>
                <h2>Your recommendations</h2>
              </div>

              <button
                className="category-chip"
                onClick={() => setShowRecommendations(false)}
              >
                Hide results
              </button>
            </div>

            {recommendations.length > 0 ? (
              <div className="product-grid">
                {recommendations.map(renderProductCard)}
              </div>
            ) : !recommendationError ? (
              <p className="store-message">
                No matching products found. Try describing a
                different outfit or colour.
              </p>
            ) : null}
          </div>
        )}

        {recommendationLoading && (
          <p className="store-message">
            Finding outfits for you...
          </p>
        )}
      </section>

      {/* FULL PRODUCT CATALOGUE */}
      <section className="catalogue">
        <div className="catalogue-heading">
          <div>
            <p className="eyebrow">THE COLLECTION</p>
            <h2>Find your style</h2>
          </div>

          <span className="result-count">
            {loading ? "Loading..." : `${visibleProducts.length} shown`}
          </span>
        </div>

        <input
          className="search-input"
          type="search"
          placeholder="Search shirts, jeans, colours..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <div className="category-list">
          {categories.map((item) => (
            <button
              key={item}
              className={`category-chip ${
                category === item ? "active" : ""
              }`}
              onClick={() => setCategory(item)}
            >
              {item}
            </button>
          ))}
        </div>

        {error && <p className="error-message">{error}</p>}

        {loading ? (
          <p className="store-message">
            Preparing your collection...
          </p>
        ) : visibleProducts.length === 0 ? (
          <p className="store-message">
            No matching products found.
          </p>
        ) : (
          <div className="product-grid">
            {visibleProducts.map(renderProductCard)}
          </div>
        )}
      </section>

      {/* VIRTUAL TRY-ON PREVIEW */}
      {selectedProduct && (
        <div
          className="modal-backdrop"
          onClick={() => setSelectedProduct(null)}
        >
          <section
            className="try-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="modal-close"
              onClick={() => setSelectedProduct(null)}
              aria-label="Close"
            >
              ×
            </button>

            <p className="eyebrow">VIRTUAL TRY-ON</p>
            <h2>Make it your look.</h2>

            <img
              className="modal-product-image"
              src={`${API}${selectedProduct.image}`}
              alt={selectedProduct.productDisplayName}
            />

            <h3>{selectedProduct.productDisplayName}</h3>

            <p>
              This item is selected. Continue to upload your photo and create a try-on preview.
            </p>

            <button
              className="try-button"
              onClick={() => {
                setTryOnProduct(selectedProduct);
                setSelectedProduct(null);
                setShowTryOnUpload(true);
                setUserPhoto(null);
                setUserPhotoPreview("");
                setTryOnResult("");
                setTryOnError("");
              }}
            >
              Upload your photo
            </button>
          </section>
        </div>
      )}

      {showTryOnUpload && (
        <div
          className="modal-backdrop"
          onClick={() => setShowTryOnUpload(false)}
        >
          <section
            className="try-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              className="modal-close"
              onClick={() => setShowTryOnUpload(false)}
              aria-label="Close"
            >
              ×
            </button>

            <p className="eyebrow">VIRTUAL TRY-ON</p>
            <h2>Try on your selection</h2>
            {tryOnProduct && (
              <>
                <img
                  className="modal-product-image"
                  src={`${API}${tryOnProduct.image}`}
                  alt={tryOnProduct.productDisplayName}
                />
                <h3>{tryOnProduct.productDisplayName}</h3>
              </>
            )}
            <p>Select a clear, full-body photo to preview this item.</p>

            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(event) => {
                const file = event.target.files?.[0];

                if (file) {
                  setUserPhoto(file);
                  setUserPhotoPreview(URL.createObjectURL(file));
                  setTryOnResult("");
                  setTryOnError("");
                }
              }}
            />

            {userPhotoPreview ? (
              <img
                src={userPhotoPreview}
                alt="Your uploaded photo preview"
                style={{
                  display: "block",
                  width: "100%",
                  maxHeight: "320px",
                  objectFit: "contain",
                  margin: "20px auto",
                  borderRadius: "8px",
                }}
              />
            ) : (
              <p>No photo selected yet.</p>
            )}

            {tryOnError && (
              <p className="error-message" role="alert">
                {tryOnError}
              </p>
            )}

            {tryOnResult && (
              <>
                <h3>Your try-on preview</h3>
                <img
                  src={tryOnResult}
                  alt="Generated virtual try-on preview"
                  style={{
                    display: "block",
                    width: "100%",
                    maxHeight: "50vh",
                    objectFit: "contain",
                    margin: "20px auto",
                    borderRadius: "8px",
                  }}
                />
              </>
            )}

            <button
              className="try-button"
              onClick={generateTryOn}
              disabled={!userPhoto || tryOnLoading}
            >
              {tryOnLoading ? "Generating try-on..." : "Generate try-on"}
            </button>
          </section>
        </div>
      )}

      <footer className="footer">
        STYLIST AI · YOUR PERSONAL STYLE, REIMAGINED
      </footer>
    </div>
  );
}

export default App;
