import { ProblemSubmissionPage } from "../../../components/problem-submission-page";

export default async function ProblemPage({ params }: { params: Promise<{ problemId: string }> }) {
  const { problemId } = await params;
  return <ProblemSubmissionPage problemId={problemId} />;
}
