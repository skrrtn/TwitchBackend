import os
import asyncio
import json
import logging
from typing import Dict, Set, Optional, List, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
import websockets
import aiohttp
from dotenv import load_dotenv


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TwitchUser:
    """Represents a Twitch user with their metadata"""

    username: str
    display_name: str
    user_id: str
    color: Optional[str] = None
    is_subscriber: bool = False
    is_moderator: bool = False
    is_vip: bool = False
    is_broadcaster: bool = False
    badges: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.badges is None:
            self.badges = []


@dataclass
class ChatMessage:
    """Represents a chat message"""

    channel: str
    user: TwitchUser
    message: str
    timestamp: datetime
    message_id: str
    emotes: Dict = field(default_factory=dict)

    def __post_init__(self):
        if self.emotes is None:
            self.emotes = {}

    def to_dict(self):
        return {
            "type": "chat_message",
            "channel": self.channel,
            "user": asdict(self.user),
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
            "emotes": self.emotes,
        }


@dataclass
class TwitchEvent:
    """Represents various Twitch events"""

    event_type: str
    channel: str
    data: Dict
    timestamp: datetime

    def to_dict(self):
        return {
            "type": "twitch_event",
            "event_type": self.event_type,
            "channel": self.channel,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
        }


class TwitchAPI:
    """Handles Twitch API requests"""

    def __init__(self, client_id: str, client_secret: str, access_token: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.base_url = "https://api.twitch.tv/helix"
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Client-Id": self.client_id,
            "Content-Type": "application/json",
        }

    async def get_user_info(self, username: str) -> Optional[Dict]:
        """Get user information from Twitch API"""
        url = f"{self.base_url}/users"
        params = {"login": username}

        try:
            if not self.session:
                raise RuntimeError(
                    "Session is not initialized. Ensure you are using the TwitchAPI instance within an async context manager."
                )
            async with self.session.get(
                url, headers=self._get_headers(), params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["data"][0] if data["data"] else None
                else:
                    logger.error(
                        f"Failed to get user info for {username}: {response.status}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error getting user info for {username}: {e}")
            return None

    async def get_channel_info(self, broadcaster_id: str) -> Optional[Dict]:
        """Get channel information"""
        url = f"{self.base_url}/channels"
        params = {"broadcaster_id": broadcaster_id}

        try:
            if not self.session:
                raise RuntimeError(
                    "Session is not initialized. Ensure you are using the TwitchAPI instance within an async context manager."
                )
            async with self.session.get(
                url, headers=self._get_headers(), params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["data"][0] if data["data"] else None
                else:
                    logger.error(
                        f"Failed to get channel info for {broadcaster_id}: {response.status}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error getting channel info for {broadcaster_id}: {e}")
            return None


class TwitchIRCClient:
    """Handles Twitch IRC connection and message parsing"""

    def __init__(self, nickname: str, token: str, api_client: TwitchAPI):
        self.nickname = nickname
        self.token = token
        self.api_client = api_client
        self.reader = None
        self.writer = None
        self.connected_channels: Set[str] = set()
        self.user_cache: Dict[str, TwitchUser] = {}

        self.on_message: Optional[Any] = None
        self.on_event: Optional[Any] = None

    async def connect(self):
        """Connect to Twitch IRC"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                "irc.chat.twitch.tv", 6667
            )

            await self._send(f"PASS oauth:{self.token}")
            await self._send(f"NICK {self.nickname}")

            await self._send(
                "CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership"
            )

            logger.info("Connected to Twitch IRC")

            asyncio.create_task(self._process_messages())

        except Exception as e:
            logger.error(f"Failed to connect to Twitch IRC: {e}")
            raise

    async def join_channel(self, channel: str):
        """Join a Twitch channel"""
        channel = channel.lower().lstrip("#")
        if channel not in self.connected_channels:
            await self._send(f"JOIN #{channel}")
            self.connected_channels.add(channel)
            logger.info(f"Joined channel: #{channel}")

    async def leave_channel(self, channel: str):
        """Leave a Twitch channel"""
        channel = channel.lower().lstrip("#")
        if channel in self.connected_channels:
            await self._send(f"PART #{channel}")
            self.connected_channels.remove(channel)
            logger.info(f"Left channel: #{channel}")

    async def _send(self, message: str):
        """Send a message to IRC"""
        if self.writer:
            self.writer.write(f"{message}\r\n".encode("utf-8"))
            await self.writer.drain()

    async def _process_messages(self):
        """Process incoming IRC messages"""
        try:
            while self.reader:
                line = await self.reader.readline()
                if not line:
                    break

                message = line.decode("utf-8").strip()
                await self._handle_message(message)

        except Exception as e:
            logger.error(f"Error processing IRC messages: {e}")

    async def _handle_message(self, raw_message: str):
        """Handle individual IRC messages"""
        try:

            if raw_message.startswith("PING"):
                await self._send(f"PONG {raw_message.split()[1]}")
                return

            tags = {}
            if raw_message.startswith("@"):
                tag_part, raw_message = raw_message[1:].split(" ", 1)
                for tag in tag_part.split(";"):
                    if "=" in tag:
                        key, value = tag.split("=", 1)
                        tags[key] = value

            parts = raw_message.split(" ")
            if len(parts) < 3:
                return

            prefix = parts[0] if parts[0].startswith(":") else None
            command = parts[1] if prefix else parts[0]
            params = parts[2:] if prefix else parts[1:]

            if command == "PRIVMSG":
                if prefix is None:
                    prefix = ""
                await self._handle_chat_message(tags, prefix, params)
            elif command == "CLEARCHAT":
                await self._handle_timeout_ban(tags, params)
            elif command == "USERNOTICE":
                await self._handle_user_notice(tags, params)

        except Exception as e:
            logger.error(f"Error handling message '{raw_message}': {e}")

    async def _handle_chat_message(self, tags: Dict, prefix: str, params: List[str]):
        """Handle chat messages"""
        try:
            channel = params[0].lstrip("#")
            message_text = " ".join(params[1:]).lstrip(":")

            username = tags.get("display-name", "").lower()
            if not username and prefix:
                username = prefix.split("!")[0].lstrip(":")

            user = await self._create_user_from_tags(username, tags)

            chat_message = ChatMessage(
                channel=channel,
                user=user,
                message=message_text,
                timestamp=datetime.now(),
                message_id=tags.get("id", ""),
                emotes=self._parse_emotes(tags.get("emotes", "")),
            )

            if self.on_message:
                await self.on_message(chat_message)

        except Exception as e:
            logger.error(f"Error handling chat message: {e}")

    async def _handle_timeout_ban(self, tags: Dict, params: List[str]):
        """Handle timeout/ban events"""
        try:
            channel = params[0].lstrip("#")
            target_user = params[1] if len(params) > 1 else None

            duration = tags.get("ban-duration")

            event_data = {
                "target_user": target_user,
                "duration": duration,
                "reason": tags.get("ban-reason", ""),
            }

            event_type = "timeout" if duration else "ban"

            event = TwitchEvent(
                event_type=event_type,
                channel=channel,
                data=event_data,
                timestamp=datetime.now(),
            )

            if self.on_event:
                await self.on_event(event)

        except Exception as e:
            logger.error(f"Error handling timeout/ban: {e}")

    async def _handle_user_notice(self, tags: Dict, params: List[str]):
        """Handle user notices (subs, bits, raids, etc.)"""
        try:
            channel = params[0].lstrip("#")
            msg_id = tags.get("msg-id", "")

            event_data = {
                "msg_id": msg_id,
                "user": tags.get("display-name", ""),
                "system_msg": tags.get("system-msg", ""),
                "msg_param_cumulative_months": tags.get("msg-param-cumulative-months"),
                "msg_param_streak_months": tags.get("msg-param-streak-months"),
                "msg_param_sub_plan": tags.get("msg-param-sub-plan"),
                "msg_param_sub_plan_name": tags.get("msg-param-sub-plan-name"),
                "msg_param_bits": tags.get("bits"),
                "msg_param_viewer_count": tags.get("msg-param-viewerCount"),
                "msg_param_displayName": tags.get("msg-param-displayName"),
            }

            event_type_map = {
                "sub": "subscription",
                "resub": "subscription",
                "subgift": "subscription",
                "submysterygift": "subscription",
                "raid": "raid",
                "ritual": "ritual",
            }

            event_type = event_type_map.get(msg_id, "user_notice")

            if tags.get("bits"):
                event_type = "bits"
                bits_value = tags.get("bits")
                if bits_value is not None:
                    event_data["bits"] = int(bits_value)

            event = TwitchEvent(
                event_type=event_type,
                channel=channel,
                data=event_data,
                timestamp=datetime.now(),
            )

            if self.on_event:
                await self.on_event(event)

        except Exception as e:
            logger.error(f"Error handling user notice: {e}")

    async def _create_user_from_tags(self, username: str, tags: Dict) -> TwitchUser:
        """Create a TwitchUser object from IRC tags"""

        cache_key = f"{username}_{tags.get('user-id', '')}"
        if cache_key in self.user_cache:
            return self.user_cache[cache_key]

        badges = []
        badge_info = tags.get("badges", "")
        if badge_info:
            badges = [badge.split("/")[0] for badge in badge_info.split(",")]

        user = TwitchUser(
            username=username,
            display_name=tags.get("display-name", username),
            user_id=tags.get("user-id", ""),
            color=tags.get("color"),
            is_subscriber="subscriber" in badges,
            is_moderator="moderator" in badges,
            is_vip="vip" in badges,
            is_broadcaster="broadcaster" in badges,
            badges=badges,
        )

        self.user_cache[cache_key] = user
        return user

    def _parse_emotes(self, emote_string: str) -> Dict:
        """Parse emotes from IRC tags"""
        emotes = {}
        if emote_string:
            for emote in emote_string.split("/"):
                if ":" in emote:
                    emote_id, positions = emote.split(":", 1)
                    emotes[emote_id] = positions.split(",")
        return emotes

    async def disconnect(self):
        """Disconnect from IRC"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        logger.info("Disconnected from Twitch IRC")


class WebSocketManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.connections: Set[Any] = set()
        self.channel_subscriptions: Dict[str, Set[Any]] = {}

    async def register(self, websocket: Any):
        """Register a new WebSocket connection"""
        self.connections.add(websocket)
        logger.info(f"WebSocket connected: {websocket.remote_address}")

    async def unregister(self, websocket: Any):
        """Unregister a WebSocket connection"""
        self.connections.discard(websocket)

        for channel, subscribers in self.channel_subscriptions.items():
            subscribers.discard(websocket)

        logger.info(f"WebSocket disconnected: {websocket.remote_address}")

    async def subscribe_to_channel(self, websocket: Any, channel: str):
        """Subscribe a WebSocket to a specific channel"""
        channel = channel.lower()
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()
        self.channel_subscriptions[channel].add(websocket)
        logger.info(
            f"WebSocket {websocket.remote_address} subscribed to channel: {channel}"
        )

    async def unsubscribe_from_channel(self, websocket: Any, channel: str):
        """Unsubscribe a WebSocket from a specific channel"""
        channel = channel.lower()
        if channel in self.channel_subscriptions:
            self.channel_subscriptions[channel].discard(websocket)
            logger.info(
                f"WebSocket {websocket.remote_address} unsubscribed from channel: {channel}"
            )

    async def broadcast_to_channel(self, channel: str, message: Dict):
        """Broadcast a message to all WebSockets subscribed to a channel"""
        channel = channel.lower()
        if channel in self.channel_subscriptions:
            message_str = json.dumps(message)

            disconnected = set()
            for websocket in self.channel_subscriptions[channel]:
                try:
                    await websocket.send(message_str)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(websocket)
                except Exception as e:
                    logger.error(f"Error sending message to WebSocket: {e}")
                    disconnected.add(websocket)

            for websocket in disconnected:
                await self.unregister(websocket)

    async def broadcast_to_all(self, message: Dict):
        """Broadcast a message to all connected WebSockets"""
        message_str = json.dumps(message)

        disconnected = set()
        for websocket in self.connections.copy():
            try:
                await websocket.send(message_str)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(websocket)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(websocket)

        for websocket in disconnected:
            await self.unregister(websocket)


class TwitchBackend:
    """Main Twitch backend coordinator"""

    def __init__(self):

        client_id_env = os.getenv("TWITCH_CLIENT_ID")
        client_secret_env = os.getenv("TWITCH_CLIENT_SECRET")
        access_token_env = os.getenv("TWITCH_ACCESS_TOKEN")

        if not client_id_env:
            raise ValueError("TWITCH_CLIENT_ID environment variable is required")
        if not client_secret_env:
            raise ValueError("TWITCH_CLIENT_SECRET environment variable is required")
        if not access_token_env:
            raise ValueError("TWITCH_ACCESS_TOKEN environment variable is required")

        self.client_id: str = client_id_env
        self.client_secret: str = client_secret_env
        self.access_token: str = access_token_env
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", 8080))

        self.api_client: Optional[TwitchAPI] = None
        self.irc_client: Optional[TwitchIRCClient] = None
        self.websocket_manager = WebSocketManager()

        self.monitored_channels: Set[str] = set()

    async def initialize(self):
        """Initialize all components"""

        self.api_client = TwitchAPI(
            self.client_id, self.client_secret, self.access_token
        )
        await self.api_client.__aenter__()

        self.irc_client = TwitchIRCClient(
            self.client_id.lower(), self.access_token, self.api_client
        )
        self.irc_client.on_message = self._handle_irc_message
        self.irc_client.on_event = self._handle_irc_event

        await self.irc_client.connect()

        logger.info("Twitch backend initialized")

    async def _handle_irc_message(self, message: ChatMessage):
        """Handle incoming chat messages from IRC and broadcast to WebSockets."""
        if self.websocket_manager:
            await self.websocket_manager.broadcast_to_channel(
                message.channel, message.to_dict()
            )

    async def _handle_irc_event(self, event: TwitchEvent):
        """Handle incoming Twitch events from IRC and broadcast to WebSockets."""
        if self.websocket_manager:
            await self.websocket_manager.broadcast_to_channel(
                event.channel, event.to_dict()
            )

    async def _handle_websocket_connection(self, websocket: Any):
        if self.irc_client is None:
            logger.error(
                f"CRITICAL: _handle_websocket_connection called for {websocket.remote_address} but self.irc_client is None."
            )
            try:
                await websocket.send(
                    json.dumps(
                        {"error": "Internal server error: Core component not ready."}
                    )
                )
                await websocket.close()
            except websockets.exceptions.ConnectionClosed:
                pass
            except Exception as e_ws:
                logger.error(
                    f"Error sending critical error message to WebSocket {websocket.remote_address}: {e_ws}"
                )
            return

        await self.websocket_manager.register(websocket)
        current_ws_channels = set()

        try:
            async for message_str in websocket:
                try:
                    data = json.loads(message_str)
                    command = data.get("command")
                    channel_param = data.get("channel")

                    if command == "join_channel" and channel_param:
                        channel_to_join = channel_param.lower()
                        logger.info(
                            f"WebSocket {websocket.remote_address} requested to join channel {channel_to_join}"
                        )

                        current_ws_channels.add(channel_to_join)

                        await self.websocket_manager.subscribe_to_channel(
                            websocket, channel_to_join
                        )

                        if channel_to_join not in self.monitored_channels:
                            await self.irc_client.join_channel(channel_to_join)
                            self.monitored_channels.add(channel_to_join)
                        await websocket.send(
                            json.dumps(
                                {"status": "joined_channel", "channel": channel_to_join}
                            )
                        )

                    elif command == "leave_channel" and channel_param:
                        channel_to_leave = channel_param.lower()
                        logger.info(
                            f"WebSocket {websocket.remote_address} requested to leave channel {channel_to_leave}"
                        )

                        current_ws_channels.discard(channel_to_leave)

                        await self.websocket_manager.unsubscribe_from_channel(
                            websocket, channel_to_leave
                        )

                        is_channel_still_globally_subscribed = False
                        if (
                            channel_to_leave
                            in self.websocket_manager.channel_subscriptions
                            and self.websocket_manager.channel_subscriptions[
                                channel_to_leave
                            ]
                        ):
                            is_channel_still_globally_subscribed = True

                        if not is_channel_still_globally_subscribed:
                            if channel_to_leave in self.monitored_channels:
                                logger.info(
                                    f"No more WebSocket clients for channel {channel_to_leave}. Leaving IRC channel."
                                )
                                await self.irc_client.leave_channel(channel_to_leave)
                                self.monitored_channels.discard(channel_to_leave)

                        await websocket.send(
                            json.dumps(
                                {"status": "left_channel", "channel": channel_to_leave}
                            )
                        )

                    elif command == "ping":
                        await websocket.send(json.dumps({"type": "pong"}))

                    else:
                        logger.warning(
                            f"Received unknown command from WebSocket {websocket.remote_address}: {data}"
                        )
                        await websocket.send(
                            json.dumps(
                                {
                                    "error": "Unknown command",
                                    "command": data.get("command"),
                                }
                            )
                        )

                except json.JSONDecodeError:
                    logger.error(
                        f"Failed to decode JSON from WebSocket {websocket.remote_address}"
                    )
                    await websocket.send(json.dumps({"error": "Invalid JSON"}))
                except Exception as e_msg_proc:
                    logger.error(
                        f"Error processing WebSocket message from {websocket.remote_address}: {e_msg_proc}"
                    )
                    await websocket.send(
                        json.dumps({"error": "Error processing message"})
                    )

        except websockets.exceptions.ConnectionClosedError:
            logger.info(
                f"WebSocket connection closed by error by remote: {websocket.remote_address}"
            )
        except websockets.exceptions.ConnectionClosedOK:
            logger.info(
                f"WebSocket connection closed gracefully by remote: {websocket.remote_address}"
            )
        except Exception as e_conn:
            logger.error(
                f"WebSocket connection error for {websocket.remote_address}: {e_conn}"
            )
        finally:
            logger.info(f"Cleaning up WebSocket connection: {websocket.remote_address}")
            await self.websocket_manager.unregister(websocket)

            for channel_to_check in current_ws_channels:
                is_channel_still_globally_subscribed = False
                if (
                    channel_to_check in self.websocket_manager.channel_subscriptions
                    and self.websocket_manager.channel_subscriptions[channel_to_check]
                ):
                    is_channel_still_globally_subscribed = True

                if not is_channel_still_globally_subscribed:
                    if channel_to_check in self.monitored_channels:
                        logger.info(
                            f"Last WebSocket client for channel {channel_to_check} disconnected. Leaving IRC channel."
                        )
                        if self.irc_client:
                            await self.irc_client.leave_channel(channel_to_check)
                            self.monitored_channels.discard(channel_to_check)
            logger.info(
                f"Finished cleaning up WebSocket connection: {websocket.remote_address}"
            )

    async def start_websocket_server(self):
        """Starts the WebSocket server."""
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")

        async def handler(websocket):
            try:

                remote_address = (
                    f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
                )
                logger.info(f"New WebSocket connection attempt from {remote_address}")

                await asyncio.wait_for(
                    self._handle_websocket_connection(websocket), timeout=60
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Connection timeout for {getattr(websocket, 'remote_address', 'unknown')}"
                )
                try:
                    await websocket.close(1001, "Connection timeout")
                except Exception:
                    pass
            except websockets.exceptions.InvalidMessage as e:
                logger.error(f"Invalid WebSocket handshake: {e}")
                try:

                    error_response = json.dumps(
                        {"error": "Invalid WebSocket handshake"}
                    )
                    await websocket.send(error_response)
                    await websocket.close(1002, "Invalid WebSocket handshake")
                except Exception:
                    pass
            except websockets.exceptions.ConnectionClosedError as e:
                logger.info(f"Connection closed by client: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error in WebSocket handler: {e}", exc_info=True
                )
                try:
                    await websocket.close(1011, "Internal server error")
                except Exception:
                    pass

        server = await websockets.serve(
            handler,
            self.host,
            self.port,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=10,
            max_size=2**20,
            max_queue=32,
        )

        logger.info(f"WebSocket server is running on {self.host}:{self.port}")

        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            logger.info("WebSocket server shutdown requested")
            server.close()
            await server.wait_closed()
            logger.info("WebSocket server shutdown complete")

    async def run(self):
        """Run the Twitch backend"""
        try:
            self.api_client = TwitchAPI(
                self.client_id, self.client_secret, self.access_token
            )
            async with self.api_client:
                self.irc_client = TwitchIRCClient(
                    nickname=self.client_id.lower(),
                    token=self.access_token,
                    api_client=self.api_client,
                )

                self.irc_client.on_message = self._handle_irc_message
                self.irc_client.on_event = self._handle_irc_event
                await self.irc_client.connect()

                await self.start_websocket_server()
        except Exception as e:
            logger.critical(f"Failed to run Twitch backend: {e}", exc_info=True)
        finally:
            logger.info("Shutting down Twitch backend...")
            if self.irc_client:
                await self.irc_client.disconnect()
            logger.info("Twitch backend shut down.")


if __name__ == "__main__":
    backend = TwitchBackend()
    try:
        asyncio.run(backend.run())
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(
            f"Unhandled exception in main execution block: {e}", exc_info=True
        )
    finally:
        logger.info("Main application process finished.")
