'use client';

interface MarkdownReportProps {
  markdown: string;
}

/**
 * Renders a Markdown review report with section-based layout.
 *
 * Instead of using a full Markdown parser (which would add a dependency),
 * this component uses CSS-based rendering for the well-known section
 * structure produced by the PR Review Agent prompt.
 *
 * The report follows this structure:
 *   ## 📋 PR Summary
 *   ## 🔧 Changed Modules
 *   ## ⚠️ Potential Risks
 *   ## 🐛 Bug Suggestions
 *   ## ⚡ Performance Suggestions
 *   ## 🔒 Security Suggestions
 */
export function MarkdownReport({ markdown }: MarkdownReportProps) {
  if (!markdown) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-8 text-center text-gray-500">
        审核报告为空
      </div>
    );
  }

  // Split the markdown into sections by ## headings
  const sections = splitIntoSections(markdown);

  return (
    <div className="space-y-6">
      {sections.map((section, index) => (
        <div
          key={index}
          className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
        >
          {section.emoji && (
            <div className="mb-4 text-2xl">{section.emoji}</div>
          )}
          {section.title && (
            <h2 className="mb-4 text-xl font-bold text-gray-900">
              {section.title}
            </h2>
          )}
          <div className="prose prose-sm prose-gray max-w-none">
            <FormattedBody body={section.body} />
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface Section {
  emoji: string;
  title: string;
  body: string;
}

function splitIntoSections(markdown: string): Section[] {
  // Known section headings with emoji prefixes
  const headingPattern = /^##\s+(.*)$/gm;
  const headings: { index: number; text: string }[] = [];
  let match: RegExpExecArray | null;

  while ((match = headingPattern.exec(markdown)) !== null) {
    headings.push({ index: match.index, text: match[1] });
  }

  if (headings.length === 0) {
    // No sections found — treat whole content as one body
    return [{ emoji: '', title: '', body: markdown }];
  }

  const sections: Section[] = [];
  for (let i = 0; i < headings.length; i++) {
    const start = headings[i].index;
    const end = i + 1 < headings.length ? headings[i + 1].index : markdown.length;
    const headingText = headings[i].text;
    const body = markdown.slice(
      markdown.indexOf('\n', start) + 1,
      end,
    ).trim();

    const { emoji, title } = parseHeading(headingText);

    sections.push({ emoji, title, body });
  }

  return sections;
}

function parseHeading(text: string): { emoji: string; title: string } {
  // Extract emoji prefix (if any) and title
  // Headings look like: "📋 PR Summary" or "🔧 Changed Modules"
  const emojiMatch = text.match(
    /^([\u{1F000}-\u{1FFFF}]|[\u{2600}-\u{27BF}]|[\u{2700}-\u{27BF}])\s*(.*)$/u,
  );
  if (emojiMatch) {
    return { emoji: emojiMatch[1], title: emojiMatch[2] };
  }
  return { emoji: '', title: text };
}

// ---------------------------------------------------------------------------
// Markdown body renderer (lightweight)
// ---------------------------------------------------------------------------

function FormattedBody({ body }: { body: string }) {
  const lines = body.split('\n');
  const elements: JSX.Element[] = [];
  let inCodeBlock = false;
  let codeLines: string[] = [];
  let key = 0;

  for (const line of lines) {
    // Code block fence
    if (line.trimStart().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre
            key={key++}
            className="mb-3 overflow-x-auto rounded-lg bg-gray-100 p-4 text-sm text-gray-800"
          >
            <code>{codeLines.join('\n')}</code>
          </pre>,
        );
        codeLines = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    // Empty line
    if (line.trim() === '') {
      elements.push(<div key={key++} className="h-2" />);
      continue;
    }

    // Bold (**text**)
    const boldLine = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Inline code (`code`)
    const codeLine = boldLine.replace(/`(.+?)`/g, '<code class="rounded bg-gray-100 px-1 text-sm text-red-600">$1</code>');

    // List item
    if (line.trimStart().match(/^[\d]+\.\s/)) {
      elements.push(
        <div
          key={key++}
          className="mb-1 text-sm text-gray-700"
          dangerouslySetInnerHTML={{ __html: codeLine }}
        />,
      );
      continue;
    }

    // Bullet point
    if (line.trimStart().startsWith('- ') || line.trimStart().startsWith('* ')) {
      elements.push(
        <div
          key={key++}
          className="mb-1 flex items-start gap-2 text-sm text-gray-700"
        >
          <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-gray-400" />
          <span dangerouslySetInnerHTML={{ __html: codeLine.trimStart().slice(2) }} />
        </div>,
      );
      continue;
    }

    // Regular paragraph
    elements.push(
      <p
        key={key++}
        className="mb-2 text-sm leading-relaxed text-gray-700"
        dangerouslySetInnerHTML={{ __html: codeLine }}
      />,
    );
  }

  // Unclosed code block
  if (inCodeBlock && codeLines.length > 0) {
    elements.push(
      <pre
        key={key++}
        className="mb-3 overflow-x-auto rounded-lg bg-gray-100 p-4 text-sm text-gray-800"
      >
        <code>{codeLines.join('\n')}</code>
      </pre>,
    );
  }

  return <>{elements}</>;
}
