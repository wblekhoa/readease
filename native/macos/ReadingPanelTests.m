// RE-PLAY-024: exercise production AppKit views without showing a test window.
#import "ReadingPanel.m"
#import <objc/runtime.h>

#define CHECK(condition, message) do { if (!(condition)) { fprintf(stderr, "FAIL: %s\n", message); return 1; } } while (0)
static void keepHidden(id self, SEL command) {}
static int lastAction;
static void recordAction(int action) { lastAction = action; }

int main(void) { @autoreleasepool {
    [NSApplication sharedApplication];
    [NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited];
    [NSUserDefaults.standardUserDefaults setVolatileDomain:@{enabledKey: @YES} forName:NSArgumentDomain];
    // Only suppress presentation. Rendering, state updates and controls are real.
    class_addMethod(RDXReadingPanel.class, @selector(orderFrontRegardless), (IMP)keepHidden, "v@:");
    RDXReadingPanelInstall(NULL, recordAction);
    [controller makePanel];
    CHECK(!controller.panel.hasShadow, "window shadow must not expose a rectangular footprint");
    CHECK(!controller.panel.opaque && controller.panel.backgroundColor.alphaComponent == 0,
        "window must preserve transparent corners");
    CHECK(![controller.panel.contentView isKindOfClass:NSVisualEffectView.class], "surface must not blur its backdrop");
    CHECK(!controller.panel.canBecomeKeyWindow && !controller.panel.canBecomeMainWindow,
        "controls must not take keyboard focus");

    NSRect a = controller.toggle.frame, b = controller.stop.frame;
    NSRect bounds = controller.panel.contentView.bounds;
    CHECK(a.size.width >= 40 && a.size.height >= 40 && NSEqualSizes(a.size, b.size), "equal usable hit targets");
    CHECK(NSMinX(a) == NSMinY(a) && bounds.size.width-NSMaxX(b) == NSMinY(a)
        && bounds.size.height-NSMaxY(a) == NSMinY(a), "outer insets must be equal on all sides");
    CHECK(NSContainsRect(bounds,a) && NSContainsRect(bounds,b) && NSMinX(b)-NSMaxX(a) == 8,
        "controls must fit with an eight point gap");

    NSUInteger renders = 0;
    for (NSString *appearance in @[NSAppearanceNameAqua, NSAppearanceNameDarkAqua]) {
        controller.panel.appearance = [NSAppearance appearanceNamed:appearance];
        for (NSUInteger state = 0; state < 6; state++) {
            // Reading, hover, pressed, paused, preparing, completed.
            controller.phase = state == 5 ? 2 : 1;
            controller.paused = state == 3;
            controller.current = 3;
            controller.total = state == 4 ? 0 : 12;
            controller.external = YES;
            [controller apply];
            ((RDXReadingButton *)controller.toggle).pointerInside = state == 1 || state == 2;
            controller.toggle.highlighted = state == 2;
            NSView *view = controller.panel.contentView;
            [view layoutSubtreeIfNeeded];
            for (NSUInteger scale = 1; scale <= 2; scale++) {
                NSBitmapImageRep *rep = [[NSBitmapImageRep alloc] initWithBitmapDataPlanes:NULL
                    pixelsWide:bounds.size.width*scale pixelsHigh:bounds.size.height*scale
                    bitsPerSample:8 samplesPerPixel:4 hasAlpha:YES isPlanar:NO
                    colorSpaceName:NSDeviceRGBColorSpace bytesPerRow:0 bitsPerPixel:0];
                rep.size = bounds.size;
                [controller.panel.effectiveAppearance performAsCurrentDrawingAppearance:^{
                    [view cacheDisplayInRect:bounds toBitmapImageRep:rep];
                }];
                for (NSNumber *x in @[@0, @(rep.pixelsWide-1)]) {
                    for (NSNumber *y in @[@0, @(rep.pixelsHigh-1)]) {
                        CHECK([rep colorAtX:x.integerValue y:y.integerValue].alphaComponent < 0.01,
                            "corner pixels must be transparent in every state and appearance");
                    }
                }
                CHECK([rep colorAtX:rep.pixelsWide/2 y:rep.pixelsHigh/2].alphaComponent >= 0.995,
                    "solid surface must not show a seam when crossing light and dark backdrops");
                renders++;
            }
            CHECK(!controller.panel.visible, "test must never show a window");
            if (state == 0) {
                // The hover should reach beyond the old 24pt disk, for both
                // controls, without requiring a larger window or hit target.
                for (RDXReadingButton *button in @[controller.toggle, controller.stop]) {
                    NSPoint sample = NSMakePoint(NSMidX(button.frame)+15, NSMidY(button.frame));
                    NSBitmapImageRep *normal = [view bitmapImageRepForCachingDisplayInRect:bounds];
                    [view cacheDisplayInRect:bounds toBitmapImageRep:normal];
                    button.pointerInside = YES;
                    button.needsDisplay = YES;
                    NSBitmapImageRep *hover = [view bitmapImageRepForCachingDisplayInRect:bounds];
                    [view cacheDisplayInRect:bounds toBitmapImageRep:hover];
                    NSInteger x = sample.x * normal.pixelsWide/bounds.size.width;
                    NSInteger y = sample.y * normal.pixelsHigh/bounds.size.height;
                    NSColor *before = [[normal colorAtX:x y:y] colorUsingColorSpace:NSColorSpace.genericRGBColorSpace];
                    NSColor *after = [[hover colorAtX:x y:y] colorUsingColorSpace:NSColorSpace.genericRGBColorSpace];
                    CHECK(fabs(before.redComponent-after.redComponent) > 0.02,
                        "hover must fill a generous disk around each symbol, not huddle in its centre");
                    button.pointerInside = NO;
                    button.needsDisplay = YES;
                }
            }
            lastAction = 0;
            [controller.toggle performClick:nil];
            CHECK(lastAction == (state == 4 || state == 5 ? 0 : 1), "toggle follows preparation and completion state");
            lastAction = 0;
            [controller.stop performClick:nil];
            CHECK(lastAction == (state == 5 ? 0 : 2), "stop remains available while preparing");
        }
    }
    [controller.spinner stopAnimation:nil];
    printf("NATIVE_READING_PANEL PASS: %lu renders, alpha, geometry, actions, non-activating policy; no window shown\n", renders);
} return 0; }
