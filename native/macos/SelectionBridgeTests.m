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

        RDXRetryPasteboard *retryPasteboard = [[RDXRetryPasteboard alloc] init];
        retryPasteboard.pasteboardItems = @[];
        RDXAssert(
            RDXRestorePasteboard((NSPasteboard *)retryPasteboard, snapshot),
            @"restore retry must rebuild pasteboard items"
        );
        RDXAssert(retryPasteboard.writeAttempts == 2, @"restore retried exactly once");
        RDXAssert(retryPasteboard.sawFreshRetryItem, @"retry used a fresh pasteboard item");
    }
    puts("NATIVE_SELECTION_BRIDGE_TEST PASS supported_source=1 frame=1 restore=1 retry_fresh_items=1");
    return 0;
}
