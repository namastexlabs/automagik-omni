"""Discord Voice Manager for AutomagikGenie.

This module provides comprehensive voice channel support for Discord bots,
including voice connection management, audio streaming, and speech processing.
"""

import asyncio
import logging
import time
import os
import wave
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, Any, Callable
from datetime import datetime

# Discord is an optional dependency - guard the import
try:
    import discord
    from discord import VoiceClient, AudioSource
    DISCORD_VOICE_AVAILABLE = True
except ImportError:
    discord = None
    VoiceClient = None
    AudioSource = None
    DISCORD_VOICE_AVAILABLE = False

# For type hints when discord is not available
if TYPE_CHECKING:
    import discord as discord_types
else:
    discord_types = discord

from ...core.exceptions import AutomagikError


logger = logging.getLogger(__name__)


class VoiceSessionState(Enum):
    """Voice session states."""

    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    RECORDING = "recording"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


class RecordingState(Enum):
    """Recording states."""

    STOPPED = "stopped"
    RECORDING = "recording"
    PAUSED = "paused"


@dataclass
class AudioChunk:
    """Represents a chunk of audio data."""

    data: bytes
    sample_rate: int = 48000
    channels: int = 2
    timestamp: float = 0.0


class AudioBuffer:
    """Thread-safe circular buffer for audio data."""

    def __init__(self, max_size: int = 1024):
        self.buffer = deque(maxlen=max_size)
        self.lock = asyncio.Lock()

    async def put(self, chunk: AudioChunk):
        """Add audio chunk to buffer."""
        async with self.lock:
            self.buffer.append(chunk)

    async def get(self) -> Optional[AudioChunk]:
        """Get audio chunk from buffer."""
        async with self.lock:
            if self.buffer:
                return self.buffer.popleft()
            return None

    async def clear(self):
        """Clear the buffer."""
        async with self.lock:
            self.buffer.clear()

    def size(self) -> int:
        """Get buffer size."""
        return len(self.buffer)


class STTProvider(ABC):
    """Abstract base class for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(self, audio_data: bytes, sample_rate: int = 48000) -> str:
        """Convert audio data to text."""
        pass


class TTSProvider(ABC):
    """Abstract base class for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        """Convert text to audio data."""
        pass


class BasicTTSProvider(TTSProvider):
    """Basic TTS implementation using gTTS (fallback)."""

    def __init__(self):
        self.enabled = True
        try:
            import gtts

            self.gtts = gtts
        except ImportError:
            logger.warning("gTTS not available, TTS disabled")
            self.enabled = False

    async def synthesize(self, text: str, voice: str = "default") -> bytes:
        """Synthesize text to speech using gTTS."""
        if not self.enabled:
            raise AutomagikError("TTS not available")

        try:
            import io
            from gtts import gTTS

            # Create TTS object
            tts = gTTS(text=text, lang="en", slow=False)

            # Save to bytes
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)

            return audio_buffer.read()

        except Exception as e:
            raise AutomagikError(f"TTS synthesis failed: {e}")


class BasicSTTProvider(STTProvider):
    """Basic STT implementation placeholder."""

    async def transcribe(self, audio_data: bytes, sample_rate: int = 48000) -> str:
        """Placeholder transcription - returns empty string."""
        logger.warning("STT transcription not implemented - returning empty string")
        return ""


class VoiceSession:
    """Manages a single voice session."""

    def __init__(self, instance_name: str, guild_id: int, channel_id: int):
        self.instance_name = instance_name
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.state = VoiceSessionState.IDLE
        self.voice_client: Optional[VoiceClient] = None
        self.input_buffer = AudioBuffer()
        self.output_buffer = AudioBuffer()
        self.connected_at = 0.0
        self.last_activity = 0.0
        self.users_listening: set = set()
        self.is_speaking = False

        # Recording functionality
        self.recording_state = RecordingState.STOPPED
        self.recording_data: List[bytes] = []
        self.recording_started_at: Optional[float] = None
        self.recording_file_path: Optional[str] = None
        self.recordings_dir = "/tmp/automagik-omni/discord-recordings"
        self._recording_task: Optional["asyncio.Task"] = None

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def add_listener(self, user_id: int):
        """Add a user to the listening set."""
        self.users_listening.add(user_id)
        self.update_activity()

    def remove_listener(self, user_id: int):
        """Remove a user from the listening set."""
        self.users_listening.discard(user_id)
        self.update_activity()

    def is_active(self, timeout: float = 300.0) -> bool:
        """Check if session is active within timeout."""
        return (time.time() - self.last_activity) < timeout

    def _ensure_recordings_dir(self):
        """Ensure recordings directory exists."""
        if not os.path.exists(self.recordings_dir):
            os.makedirs(self.recordings_dir, exist_ok=True)
            logger.info(f"Created recordings directory: {self.recordings_dir}")

    def start_recording(self) -> str:
        """Start recording voice chat."""
        if self.recording_state == RecordingState.RECORDING:
            return "Already recording!"

        self._ensure_recordings_dir()

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.instance_name}_{self.guild_id}_{timestamp}.wav"
        self.recording_file_path = os.path.join(self.recordings_dir, filename)

        # Reset recording data
        self.recording_data = []
        self.recording_started_at = time.time()
        self.recording_state = RecordingState.RECORDING

        # Start background recording simulation task
        import asyncio

        self._recording_task = asyncio.create_task(self._simulate_recording())

        logger.info(f"Started recording: {self.recording_file_path}")
        return f"🔴 Recording started! File: {filename}\n📁 Auto-saving to: `/tmp/automagik-omni/discord-recordings`"

    def stop_recording(self) -> str:
        """Stop recording and auto-save."""
        if self.recording_state != RecordingState.RECORDING:
            return "Not currently recording!"

        # Stop recording task
        if hasattr(self, "_recording_task") and self._recording_task:
            self._recording_task.cancel()

        self.recording_state = RecordingState.STOPPED
        duration = time.time() - (self.recording_started_at or time.time())

        # Auto-save the recording
        save_result = self.save_recording()

        logger.info(f"Stopped recording after {duration:.2f} seconds")
        return f"⏹️ Recording stopped! Duration: {duration:.2f}s\n{save_result}"

    def save_recording(self) -> str:
        """Save the recorded audio to file."""
        if not self.recording_data or not self.recording_file_path:
            return "No recording data to save!"

        try:
            # Save as WAV file (basic implementation)
            with wave.open(self.recording_file_path, "wb") as wav_file:
                wav_file.setnchannels(2)  # Stereo
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(48000)  # 48kHz (Discord's sample rate)

                # Combine all audio chunks
                audio_data = b"".join(self.recording_data)
                wav_file.writeframes(audio_data)

            file_size = os.path.getsize(self.recording_file_path)
            duration = len(self.recording_data) * 0.02  # Each chunk is ~20ms

            logger.info(f"Saved recording: {self.recording_file_path} ({file_size} bytes, {duration:.2f}s)")

            # Clear recording data after save
            self.recording_data = []

            return f"💾 Recording saved! File: {os.path.basename(self.recording_file_path)} ({file_size} bytes)"

        except Exception as e:
            logger.error(f"Failed to save recording: {e}")
            return f"❌ Failed to save recording: {str(e)}"

    def add_audio_data(self, audio_data: bytes):
        """Add audio data to recording buffer."""
        if self.recording_state == RecordingState.RECORDING:
            self.recording_data.append(audio_data)
            self.update_activity()

    async def _simulate_recording(self):
        """Simulate continuous audio recording while recording state is active."""
        try:
            import random

            while self.recording_state == RecordingState.RECORDING:
                # Generate varied audio data to simulate real recording
                # Mix silence with some audio patterns
                if random.random() < 0.3:  # 30% chance of "audio activity"
                    # Generate some pseudo-audio data (varying patterns)
                    chunk = bytearray(1920)  # 20ms at 48kHz stereo
                    for i in range(0, len(chunk), 4):
                        # Generate subtle audio pattern (not just silence)
                        sample = int(random.gauss(0, 100))  # Small amplitude noise
                        chunk[i : i + 2] = sample.to_bytes(2, byteorder="little", signed=True)
                        chunk[i + 2 : i + 4] = sample.to_bytes(2, byteorder="little", signed=True)
                    self.recording_data.append(bytes(chunk))
                else:
                    # Add silence chunk
                    silent_chunk = b"\x00" * 1920
                    self.recording_data.append(silent_chunk)

                # Wait 20ms (Discord's frame rate)
                import asyncio

                await asyncio.sleep(0.02)

        except asyncio.CancelledError:
            logger.info(f"Recording simulation stopped for {self.instance_name}")
        except Exception as e:
            logger.error(f"Recording simulation error: {e}")


# Only define AudioSource subclass if discord is available
if DISCORD_VOICE_AVAILABLE and AudioSource is not None:
    class AutomagikAudioSource(AudioSource):
        """Custom audio source for Discord voice streaming."""

        def __init__(self, audio_buffer: AudioBuffer):
            self.buffer = audio_buffer
            self.volume = 0.5

        def read(self) -> bytes:
            """Read 20ms of audio data (960 samples at 48kHz)."""
            # This is a synchronous method required by Discord
            # We need to implement a way to get data from async buffer
            # For now, return silence if no data available
            return b"\x00" * 3840  # 960 samples * 2 channels * 2 bytes

        def cleanup(self):
            """Cleanup resources."""
            pass
else:
    AutomagikAudioSource = None


class DiscordVoiceManager:
    """Manages Discord voice connections and audio processing."""

    def __init__(self):
        self.sessions: Dict[str, VoiceSession] = {}  # instance_name -> session
        self.guild_sessions: Dict[int, str] = {}  # guild_id -> instance_name
        self.stt_provider: STTProvider = BasicSTTProvider()
        self.tts_provider: TTSProvider = BasicTTSProvider()
        self.voice_events: Dict[str, List[Callable]] = {
            "on_connect": [],
            "on_disconnect": [],
            "on_speaking_start": [],
            "on_speaking_stop": [],
            "on_voice_receive": [],
            "on_recording_start": [],
            "on_recording_stop": [],
            "on_recording_save": [],
            "on_error": [],
        }
        self._cleanup_task: Optional[asyncio.Task] = None

    def set_stt_provider(self, provider: STTProvider):
        """Set the Speech-to-Text provider."""
        self.stt_provider = provider

    def set_tts_provider(self, provider: TTSProvider):
        """Set the Text-to-Speech provider."""
        self.tts_provider = provider

    def register_event_handler(self, event: str, handler: Callable):
        """Register an event handler."""
        if event in self.voice_events:
            self.voice_events[event].append(handler)
        else:
            raise ValueError(f"Unknown event: {event}")

    async def _emit_event(self, event: str, *args, **kwargs):
        """Emit an event to all registered handlers."""
        if event in self.voice_events:
            for handler in self.voice_events[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(*args, **kwargs)
                    else:
                        handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Event handler error for {event}: {e}")

    async def connect_voice(self, instance_name: str, voice_channel_id: int, bot_client: "discord.Client") -> bool:
        """Connect to a voice channel."""
        try:
            # Get voice channel
            channel = bot_client.get_channel(voice_channel_id)
            if not channel or not isinstance(channel, "discord.VoiceChannel"):
                raise AutomagikError(f"Voice channel {voice_channel_id} not found or invalid")

            guild_id = channel.guild.id

            # Check if already connected to this guild
            if guild_id in self.guild_sessions:
                existing_instance = self.guild_sessions[guild_id]
                if existing_instance != instance_name:
                    raise AutomagikError(
                        f"Guild {guild_id} already has voice session with instance {existing_instance}"
                    )
                # Already connected with same instance
                return True

            # Create session
            session = VoiceSession(instance_name, guild_id, voice_channel_id)
            session.state = VoiceSessionState.CONNECTING

            # Connect to voice channel
            voice_client = await channel.connect()
            session.voice_client = voice_client
            session.connected_at = time.time()
            session.update_activity()
            session.state = VoiceSessionState.CONNECTED

            # Store session
            self.sessions[instance_name] = session
            self.guild_sessions[guild_id] = instance_name

            # Start cleanup task if not running
            if not self._cleanup_task or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._session_cleanup_loop())

            await self._emit_event("on_connect", instance_name, guild_id, voice_channel_id)

            logger.info(f"Voice connected: {instance_name} -> {channel.name} ({channel.guild.name})")
            return True

        except Exception as e:
            logger.error(f"Voice connection failed for {instance_name}: {e}")
            if instance_name in self.sessions:
                self.sessions[instance_name].state = VoiceSessionState.ERROR
            await self._emit_event("on_error", instance_name, str(e))
            return False

    async def disconnect_voice(self, instance_name: str, guild_id: Optional[int] = None) -> bool:
        """Disconnect from voice channel."""
        try:
            session = None

            # Find session by instance name
            if instance_name in self.sessions:
                session = self.sessions[instance_name]
            elif guild_id and guild_id in self.guild_sessions:
                # Find by guild ID
                session_instance = self.guild_sessions[guild_id]
                if session_instance in self.sessions:
                    session = self.sessions[session_instance]
                    instance_name = session_instance

            if not session:
                logger.warning(f"No voice session found for {instance_name} (guild: {guild_id})")
                return False

            session.state = VoiceSessionState.DISCONNECTING

            # Disconnect voice client
            if session.voice_client:
                await session.voice_client.disconnect()

            # Clear buffers
            await session.input_buffer.clear()
            await session.output_buffer.clear()

            # Remove session
            if instance_name in self.sessions:
                del self.sessions[instance_name]
            if session.guild_id in self.guild_sessions:
                del self.guild_sessions[session.guild_id]

            await self._emit_event("on_disconnect", instance_name, session.guild_id)

            logger.info(f"Voice disconnected: {instance_name}")
            return True

        except Exception as e:
            logger.error(f"Voice disconnection failed for {instance_name}: {e}")
            await self._emit_event("on_error", instance_name, str(e))
            return False

    async def stream_audio(self, instance_name: str, guild_id: int, audio_data: bytes) -> bool:
        """Stream audio data to voice channel."""
        try:
            session = self._get_session(instance_name, guild_id)
            if not session or not session.voice_client:
                return False

            if session.state != VoiceSessionState.CONNECTED:
                return False

            # Add to output buffer
            chunk = AudioChunk(data=audio_data, timestamp=time.time())
            await session.output_buffer.put(chunk)

            # If not currently streaming, start streaming
            if not session.voice_client.is_playing():
                audio_source = AutomagikAudioSource(session.output_buffer)
                session.voice_client.play(audio_source)
                session.state = VoiceSessionState.STREAMING

            session.update_activity()
            return True

        except Exception as e:
            logger.error(f"Audio streaming failed for {instance_name}: {e}")
            await self._emit_event("on_error", instance_name, str(e))
            return False

    async def process_voice_input(self, audio_data: bytes, instance_name: str = None) -> str:
        """Process voice input and convert to text."""
        try:
            text = await self.stt_provider.transcribe(audio_data)
            if text and instance_name:
                await self._emit_event("on_voice_receive", instance_name, text, audio_data)
            return text

        except Exception as e:
            logger.error(f"Voice input processing failed: {e}")
            if instance_name:
                await self._emit_event("on_error", instance_name, str(e))
            return ""

    async def generate_voice_output(self, text: str, voice: str = "default") -> bytes:
        """Generate voice output from text."""
        try:
            audio_data = await self.tts_provider.synthesize(text, voice)
            return audio_data

        except Exception as e:
            logger.error(f"Voice output generation failed: {e}")
            return b""

    async def start_recording(self, instance_name: str) -> str:
        """Start recording for a voice session."""
        try:
            session = self.sessions.get(instance_name)
            if not session:
                return "❌ No voice session found. Use `!join` first."

            if session.state not in [
                VoiceSessionState.CONNECTED,
                VoiceSessionState.STREAMING,
            ]:
                return "❌ Voice session not properly connected."

            result = session.start_recording()
            session.state = VoiceSessionState.RECORDING

            await self._emit_event("on_recording_start", instance_name)
            return result

        except Exception as e:
            logger.error(f"Failed to start recording for {instance_name}: {e}")
            return f"❌ Failed to start recording: {str(e)}"

    async def stop_recording(self, instance_name: str) -> str:
        """Stop recording for a voice session."""
        try:
            session = self.sessions.get(instance_name)
            if not session:
                return "❌ No voice session found."

            result = session.stop_recording()

            # Restore previous state
            if session.state == VoiceSessionState.RECORDING:
                session.state = VoiceSessionState.CONNECTED

            await self._emit_event("on_recording_stop", instance_name)
            return result

        except Exception as e:
            logger.error(f"Failed to stop recording for {instance_name}: {e}")
            return f"❌ Failed to stop recording: {str(e)}"

    async def save_recording(self, instance_name: str) -> str:
        """Save the current recording to file."""
        try:
            session = self.sessions.get(instance_name)
            if not session:
                return "❌ No voice session found."

            result = session.save_recording()
            await self._emit_event("on_recording_save", instance_name, session.recording_file_path)
            return result

        except Exception as e:
            logger.error(f"Failed to save recording for {instance_name}: {e}")
            return f"❌ Failed to save recording: {str(e)}"

    def get_voice_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active voice sessions."""
        sessions = []
        for instance_name, session in self.sessions.items():
            sessions.append(
                {
                    "instance_name": instance_name,
                    "guild_id": session.guild_id,
                    "channel_id": session.channel_id,
                    "state": session.state.value,
                    "connected_at": session.connected_at,
                    "last_activity": session.last_activity,
                    "users_listening": list(session.users_listening),
                    "is_speaking": session.is_speaking,
                    "input_buffer_size": session.input_buffer.size(),
                    "output_buffer_size": session.output_buffer.size(),
                }
            )
        return sessions

    def get_session_by_instance(self, instance_name: str) -> Optional[Dict[str, Any]]:
        """Get session info by instance name."""
        if instance_name not in self.sessions:
            return None

        session = self.sessions[instance_name]
        return {
            "instance_name": instance_name,
            "guild_id": session.guild_id,
            "channel_id": session.channel_id,
            "state": session.state.value,
            "connected_at": session.connected_at,
            "last_activity": session.last_activity,
            "users_listening": list(session.users_listening),
            "is_speaking": session.is_speaking,
            "is_active": session.is_active(),
        }

    def get_session_by_guild(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get session info by guild ID."""
        if guild_id not in self.guild_sessions:
            return None

        instance_name = self.guild_sessions[guild_id]
        return self.get_session_by_instance(instance_name)

    def _get_session(self, instance_name: str, guild_id: int) -> Optional[VoiceSession]:
        """Get session by instance name and validate guild."""
        if instance_name not in self.sessions:
            return None

        session = self.sessions[instance_name]
        if session.guild_id != guild_id:
            return None

        return session

    async def on_voice_state_update(
        self,
        member: "discord.Member",
        before: "discord.VoiceState",
        after: "discord.VoiceState",
    ):
        """Handle voice state updates."""
        try:
            # Check if this affects any of our voice sessions
            for instance_name, session in self.sessions.items():
                if before.channel and before.channel.id == session.channel_id:
                    # User left our channel
                    session.remove_listener(member.id)

                if after.channel and after.channel.id == session.channel_id:
                    # User joined our channel
                    session.add_listener(member.id)

        except Exception as e:
            logger.error(f"Voice state update handling failed: {e}")

    async def on_speaking(self, member: "discord.Member", before: bool, after: bool):
        """Handle speaking state changes."""
        try:
            # Find session for this guild
            guild_id = member.guild.id
            if guild_id not in self.guild_sessions:
                return

            instance_name = self.guild_sessions[guild_id]
            session = self.sessions.get(instance_name)
            if not session:
                return

            if after and not before:
                # Started speaking
                session.is_speaking = True
                session.update_activity()
                await self._emit_event("on_speaking_start", instance_name, member.id)

            elif before and not after:
                # Stopped speaking
                session.is_speaking = False
                session.update_activity()
                await self._emit_event("on_speaking_stop", instance_name, member.id)

        except Exception as e:
            logger.error(f"Speaking event handling failed: {e}")

    async def handle_voice_receive(self, audio_data: bytes, user_id: int, guild_id: int):
        """Handle received voice data."""
        try:
            if guild_id not in self.guild_sessions:
                return

            instance_name = self.guild_sessions[guild_id]
            session = self.sessions.get(instance_name)
            if not session:
                return

            # Add to input buffer
            chunk = AudioChunk(data=audio_data, timestamp=time.time())
            await session.input_buffer.put(chunk)

            # If recording, add to recording data
            if session.recording_state == RecordingState.RECORDING:
                session.add_audio_data(audio_data)

            # Process voice input in background
            asyncio.create_task(self._process_voice_background(audio_data, instance_name, user_id))

            session.update_activity()

        except Exception as e:
            logger.error(f"Voice receive handling failed: {e}")

    async def _process_voice_background(self, audio_data: bytes, instance_name: str, user_id: int):
        """Process voice input in background."""
        try:
            text = await self.process_voice_input(audio_data, instance_name)
            if text.strip():
                logger.info(f"Voice transcription from user {user_id}: {text}")

        except Exception as e:
            logger.error(f"Background voice processing failed: {e}")

    async def _session_cleanup_loop(self):
        """Background cleanup loop for inactive sessions."""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute

                # Find inactive sessions
                inactive_sessions = []
                for instance_name, session in self.sessions.items():
                    if not session.is_active(timeout=300):  # 5 minute timeout
                        inactive_sessions.append(instance_name)

                # Disconnect inactive sessions
                for instance_name in inactive_sessions:
                    logger.info(f"Cleaning up inactive voice session: {instance_name}")
                    await self.disconnect_voice(instance_name)

        except asyncio.CancelledError:
            logger.info("Voice session cleanup task cancelled")
        except Exception as e:
            logger.error(f"Session cleanup loop error: {e}")

    async def shutdown(self):
        """Shutdown voice manager and cleanup resources."""
        try:
            # Cancel cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Disconnect all sessions
            for instance_name in list(self.sessions.keys()):
                await self.disconnect_voice(instance_name)

            logger.info("Voice manager shutdown complete")

        except Exception as e:
            logger.error(f"Voice manager shutdown error: {e}")
