from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import AudioEvent
import asyncio
import base64
from fastapi.middleware.cors import CORSMiddleware
import boto3
import json
import os
import base64
import io
import asyncio
from dotenv import load_dotenv
from typing import Dict, Optional
import wave
import struct
import uuid
from datetime import datetime, timedelta

load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize AWS clients with specific credentials
transcribe = boto3.client(
    'transcribe',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

translate = boto3.client(
    'translate',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

polly = boto3.client(
    'polly',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

# In-memory storage for audio files
audio_files = {}

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import AudioEvent
import asyncio
import base64

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, str] = {}
        self.speaker_connection: Optional[WebSocket] = None
        self.transcribe_client = TranscribeStreamingClient(region=os.getenv('AWS_REGION'))

    async def connect(self, websocket: WebSocket, is_speaker: bool = False, language: str = None):
        await websocket.accept()
        if is_speaker:
            self.speaker_connection = websocket
        else:
            self.active_connections[websocket] = language

    def disconnect(self, websocket: WebSocket):
        if websocket == self.speaker_connection:
            self.speaker_connection = None
        else:
            self.active_connections.pop(websocket, None)

    async def handle_speaker_stream(self, audio_queue: asyncio.Queue):
        stream = await self.transcribe_client.start_stream_transcription(
            language_code="en-US",
            media_sample_rate_hz=16000,
            media_encoding="pcm"
        )

        async def write_audio():
            while True:
                audio_chunk = await audio_queue.get()
                await stream.input_stream.send_audio_event(audio_chunk=audio_chunk)

        async def read_transcripts():
            async for event in stream.output_stream:
                for result in event.transcript.results:
                    if not result.is_partial:
                        text = result.alternatives[0].transcript
                        print(f"[Transcript] {text}")
                        await self.broadcast_translation(text.strip())

        await asyncio.gather(write_audio(), read_transcripts())

    async def broadcast_translation(self, text: str):
        print(f"[DEBUG] Attempting to broadcast: '{text}' to {len(self.active_connections)} audience members.")
        # Group connections by language
        language_to_connections = {}
        for connection, language in self.active_connections.items():
            language_to_connections.setdefault(language, []).append(connection)

        for language, connections in language_to_connections.items():
            try:
                print(f"[DEBUG] Translating to {language}: '{text}'")
                translated = translate.translate_text(
                    Text=text,
                    SourceLanguageCode='en',
                    TargetLanguageCode=language
                )['TranslatedText']
                print(f"[DEBUG] Translated text: '{translated}'")

                response = polly.synthesize_speech(
                    Text=translated,
                    OutputFormat='mp3',
                    VoiceId=self._get_voice_id(language)
                )

                audio_b64 = base64.b64encode(response['AudioStream'].read()).decode('utf-8')

                for connection in connections:
                    await connection.send_json({
                        'type': 'translation',
                        'text': translated,
                        'audio': audio_b64
                    })
                print(f"[DEBUG] Sent translation to {len(connections)} audience in {language}.")
            except Exception as e:
                print(f"[ERROR] Error broadcasting to {language}: {e}")

    def _get_voice_id(self, language_code: str) -> str:
        voice_map = {
            'es': 'Lupe', 'fr': 'Lea', 'de': 'Vicki', 'it': 'Bianca',
            'pt': 'Camila', 'ru': 'Tatyana', 'ja': 'Takumi',
            'ko': 'Seoyeon', 'zh': 'Zhiyu', 'ar': 'Zeina'
        }
        return voice_map.get(language_code, 'Joanna')


manager = ConnectionManager()

@app.get("/")
async def get():
    return FileResponse('static/index.html')

@app.get("/speaker")
async def get_speaker():
    return FileResponse('static/speaker.html')

@app.get("/audience")
async def get_audience():
    return FileResponse('static/audience.html')

@app.get("/audio/{file_id}")
async def get_audio(file_id: str):
    if file_id in audio_files:
        return StreamingResponse(
            io.BytesIO(audio_files[file_id]['data']),
            media_type="audio/wav"
        )
    return {"error": "Audio file not found"}

@app.websocket("/ws/speaker")
async def websocket_speaker(websocket: WebSocket):
    await manager.connect(websocket, is_speaker=True)
    audio_queue = asyncio.Queue()
    asyncio.create_task(manager.handle_speaker_stream(audio_queue))

    try:
        while True:
            audio_data = await websocket.receive_bytes()
            await audio_queue.put(audio_data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/audience")
async def websocket_audience(websocket: WebSocket):
    await manager.connect(websocket, language='es')  # default to Spanish
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message['type'] == 'language':
                manager.active_connections[websocket] = message['language']
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 