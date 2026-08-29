#import <AppKit/AppKit.h>
#import <ApplicationServices/ApplicationServices.h>
#import <Carbon/Carbon.h>
#import <stdlib.h>
#import <string.h>
#import <unistd.h>

static NSString *const RDXBooksBundleIdentifier = @"com.apple.iBooksX";
static NSString *const RDXReadEaseBundleIdentifier = @"vn.dolenglish.vieneureader";
// Password managers mark their items with this so clipboard tools skip them.
static NSString *const RDXConcealedType = @"org.nspasteboard.ConcealedType";
static NSString *const RDXSnapshotTypeKey = @"type";
static NSString *const RDXSnapshotDataKey = @"data";

enum {
    RDXSelectionSuccess = 0,
    RDXSelectionPermissionRequired = 1,
    RDXSelectionNoSelection = 2,
    RDXSelectionUnsupportedSource = 3,
    RDXSelectionClipboardRestoreFailed = 4,
    RDXSelectionUnavailable = 5,
    RDXSelectionConcealedSource = 6,
};

BOOL RDXIsBooksBundleIdentifier(NSString *bundleIdentifier) {
    return [bundleIdentifier isEqualToString:RDXBooksBundleIdentifier];
}

// The shortcut reads a selection wherever the person made one, so this asks
// what must be refused rather than what is allowed: a process with no identity
// to send a copy to, and ReadEase itself, which has its own read button.
BOOL RDXCanReadSelectionFrom(NSString *bundleIdentifier) {
    if (bundleIdentifier.length == 0) {
        return NO;
    }
    return ![bundleIdentifier isEqualToString:RDXReadEaseBundleIdentifier];
}

BOOL RDXPasteboardIsConcealed(NSPasteboard *pasteboard) {
    for (NSPasteboardItem *item in pasteboard.pasteboardItems ?: @[]) {
        for (NSPasteboardType type in item.types) {
            if ([type isEqualToString:RDXConcealedType]) {
                return YES;
            }
        }
    }
    return NO;
}

// The only way text leaves a pasteboard in this file. Routing every reader
// through here means a caller cannot forget to ask whether the item was marked
// secret; it reports that separately from "there was simply no text".
NSString *RDXReadableStringFrom(NSPasteboard *pasteboard, BOOL *outConcealed) {
    BOOL concealed = RDXPasteboardIsConcealed(pasteboard);
    if (outConcealed != NULL) {
        *outConcealed = concealed;
    }
    if (concealed) {
        return nil;
    }
    return [pasteboard stringForType:NSPasteboardTypeString];
}

// Read-on-copy is deliberately narrower than the shortcut: it watches Apple
// Books and nothing else, so text copied in a banking page or a password
// manager never reaches ReadEase even when the switch is on.
int RDXCopyWatchDecision(NSString *bundleIdentifier) {
    return RDXIsBooksBundleIdentifier(bundleIdentifier)
        ? RDXSelectionSuccess
        : RDXSelectionUnsupportedSource;
}

NSArray *RDXCapturePasteboard(NSPasteboard *pasteboard) {
    NSMutableArray *snapshot = [NSMutableArray array];
    for (NSPasteboardItem *item in pasteboard.pasteboardItems ?: @[]) {
        NSMutableArray *entries = [NSMutableArray array];
        for (NSPasteboardType type in item.types) {
            NSData *data = [item dataForType:type];
            if (data == nil) {
                return nil;
            }
            [entries addObject:@{
                RDXSnapshotTypeKey: type,
                RDXSnapshotDataKey: data,
            }];
        }
        [snapshot addObject:entries];
    }
    return snapshot;
}

static NSDictionary *RDXSnapshotItemDictionary(NSArray *entries) {
    NSMutableDictionary *dictionary = [NSMutableDictionary dictionary];
    for (NSDictionary *entry in entries) {
        NSString *type = entry[RDXSnapshotTypeKey];
        NSData *data = entry[RDXSnapshotDataKey];
        if (type == nil || data == nil || dictionary[type] != nil) {
            return nil;
        }
        dictionary[type] = data;
    }
    return dictionary;
}

BOOL RDXSnapshotsEqual(NSArray *left, NSArray *right) {
    if (left == nil || right == nil || left.count != right.count) {
        return NO;
    }
    for (NSUInteger index = 0; index < left.count; index += 1) {
        NSDictionary *leftItem = RDXSnapshotItemDictionary(left[index]);
        NSDictionary *rightItem = RDXSnapshotItemDictionary(right[index]);
        if (leftItem == nil || rightItem == nil || ![leftItem isEqual:rightItem]) {
            return NO;
        }
    }
    return YES;
}

static NSArray<NSPasteboardItem *> *RDXMakePasteboardItems(NSArray *snapshot) {
    NSMutableArray<NSPasteboardItem *> *items = [NSMutableArray array];
    for (NSArray *entries in snapshot) {
        NSPasteboardItem *item = [[NSPasteboardItem alloc] init];
        for (NSDictionary *entry in entries) {
            NSString *type = entry[RDXSnapshotTypeKey];
            NSData *data = entry[RDXSnapshotDataKey];
            if (type == nil || data == nil || ![item setData:data forType:type]) {
                return nil;
            }
        }
        [items addObject:item];
    }
    return items;
}

BOOL RDXRestorePasteboard(NSPasteboard *pasteboard, NSArray *snapshot) {
    if (snapshot == nil) {
        return NO;
    }
    for (NSUInteger attempt = 0; attempt < 3; attempt += 1) {
        NSArray<NSPasteboardItem *> *items = RDXMakePasteboardItems(snapshot);
        if (items == nil) {
            return NO;
        }
        [pasteboard clearContents];
        BOOL wrote = items.count == 0 || [pasteboard writeObjects:items];
        if (wrote && RDXSnapshotsEqual(snapshot, RDXCapturePasteboard(pasteboard))) {
            return YES;
        }
    }
    return NO;
}

static BOOL RDXEnsureAccessibility(BOOL prompt) {
    NSDictionary *options = @{
        (__bridge NSString *)kAXTrustedCheckOptionPrompt: @(prompt),
    };
    return AXIsProcessTrustedWithOptions((__bridge CFDictionaryRef)options);
}

static void RDXPostCopy(pid_t processIdentifier) {
    CGEventSourceRef source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState);
    CGEventRef keyDown = CGEventCreateKeyboardEvent(source, kVK_ANSI_C, true);
    CGEventRef keyUp = CGEventCreateKeyboardEvent(source, kVK_ANSI_C, false);
    CGEventSetFlags(keyDown, kCGEventFlagMaskCommand);
    CGEventSetFlags(keyUp, kCGEventFlagMaskCommand);
    CGEventPostToPid(processIdentifier, keyDown);
    CGEventPostToPid(processIdentifier, keyUp);
    CFRelease(keyDown);
    CFRelease(keyUp);
    if (source != NULL) {
        CFRelease(source);
    }
}

static BOOL RDXWaitForPasteboardChange(NSPasteboard *pasteboard, NSInteger initialCount) {
    for (NSUInteger attempt = 0; attempt < 200; attempt += 1) {
        if (pasteboard.changeCount != initialCount) {
            return YES;
        }
        usleep(5 * 1000);
    }
    return NO;
}

__attribute__((visibility("default")))
int RDXSelectionIsAccessibilityTrusted(int prompt) {
    @autoreleasepool {
        return RDXEnsureAccessibility(prompt != 0) ? 1 : 0;
    }
}

__attribute__((visibility("default")))
int RDXSelectionAcquire(char **outputBytes, size_t *outputLength) {
    if (outputBytes == NULL || outputLength == NULL) {
        return RDXSelectionUnavailable;
    }
    *outputBytes = NULL;
    *outputLength = 0;
    @autoreleasepool {
        NSRunningApplication *sourceApplication = NSWorkspace.sharedWorkspace.frontmostApplication;
        if (!RDXCanReadSelectionFrom(sourceApplication.bundleIdentifier)) {
            return RDXSelectionUnsupportedSource;
        }
        if (!RDXEnsureAccessibility(YES)) {
            return RDXSelectionPermissionRequired;
        }

        NSPasteboard *pasteboard = NSPasteboard.generalPasteboard;
        NSArray *snapshot = RDXCapturePasteboard(pasteboard);
        if (snapshot == nil) {
            return RDXSelectionClipboardRestoreFailed;
        }
        NSInteger initialChangeCount = pasteboard.changeCount;
        RDXPostCopy(sourceApplication.processIdentifier);
        if (!RDXWaitForPasteboardChange(pasteboard, initialChangeCount)) {
            return RDXSelectionNoSelection;
        }

        BOOL concealed = NO;
        NSString *selectedText = RDXReadableStringFrom(pasteboard, &concealed);
        if (!RDXRestorePasteboard(pasteboard, snapshot)) {
            return RDXSelectionClipboardRestoreFailed;
        }
        if (concealed) {
            return RDXSelectionConcealedSource;
        }
        NSString *trimmed = [selectedText stringByTrimmingCharactersInSet:
            NSCharacterSet.whitespaceAndNewlineCharacterSet];
        if (trimmed.length == 0) {
            return RDXSelectionNoSelection;
        }
        NSData *payload = [selectedText dataUsingEncoding:NSUTF8StringEncoding];
        if (payload == nil || payload.length == 0 || payload.length > 500000) {
            return RDXSelectionUnavailable;
        }
        char *copy = malloc(payload.length);
        if (copy == NULL) {
            return RDXSelectionUnavailable;
        }
        memcpy(copy, payload.bytes, payload.length);
        *outputBytes = copy;
        *outputLength = payload.length;
        return RDXSelectionSuccess;
    }
}

__attribute__((visibility("default")))
int RDXClipboardBooksIsFrontmost(void) {
    @autoreleasepool {
        NSRunningApplication *front = NSWorkspace.sharedWorkspace.frontmostApplication;
        return RDXIsBooksBundleIdentifier(front.bundleIdentifier) ? 1 : 0;
    }
}

__attribute__((visibility("default")))
long long RDXClipboardChangeCount(void) {
    @autoreleasepool {
        return (long long)NSPasteboard.generalPasteboard.changeCount;
    }
}

__attribute__((visibility("default")))
int RDXClipboardCopyBooksText(char **outputBytes, size_t *outputLength) {
    if (outputBytes == NULL || outputLength == NULL) {
        return RDXSelectionUnavailable;
    }
    *outputBytes = NULL;
    *outputLength = 0;
    @autoreleasepool {
        // Read-on-copy never leaves Apple Books. Text copied anywhere else --
        // a password manager, a banking page -- must not reach ReadEase at
        // all, so the gate lives here rather than in the caller.
        NSRunningApplication *source = NSWorkspace.sharedWorkspace.frontmostApplication;
        int decision = RDXCopyWatchDecision(source.bundleIdentifier);
        if (decision != RDXSelectionSuccess) {
            return decision;
        }
        // A password manager asks every clipboard tool to ignore its items;
        // honour that regardless of which app happens to be in front.
        BOOL concealed = NO;
        NSString *copiedText = RDXReadableStringFrom(
            NSPasteboard.generalPasteboard, &concealed);
        if (concealed) {
            return RDXSelectionUnsupportedSource;
        }
        NSString *trimmed = [copiedText stringByTrimmingCharactersInSet:
            NSCharacterSet.whitespaceAndNewlineCharacterSet];
        if (trimmed.length == 0) {
            return RDXSelectionNoSelection;
        }
        NSData *payload = [copiedText dataUsingEncoding:NSUTF8StringEncoding];
        if (payload == nil || payload.length == 0 || payload.length > 500000) {
            return RDXSelectionUnavailable;
        }
        char *copy = malloc(payload.length);
        if (copy == NULL) {
            return RDXSelectionUnavailable;
        }
        memcpy(copy, payload.bytes, payload.length);
        *outputBytes = copy;
        *outputLength = payload.length;
        return RDXSelectionSuccess;
    }
}

__attribute__((visibility("default")))
void RDXSelectionFree(void *bytes) {
    free(bytes);
}
