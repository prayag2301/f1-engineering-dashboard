"use client";

import { useState } from "react";

const CATEGORIES = ["All", "Aero", "Mechanical", "Cooling", "Floor", "Suspension"];

export default function CategoryFilter({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (cat: string) => void;
}) {
  return (
    <div className="filters">
      {CATEGORIES.map((cat) => (
        <button
          key={cat}
          className={`filter-btn ${selected === cat ? "filter-btn--active" : ""}`}
          onClick={() => onSelect(cat)}
        >
          {cat}
        </button>
      ))}
    </div>
  );
}
