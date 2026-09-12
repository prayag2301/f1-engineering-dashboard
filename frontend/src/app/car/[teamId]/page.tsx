import { notFound } from "next/navigation";
import Link from "next/link";
import ReleaseExplorer from "@/components/ReleaseExplorer";
export function generateStaticParams() {
  return [{ teamId: "ferrari" }, { teamId: "mercedes" }];
}
export const dynamicParams = false;
export default function Car({ params }: { params: { teamId: string } }) {
  if (params.teamId !== "ferrari" && params.teamId !== "mercedes") notFound();
  return (
    <main className="container">
      <Link className="text-link" href="/">
        ← Archive
      </Link>
      <ReleaseExplorer initialTeam={params.teamId} />
    </main>
  );
}
