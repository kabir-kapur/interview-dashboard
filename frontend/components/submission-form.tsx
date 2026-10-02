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

  return <form onSubmit={onSubmit}><div className="heading"><h3>Submission</h3><button>Save submission</button></div><CodeField value={code} onChange={setCode} /><input name="code" type="hidden" value={code} /><div className="grid"><Field name="time" label="Time complexity" value={submission?.timeComplexity} /><Field name="space" label="Space complexity" value={submission?.spaceComplexity} /></div><Field name="explanation" label="Explanation (optional)" value={submission?.explanation} /></form>;
}

function Field({ name, label, value, required }: { name: string; label: string; value?: string; required?: boolean }) { return <label>{label}<textarea required={required} name={name} defaultValue={value} /></label>; }

function CodeField({ value, onChange }: { value: string; onChange: (code: string) => void }) {
  return <label>Code <span className="runtime-label">Python 3 runtime</span><CodeMirror className="code-editor" value={value} height="300px" theme="dark" extensions={[python(), keymap.of([indentWithTab])]} onChange={onChange} basicSetup={{ lineNumbers: true, bracketMatching: true, highlightActiveLine: true, indentOnInput: true }} /></label>;
}
