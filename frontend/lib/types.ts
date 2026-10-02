export type Status = "not_started" | "attempted" | "solved" | "reviewed_needs_retry" | "reviewed_complete";
export type Evaluation = { retryRecommended: boolean; completeness?: string; correctness?: string; bugsAndEdgeCases?: string; complexityAnalysis?: string; reasoningQuality?: string; betterApproach?: string; conceptTags?: string[]; notes?: string };
export type Submission = { id: string; code: string; timeComplexity?: string; spaceComplexity?: string; explanation?: string; evaluation?: Evaluation };
export type Problem = { id: string; title: string; prompt: string; link?: string; sourceId?: string; starterCode?: string; topics?: string[]; difficulty?: string; companies?: string[]; status: Status; latestSubmission?: Submission };
export type Plan = { problems: Problem[] };
export const statusLabels: Record<Status, string> = { not_started: "Not started", attempted: "Attempted", solved: "Solved", reviewed_needs_retry: "Reviewed · needs retry", reviewed_complete: "Reviewed · complete" };
