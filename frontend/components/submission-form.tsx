import { FormEvent, KeyboardEvent } from "react";
import { Submission } from "../lib/types";

export function SubmissionForm({ submission, onSubmit }: { submission?: Submission; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return <form onSubmit={onSubmit}><div className="heading"><h3>Submission</h3><button>Save submission</button></div><CodeField value={submission?.code} /><div className="grid"><Field name="time" label="Time complexity" value={submission?.timeComplexity} /><Field name="space" label="Space complexity" value={submission?.spaceComplexity} /></div><Field name="explanation" label="Explanation (optional)" value={submission?.explanation} /></form>;
}

function Field({ name, label, value, required }: { name: string; label: string; value?: string; required?: boolean }) { return <label>{label}<textarea required={required} name={name} defaultValue={value} /></label>; }

function CodeField({ value }: { value?: string }) {
  const indent = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Tab") return;
    event.preventDefault();
    const field = event.currentTarget;
    const before = field.value.slice(0, field.selectionStart);
    const after = field.value.slice(field.selectionEnd);
    field.value = `${before}    ${after}`;
    field.selectionStart = field.selectionEnd = before.length + 4;
  };
  return <label>Code<textarea className="code-editor" required name="code" defaultValue={value} onKeyDown={indent} spellCheck={false} autoCapitalize="off" autoCorrect="off" wrap="off" /></label>;
}
