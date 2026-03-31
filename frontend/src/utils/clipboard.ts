/**
 * Rich clipboard copy & title extraction utilities.
 * - copyRichText: copies both plain text + HTML so Word paste preserves formatting
 * - extractTitle: extracts first heading from markdown for filenames
 * - generateFilename: generates standardized filename with project, menu, date/time
 */

/**
 * Generate standardized filename: (프로젝트명)_메뉴이름_YYYYMMDD_HHmmss.ext
 */
export function generateFilename(menuName: string, ext: string, project?: string): string {
  const now = new Date();
  const date = now.getFullYear().toString()
    + String(now.getMonth() + 1).padStart(2, '0')
    + String(now.getDate()).padStart(2, '0');
  const time = String(now.getHours()).padStart(2, '0')
    + String(now.getMinutes()).padStart(2, '0')
    + String(now.getSeconds()).padStart(2, '0');
  const sanitize = (s: string) => s.replace(/[\\/:*?"<>|]/g, '_').trim();
  const prefix = project ? `${sanitize(project)}_` : '';
  const cleanExt = ext.startsWith('.') ? ext.slice(1) : ext;
  return `${prefix}${sanitize(menuName)}_${date}_${time}.${cleanExt}`;
}

/** Simple markdown → HTML converter for clipboard (not for display). */
function mdToHtml(md: string): string {
  const lines = md.split('\n');
  const out: string[] = [];
  let inTable = false;
  let inCode = false;

  for (const raw of lines) {
    const line = raw.trimEnd();

    // Code block toggle
    if (line.trim().startsWith('```')) {
      if (inCode) { out.push('</pre>'); inCode = false; }
      else { out.push('<pre style="background:#f5f5f5;padding:8px;font-family:monospace;font-size:12px;">'); inCode = true; }
      continue;
    }
    if (inCode) { out.push(esc(line)); continue; }

    const s = line.trim();
    if (!s) {
      if (inTable) { out.push('</table>'); inTable = false; }
      continue;
    }

    // Table
    if (s.startsWith('|') && s.endsWith('|')) {
      const cells = s.split('|').slice(1, -1).map(c => c.trim());
      if (cells.every(c => /^[-:\s]+$/.test(c))) continue; // separator
      if (!inTable) {
        out.push('<table style="border-collapse:collapse;width:100%;margin:8px 0;">');
        inTable = true;
        const tag = 'th';
        out.push('<tr>' + cells.map(c =>
          `<${tag} style="border:1px solid #dee2e6;padding:6px 10px;background:#f0f2f6;font-weight:bold;text-align:left;font-size:13px;">${inline(c)}</${tag}>`
        ).join('') + '</tr>');
      } else {
        out.push('<tr>' + cells.map(c =>
          `<td style="border:1px solid #dee2e6;padding:6px 10px;text-align:left;font-size:13px;">${inline(c)}</td>`
        ).join('') + '</tr>');
      }
      continue;
    }
    if (inTable) { out.push('</table>'); inTable = false; }

    // Headers
    const hm = s.match(/^(#{1,6})\s+(.+)/);
    if (hm) {
      const lv = hm[1].length;
      const sizes = ['20px', '17px', '15px', '14px', '13px', '13px'];
      out.push(`<h${lv} style="font-size:${sizes[lv - 1]};font-weight:bold;margin:12px 0 6px;">${inline(hm[2])}</h${lv}>`);
      continue;
    }

    // HR
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(s)) { out.push('<hr>'); continue; }

    // Blockquote
    if (s.startsWith('>')) {
      out.push(`<blockquote style="border-left:4px solid #0068c9;padding-left:12px;color:#555;margin:8px 0;">${inline(s.slice(1).trim())}</blockquote>`);
      continue;
    }

    // Unordered list - detect indent level for bullet style
    if (/^\s*[-*]\s/.test(line)) {
      const indent = line.match(/^(\s*)/)?.[1].length || 0;
      const text = inline(s.replace(/^[-*]\s+/, ''));
      if (indent >= 2) {
        out.push(`<p style="margin:1px 0;font-size:13px;line-height:1.6;padding-left:18px;">- ${text}</p>`);
      } else {
        out.push(`<p style="margin:2px 0;font-size:13px;line-height:1.6;">· ${text}</p>`);
      }
      continue;
    }

    // Ordered list - detect indent level
    if (/^\s*\d+\.\s/.test(line)) {
      const indent = line.match(/^(\s*)/)?.[1].length || 0;
      const numMatch = line.match(/^\s*(\d+)\.\s/);
      const num = numMatch ? numMatch[1] : '1';
      const text = inline(s.replace(/^\d+\.\s+/, ''));
      if (indent >= 2) {
        out.push(`<p style="margin:1px 0;font-size:13px;line-height:1.6;padding-left:18px;">${num}. ${text}</p>`);
      } else {
        out.push(`<p style="margin:2px 0;font-size:13px;line-height:1.6;">${num}. ${text}</p>`);
      }
      continue;
    }

    // Paragraph
    out.push(`<p style="margin:6px 0;font-size:13px;line-height:1.6;">${inline(s)}</p>`);
  }

  if (inTable) out.push('</table>');
  if (inCode) out.push('</pre>');

  return out.join('\n');
}

function esc(t: string) {
  return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function inline(t: string) {
  let s = esc(t);
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/__(.+?)__/g, '<strong>$1</strong>');
  s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
  s = s.replace(/~~(.+?)~~/g, '<del>$1</del>');
  s = s.replace(/`(.+?)`/g, '<code style="background:#f0f2f6;padding:1px 4px;border-radius:3px;font-family:monospace;font-size:12px;">$1</code>');
  s = s.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2">$1</a>');
  return s;
}


/**
 * Copy markdown text to clipboard as both plain text and styled HTML.
 * Word will use the HTML version, preserving tables, headings, bold, etc.
 */
export async function copyRichText(markdown: string): Promise<void> {
  const html = `<html><body style="font-family:'Malgun Gothic',-apple-system,sans-serif;font-size:13px;line-height:1.6;color:#333;">${mdToHtml(markdown)}</body></html>`;

  try {
    // Modern Clipboard API with ClipboardItem
    const htmlBlob = new Blob([html], { type: 'text/html' });
    const textBlob = new Blob([markdown], { type: 'text/plain' });
    await navigator.clipboard.write([
      new ClipboardItem({
        'text/html': htmlBlob,
        'text/plain': textBlob,
      }),
    ]);
  } catch {
    // Fallback: plain text only
    await navigator.clipboard.writeText(markdown);
  }
}


/**
 * Extract the first heading (or first non-empty line) from markdown.
 * Returns sanitized string suitable for filenames.
 */
/**
 * Download markdown as Word (.docx) via backend API.
 */
export async function downloadAsWord(markdown: string, filename?: string): Promise<void> {
  let title = filename || (extractTitle(markdown) + '.docx');
  // Strip any existing doc/docx extension, then add .docx
  title = title.replace(/\.(docx?|md)$/i, '');
  const fname = title + '.docx';
  const token = (await import('../stores/authStore')).useAuthStore.getState().token;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch('/api/markdown-to-docx', {
    method: 'POST',
    headers,
    body: JSON.stringify({ markdown, filename: fname }),
  });
  if (!res.ok) throw new Error(`Word 변환 실패: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fname;
  a.click();
  URL.revokeObjectURL(url);
}


/**
 * Download markdown as .md file (client-side, no backend needed).
 */
export function downloadAsMd(markdown: string, filename?: string): void {
  let title = filename || (extractTitle(markdown) + '.md');
  title = title.replace(/\.(docx?|md)$/i, '');
  const fname = title + '.md';
  const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fname;
  a.click();
  URL.revokeObjectURL(url);
}


export function extractTitle(markdown: string): string {
  if (!markdown) return 'report';
  for (const line of markdown.split('\n')) {
    const s = line.trim();
    if (s.startsWith('#')) {
      const title = s.replace(/^#+\s*/, '').trim();
      const clean = title.replace(/[\/*?:"<>|]/g, '').trim();
      if (clean) return clean.slice(0, 50);
    }
  }
  // Fallback: first non-empty line
  for (const line of markdown.split('\n')) {
    const s = line.trim();
    if (s) {
      const clean = s.replace(/[\/*?:"<>|]/g, '').trim();
      if (clean) return clean.slice(0, 50);
    }
  }
  return 'report';
}
