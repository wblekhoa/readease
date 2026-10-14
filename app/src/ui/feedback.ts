/**
 * "Báo lỗi hoặc góp ý…" (RE-HELP-001): the bug form on GitHub, opened with
 * the two answers a reader has to go looking for - which build, which macOS -
 * already filled in. Only what `feedback_facts` returns goes into the
 * address: never the document, the library or a setting. Without the facts
 * (the call failed, or the browser mock) the plain form opens; feedback must
 * never fail because the facts did.
 */
export const NEW_ISSUE_URL = "https://github.com/wblekhoa/readease/issues/new";

export interface FeedbackFacts {
  build: string;
  macos: string | null;
  arch: string;
}

const CHIP: Record<string, string> = { aarch64: "Apple silicon", x86_64: "Intel" };

export function feedbackUrl(facts: FeedbackFacts | null): string {
  if (!facts) return NEW_ISSUE_URL;
  const params = new URLSearchParams({ template: "bug.yml", version: facts.build });
  const chip = CHIP[facts.arch] ?? facts.arch;
  params.set("macos", facts.macos ? `macOS ${facts.macos} · ${chip}` : chip);
  // URLSearchParams writes "+" for a space and "%2B" for a "+", so a build
  // id like 0.1.21+5c39011 arrives intact.
  return `${NEW_ISSUE_URL}?${params.toString()}`;
}
