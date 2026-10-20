import assert from "node:assert/strict";
import { test } from "node:test";
import { UpdateFlow } from "../src/ui/updateFlow.ts";

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>(done => { resolve = done; });
  return { promise, resolve };
}
function fixture() {
  const held = deferred();
  const calls: string[] = [];
  let blocked = false;
  let failCheck = false;
  let failInstall = false;
  let failRestart = false;
  const update = {
    version: "0.1.24", date: null, body: null,
    async download(progress: (event: any) => void) {
      calls.push("download");
      progress({ event: "Started", data: { contentLength: 100 } });
      progress({ event: "Progress", data: { chunkLength: 40 } });
      await held.promise;
    },
    async install() { calls.push("install"); if (failInstall) throw new Error("disk full"); },
    async close() { calls.push("close"); },
  };
  const flow = new UpdateFlow({
    check: async () => { calls.push("check"); if (failCheck) throw new Error("offline"); return update; },
    arm: async value => { calls.push(`arm:${value}`); },
    relaunch: async () => { calls.push("relaunch"); if (failRestart) throw new Error("restart failed"); },
    canApply: () => !blocked,
  });
  return { flow, calls, held, block: () => { blocked = true; }, unblock: () => { blocked = false; },
    failCheck: () => { failCheck = true; }, recoverCheck: () => { failCheck = false; },
    failInstall: () => { failInstall = true; }, recoverInstall: () => { failInstall = false; },
    failRestart: () => { failRestart = true; }, recoverRestart: () => { failRestart = false; } };
}
// RE-UPDATE-001: downloading never applies an update or blocks other work.
test("background download coalesces repeated clicks and only prepares the archive", async () => {
  const f = fixture(); await f.flow.check("0.1.23");
  const a = f.flow.download(); const b = f.flow.download();
  assert.deepEqual(f.flow.snapshot().phase, { kind: "downloading", version: "0.1.24", percent: 40 });
  await f.flow.check("0.1.23");
  f.held.resolve(); await Promise.all([a, b]);
  assert.equal(f.flow.snapshot().phase.kind, "ready");
  assert.deepEqual(f.calls, ["check", "download"]);
});
test("export starting during preparation prevents applying until the user retries", async () => {
  const f = fixture(); await f.flow.check("0.1.23");
  const download = f.flow.download(); f.block(); f.held.resolve(); await download;
  await f.flow.installAndRestart();
  assert.equal(f.flow.snapshot().phase.kind, "ready");
  assert.ok(!f.calls.includes("install"));
  f.unblock(); await f.flow.installAndRestart();
  assert.deepEqual(f.calls.slice(-3), ["arm:false", "install", "relaunch"]);
});
test("install when quitting arms only after download and never installs while in use", async () => {
  const f = fixture(); await f.flow.check("0.1.23");
  const scheduled = f.flow.installOnQuit();
  assert.equal(f.flow.snapshot().onQuit, false);
  f.held.resolve(); await scheduled;
  assert.equal(f.flow.snapshot().onQuit, true);
  assert.ok(!f.calls.includes("install"));
  assert.equal(await f.flow.applyOnQuit(), true);
  assert.ok(f.calls.includes("install"));
  assert.ok(!f.calls.includes("relaunch"));
});
test("repeated apply clicks install and restart once", async () => {
  const f = fixture(); await f.flow.check("0.1.23"); f.held.resolve(); await f.flow.download();
  await Promise.all([f.flow.installAndRestart(), f.flow.installAndRestart()]);
  assert.equal(f.calls.filter(c => c === "install").length, 1);
  assert.equal(f.calls.filter(c => c === "relaunch").length, 1);
});
test("failed checks can be retried", async () => {
  const f = fixture(); f.failCheck(); await f.flow.check("0.1.23");
  assert.equal(f.flow.snapshot().phase.kind, "failed");
  f.recoverCheck(); await f.flow.check("0.1.23");
  assert.equal(f.flow.snapshot().phase.kind, "available");
});
test("failed install preserves the archive for a retry without downloading again", async () => {
  const f = fixture(); await f.flow.check("0.1.23"); f.held.resolve(); await f.flow.download();
  f.failInstall(); await f.flow.installAndRestart();
  assert.equal(f.flow.snapshot().phase.kind, "failed");
  assert.ok(!f.calls.includes("relaunch"));
  f.recoverInstall(); await f.flow.installAndRestart();
  assert.equal(f.calls.filter(c => c === "download").length, 1);
  assert.equal(f.calls.filter(c => c === "relaunch").length, 1);
});
test("relaunch failure is visible and retry does not reinstall", async () => {
  const f = fixture(); await f.flow.check("0.1.23"); f.held.resolve(); await f.flow.download();
  f.failRestart(); await f.flow.installAndRestart();
  assert.equal(f.flow.snapshot().phase.kind, "installed");
  assert.match(JSON.stringify(f.flow.snapshot()), /restart failed/);
  f.recoverRestart(); await f.flow.installAndRestart();
  assert.equal(f.calls.filter(c => c === "install").length, 1);
  assert.equal(f.calls.filter(c => c === "relaunch").length, 2);
});
test("quit installation respects the current export guard", async () => {
  const f = fixture(); await f.flow.check("0.1.23"); f.held.resolve(); await f.flow.installOnQuit();
  f.block(); assert.equal(await f.flow.applyOnQuit(), false);
  assert.ok(!f.calls.includes("install"));
});
test("failed quit install cancels the native timeout and keeps the app open", async () => {
  const f = fixture(); await f.flow.check("0.1.23"); f.held.resolve(); await f.flow.installOnQuit();
  f.failInstall(); assert.equal(await f.flow.applyOnQuit(), false);
  assert.equal(f.flow.snapshot().onQuit, false);
  assert.equal(f.calls.at(-1), "arm:false");
  assert.equal(f.flow.snapshot().phase.kind, "failed");
});
test("skipping a downloaded version disarms installation and forgets the archive", async () => {
  const f = fixture(); await f.flow.check("0.1.23"); f.held.resolve(); await f.flow.installOnQuit();
  assert.equal(await f.flow.skip(), "0.1.24");
  assert.equal(f.flow.snapshot().phase.kind, "idle");
  assert.equal(f.flow.snapshot().onQuit, false);
  assert.equal(await f.flow.applyOnQuit(), false);
});
test("skip during download cannot discard the archive being prepared", async () => {
  const f = fixture(); await f.flow.check("0.1.23"); const pending = f.flow.download();
  assert.equal(await f.flow.skip(), null);
  f.held.resolve(); await pending;
  assert.equal(f.flow.snapshot().phase.kind, "ready");
});
test("download errors retry on the same update without installing", async () => {
  let attempts = 0; let installed = false;
  const flow = new UpdateFlow({
    check: async () => ({ version: "next", close: async () => {},
      download: async () => { if (++attempts === 1) throw new Error("offline"); },
      install: async () => { installed = true; } }),
    arm: async () => {}, relaunch: async () => {}, canApply: () => true,
  });
  await flow.check("old"); assert.equal(await flow.download(), false);
  assert.equal(flow.snapshot().phase.kind, "failed");
  assert.equal(await flow.download(), true);
  assert.equal(flow.snapshot().phase.kind, "ready"); assert.equal(installed, false);
});
test("a second guard after native disarm catches an export beginning during the await", async () => {
  let allowed = true; let installs = 0;
  const flow = new UpdateFlow({
    check: async () => ({ version: "next", close: async () => {}, download: async () => {}, install: async () => { installs++; } }),
    arm: async () => { allowed = false; }, relaunch: async () => {}, canApply: () => allowed,
  });
  await flow.check("old"); await flow.download(); await flow.installAndRestart();
  assert.equal(installs, 0); assert.equal(flow.snapshot().phase.kind, "ready");
});
test("double-clicking relaunch retry starts one relaunch", async () => {
  const f = fixture(); await f.flow.check("old"); f.held.resolve(); await f.flow.download();
  f.failRestart(); await f.flow.installAndRestart(); f.recoverRestart();
  await Promise.all([f.flow.installAndRestart(), f.flow.installAndRestart()]);
  assert.equal(f.calls.filter(c => c === "relaunch").length, 2);
});
test("retrying a failed quit schedule clears the error and never restarts", async () => {
  const f = fixture(); await f.flow.check("old"); f.held.resolve(); await f.flow.installOnQuit();
  f.failInstall(); await f.flow.applyOnQuit(); f.recoverInstall(); await f.flow.installOnQuit();
  assert.equal(f.flow.snapshot().phase.kind, "ready");
  assert.equal(f.flow.snapshot().onQuit, true);
  assert.ok(!f.calls.includes("relaunch"));
});
