import { CoursePlayerClient } from "./CoursePlayerClient";

export default async function CoursePlayPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CoursePlayerClient id={id} />;
}
