import ArchiveAbout from "@/components/ArchiveAbout";
export default async function Review() {
  if (process.env.NEXT_PUBLIC_STATIC_ARCHIVE === "true")
    return <ArchiveAbout />;
  const { default: ReviewStudio } = await import("@/components/ReviewStudio");
  return <ReviewStudio />;
}
