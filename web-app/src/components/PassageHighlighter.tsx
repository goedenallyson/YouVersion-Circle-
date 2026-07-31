import { useMemo, useRef, useState } from "react";

interface Props {
  text: string;
  onHighlight: (phrase: string | null) => void;
}

// Highlight directly on the passage. Tap one word, or drag across words to
// select a phrase. Selection snaps to whole words and is emitted as structured
// text (not coordinates). Keyboard + ARIA accessible; highlighted words carry a
// non-color indicator (underline + weight) in addition to background color.
export function PassageHighlighter({ text, onHighlight }: Props) {
  const tokens = useMemo(() => text.replace(/[“”]/g, "").split(/(\s+)/), [text]);
  const [range, setRange] = useState<[number, number] | null>(null);
  const dragStart = useRef<number | null>(null);

  const emit = (lo: number, hi: number) => {
    setRange([lo, hi]);
    const picked = tokens
      .map((t, i) => (i >= lo && i <= hi && t.trim() ? t : ""))
      .join(" ")
      .replace(/\s+/g, " ")
      .replace(/[.,;:""]/g, "")
      .trim();
    onHighlight(picked || null);
  };

  const inRange = (i: number) => range != null && i >= range[0] && i <= range[1];

  return (
    <div
      className="verse"
      role="group"
      aria-label="Daily passage. Highlight a word or phrase that stands out."
      onMouseLeave={() => (dragStart.current = null)}
    >
      {"\u201c"}
      {tokens.map((tok, i) => {
        if (!tok.trim()) return <span key={i}>{tok}</span>;
        const selected = inRange(i);
        return (
          <span
            key={i}
            className={"word-tok" + (selected ? " hl" : "")}
            role="button"
            tabIndex={0}
            aria-pressed={selected}
            aria-label={`highlight word ${tok}`}
            onMouseDown={(e) => {
              e.preventDefault();
              dragStart.current = i;
              emit(i, i);
            }}
            onMouseEnter={() => {
              if (dragStart.current != null) {
                emit(Math.min(dragStart.current, i), Math.max(dragStart.current, i));
              }
            }}
            onMouseUp={() => (dragStart.current = null)}
            onClick={() => emit(i, i)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                // Shift+Enter extends selection to this word from the anchor.
                if (e.shiftKey && range) emit(Math.min(range[0], i), Math.max(range[1], i));
                else emit(i, i);
              }
            }}
          >
            {tok}
          </span>
        );
      })}
      {"\u201d"}
    </div>
  );
}

export const _testHelpers = { };
