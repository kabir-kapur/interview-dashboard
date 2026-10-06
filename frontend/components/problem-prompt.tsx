import ReactMarkdown from "react-markdown";

const looksLikeHtml = (value: string) => /<\/?[a-z][^>]*>/i.test(value);

function markdownContent(prompt: string): string | undefined {
  const wrapped = prompt.match(/^\s*<pre>\s*([\s\S]*?)\s*<\/pre>\s*$/i)?.[1];
  const content = wrapped ?? prompt;
  const looksLikeMarkdown = /(^#{1,6}\s|^\s*[-*+]\s|^\s*\d+\.\s|\*\*|```)/m.test(content);
  return !looksLikeHtml(content) && looksLikeMarkdown ? content : undefined;
}

export function ProblemPrompt({ html }: { html: string }) {
  const markdown = markdownContent(html);
  const normalized = html
    .replace(/<(p|div)>\s*(?:&nbsp;|\u00a0|<br\s*\/?>(?:\s|&nbsp;|\u00a0)*)*<\/\1>/gi, "")
    .replace(/>\s+</g, "><");

  if (markdown) return <div className="full problem-prompt"><ReactMarkdown>{markdown}</ReactMarkdown></div>;

  return <div className="full problem-prompt" dangerouslySetInnerHTML={{ __html: normalized }} />;
}
