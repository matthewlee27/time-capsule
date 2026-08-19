"use client";

// Approximate preference order from a fixed, small comparison budget —
// not an exact sort. A merge sort needs n*log2(n) comparisons (148 for
// 30 tracks) to guarantee a total order; that's too many picks to ask
// of someone. Instead we spend budget = n * (2/3) comparisons updating
// an Elo rating per track (same idea "hot or not"-style apps use) and
// sort by final rating. More comparisons sharpen the result; fewer just
// make it noisier — unlike an unfinished merge sort, which has no valid
// partial order at all.

import { useEffect, useRef, useState } from "react";

const K_FACTOR = 32;
const STARTING_RATING = 1500;
const BUDGET_RATIO = 2 / 3; // 30 tracks -> 20 comparisons, 15 -> 10

function expectedScore(ratingA, ratingB) {
  return 1 / (1 + 10 ** ((ratingB - ratingA) / 400));
}

function shuffledIndices(n) {
  const idx = Array.from({ length: n }, (_, i) => i);
  for (let i = idx.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [idx[i], idx[j]] = [idx[j], idx[i]];
  }
  return idx;
}

function pairKey(a, b) {
  return a < b ? `${a}-${b}` : `${b}-${a}`;
}

// After round 1 (everyone compared once), spend the rest of the budget
// on whichever un-asked pair currently has the closest ratings — that's
// the comparison the model is least sure about, so it does the most to
// sharpen the final order.
function pickClosestPair(ratings, asked) {
  let best = null;
  let bestGap = Infinity;
  for (let i = 0; i < ratings.length; i++) {
    for (let j = i + 1; j < ratings.length; j++) {
      if (asked.has(pairKey(i, j))) continue;
      const gap = Math.abs(ratings[i] - ratings[j]);
      if (gap < bestGap) {
        bestGap = gap;
        best = [i, j];
      }
    }
  }
  return best;
}

function estimateBudget(n) {
  return Math.max(1, Math.round(n * BUDGET_RATIO));
}

export default function PreferenceSort({ items, onComplete }) {
  const ratingsRef = useRef([]);
  const askedRef = useRef(new Set());
  const scheduleRef = useRef([]);
  const budgetRef = useRef(0);
  const [pairIdx, setPairIdx] = useState(null);
  const [comparisonsMade, setComparisonsMade] = useState(0);

  useEffect(() => {
    const n = items.length;
    if (n <= 1) {
      onComplete(items);
      return;
    }

    ratingsRef.current = Array(n).fill(STARTING_RATING);
    askedRef.current = new Set();
    budgetRef.current = estimateBudget(n);

    const order = shuffledIndices(n);
    const roundOne = [];
    for (let i = 0; i + 1 < order.length; i += 2) {
      roundOne.push([order[i], order[i + 1]]);
    }
    scheduleRef.current = roundOne;

    setComparisonsMade(0);
    setPairIdx(nextPair());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

  function nextPair() {
    if (scheduleRef.current.length > 0) {
      return scheduleRef.current.shift();
    }
    return pickClosestPair(ratingsRef.current, askedRef.current);
  }

  function finish() {
    const ranked = items
      .map((item, i) => ({ item, rating: ratingsRef.current[i] }))
      .sort((a, b) => b.rating - a.rating)
      .map((x) => x.item);
    onComplete(ranked);
  }

  function pick(aWon) {
    const [i, j] = pairIdx;
    askedRef.current.add(pairKey(i, j));

    const ra = ratingsRef.current[i];
    const rb = ratingsRef.current[j];
    const ea = expectedScore(ra, rb);
    const eb = 1 - ea;
    ratingsRef.current[i] = ra + K_FACTOR * ((aWon ? 1 : 0) - ea);
    ratingsRef.current[j] = rb + K_FACTOR * ((aWon ? 0 : 1) - eb);

    const made = comparisonsMade + 1;
    setComparisonsMade(made);

    const next = made < budgetRef.current ? nextPair() : null;
    if (!next) {
      setPairIdx(null);
      finish();
      return;
    }
    setPairIdx(next);
  }

  if (!pairIdx) return null;

  const [i, j] = pairIdx;
  const a = items[i];
  const b = items[j];

  return (
    <section>
      <p>Which one fits better?</p>
      <div style={{ display: "flex", gap: "0.75rem" }}>
        <button onClick={() => pick(true)}>
          {a.artist} — {a.track}
        </button>
        <button onClick={() => pick(false)}>
          {b.artist} — {b.track}
        </button>
      </div>
      <p>
        {comparisonsMade} / {budgetRef.current} comparisons
      </p>
    </section>
  );
}
