export default function ComingSoon({ feature }: { feature: string }) {
  return (
    <div
      style={{
        padding: "48px 32px",
        background: "#111",
        border: "1px solid #1a1a1a",
        borderLeft: "3px solid #f59e0b",
        borderRadius: "8px",
        fontFamily: "monospace",
        color: "#bbb",
      }}
    >
      <p
        style={{
          fontSize: "11px",
          color: "#f59e0b",
          letterSpacing: "2px",
          textTransform: "uppercase",
          marginBottom: "10px",
        }}
      >
        Live backend required
      </p>
      <h2 style={{ fontSize: "20px", color: "#e5e5e5", marginBottom: "10px" }}>
        {feature} — coming soon
      </h2>
      <p style={{ fontSize: "13px", lineHeight: 1.6, color: "#888" }}>
        This page depends on the FastAPI backend and live data feeds, which are not part
        of the static demo. The full version will be hosted soon.
      </p>
    </div>
  );
}
