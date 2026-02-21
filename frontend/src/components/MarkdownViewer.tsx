import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownViewerProps {
  content: string;
  className?: string;
}

export default function MarkdownViewer({ content, className = '' }: MarkdownViewerProps) {
  if (!content) {
    return <div className="text-[#9B9A97] text-sm italic">결과가 여기에 표시됩니다.</div>;
  }

  return (
    <div className={`markdown-body ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="text-xl font-bold text-[#37352F] mt-6 mb-3 pb-2 border-b border-[#E9E9E7]">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg font-bold text-[#37352F] mt-5 mb-2">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-semibold text-[#37352F] mt-4 mb-2">{children}</h3>,
          p: ({ children }) => <p className="text-sm text-[#37352F] mb-3 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1 text-sm text-[#37352F]">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1 text-sm text-[#37352F]">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-[#37352F]">{children}</strong>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-3 border-[#2383E2] pl-4 my-3 text-sm text-[#787774] italic">{children}</blockquote>
          ),
          code: ({ children, className: codeClass }) => {
            const isBlock = codeClass?.startsWith('language-');
            if (isBlock) {
              return (
                <pre className="bg-[#F7F6F3] rounded-lg p-4 my-3 overflow-x-auto">
                  <code className="text-xs font-mono text-[#37352F]">{children}</code>
                </pre>
              );
            }
            return <code className="bg-[#F7F6F3] px-1.5 py-0.5 rounded text-xs font-mono text-[#EB5757]">{children}</code>;
          },
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto">
              <table className="w-full text-sm border-collapse border border-[#E9E9E7]">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-[#F7F6F3]">{children}</thead>,
          th: ({ children }) => <th className="border border-[#E9E9E7] px-3 py-2 text-left font-semibold text-[#37352F]">{children}</th>,
          td: ({ children }) => <td className="border border-[#E9E9E7] px-3 py-2 text-[#37352F]">{children}</td>,
          hr: () => <hr className="my-4 border-[#E9E9E7]" />,
          a: ({ href, children }) => <a href={href} className="text-[#2383E2] hover:underline" target="_blank" rel="noreferrer">{children}</a>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
