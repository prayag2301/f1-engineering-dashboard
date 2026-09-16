import Link from "next/link";
export default function NotFound() {
  return (
    <main className="container archive-about">
      <p className="eyebrow">404 / PAGE NOT FOUND</p>
      <h1>This view is unavailable.</h1>
      <p>The archive currently covers Ferrari and Mercedes in 2026.</p>
      <Link className="button" href="/">
        Return to the car archive →
      </Link>
    </main>
  );
}
