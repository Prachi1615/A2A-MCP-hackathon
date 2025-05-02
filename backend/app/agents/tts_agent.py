# handler.py
import asyncio
import json
import os
import traceback
import httpx

RIME_API_URL = "https://users.rime.ai/v1/rime-tts"
RIME_API_KEY = os.environ.get("RIME_API_KEY", "your_rime_api_key_here")  # set env var or replace directly

class AudioLoop:
    def __init__(self):
        # Queue to hold text inputs that need TTS synthesis
        self.text_queue = asyncio.Queue()

    async def synthesize_with_rime(self, text, output_path="audio_output.mp3"):
        """Send text to Rime TTS and save the resulting MP3."""
        payload = {
            "speaker": "Cove",
            "text": text,
            "modelId": "Mist v2",
            "lang": "eng",
            "samplingRate": 22050,
            "speedAlpha": 1.0,
            "reduceLatency": False,
            "pauseBetweenBrackets": False,
            "phonemizeBetweenBrackets": False
        }
        headers = {
            "Accept": "audio/mp3",
            "Authorization": f"Bearer {RIME_API_KEY}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(RIME_API_URL, headers=headers, json=payload)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    print(f"[AudioLoop] Rime audio written to {output_path}")
                else:
                    print(f"[AudioLoop] Rime API error: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"[AudioLoop] Rime request failed: {e}")

    async def process_json(self, json_data):
        """Convert a JSON object to text and synthesize it via Rime."""
        text = f"The user has shared the following JSON data:\n\n{json.dumps(json_data, indent=2)}"
        await self.text_queue.put(text)
        print("[AudioLoop] Queued JSON for Rime synthesis")

    async def tts_worker(self):
        """Background task to process queued texts and synthesize them."""
        while True:
            text = await self.text_queue.get()
            await self.synthesize_with_rime(text)
            self.text_queue.task_done()

    async def run(self):
        """Main entry point for the Rime audio loop."""
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.tts_worker())
                await asyncio.Future()  # Keeps running
        except asyncio.CancelledError:
            print("[AudioLoop] Cancelled")
        except Exception:
            traceback.print_exc()
            raise
