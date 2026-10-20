/** RE-UPDATE-001: prepare in the background; apply only at an explicit safe boundary. */
export type UpdatePhase =
  | { kind: "idle" } | { kind: "checking" } | { kind: "none"; version: string }
  | { kind: "available" | "ready"; version: string; date: string | null; notes: string | null }
  | { kind: "downloading"; version: string; percent: number | null }
  | { kind: "installing"; version: string }
  | { kind: "installed"; version: string; error?: string }
  | { kind: "failed"; message: string; recovery: "check" | "download" | "install" | "schedule" };
export type DownloadEvent = { event: "Started"; data: { contentLength?: number } }
  | { event: "Progress"; data: { chunkLength: number } } | { event: "Finished" };
interface Archive {
  version: string; date?: string | null; body?: string | null;
  download: (progress: (event: DownloadEvent) => void) => Promise<unknown>;
  install: () => Promise<void>;
  close: () => Promise<void>;
}
interface Host {
  check: () => Promise<Archive | null>;
  arm: (armed: boolean) => Promise<void>;
  relaunch: () => Promise<void>;
  canApply: () => boolean;
}
export class UpdateFlow {
  private host: Host;
  private value: { phase: UpdatePhase; onQuit: boolean } = { phase: { kind: "idle" }, onQuit: false };
  private listeners = new Set<() => void>();
  private archive: Archive | null = null;
  private downloaded = false;
  private checking = false;
  private downloading: Promise<boolean> | null = null;
  private applying = false;
  private scheduling = false;
  constructor(host: Host) { this.host = host; }
  snapshot = () => this.value;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private phase(phase: UpdatePhase) { this.value = { ...this.value, phase }; this.listeners.forEach(listener => listener()); }
  private scheduled(onQuit: boolean) { this.value = { ...this.value, onQuit }; this.listeners.forEach(listener => listener()); }
  private offer() {
    const update = this.archive!;
    this.phase({ kind: this.downloaded ? "ready" : "available", version: update.version, date: update.date ?? null, notes: update.body ?? null });
  }
  async check(version: string, skipped?: string | null) {
    if (this.archive || this.checking) return;
    this.checking = true; this.phase({ kind: "checking" });
    try {
      const update = await this.host.check();
      if (!update) { this.phase({ kind: "none", version }); return; }
      if (update.version === skipped) { await update.close(); this.phase({ kind: "idle" }); return; }
      this.archive = update; this.offer();
    } catch (error) { this.phase({ kind: "failed", message: describe(error), recovery: "check" }); }
    finally { this.checking = false; }
  }
  download(): Promise<boolean> {
    if (this.downloading) return this.downloading;
    if (!this.archive || this.applying) return Promise.resolve(false);
    if (this.downloaded) return Promise.resolve(true);
    this.downloading = this.fetchArchive().finally(() => { this.downloading = null; });
    return this.downloading;
  }
  private async fetchArchive() {
    const update = this.archive!;
    let total: number | undefined; let received = 0;
    this.phase({ kind: "downloading", version: update.version, percent: null });
    try {
      await update.download(event => {
        if (event.event === "Started") total = event.data.contentLength;
        if (event.event === "Progress") {
          received += event.data.chunkLength;
          const percent = total ? Math.min(100, Math.round(received / total * 100)) : null;
          const phase = this.value.phase;
          if (phase.kind !== "downloading" || phase.percent !== percent) this.phase({ kind: "downloading", version: update.version, percent });
        }
      });
      this.downloaded = true; this.offer(); return true;
    } catch (error) { this.phase({ kind: "failed", message: describe(error), recovery: "download" }); return false; }
  }
  async installOnQuit() {
    if (this.scheduling || this.applying) return;
    this.scheduling = true;
    try {
      if (!(await this.download())) return;
      await this.host.arm(true); this.offer(); this.scheduled(true);
    } catch (error) { this.phase({ kind: "failed", message: describe(error), recovery: "schedule" }); }
    finally { this.scheduling = false; }
  }
  async installAndRestart() {
    if (!this.archive || this.applying || this.scheduling || !this.host.canApply()) return;
    if (this.value.phase.kind === "installed") {
      this.applying = true;
      try { await this.restart(); } finally { this.applying = false; }
      return;
    }
    // The UI only offers this after preparing the archive. No delayed surprise restart.
    if (!this.downloaded || this.downloading) return;
    this.applying = true;
    try {
      this.phase({ kind: "installing", version: this.archive.version });
      await this.host.arm(false); this.scheduled(false);
      if (!this.host.canApply()) { this.offer(); return; }
      await this.archive.install();
      this.phase({ kind: "installed", version: this.archive.version });
      await this.restart();
    } catch (error) { this.phase({ kind: "failed", message: describe(error), recovery: "install" }); }
    finally { this.applying = false; }
  }
  private async restart() {
    if (!this.archive || !this.host.canApply()) return;
    try { await this.host.relaunch(); }
    catch (error) { this.phase({ kind: "installed", version: this.archive.version, error: describe(error) }); }
  }
  async applyOnQuit() {
    if (!this.archive || !this.downloaded || !this.value.onQuit || this.applying || !this.host.canApply()) return false;
    this.applying = true;
    try {
      this.phase({ kind: "installing", version: this.archive.version });
      await this.archive.install(); return true;
    } catch (error) {
      this.phase({ kind: "failed", message: describe(error), recovery: "schedule" });
      await this.host.arm(false); this.scheduled(false); return false;
    } finally { this.applying = false; }
  }
  async skip(): Promise<string | null> {
    if (this.checking || this.downloading || this.applying || this.scheduling || this.value.phase.kind === "installed") return null;
    const version = this.archive?.version ?? null;
    try { await this.host.arm(false); }
    catch (error) { this.phase({ kind: "failed", message: describe(error), recovery: "install" }); return null; }
    const archive = this.archive; this.archive = null; this.downloaded = false;
    this.scheduled(false); this.phase({ kind: "idle" });
    void archive?.close().catch(() => undefined); return version;
  }
}
// Updater transport errors are independent of engine RPC errors.
function describe(cause: unknown) { return cause instanceof Error ? cause.message : String(cause); }
