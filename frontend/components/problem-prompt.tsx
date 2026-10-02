export function ProblemPrompt({ html }: { html: string }) {
  const normalized = html
    .replace(/<(p|div)>\s*(?:&nbsp;|\u00a0|<br\s*\/?>(?:\s|&nbsp;|\u00a0)*)*<\/\1>/gi, "")
    .replace(/>\s+</g, "><");

  return <div className="full problem-prompt" dangerouslySetInnerHTML={{ __html: normalized }} />;
}
