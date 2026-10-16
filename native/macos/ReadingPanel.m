// RE-PLAY-024. AppKit controls only: no extra webview, text or audio buffer.
#import <Cocoa/Cocoa.h>
#import <QuartzCore/QuartzCore.h>
#include <stdint.h>

// HIG spacing: 8pt inset and gap; equal 48pt native hit targets.
static const CGFloat controlSize = 48;
static const CGFloat controlInset = 8;
static const CGFloat controlGap = 8;
static const CGFloat panelWidth = 120;
static const CGFloat panelHeight = 64;

@interface RDXReadingPanel : NSPanel
@end
@implementation RDXReadingPanel
- (BOOL)canBecomeKeyWindow { return NO; }
- (BOOL)canBecomeMainWindow { return NO; }
@end

@interface RDXReadingButton : NSButton
@property BOOL pointerInside;
@property NSTrackingArea *hoverArea;
@end
@implementation RDXReadingButton
- (void)updateTrackingAreas {
    if (self.hoverArea) [self removeTrackingArea:self.hoverArea];
    [super updateTrackingAreas];
    self.hoverArea = [[NSTrackingArea alloc] initWithRect:NSZeroRect
        options:NSTrackingMouseEnteredAndExited | NSTrackingActiveAlways | NSTrackingInVisibleRect
        owner:self userInfo:nil];
    [self addTrackingArea:self.hoverArea];
}
- (void)mouseEntered:(NSEvent *)event { self.pointerInside = YES; self.needsDisplay = YES; }
- (void)mouseExited:(NSEvent *)event { self.pointerInside = NO; self.needsDisplay = YES; }
- (void)drawRect:(NSRect)dirty {
    // Native equivalent of the existing HIG wash/press (10% / 20% ink).
    // Leave room for the progress ring outside the hover disk.
    if (self.enabled && (self.pointerInside || self.highlighted)) {
        [[NSColor.labelColor colorWithAlphaComponent:self.highlighted ? 0.20 : 0.10] setFill];
        [[NSBezierPath bezierPathWithOvalInRect:NSInsetRect(self.bounds,4,4)] fill];
    }
    [super drawRect:dirty];
}
@end

@interface RDXReadingRing : NSView
@property double progress;
@end
@implementation RDXReadingRing
- (BOOL)isAccessibilityElement { return NO; }
- (NSView *)hitTest:(NSPoint)point { return nil; }
- (void)drawRect:(NSRect)dirty {
    NSRect circle = NSInsetRect(self.bounds, 2, 2);
    NSBezierPath *track = [NSBezierPath bezierPathWithOvalInRect:circle];
    track.lineWidth = 2;
    [NSColor.tertiaryLabelColor setStroke]; [track stroke];
    NSBezierPath *arc = [NSBezierPath bezierPath];
    arc.lineWidth = 2; arc.lineCapStyle = NSLineCapStyleRound;
    [arc appendBezierPathWithArcWithCenter:NSMakePoint(NSMidX(circle), NSMidY(circle))
        radius:circle.size.width / 2 startAngle:90 endAngle:90 - 360 * fmax(0, fmin(1, self.progress)) clockwise:YES];
    [NSColor.controlAccentColor setStroke]; [arc stroke];
}
@end

@interface RDXReadingBackground : NSVisualEffectView
@end
@implementation RDXReadingBackground
- (BOOL)mouseDownCanMoveWindow { return YES; }
@end

@interface RDXReadingController : NSObject <NSWindowDelegate>
@property (weak) NSWindow *mainWindow;
@property RDXReadingPanel *panel;
@property NSButton *toggle;
@property NSButton *stop;
@property RDXReadingRing *ring;
@property NSProgressIndicator *spinner;
@property int phase; // 0 stopped; 1 reading/preparing; 2 completed
@property BOOL paused;
@property BOOL external;
@property BOOL vi;
@property BOOL placing;
@property uint64_t current;
@property uint64_t total;
@property uint64_t generation;
@property uint64_t completedGeneration;
@property void (*action)(int);
- (void)apply;
@end
static RDXReadingController *controller;
static NSString * const enabledKey = @"readingController.enabled";

@implementation RDXReadingController
- (instancetype)init {
    self = [super init];
    if (self) {
        _completedGeneration = UINT64_MAX;
        NSNotificationCenter *center = NSNotificationCenter.defaultCenter;
        for (NSString *name in @[NSWindowDidMiniaturizeNotification, NSWindowDidDeminiaturizeNotification,
            NSWindowDidBecomeKeyNotification, NSWindowDidResignKeyNotification, NSWindowDidChangeOcclusionStateNotification,
            NSApplicationDidHideNotification, NSApplicationDidUnhideNotification,
            NSApplicationDidBecomeActiveNotification, NSApplicationDidChangeScreenParametersNotification]) {
            [center addObserver:self selector:@selector(environmentChanged:) name:name object:nil];
        }
        [NSWorkspace.sharedWorkspace.notificationCenter addObserver:self selector:@selector(environmentChanged:)
            name:NSWorkspaceAccessibilityDisplayOptionsDidChangeNotification object:nil];
    }
    return self;
}
- (void)environmentChanged:(NSNotification *)notification {
    // Ordering our own panel also sends window notifications.
    if (notification.object == self.panel) return;
    [self apply];
}
- (void)makePanel {
    if (self.panel) return;
    self.panel = [[RDXReadingPanel alloc] initWithContentRect:NSMakeRect(0,0,panelWidth,panelHeight)
        styleMask:NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
        backing:NSBackingStoreBuffered defer:NO];
    self.panel.releasedWhenClosed = NO;
    self.panel.hidesOnDeactivate = NO;
    self.panel.becomesKeyOnlyIfNeeded = YES;
    self.panel.level = NSFloatingWindowLevel;
    self.panel.collectionBehavior = NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary;
    self.panel.opaque = NO;
    self.panel.backgroundColor = NSColor.clearColor;
    self.panel.hasShadow = YES;
    self.panel.movableByWindowBackground = YES;
    self.panel.delegate = self;
    RDXReadingBackground *background = [[RDXReadingBackground alloc] initWithFrame:NSMakeRect(0,0,panelWidth,panelHeight)];
    background.material = NSVisualEffectMaterialHUDWindow;
    background.blendingMode = NSVisualEffectBlendingModeBehindWindow;
    background.state = NSVisualEffectStateActive;
    background.wantsLayer = YES;
    background.layer.cornerRadius = panelHeight / 2;
    background.layer.masksToBounds = YES;
    self.panel.contentView = background;
    NSRect toggleFrame = NSMakeRect(controlInset,controlInset,controlSize,controlSize);
    self.ring = [[RDXReadingRing alloc] initWithFrame:toggleFrame];
    [background addSubview:self.ring];
    self.spinner = [[NSProgressIndicator alloc] initWithFrame:toggleFrame];
    self.spinner.style = NSProgressIndicatorStyleSpinning;
    self.spinner.controlSize = NSControlSizeRegular;
    self.spinner.displayedWhenStopped = NO;
    [background addSubview:self.spinner];
    self.toggle = [[RDXReadingButton alloc] initWithFrame:toggleFrame];
    self.stop = [[RDXReadingButton alloc] initWithFrame:NSOffsetRect(toggleFrame,controlSize + controlGap,0)];
    for (NSButton *button in @[self.toggle,self.stop]) {
        button.bordered = NO;
        button.imagePosition = NSImageOnly;
        button.target = self;
        button.focusRingType = NSFocusRingTypeNone;
        button.contentTintColor = NSColor.labelColor;
        button.symbolConfiguration = [NSImageSymbolConfiguration configurationWithPointSize:16 weight:NSFontWeightSemibold];
        [background addSubview:button];
    }
    self.toggle.action = @selector(toggleReading:);
    self.stop.action = @selector(stopReading:);
    self.stop.image = [NSImage imageWithSystemSymbolName:@"stop.fill" accessibilityDescription:nil];
    [self placeOnScreen:[self cursorScreen]];
}
- (NSScreen *)cursorScreen {
    NSPoint cursor = NSEvent.mouseLocation;
    for (NSScreen *screen in NSScreen.screens) if (NSPointInRect(cursor,screen.frame)) return screen;
    return NSScreen.mainScreen;
}
- (NSString *)positionKey:(NSScreen *)screen {
    return [NSString stringWithFormat:@"readingController.position.%@",screen.deviceDescription[@"NSScreenNumber"]];
}
- (void)placeOnScreen:(NSScreen *)screen {
    if (!screen || !self.panel) return;
    NSRect room = NSInsetRect(screen.visibleFrame,12,12);
    double x = NSMidX(room) - panelWidth / 2, y = NSMinY(room) + 12;
    NSArray *saved = [NSUserDefaults.standardUserDefaults arrayForKey:[self positionKey:screen]];
    if (saved.count == 2 && [saved[0] isKindOfClass:NSNumber.class] && [saved[1] isKindOfClass:NSNumber.class]) {
        x = NSMinX(room) + [saved[0] doubleValue] * fmax(0,room.size.width-panelWidth);
        y = NSMinY(room) + [saved[1] doubleValue] * fmax(0,room.size.height-panelHeight);
    }
    x = fmax(NSMinX(room),fmin(x,NSMaxX(room)-panelWidth));
    y = fmax(NSMinY(room),fmin(y,NSMaxY(room)-panelHeight));
    self.placing = YES;
    [self.panel setFrameOrigin:NSMakePoint(x,y)];
    self.placing = NO;
}
- (void)windowDidMove:(NSNotification *)notification {
    if (self.placing || !self.panel.visible || notification.object != self.panel) return;
    NSScreen *screen = self.panel.screen;
    if (!screen) return;
    NSRect room = NSInsetRect(screen.visibleFrame,12,12), frame = self.panel.frame;
    double x = (frame.origin.x-room.origin.x)/fmax(1,room.size.width-panelWidth);
    double y = (frame.origin.y-room.origin.y)/fmax(1,room.size.height-panelHeight);
    [NSUserDefaults.standardUserDefaults setObject:@[@(fmax(0,fmin(1,x))),@(fmax(0,fmin(1,y)))] forKey:[self positionKey:screen]];
}
- (void)toggleReading:(id)sender { if (self.phase == 1 && (self.total > 0 || self.paused) && self.action) self.action(1); }
- (void)stopReading:(id)sender { if (self.phase == 1 && self.action) self.action(2); }
- (void)apply {
    if (![NSThread isMainThread]) return;
    BOOL enabled = ![NSUserDefaults.standardUserDefaults objectForKey:enabledKey] || [NSUserDefaults.standardUserDefaults boolForKey:enabledKey];
    BOOL outside = self.external || NSApp.hidden || self.mainWindow.miniaturized || !self.mainWindow.visible;
    BOOL visible = enabled && outside && self.phase != 0;
    if (!visible) { [self.spinner stopAnimation:nil]; [self.panel orderOut:nil]; return; }
    [self makePanel];
    if (!self.panel.screen) [self placeOnScreen:[self cursorScreen]];
    BOOL warming = self.phase == 1 && self.total == 0;
    BOOL preparing = warming && !self.paused;
    BOOL spinning = preparing && !NSWorkspace.sharedWorkspace.accessibilityDisplayShouldReduceMotion;
    self.ring.hidden = spinning;
    self.spinner.hidden = !spinning;
    if (spinning) [self.spinner startAnimation:nil]; else [self.spinner stopAnimation:nil];
    self.ring.progress = preparing ? 0.25 : self.phase == 2 ? 1 : (double)self.current / fmax(1,(double)self.total);
    self.ring.needsDisplay = YES;
    NSString *symbol = self.phase == 2 ? @"checkmark" : self.paused ? @"play.fill" : @"pause.fill";
    self.toggle.image = preparing ? nil : [NSImage imageWithSystemSymbolName:symbol accessibilityDescription:nil];
    self.toggle.enabled = self.phase == 1 && (self.total > 0 || self.paused);
    self.stop.enabled = self.phase == 1;
    NSString *toggle = self.phase == 2 ? (self.vi ? @"Đã đọc xong" : @"Finished reading") : self.paused ? (self.vi ? @"Tiếp tục" : @"Resume") : (self.vi ? @"Tạm dừng" : @"Pause");
    NSString *stop = self.vi ? @"Dừng" : @"Stop";
    NSString *status = warming ? (self.vi ? @"Đang chuẩn bị…" : @"Preparing…") : [NSString stringWithFormat:self.vi ? @"câu %llu/%llu" : @"sentence %llu/%llu",(unsigned long long)self.current,(unsigned long long)self.total];
    [self.toggle setAccessibilityLabel:toggle]; [self.toggle setAccessibilityValue:status];
    [self.stop setAccessibilityLabel:stop];
    self.toggle.toolTip = [NSString stringWithFormat:@"%@ · %@",toggle,status];
    self.stop.toolTip = stop;
    self.panel.title = self.vi ? @"Điều khiển đọc ReadEase" : @"ReadEase reading controls";
    if (!self.panel.visible) [self.panel orderFrontRegardless]; // Never activate NSApp or make key.
}
@end

void RDXReadingPanelInstall(void *mainWindow, void (*action)(int)) {
    if (![NSThread isMainThread] || controller) return;
    controller = [RDXReadingController new];
    controller.mainWindow = (__bridge NSWindow *)mainWindow;
    controller.action = action;
}
void RDXReadingPanelUpdate(int phase, int paused, uint64_t current, uint64_t total, int external, int vi, uint64_t generation) {
    if (![NSThread isMainThread] || !controller) return;
    int previous = controller.phase;
    if (phase == 2 && (controller.completedGeneration == generation || !controller.panel.visible)) phase = 0;
    controller.phase = phase; controller.paused = paused; controller.current = current;
    controller.total = total; controller.external = external; controller.vi = vi;
    controller.generation = generation;
    if (phase == 1 && previous != 1 && controller.panel) {
        [controller placeOnScreen:[controller cursorScreen]];
    }
    [controller apply];
    if (phase == 2 && previous != 2) {
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW,3*NSEC_PER_SEC),dispatch_get_main_queue(),^{
            if (controller.phase == 2 && controller.generation == generation) {
                controller.completedGeneration = generation; controller.phase = 0; [controller apply];
            }
        });
    }
}
int RDXReadingPanelEnabled(void) {
    return ![NSUserDefaults.standardUserDefaults objectForKey:enabledKey] || [NSUserDefaults.standardUserDefaults boolForKey:enabledKey];
}
void RDXReadingPanelSetEnabled(int enabled) {
    [NSUserDefaults.standardUserDefaults setBool:enabled != 0 forKey:enabledKey];
    [controller apply];
}
