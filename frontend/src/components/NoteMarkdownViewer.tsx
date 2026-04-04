/**
 * NoteMarkdownViewer — MarkdownViewer extended with wikilink/tag/callout support.
 */
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { preprocessNoteMarkdown } from '../utils/noteMarkdown';

interface NoteMarkdownViewerProps {
  content: string;
  existingSlugs?: Set<string>;
  onNavigate?: (slug: string) => void;
  onTagClick?: (tag: string) => void;
  className?: string;
}

export default function NoteMarkdownViewer({
  content,
  existingSlugs = new Set(),
  onNavigate,
  onTagClick,
  className = '',
}: NoteMarkdownViewerProps) {
  const processed = preprocessNoteMarkdown(content, existingSlugs);

  return (
    <div className={`note-md-viewer ${className}`}>
      <ReactMarkdown
        remarkPlugins={[[remarkGfm, { singleTilde: false }]]}
        rehypePlugins={[rehypeRaw]}
        components={{
          h1: ({ children }) => <h1 className="text-xl font-bold mt-4 mb-2 pb-1 border-b border-slate-200">{children}</h1>,
          h2: ({ children }) => <h2 className="text-lg font-bold mt-3 mb-1.5 pb-0.5 border-b border-slate-100">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-semibold mt-2 mb-1">{children}</h3>,
          p: ({ children }) => <p className="mb-2 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-5 my-1.5 space-y-0.5">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 my-1.5 space-y-0.5">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-blue-300 bg-blue-50/50 pl-3 pr-2 py-1 my-2 text-slate-600 italic rounded-r">
              {children}
            </blockquote>
          ),
          code: ({ className: cn, children, ...props }) => {
            const isBlock = cn?.startsWith('language-');
            if (isBlock) {
              return (
                <pre className="bg-slate-800 text-slate-100 rounded-lg p-3 my-2 overflow-x-auto text-[13px]">
                  <code className={cn} {...props}>{children}</code>
                </pre>
              );
            }
            return <code className="bg-rose-50 text-rose-700 px-1 py-0.5 rounded text-[0.9em]" {...props}>{children}</code>;
          },
          table: ({ children }) => <table className="w-full border-collapse border border-slate-200 my-2 text-sm">{children}</table>,
          th: ({ children }) => <th className="border border-slate-200 px-2 py-1 bg-slate-50 font-semibold text-left">{children}</th>,
          td: ({ children }) => <td className="border border-slate-200 px-2 py-1">{children}</td>,
          a: ({ href, children, ...props }) => {
            const el = props as any;
            const wikilink = el['data-wikilink'];
            if (wikilink) {
              return (
                <a
                  href="#"
                  className={`wikilink ${el.className || ''}`}
                  onClick={(e) => { e.preventDefault(); onNavigate?.(wikilink); }}
                  title={`→ ${wikilink}`}
                >
                  {children}
                </a>
              );
            }
            return <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline" {...props}>{children}</a>;
          },
          span: ({ children, ...props }) => {
            const el = props as any;
            const tag = el['data-tag'];
            if (tag) {
              return (
                <span
                  className="note-tag cursor-pointer"
                  onClick={() => onTagClick?.(tag)}
                >
                  #{tag}
                </span>
              );
            }
            return <span {...props}>{children}</span>;
          },
          img: ({ src, alt }) => (
            <img src={src} alt={alt || ''} className="max-w-full rounded-lg border border-slate-200 my-2" />
          ),
        }}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}
