import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownViewerProps {
  content: string;
  className?: string;
}

export default function MarkdownViewer({ content, className = '' }: MarkdownViewerProps) {
  if (!content) {
    return <div className="text-slate-400 text-sm italic">결과가 여기에 표시됩니다.</div>;
  }

  return (
    <div className={`markdown-body ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-xl font-bold text-slate-800 mt-6 mb-3 pb-2 border-b border-slate-200">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-bold text-slate-800 mt-5 mb-2">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-semibold text-slate-700 mt-4 mb-2">{children}</h3>
          ),
          p: ({ children }) => (
            <p className="text-sm text-slate-700 mb-3 leading-[1.75]">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-5 mb-3 space-y-1 text-sm text-slate-700">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 mb-3 space-y-1 text-sm text-slate-700">{children}</ol>
          ),
          li: ({ children }) => <li className="leading-[1.75]">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-slate-800">{children}</strong>,
          del: ({ children }) => <del className="line-through text-slate-500">{children}</del>,
          img: ({ src, alt }) => (
            <img src={src} alt={alt} className="max-w-full rounded-lg my-3 border border-slate-200" />
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-[3px] border-blue-400 pl-4 my-3 text-sm text-slate-500 italic bg-blue-50/30 py-2 rounded-r-lg">{children}</blockquote>
          ),
          code: ({ children, className: codeClass }) => {
            const isBlock = codeClass?.startsWith('language-');
            if (isBlock) {
              return (
                <pre className="bg-slate-900 rounded-xl p-4 my-3 overflow-x-auto">
                  <code className="text-xs text-slate-200" style={{ fontFamily: 'var(--font-mono)' }}>{children}</code>
                </pre>
              );
            }
            return (
              <code className="bg-slate-100 px-1.5 py-0.5 rounded-md text-xs text-rose-600 font-medium" style={{ fontFamily: 'var(--font-mono)' }}>
                {children}
              </code>
            );
          },
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-sm border-collapse">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-slate-50">{children}</thead>,
          th: ({ children }) => (
            <th className="border-b border-slate-200 px-3 py-2.5 text-left font-semibold text-slate-700 text-xs uppercase tracking-wider">{children}</th>
          ),
          td: ({ children }) => (
            <td className="border-b border-slate-100 px-3 py-2 text-slate-700">{children}</td>
          ),
          hr: () => <hr className="my-5 border-slate-200" />,
          a: ({ href, children }) => (
            <a href={href} className="text-blue-500 hover:text-blue-600 underline underline-offset-2 decoration-blue-200 hover:decoration-blue-400 transition-colors" target="_blank" rel="noreferrer">{children}</a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
