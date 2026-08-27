#import <Foundation/Foundation.h>
#import <Carbon/Carbon.h>
#import <arpa/inet.h>
#import <errno.h>
#import <signal.h>
#import <stdlib.h>
#import <unistd.h>

enum {
    RDXDefaultHotKeyCode = kVK_ANSI_R,
    RDXDefaultHotKeyModifiers = controlKey | optionKey | cmdKey,
    RDXSupportedHotKeyModifiers = controlKey | optionKey | shiftKey | cmdKey,
    // Shift alone still leaves an ordinary typing key, and a global hotkey on
    // one would swallow that key in every app.
    RDXRequiredHotKeyModifiers = controlKey | optionKey | cmdKey,
    RDXMaximumHotKeyCode = 127,
};

typedef struct {
    UInt32 keyCode;
    UInt32 modifiers;
    BOOL valid;
} RDXHotKeyConfiguration;

NSData *RDXFrameData(char kind, NSData *payload) {
    NSData *safePayload = payload ?: [NSData data];
    if (safePayload.length > UINT32_MAX) {
        return nil;
    }
    uint32_t networkLength = htonl((uint32_t)safePayload.length);
    NSMutableData *frame = [NSMutableData dataWithCapacity:safePayload.length + 5];
    [frame appendBytes:&kind length:1];
    [frame appendBytes:&networkLength length:sizeof(networkLength)];
    [frame appendData:safePayload];
    return frame;
}

BOOL RDXParentMatches(pid_t expectedParent, pid_t currentParent) {
    return expectedParent > 1 && currentParent == expectedParent;
}

static BOOL RDXParseHotKeyNumber(const char *argument, UInt32 *outValue) {
    if (argument == NULL || argument[0] == '\0') {
        return NO;
    }
    char *end = NULL;
    errno = 0;
    long parsed = strtol(argument, &end, 10);
    // kVK_ANSI_A is zero, so only the end pointer can report a bad argument.
    if (errno != 0 || end == NULL || *end != '\0' || parsed < 0) {
        return NO;
    }
    if (parsed > UINT16_MAX) {
        return NO;
    }
    *outValue = (UInt32)parsed;
    return YES;
}

RDXHotKeyConfiguration RDXParseHotKeyArguments(int argc, const char *const *argv) {
    RDXHotKeyConfiguration configuration = {
        .keyCode = (UInt32)RDXDefaultHotKeyCode,
        .modifiers = (UInt32)RDXDefaultHotKeyModifiers,
        .valid = YES,
    };
    if (argc <= 1 || argv == NULL) {
        return configuration;
    }
    if (argc != 3) {
        configuration.valid = NO;
        return configuration;
    }
    UInt32 keyCode = 0;
    UInt32 modifiers = 0;
    if (!RDXParseHotKeyNumber(argv[1], &keyCode) ||
        !RDXParseHotKeyNumber(argv[2], &modifiers)) {
        configuration.valid = NO;
        return configuration;
    }
    BOOL registrable =
        keyCode <= (UInt32)RDXMaximumHotKeyCode &&
        (modifiers & ~(UInt32)RDXSupportedHotKeyModifiers) == 0 &&
        (modifiers & (UInt32)RDXRequiredHotKeyModifiers) != 0;
    if (!registrable) {
        configuration.valid = NO;
        return configuration;
    }
    configuration.keyCode = keyCode;
    configuration.modifiers = modifiers;
    return configuration;
}

static void RDXWriteAll(const void *bytes, size_t length) {
    const unsigned char *cursor = bytes;
    while (length > 0) {
        ssize_t written = write(STDOUT_FILENO, cursor, length);
        if (written <= 0) {
            return;
        }
        cursor += written;
        length -= (size_t)written;
    }
}

static void RDXSendFrame(char kind, NSData *payload) {
    NSData *frame = RDXFrameData(kind, payload);
    if (frame != nil) {
        RDXWriteAll(frame.bytes, frame.length);
    }
}

#ifndef RDX_TESTING

static OSStatus RDXHotKeyHandler(
    EventHandlerCallRef nextHandler,
    EventRef event,
    void *userData
) {
    (void)nextHandler;
    (void)event;
    (void)userData;
    RDXSendFrame('H', nil);
    return noErr;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        signal(SIGPIPE, SIG_IGN);
        pid_t parentProcessIdentifier = getppid();
        if (parentProcessIdentifier <= 1) {
            RDXSendFrame('E', nil);
            return 1;
        }
        RDXHotKeyConfiguration configuration = RDXParseHotKeyArguments(argc, argv);
        if (!configuration.valid) {
            RDXSendFrame('E', nil);
            return 1;
        }
        EventTypeSpec eventType = {
            .eventClass = kEventClassKeyboard,
            .eventKind = kEventHotKeyPressed,
        };
        OSStatus handlerStatus = InstallApplicationEventHandler(
            &RDXHotKeyHandler,
            1,
            &eventType,
            NULL,
            NULL
        );
        EventHotKeyID hotKeyID = {
            .signature = 'RDX1',
            .id = 1,
        };
        EventHotKeyRef hotKey = NULL;
        OSStatus hotKeyStatus = RegisterEventHotKey(
            configuration.keyCode,
            configuration.modifiers,
            hotKeyID,
            GetApplicationEventTarget(),
            0,
            &hotKey
        );
        if (handlerStatus != noErr) {
            RDXSendFrame('E', nil);
            return 1;
        }
        if (hotKeyStatus != noErr || hotKey == NULL) {
            // macOS refuses a combination it or another app already owns; say
            // so instead of looking broken.
            RDXSendFrame('K', nil);
            return 1;
        }
        RDXSendFrame('R', nil);
        while (RDXParentMatches(parentProcessIdentifier, getppid())) {
            EventRef event = NULL;
            OSStatus eventStatus = ReceiveNextEvent(
                0,
                NULL,
                0.5,
                true,
                &event
            );
            if (eventStatus == eventLoopTimedOutErr) {
                continue;
            }
            if (eventStatus != noErr || event == NULL) {
                break;
            }
            SendEventToEventTarget(event, GetEventDispatcherTarget());
            ReleaseEvent(event);
        }
        UnregisterEventHotKey(hotKey);
    }
    return 0;
}

#endif
