"""
engine/classifier.py
────────────────────
Trained RandomForest segment classifier.

Because we only have 40 labelled customers in seed.py, we generate a
synthetic training corpus (200 samples/segment × 6 segments = 1,200 rows)
whose feature distributions are derived from those real customers.  The
trained model then replaces the hand-coded scoring functions in predictor.py.

Feature vector (15 dimensions)
───────────────────────────────
  0  avg_order_value
  1  purchase_freq
  2  discount_usage
  3  size_consistent
  4  engagement_score
  5  timing_morning        ┐
  6  timing_lunch          │
  7  timing_afternoon      │  one-hot
  8  timing_evening        │
  9  timing_late_night     │
 10  timing_varied         │
 11  timing_weekend        ┘
 12  has_streetwear
 13  has_athletic
 14  has_formal
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from models.customer import CustomerProfile, Segment, SessionTiming, Category


# ── Segment distributions ─────────────────────────────────────────────────────
# Each entry: (mean, std, lo_clip, hi_clip)
# Derived from the 40 seed customers in data/seed.py.

_DISTS: dict[Segment, dict] = {
    Segment.FULL_PRICE: {
        "aov":        (267,  45,  150, 450),
        "freq":       (4.2,  0.6,  2.5,  6.5),
        "discount":   (0.07, 0.03, 0.01, 0.18),
        "size":       (0.93, 0.03, 0.80, 1.00),
        "engagement": (89,   6,   70,  100),
        # timing weights: [morning, lunch, afternoon, evening, late_night, varied, weekend]
        "timing_w":   [0.00, 0.00, 0.00, 0.92, 0.00, 0.04, 0.04],
        # category probabilities (independent bernoullis): [streetwear, athletic, formal]
        "cat_p":      [0.50, 0.33, 0.75],
    },
    Segment.NIGHT_STREETWEAR: {
        "aov":        (89,  16,  50, 140),
        "freq":       (2.4,  0.4,  1.2,  4.0),
        "discount":   (0.20, 0.08, 0.05, 0.45),
        "size":       (0.85, 0.04, 0.70, 1.00),
        "engagement": (65,   9,   40,   85),
        "timing_w":   [0.00, 0.00, 0.00, 0.00, 0.96, 0.02, 0.02],
        "cat_p":      [0.92, 0.18, 0.05],
    },
    Segment.LUNCH_SHOPPER: {
        "aov":        (78,  17,  40, 130),
        "freq":       (2.8,  0.4,  1.5,  4.5),
        "discount":   (0.41, 0.08, 0.20, 0.65),
        "size":       (0.85, 0.04, 0.70, 1.00),
        "engagement": (59,   8,   38,   80),
        "timing_w":   [0.00, 0.94, 0.00, 0.00, 0.00, 0.04, 0.02],
        "cat_p":      [0.55, 0.65, 0.10],
    },
    Segment.SALE_SHOPPER: {
        "aov":        (42,   9,  20,  70),
        "freq":       (1.3,  0.3,  0.5,  2.2),
        "discount":   (0.91, 0.05, 0.75, 1.00),
        "size":       (0.68, 0.05, 0.50, 0.85),
        "engagement": (34,   9,   10,   55),
        "timing_w":   [0.00, 0.10, 0.15, 0.30, 0.00, 0.45, 0.00],
        "cat_p":      [0.70, 0.50, 0.40],
    },
    Segment.ATHLETIC_REGULAR: {
        "aov":        (131, 16,  90, 175),
        "freq":       (3.9,  0.5,  2.5,  5.5),
        "discount":   (0.21, 0.05, 0.10, 0.38),
        "size":       (0.95, 0.02, 0.88, 1.00),
        "engagement": (81,   7,   60,   97),
        "timing_w":   [0.96, 0.00, 0.00, 0.00, 0.00, 0.02, 0.02],
        "cat_p":      [0.20, 0.95, 0.05],
    },
    Segment.FORMAL_RARE: {
        "aov":        (449, 52, 320, 600),
        "freq":       (0.64, 0.12, 0.30, 1.00),
        "discount":   (0.03, 0.02, 0.00, 0.10),
        "size":       (0.98, 0.01, 0.93, 1.00),
        "engagement": (50,   5,   38,   65),
        "timing_w":   [0.00, 0.00, 0.00, 0.00, 0.00, 0.02, 0.98],
        "cat_p":      [0.05, 0.05, 1.00],
    },
}

_TIMING_ORDER = [
    SessionTiming.MORNING,
    SessionTiming.LUNCH,
    SessionTiming.AFTERNOON,
    SessionTiming.EVENING,
    SessionTiming.LATE_NIGHT,
    SessionTiming.VARIED,
    SessionTiming.WEEKEND,
]

_SEGMENT_ORDER = list(_DISTS.keys())   # fixed label ordering
_SAMPLES_PER_SEGMENT = 200
_RANDOM_SEED = 42


# ── Synthetic training data generator ────────────────────────────────────────

def _generate_dataset(
    samples_per_segment: int = _SAMPLES_PER_SEGMENT,
    seed: int = _RANDOM_SEED,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Return (X, y) where X is (N, 15) float32 and y is (N,) int class labels.
    Labels correspond to _SEGMENT_ORDER indices.
    """
    rng = np.random.default_rng(seed)
    X_parts, y_parts = [], []

    for label_idx, seg in enumerate(_SEGMENT_ORDER):
        d = _DISTS[seg]
        n = samples_per_segment

        def _gauss(mean, std, lo, hi):
            return np.clip(rng.normal(mean, std, n), lo, hi)

        aov        = _gauss(*d["aov"])
        freq       = _gauss(*d["freq"])
        discount   = _gauss(*d["discount"])
        size       = _gauss(*d["size"])
        engagement = _gauss(*d["engagement"])

        # timing one-hot: sample one timing slot per row
        timing_idx = rng.choice(len(_TIMING_ORDER), size=n, p=d["timing_w"])
        timing_ohe = np.zeros((n, len(_TIMING_ORDER)), dtype=np.float32)
        timing_ohe[np.arange(n), timing_idx] = 1.0

        # category flags (independent bernoulli)
        cat_p = d["cat_p"]
        has_sw  = (rng.random(n) < cat_p[0]).astype(np.float32)
        has_ath = (rng.random(n) < cat_p[1]).astype(np.float32)
        has_frm = (rng.random(n) < cat_p[2]).astype(np.float32)
        # ensure at least one category per row
        no_cat = (has_sw + has_ath + has_frm) == 0
        dominant = np.argmax(cat_p)
        if dominant == 0: has_sw[no_cat]  = 1.0
        elif dominant == 1: has_ath[no_cat] = 1.0
        else: has_frm[no_cat] = 1.0

        numeric = np.stack([aov, freq, discount, size, engagement], axis=1).astype(np.float32)
        cats    = np.stack([has_sw, has_ath, has_frm], axis=1)
        X_seg   = np.concatenate([numeric, timing_ohe, cats], axis=1)

        X_parts.append(X_seg)
        y_parts.append(np.full(n, label_idx, dtype=np.int32))

    return np.vstack(X_parts), np.concatenate(y_parts)


# ── Feature extraction ────────────────────────────────────────────────────────

def extract_features(c: CustomerProfile) -> np.ndarray:
    """Convert a CustomerProfile into the 15-dim feature vector."""
    timing_ohe = [0.0] * len(_TIMING_ORDER)
    timing_ohe[_TIMING_ORDER.index(c.timing)] = 1.0

    has_sw  = float(Category.STREETWEAR in c.categories)
    has_ath = float(Category.ATHLETIC   in c.categories)
    has_frm = float(Category.FORMAL     in c.categories)

    vec = [
        c.avg_order_value,
        c.purchase_freq,
        c.discount_usage,
        c.size_consistent,
        float(c.engagement_score),
        *timing_ohe,
        has_sw, has_ath, has_frm,
    ]
    return np.array(vec, dtype=np.float32).reshape(1, -1)


# ── Model training ────────────────────────────────────────────────────────────

def _build_model() -> tuple[RandomForestClassifier, LabelEncoder]:
    X, y = _generate_dataset()

    le = LabelEncoder()
    le.fit(np.arange(len(_SEGMENT_ORDER)))   # labels are already 0..5

    clf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=_RANDOM_SEED,
        n_jobs=-1,
    )
    clf.fit(X, y)
    return clf, le


# Lazy singleton — trained once on first import
_MODEL: RandomForestClassifier | None = None
_LE:    LabelEncoder | None = None


def _get_model() -> tuple[RandomForestClassifier, LabelEncoder]:
    global _MODEL, _LE
    if _MODEL is None:
        _MODEL, _LE = _build_model()
    return _MODEL, _LE


# ── Public API ────────────────────────────────────────────────────────────────

def classify_customer(c: CustomerProfile) -> dict[Segment, float]:
    """
    Run the trained RandomForest on *c* and return a dict mapping each
    Segment to a probability (0–100 scale).  The highest value is the
    model's predicted segment.
    """
    clf, _ = _get_model()
    X = extract_features(c)
    probs = clf.predict_proba(X)[0]                 # shape (6,)
    return {seg: round(float(probs[i]) * 100, 1)
            for i, seg in enumerate(_SEGMENT_ORDER)}


def get_feature_importances() -> dict[str, float]:
    """Return a human-readable feature-importance dict (useful for debugging)."""
    clf, _ = _get_model()
    names = [
        "avg_order_value", "purchase_freq", "discount_usage",
        "size_consistent", "engagement_score",
        "timing_morning", "timing_lunch", "timing_afternoon",
        "timing_evening", "timing_late_night", "timing_varied", "timing_weekend",
        "has_streetwear", "has_athletic", "has_formal",
    ]
    return {n: round(float(v), 4)
            for n, v in zip(names, clf.feature_importances_)}
