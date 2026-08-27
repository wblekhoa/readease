#import <Foundation/Foundation.h>
#import <Carbon/Carbon.h>
#import <arpa/inet.h>
#import <signal.h>
#import <unistd.h>

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

int main(void) {
    @autoreleasepool {
        signal(SIGPIPE, SIG_IGN);
        pid_t parentProcessIdentifier = getppid();
        if (parentProcessIdentifier <= 1) {
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
            kVK_ANSI_R,
            controlKey | optionKey | cmdKey,
            hotKeyID,
            GetApplicationEventTarget(),
            0,
            &hotKey
        );
        if (handlerStatus != noErr || hotKeyStatus != noErr || hotKey == NULL) {
            RDXSendFrame('E', nil);
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
