/**
 * Obsidian-flavored markdown pre-processor.
 * Converts [[wikilinks]], #tags, > [!callouts] to HTML
 * that rehype-raw can render in react-markdown.
 */

// Protect code blocks from processing
function protectCode(content: string): { cleaned: string; restore: (s: string) => string } {
  const blocks: string[] = [];
  const cleaned = content.replace(/(`{1,3})[\s\S]*?\1/g, (match) => {
    blocks.push(match);
    return `\x00CODE${blocks.length - 1}\x00`;
  });
  const restore = (s: string) =>
    s.replace(/\x00CODE(\d+)\x00/g, (_, i) => blocks[Number(i)] || '');
  return { cleaned, restore };
}

/**
 * Pre-process Obsidian markdown to HTML-augmented markdown.
 * @param content raw markdown with [[links]], #tags, callouts
 * @param existingSlugs set of known note slugs (for broken link detection)
 */
export function preprocessNoteMarkdown(
  content: string,
  existingSlugs: Set<string> = new Set(),
): string {
  const { cleaned, restore } = protectCode(content);
  let result = cleaned;

  // 1. Wikilinks: [[slug|alias]], [[slug#heading|alias]], [[slug#heading]], [[slug]]
  result = result.replace(
    /\[\[([^\]]+)\]\]/g,
    (_, inner: string) => {
      let slug = inner.trim();
      let alias = '';
      let heading = '';
      if (slug.includes('|')) {
        [slug, alias] = slug.split('|', 2);
        slug = slug.trim();
        alias = alias.trim();
      }
      if (slug.includes('#')) {
        [slug, heading] = slug.split('#', 2);
        slug = slug.trim();
        heading = heading.trim();
      }
      const display = alias || (heading ? `${slug} › ${heading}` : slug);
      const slugLower = slug.toLowerCase().replace(/\s+/g, '-').replace(/[\\/*?:"<>|]/g, '');
      const broken = existingSlugs.size > 0 && !existingSlugs.has(slugLower) ? ' broken' : '';
      const headingAttr = heading ? ` data-heading="${heading}"` : '';
      return `<a data-wikilink="${slugLower}"${headingAttr} class="wikilink${broken}">${display}</a>`;
    },
  );

  // 2. Tags: #tag, #parent/child (not inside HTML tags or at start of heading)
  result = result.replace(
    /(?:^|\s)#([\w가-힣/\-]+)/gu,
    (match, tag: string) => {
      const leading = match[0] === '#' ? '' : match[0];
      return `${leading}<span data-tag="${tag}" class="note-tag">#${tag}</span>`;
    },
  );

  // 3. Callouts: > [!NOTE], > [!WARNING], etc.
  const calloutIcons: Record<string, string> = {
    NOTE: 'ℹ️', TIP: '💡', WARNING: '⚠️', IMPORTANT: '❗', CAUTION: '🔴',
    EXAMPLE: '📋', QUOTE: '💬', BUG: '🐛', SUCCESS: '✅', QUESTION: '❓',
  };
  result = result.replace(
    /^(>\s*)\[!([\w]+)\]\s*(.*)/gm,
    (_, prefix: string, type: string, title: string) => {
      const upper = type.toUpperCase();
      const icon = calloutIcons[upper] || 'ℹ️';
      const displayTitle = title.trim() || upper;
      return `${prefix}<div class="callout callout-${upper.toLowerCase()}"><div class="callout-title">${icon} ${displayTitle}</div>\n${prefix}`;
    },
  );

  return restore(result);
}
