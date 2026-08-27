#define RDX_TESTING 1
#import "ReadEaseSelectionBridge.m"
#import "ReadEaseSelectionNative.m"

static void RDXAssert(BOOL condition, NSString *message) {
    if (!condition) {
        fprintf(stderr, "NATIVE_SELECTION_BRIDGE_TEST RED %s\n", message.UTF8String);
        exit(1);
    }
}

@interface RDXRetryPasteboard : NSObject
@property(nonatomic, strong) NSArray<NSPasteboardItem *> *pasteboardItems;
@property(nonatomic) NSInteger changeCount;
@property(nonatomic) NSUInteger writeAttempts;
@property(nonatomic, strong) NSPasteboardItem *firstAttemptItem;
@property(nonatomic) BOOL sawFreshRetryItem;
@end

@implementation RDXRetryPasteboard
- (void)clearContents {
    self.pasteboardItems = @[];
    self.changeCount += 1;
}

- (BOOL)writeObjects:(NSArray<NSPasteboardItem *> *)objects {
    self.writeAttempts += 1;
    NSPasteboardItem *item = objects.firstObject;
    if (self.writeAttempts == 1) {
        self.firstAttemptItem = item;
        return NO;
    }
    self.sawFreshRetryItem = item != self.firstAttemptItem;
    if (!self.sawFreshRetryItem) {
        return NO;
    }
    self.pasteboardItems = objects;
    return YES;
}
@end

int main(void) {
    @autoreleasepool {
        RDXAssert(RDXIsSupportedBundleIdentifier(@"com.apple.iBooksX"), @"Books must be supported");
        RDXAssert(!RDXIsSupportedBundleIdentifier(@"com.apple.TextEdit"), @"other apps must fail closed");
        RDXAssert(RDXParentMatches(42, 42), @"matching parent remains alive");
        RDXAssert(!RDXParentMatches(42, 1), @"orphaned helper exits");

        RDXHotKeyConfiguration defaults = RDXParseHotKeyArguments(0, NULL);
        RDXAssert(defaults.valid, @"no arguments keep a working shortcut");
        // ReadEase pins the same two numbers on the Python side, so both
        // layers describe one shortcut contract independently.
        RDXAssert(defaults.keyCode == 15, @"default key code is kVK_ANSI_R");
        RDXAssert(defaults.modifiers == 6400, @"default mask is control+option+command");

        const char *chosen[] = {"bridge", "38", "4352"};
        RDXHotKeyConfiguration parsed = RDXParseHotKeyArguments(3, chosen);
        RDXAssert(parsed.valid, @"a chosen shortcut parses");
        RDXAssert(parsed.keyCode == 38, @"chosen key code is used");
        RDXAssert(parsed.modifiers == 4352, @"chosen modifier mask is used");

        const char *firstKey[] = {"bridge", "0", "4352"};
        RDXHotKeyConfiguration firstKeyConfiguration = RDXParseHotKeyArguments(3, firstKey);
        RDXAssert(firstKeyConfiguration.valid, @"kVK_ANSI_A is a key, not a parse failure");
        RDXAssert(firstKeyConfiguration.keyCode == 0, @"zero survives parsing");

        const char *garbage[] = {"bridge", "38x", "4352"};
        RDXAssert(!RDXParseHotKeyArguments(3, garbage).valid, @"trailing junk fails closed");

        const char *halfSpecified[] = {"bridge", "38"};
        RDXAssert(!RDXParseHotKeyArguments(2, halfSpecified).valid, @"a missing mask fails closed");

        const char *shiftOnly[] = {"bridge", "38", "512"};
        RDXAssert(!RDXParseHotKeyArguments(3, shiftOnly).valid, @"shift alone cannot own a key globally");

        const char *bareKey[] = {"bridge", "38", "0"};
        RDXAssert(!RDXParseHotKeyArguments(3, bareKey).valid, @"an unmodified key cannot be global");

        const char *unknownModifier[] = {"bridge", "38", "16640"};
        RDXAssert(!RDXParseHotKeyArguments(3, unknownModifier).valid, @"unknown modifier bits fail closed");

        const char *outOfRange[] = {"bridge", "999", "4352"};
        RDXAssert(!RDXParseHotKeyArguments(3, outOfRange).valid, @"key codes stay in range");

        NSData *payload = [@"Đọc đúng" dataUsingEncoding:NSUTF8StringEncoding];
        NSData *frame = RDXFrameData('T', payload);
        RDXAssert(frame.length == payload.length + 5, @"frame length");
        const unsigned char *bytes = frame.bytes;
        RDXAssert(bytes[0] == 'T', @"frame kind");
        uint32_t payloadLength = 0;
        memcpy(&payloadLength, bytes + 1, sizeof(payloadLength));
        RDXAssert(ntohl(payloadLength) == payload.length, @"frame payload length");

        NSPasteboard *pasteboard = [NSPasteboard pasteboardWithUniqueName];
        NSPasteboardItem *original = [[NSPasteboardItem alloc] init];
        [original setString:@"clipboard cũ" forType:NSPasteboardTypeString];
        [original setData:[NSData dataWithBytes:"\x01\x02\x03" length:3]
                   forType:@"vn.dolenglish.readease.fixture"];
        [pasteboard clearContents];
        RDXAssert([pasteboard writeObjects:@[original]], @"seed pasteboard");
        NSArray *snapshot = RDXCapturePasteboard(pasteboard);

        [pasteboard clearContents];
        [pasteboard setString:@"selection tạm" forType:NSPasteboardTypeString];
        RDXAssert(RDXRestorePasteboard(pasteboard, snapshot), @"restore pasteboard");
        NSArray *restored = RDXCapturePasteboard(pasteboard);
        RDXAssert(RDXSnapshotsEqual(snapshot, restored), @"type-and-byte equality");

        RDXAssert(!RDXPasteboardIsConcealed(pasteboard), @"an ordinary clipboard is not concealed");
        NSPasteboard *concealedPasteboard = [NSPasteboard pasteboardWithUniqueName];
        NSPasteboardItem *secret = [[NSPasteboardItem alloc] init];
        [secret setString:@"mật khẩu" forType:NSPasteboardTypeString];
        [secret setData:[NSData data] forType:@"org.nspasteboard.ConcealedType"];
        [concealedPasteboard clearContents];
        RDXAssert([concealedPasteboard writeObjects:@[secret]], @"seed concealed pasteboard");
        RDXAssert(RDXPasteboardIsConcealed(concealedPasteboard), @"a password manager item is skipped");

        RDXRetryPasteboard *retryPasteboard = [[RDXRetryPasteboard alloc] init];
        retryPasteboard.pasteboardItems = @[];
        RDXAssert(
            RDXRestorePasteboard((NSPasteboard *)retryPasteboard, snapshot),
            @"restore retry must rebuild pasteboard items"
        );
        RDXAssert(retryPasteboard.writeAttempts == 2, @"restore retried exactly once");
        RDXAssert(retryPasteboard.sawFreshRetryItem, @"retry used a fresh pasteboard item");
    }
    puts("NATIVE_SELECTION_BRIDGE_TEST PASS supported_source=1 frame=1 restore=1 retry_fresh_items=1 hotkey_arguments=1 concealed=1");
    return 0;
}
