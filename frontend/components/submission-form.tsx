"use client";

import { python } from "@codemirror/lang-python";
import { indentWithTab } from "@codemirror/commands";
import { keymap } from "@codemirror/view";
import CodeMirror from "@uiw/react-codemirror";
import { FormEvent, useEffect, useState } from "react";
import { Submission } from "../lib/types";

export function SubmissionForm({ submission, starterCode, onSubmit }: { submission?: Submission; starterCode?: string; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  const [code, setCode] = useState(submission?.code || starterCode || "");

  useEffect(() => setCode(submission?.code || starterCode || ""), [submission?.id, submission?.code, starterCode]);

  return <form onSubmit={onSubmit}><div className="heading"><h3>Submission</h3><button>Save submission</button></div><CodeField value={code} onChange={setCode} /><input name="code" type="hidden" value={code} /><div className="grid"><Field name="time" label="Time complexity" value={submission?.timeComplexity} /><Field name="space" label="Space complexity" value={submission?.spaceComplexity} /></div><div className="grid"><label>Completion outcome (optional)<select name="completionState" defaultValue={submission?.completionState || ""}><option value="">Not recorded</option><option value="solved_independently">Solved independently</option><option value="hint_used">Hint used</option><option value="gave_up">Gave up</option></select></label><label>Time taken in minutes (optional)<input name="timeTakenMinutes" type="number" min="0" defaultValue={submission?.timeTakenMinutes} /></label></div><Field name="explanation" label="Explanation (optional)" value={submission?.explanation} /></form>;
}

function Field({ name, label, value, required }: { name: string; label: string; value?: string; required?: boolean }) { return <label>{label}<textarea required={required} name={name} defaultValue={value} /></label>; }

function CodeField({ value, onChange }: { value: string; onChange: (code: string) => void }) {
  return <label>Code <span className="runtime-label">Python 3 runtime</span><CodeMirror className="code-editor" value={value} height="300px" theme="dark" extensions={[python(), keymap.of([indentWithTab])]} onChange={onChange} basicSetup={{ lineNumbers: true, bracketMatching: true, highlightActiveLine: true, indentOnInput: true }} /></label>;
}
