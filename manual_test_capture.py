#!/usr/bin/env python3
"""
Manual test to verify test capture functionality with real WhatsApp document data.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.utils.test_capture import test_capture

# Real webhook data structure from the logs I saw
webhook_data = {
    "event": "messages.upsert",
    "instance": "flashinho_pro", 
    "data": {
        "key": {
            "remoteJid": "555197285829@s.whatsapp.net",
            "fromMe": False,
            "id": "FD0155F76261F9D5717BB99AF1FA9418"
        },
        "pushName": "Cezar Vasconcelos",
        "status": "DELIVERY_ACK",
        "message": {
            "documentMessage": {
                "url": "https://mmg.whatsapp.net/v/t62.7119-24/11812422_1062522779192356_2011179736745893511_n.enc",
                "mimetype": "application/pdf",
                "fileSha256": "+rp9PdU8imQoBV9dkoHuaKpLXwz0mkMGQcNVEwj7Gu4=",
                "fileLength": "1257867",
                "pageCount": 108,
                "mediaKey": "/4bnQmUzv/ecRWZ2F8JQg3uEEteVOcuKv6HGuB4Fku4=",
                "fileName": "PBIA.pdf",
                "fileEncSha256": "I1I3Wg66mMDG85xCeDOnTgQrVVabveNn5GIkkMrAplU=",
                "directPath": "/v/t62.7119-24/11812422_1062522779192356_2011179736745893511_n.enc",
                "mediaKeyTimestamp": "1750793473",
                "thumbnailDirectPath": "/v/t62.36145-24/19974074_2528162044020873_3109129672562060016_n.enc",
                "thumbnailSha256": "ICtiA6z604FDvblb+sEyfHs8sPgjLJLHrdDjzuFR5k8=",
                "thumbnailEncSha256": "q6xlqTBZRRNH/JB/Txx/fLjCHDrCGIP44qny1ZBvFVM=",
                "jpegThumbnail": "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",
                "thumbnailHeight": 480,
                "thumbnailWidth": 339
            },
            "messageContextInfo": {
                "deviceListMetadata": {
                    "senderKeyHash": "Gu/iUJxqi7+6EA==",
                    "senderTimestamp": "1750544461",
                    "recipientKeyHash": "StFZFA4r6Wn9eA==",
                    "recipientTimestamp": "1750780146"
                },
                "deviceListMetadataVersion": 2,
                "messageSecret": "Nqq3xJsPkO+I72cC5I2rch2pgQKuS/nryuglmLJDdNQ="
            }
        },
        "mediaUrl": "http://api.bucket.namastex.ai/cezar-dev-evolution/evolution-api/ddb7eca4-96eb-4055-b657-fd9ea1b158d3/555197285829%40s.whatsapp.net/documentMessage/PBIA.pdf",
        # This is where the base64 SHOULD be, but it's missing from the webhook data I saw in logs
        # The webhook processing shows the agent got a media_url instead of base64 data
        "base64": "JVBERi0xLjUKJfbk/N8KMSAwIG9iago8PAovTGFuZyAocHQtQlIpCi9QYWdlTGFiZWxzIDIgMCBSCi9QYWdlcyAzIDAgUgovVHlwZSAvQ2F0YWxvZwovVmlld2VyUHJlZmVyZW5jZXMgPDwKL0RpcmVjdGlvbiAvTDJSCj4+Cj4+CmVuZG9iago0IDAgb2JqCjw8Ci9DcmVhdGlvbkRhdGUgKEQ6MjAyNTA2MTIwODIyNDItMDMnMDAnKQovQ3JlYXRvciAoQWRvYmUgSW5EZXNpZ24gMjAuMyBcKE1hY2ludG9zaFwpKQovTW9kRGF0ZSAoRDoyMDI1MDYxMjA4MjMzMS0wMycwMCcpCi9Qcm9kdWNlciAoQWRvYmUgUERGIExpYnJhcnkgMTcuMCkKL1RyYXBwZWQgL0ZhbHNlCj4+CmVuZG9iagoyIDAgb2JqCjw8Ci9OdW1zIFswIDUgMCBSIDIgNiAwIFIgMTA2IDcgMCBSXQo+PgplbmRvYmoKMyAwIG9iago8PAovQ291bnQgMTA4Ci9LaWRzIFs4IDAgUiA5IDAgUiAxMCAwIFIgMTEgMCBSXQovVHlwZSAvUGFnZXMKPj4KZW5kb2JqCjUgMCBvYmoKPDwKL1MgL1IKPj4KZW5kb2JqCjYgMCBvYmoKPDwKL1MgL0QKPj4KZW5kb2JqCjcgMCBvYmoKPDwKL1MgL1IKL1N0IDMKPj4KZW5kb2JqCjggMCBvYmoKPDwKL0NvdW50IDI1Ci9LaWRzIFsxMiAwIFIgMTMgMCBSIDE0IDAgUiAxNSAwIFIgMTYgMCBSXQovUGFyZW50IDMgMCBSCi9UeXBlIC9QYWdlcwo+PgplbmRvYmoKOSAwIG9iago8PAovQ291bnQgMjUKL0tpZHMgWzE3IDAgUiAxOCAwIFIgMTkgMCBSIDIwIDAgUiAyMSAwIFJdCi9QYXJlbnQgMyAwIFIKL1R5cGUgL1BhZ2VzCj4+CmVuZG9iagoxMCAwIG9iago8PAovQ291bnQgMjUKL0tpZHMgWzIyIDAgUiAyMyAwIFIgMjQgMCBSIDI1IDAgUiAyNiAwIFJdCi9QYXJlbnQgMyAwIFIKL1R5cGUgL1BhZ2VzCj4+CmVuZG9iagoxMSAwIG9iago8PAovQ291bnQgMzMKL0tpZHMgWzI3IDAgUiAyOCAwIFIgMjkgMCBSIDMwIDAgUiAzMSAwIFIgMzIgMCBSXQovUGFyZW50IDMgMCBSCi9UeXBlIC9QYWdlcwo+PgplbmRvYmoKMTIgMCBvYmoKPDwKL0NvdW50IDUKL0tpZHMgWzMzIDAgUiAzNCAwIFIgMzUgMCBSIDM2IDAgUiAzNyAwIFJdCi9QYXJlbnQgOCAwIFIKL1R5cGUgL1BhZ2VzCj4+CmVuZG9iag=="
    }
}

# Create a mock instance config
class MockInstanceConfig:
    def __init__(self, name):
        self.name = name

instance_config = MockInstanceConfig("flashinho_pro")

print("🧪 Testing test capture functionality manually...")
print(f"📊 Data has base64: {'base64' in webhook_data['data']}")
print(f"📊 Message keys: {list(webhook_data['data']['message'].keys())}")
print(f"📊 Base64 length: {len(webhook_data['data'].get('base64', ''))}")

# Enable capture
test_capture.enable_capture()

# Test the capture
result = test_capture.capture_media_message(webhook_data, instance_config)

print(f"🎯 Capture result: {result}")

if result:
    print(f"✅ SUCCESS: Test capture created at {result}")
else:
    print("❌ FAILED: No capture file created")

# List what was created
import os
if os.path.exists("test_captures"):
    files = os.listdir("test_captures")
    print(f"📁 Files in test_captures: {files}")
else:
    print("📁 test_captures directory doesn't exist")