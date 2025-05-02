import asyncio
import base64
import json
import os
from typing import AsyncGenerator, Literal

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastrtc import (
    AsyncStreamHandler,
    Stream,
    get_cloudflare_turn_credentials_async,
    wait_for_item,
)
from google import genai
from google.genai.types import (
    LiveConnectConfig,
    PrebuiltVoiceConfig,
    SpeechConfig,
    VoiceConfig,
)
from pydantic import BaseModel
from .core.config import settings
from .api.routes import router
load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def encode_audio(data: np.ndarray) -> str:
    """Encode Audio data to send to the server"""
    return base64.b64encode(data.tobytes()).decode("UTF-8")

class GeminiHandler(AsyncStreamHandler):
    """Handler for the Gemini API"""

    def __init__(
        self,
        expected_layout: Literal["mono"] = "mono",
        output_sample_rate: int = 24000,
    ) -> None:
        super().__init__(
            expected_layout,
            output_sample_rate,
            input_sample_rate=16000,
        )
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self.quit: asyncio.Event = asyncio.Event()
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("Warning: GEMINI_API_KEY environment variable is not set")

    def copy(self) -> "GeminiHandler":
        return GeminiHandler(
            expected_layout="mono",
            output_sample_rate=self.output_sample_rate,
        )

    async def start_up(self):
        try:
            if not self.phone_mode:
                await self.wait_for_args()
                api_key, voice_name = self.latest_args[1:]
            else:
                api_key, voice_name = None, "Puck"

            # Use provided API key or fall back to environment variable
            api_key = api_key or self.api_key
            if not api_key:
                raise ValueError("No API key provided")

            print(f"Using API key: {api_key[:5]}...")  # Log first 5 chars for debugging

            client = genai.Client(
                api_key=api_key,
                http_options={"api_version": "v1alpha"},
            )

            config = LiveConnectConfig(
                response_modalities=["AUDIO"],
                speech_config=SpeechConfig(
                    voice_config=VoiceConfig(
                        prebuilt_voice_config=PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            )
            async with client.aio.live.connect(
                model="gemini-2.0-flash-exp", config=config
            ) as session:
                async for audio in session.start_stream(
                    stream=self.stream(), mime_type="audio/pcm"
                ):
                    if audio.data:
                        array = np.frombuffer(audio.data, dtype=np.int16)
                        self.output_queue.put_nowait((self.output_sample_rate, array))
        except Exception as e:
            print(f"Error in start_up: {str(e)}")
            raise

    async def stream(self) -> AsyncGenerator[bytes, None]:
        while not self.quit.is_set():
            try:
                audio = await asyncio.wait_for(self.input_queue.get(), 0.1)
                yield audio
            except (asyncio.TimeoutError, TimeoutError):
                pass

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        _, array = frame
        array = array.squeeze()
        audio_message = encode_audio(array)
        self.input_queue.put_nowait(audio_message)

    async def emit(self) -> tuple[int, np.ndarray] | None:
        return await wait_for_item(self.output_queue)

    def shutdown(self) -> None:
        self.quit.set()

class InputData(BaseModel):
    webrtc_id: str
    voice_name: str
    api_key: str

stream = Stream(
    modality="audio",
    mode="send-receive",
    handler=GeminiHandler(),
    rtc_configuration=get_cloudflare_turn_credentials_async,
    concurrency_limit=5,
    time_limit=90,
)

stream.mount(app)

@app.post("/input_hook")
async def input_hook(body: InputData):
    try:
        if not body.api_key:
            raise HTTPException(status_code=400, detail="API key is required")
        stream.set_input(body.webrtc_id, body.api_key, body.voice_name)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error in input_hook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def index():
    try:
        print("Received request for RTC configuration")
        rtc_config = await get_cloudflare_turn_credentials_async()
        print("Successfully retrieved RTC configuration")
        return {"rtc_config": rtc_config}
    except Exception as e:
        print(f"Error in index endpoint: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get RTC configuration: {str(e)}"
        )

async def get_cloudflare_turn_credentials_async():
    try:
        # For development, return a basic configuration
        return {
            "iceServers": [
                {
                    "urls": [
                        "stun:stun.l.google.com:19302",
                        "stun:stun1.l.google.com:19302"
                    ]
                }
            ]
        }
    except Exception as e:
        print(f"Error getting TURN credentials: {str(e)}")
        # Return a basic STUN configuration as fallback
        return {
            "iceServers": [
                {
                    "urls": [
                        "stun:stun.l.google.com:19302",
                        "stun:stun1.l.google.com:19302"
                    ]
                }
            ]
        }
# Include API router
app.include_router(router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 