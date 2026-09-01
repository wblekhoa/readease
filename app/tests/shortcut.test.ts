/** The recorder's two pure halves: keyboard event -> accelerator string,
 * and accelerator -> what a Mac user reads. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { comboFromEvent, displayShortcut } from "../src/ui/useShortcut.ts";

function keyEvent(overrides: Partial<KeyboardEvent>): KeyboardEvent {
  return {
    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false,
    code: "", ...overrides,
  } as KeyboardEvent;
}

test("một phím trần không thành phím tắt (phải giữ modifier)", () => {
  assert.equal(comboFromEvent(keyEvent({ code: "KeyR" })), null);
  // Shift một mình cũng không đủ - gõ chữ hoa sẽ thành phím tắt mất.
  assert.equal(
    comboFromEvent(keyEvent({ code: "KeyR", shiftKey: true })),
    null,
  );
});

test("tổ hợp hợp lệ ra chuỗi đúng thứ tự control+alt+shift+super", () => {
  assert.equal(
    comboFromEvent(keyEvent({ code: "KeyR", altKey: true, metaKey: true })),
    "alt+super+r",
  );
  assert.equal(
    comboFromEvent(keyEvent({
      code: "Digit5", ctrlKey: true, shiftKey: true, metaKey: true,
    })),
    "control+shift+super+5",
  );
  assert.equal(
    comboFromEvent(keyEvent({ code: "F6", altKey: true })),
    "alt+F6",
  );
});

test("phím không phải chữ/số/F bị từ chối", () => {
  assert.equal(
    comboFromEvent(keyEvent({ code: "Space", metaKey: true })),
    null,
  );
  assert.equal(
    comboFromEvent(keyEvent({ code: "Escape", metaKey: true })),
    null,
  );
});

test("hiển thị kiểu Mac: Option + Command + R", () => {
  assert.equal(displayShortcut("alt+super+r"), "Option + Command + R");
  assert.equal(
    displayShortcut("control+shift+super+5"),
    "Control + Shift + Command + 5",
  );
});
