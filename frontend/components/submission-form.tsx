import { FormEvent } from "react";
import { Submission } from "../lib/types";

export function SubmissionForm({ submission, onSubmit }: { submission?: Submission; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return <form onSubmit={onSubmit}><div className="heading"><h3>Submission</h3><button>Save submission</button></div><Field name="code" label="Code" value={submission?.code} required /><div className="grid"><Field name="time" label="Time complexity" value={submission?.timeComplexity} /><Field name="space" label="Space complexity" value={submission?.spaceComplexity} /></div><Field name="explanation" label="Explanation (optional)" value={submission?.explanation} /></form>;
}

function Field({ name, label, value, required }: { name: string; label: string; value?: string; required?: boolean }) { return <label>{label}<textarea required={required} name={name} defaultValue={value} /></label>; }
