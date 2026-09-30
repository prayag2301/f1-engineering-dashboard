import { TEAM_KEYS, type TeamKey } from "@/lib/releases";
import { notFound } from "next/navigation";
import ReleaseExplorer from "@/components/ReleaseExplorer";
export function generateStaticParams() {
  return TEAM_KEYS.map((teamId) => ({ teamId }));
}
export const dynamicParams = false;
export default function Car({ params }: { params: { teamId: string } }) {
  if (!TEAM_KEYS.includes(params.teamId as TeamKey)) notFound();
  return <ReleaseExplorer initialTeam={params.teamId as TeamKey} />;
}
