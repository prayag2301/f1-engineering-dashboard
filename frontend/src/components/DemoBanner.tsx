export default function DemoBanner() {
  if (process.env.NEXT_PUBLIC_DEMO_MODE !== "true") return null;
  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        width: "100%",
        padding: "8px 16px",
        background: "#f59e0b",
        color: "#0a0a0a",
        fontFamily: "monospace",
        fontSize: "12px",
        fontWeight: 600,
        textAlign: "center",
        letterSpacing: "0.5px",
        borderBottom: "1px solid #d97706",
      }}
    >
      STATIC DEMO — using mock data only. Live version with full backend coming soon.
    </div>
  );
}
