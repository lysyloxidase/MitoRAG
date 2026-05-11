import type { ReactNode } from "react";

const PMID_RE = /\[PMID:(\d+)\]/g;
const DOI_RE = /\[doi:([^\]]+)\]/gi;

export function renderCitations(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const pattern = /\[PMID:\d+\]|\[doi:[^\]]+\]/gi;
  let cursor = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      parts.push(text.slice(cursor, match.index));
    }
    const marker = match[0];
    parts.push(<CitationLink key={`${marker}-${match.index}`} marker={marker} />);
    cursor = match.index + marker.length;
  }

  if (cursor < text.length) {
    parts.push(text.slice(cursor));
  }
  return parts;
}

export function CitationLink({ marker }: { marker: string }) {
  const pmid = PMID_RE.exec(marker);
  PMID_RE.lastIndex = 0;
  const doi = DOI_RE.exec(marker);
  DOI_RE.lastIndex = 0;

  const href = pmid
    ? `https://pubmed.ncbi.nlm.nih.gov/${pmid[1]}/`
    : `https://doi.org/${encodeURIComponent(doi?.[1] ?? "")}`;

  return (
    <a className="citation-link" href={href} rel="noreferrer" target="_blank">
      {marker}
    </a>
  );
}
