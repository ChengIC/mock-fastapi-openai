import asyncio
import json
import time
from typing import Optional, List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="OpenAI-compatible API")

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "mock-gpt-model"
    messages: List[Message]
    max_tokens: Optional[int] = 512
    temperature: Optional[float] = 0.1
    stream: Optional[bool] = False

async def _resp_async_generator(text_resp: str):
    tokens = text_resp.split(" ")

    for i, token in enumerate(tokens):
        # First chunk must include the role: "assistant"
        if i == 0:
            chunk = {
                "id": f"chatcmpl-{i}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "mock-gpt-model",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": token + " "},
                        "finish_reason": None,
                    }
                ],
            }
        else:
            # Subsequent chunks only include the content
            chunk = {
                "id": f"chatcmpl-{i}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "mock-gpt-model",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": token + " "},
                        "finish_reason": None if i < len(tokens) - 1 else "stop",
                    }
                ],
            }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.1)

    # Signal the end of the stream
    yield "data: [DONE]\n\n"


async def log_request_details(request: Request):
    """Extract and print all request details to the terminal."""
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    cookies = dict(request.cookies)
    method = request.method
    url = str(request.url)

    # Read and decode request body
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        body = "Invalid JSON or empty body"

    log_data = {
        "Method": method,
        "URL": url,
        "Headers": headers,
        "Query Params": query_params,
        "Cookies": cookies,
        "Body": body
    }

    print("\n" + "=" * 60)
    print("📌 REQUEST DETAILS 📌")
    print("=" * 60)
    for key, value in log_data.items():
        print(f"🔹 {key}:\n{json.dumps(value, indent=2) if isinstance(value, dict) else value}\n")
    print("=" * 60 + "\n")



@app.post("/chat/completions")
async def chat_completions(request: Request):
    raw_body = await request.body()  # Get the raw request body as bytes
    await log_request_details(request)
    # Parse the request body into the Pydantic model manually
    body = ChatCompletionRequest.model_validate_json(raw_body)

    print(f"Parsed Pydantic model: {body}")

    if not body.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    resp_content = "As a mock AI Assistant, I can only echo your last message: " + body.messages[-1].content

    if body.stream:
        return StreamingResponse(
            _resp_async_generator(resp_content), media_type="text/event-stream"
        )

    return {
        "id": "chatcmpl-1337",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": resp_content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)