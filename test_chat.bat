@echo off
curl.exe -X POST http://127.0.0.1:8000/assistant/chat -H "Content-Type: application/json" -d @test_chat_payload.json --max-time 320 2>&1