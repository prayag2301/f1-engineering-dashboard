"use client";


const CATEGORIES = ["All", "Aero", "Mechanical", "Cooling", "Floor", "Suspension", "Power Unit", "Other"];

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
