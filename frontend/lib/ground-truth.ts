/** Ground truth = the species a recording is named after, matched against the
 *  NT species catalog. Recordings are named "<Species_Name>_<XCid>.mp3".
 *
 *  Matching is synonym-aware, mirroring birddash/taxonomy.py: normalisation
 *  collapses orthographic variants (hyphen/space/case), and a small, sourced
 *  synonym table resolves true cross-checklist synonyms so a correct detection
 *  under a synonymous name is not scored as a miss. This table MUST stay in
 *  sync with birddash/taxonomy.py (the server is the source of truth); keep it
 *  deliberately conservative — only genuine synonyms, never a misidentification.
 *  Source: IOC World Bird List "Bush Thick-knee" = BirdLife Australia
 *  "Bush Stone-curlew" (Burhinus grallarius). */

export function normalize(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]/g, "");
}

// Normalized synonym → normalized canonical. Mirror of SYNONYM_GROUPS in
// birddash/taxonomy.py.
const SYNONYM_TO_CANONICAL: Record<string, string> = {
  [normalize("Bush Thick-knee")]: normalize("Bush Stone-curlew"),
  [normalize("Bush Thicknee")]: normalize("Bush Stone-curlew"),
  [normalize("Southern Stone-curlew")]: normalize("Bush Stone-curlew"),
};

function canonicalKey(name: string): string {
  const n = normalize(name);
  return SYNONYM_TO_CANONICAL[n] ?? n;
}

export function groundTruthFor(filename: string, speciesNames: string[]): string | null {
  const f = normalize(filename);
  const matches = speciesNames
    .filter((n) => f.startsWith(normalize(n)))
    .sort((a, b) => normalize(b).length - normalize(a).length); // longest wins
  return matches[0] ?? null;
}

export function speciesMatches(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a || !b) return false;
  return canonicalKey(a) === canonicalKey(b);
}
