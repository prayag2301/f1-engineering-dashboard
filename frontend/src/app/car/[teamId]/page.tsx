import CarPageClient from "./CarPageClient";

const TEAM_IDS = [
  "red-bull",
  "ferrari",
  "mercedes",
  "mclaren",
  "aston-martin",
  "alpine",
  "williams",
  "racing-bulls",
  "haas",
  "audi",
  "cadillac",
];

export function generateStaticParams() {
  return TEAM_IDS.map((teamId) => ({ teamId }));
}

export const dynamicParams = false;

export default function CarPage({ params }: { params: { teamId: string } }) {
  return <CarPageClient params={params} />;
}
