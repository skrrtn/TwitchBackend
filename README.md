# Twitch Backend
A comprehensive Python backend for monitoring Twitch chat and events via IRC, exposing real-time data through WebSocket connections.

## Features
- **Real-time Chat Monitoring**: Connect to multiple Twitch channels simultaneously
- **Rich User Information**: Display user badges (subscriber, moderator, VIP, broadcaster), username colors, and more
- **Event Handling**: Support for subscriptions, bits, timeouts, bans, raids, and other Twitch events
- **Dynamic Channel Management**: Add/remove channels on-the-fly based on frontend requests
- **WebSocket API**: Real-time communication with frontend applications
- **User Caching**: Efficient caching of user information to reduce API calls

## Prerequisites
- Python 3.8+
- Twitch Developer Account with OAuth token
- Valid Twitch API credentials

## Setup

### Linux/macOS Installation

1. **Clone and navigate to the project**:
   ```bash
   cd TwitchBackend
   ```

2. **Install Python and pip**:
   - On Ubuntu/Debian:
     ```bash
     sudo apt update
     sudo apt install python3 python3-pip
     ```
   - On Fedora:
     ```bash
     sudo dnf install python3 python3-pip
     ```
   - On macOS (with Homebrew):
     ```bash
     brew install python
     ```
   - Verify installation:
     ```bash
     python3 --version
     pip3 --version
     ```
   If your system uses `python` and `pip` instead of `python3`/`pip3`, use those commands accordingly.

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Copy the example environment file and update it with your Twitch credentials:
   ```bash
   cp example.env .env
   ```
   Then edit `.env` with your actual credentials:
   ```
   TWITCH_CLIENT_ID=your_client_id
   TWITCH_CLIENT_SECRET=your_client_secret
   TWITCH_ACCESS_TOKEN=your_oauth_token
   HOST=0.0.0.0
   PORT=8080
   ```
5. **Run the backend server**:
   ```bash
   python main.py
   ```

### Windows Installation

1. **Open Command Prompt**: Use `cmd.exe` (recommended) or PowerShell for all commands.
2. **Clone and navigate to the project**:
   ```cmd
   cd TwitchBackend
   ```
3. **Copy the environment file**:
   ```cmd
   copy example.env .env
   ```
   Or in PowerShell:
   ```powershell
   Copy-Item example.env .env
   ```
4. **Edit `.env`**: Open `.env` in Notepad or your preferred editor and enter your Twitch credentials. Make sure to include `TWITCH_CLIENT_SECRET` as well.
5. **Check Python and pip**: Make sure Python 3.8+ and pip are installed and added to your PATH. Check with:
   ```cmd
   python --version
   pip --version
   ```
   If not installed, download Python from [python.org](https://www.python.org/downloads/windows/) and select the option to add Python to PATH during installation.
6. **Install dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```
7. **Run the backend server**:
   ```cmd
   python main.py
   ```

The WebSocket server will start on `ws://localhost:8080` (or your configured host/port).

## How To Get Twitch Credentials

**Option A: Quick Setup (Recommended for testing)**
- Go to [Twitch Token Generator](https://twitchtokengenerator.com/)
- Select "Bot Chat Token"
- Authorize with your Twitch account
- Copy the **Client ID**, **Client Secret**, and **Access Token** (without the `oauth:` prefix) to your `.env` file

**Option B: Manual Setup (For production)**
- Go to the [Twitch Developer Console](https://dev.twitch.tv/console/apps)
- Log in with your Twitch account
- Click "Register Your Application"
- Fill in the required fields:
  - **Name**: Your application name (e.g., "My Twitch Chat Bot")
  - **OAuth Redirect URLs**: `http://localhost` (or your domain)
  - **Category**: Select appropriate category
- Click "Create"
- Copy the **Client ID** and **Client Secret** from your application page
- Generate an OAuth token:
  - Use the [Twitch Token Generator](https://twitchtokengenerator.com/) with your Client ID and Client Secret
  - Or use the OAuth flow: `https://id.twitch.tv/oauth2/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost&response_type=token&scope=chat:read`
- Copy all credentials to your `.env` file

## Testing with the HTML Client
1. Navigate to the examples directory and serve `client01.html` with a local web server:
   ```bash
   cd examples
   python -m http.server 8000
   ```
   Then open http://localhost:8000/client01.html in your browser, or open `examples/client01.html` directly in your browser.
2. The application will automatically connect to the WebSocket server
3. Click "Channels" in the top bar to manage channel subscriptions
4. Enter a Twitch channel name (without #) and click "Add Channel"
5. Watch real-time chat messages and events appear

## WebSocket API
The WebSocket server provides a real-time API for monitoring Twitch chat and events. Connect to `ws://localhost:8080` (or your configured host/port).

### Client → Server Messages
All messages must be sent as JSON objects with the following structure:

#### 1. Join Channel
Subscribe to a Twitch channel to receive chat messages and events.

**Request:**
```json
{
  "command": "join_channel",
  "channel": "ninja"
}
```

**Response:**
```json
{
  "status": "joined_channel",
  "channel": "ninja"
}
```

#### 2. Leave Channel
Unsubscribe from a Twitch channel.

**Request:**
```json
{
  "command": "leave_channel",
  "channel": "ninja"
}
```

**Response:**
```json
{
  "status": "left_channel",
  "channel": "ninja"
}
```

#### 3. Ping
Keep the connection alive and test connectivity.

**Request:**
```json
{
  "command": "ping"
}
```

**Response:**
```json
{
  "type": "pong"
}
```

### Server → Client Messages
The server sends various types of messages to subscribed clients:

#### 1. Chat Messages
Real-time chat messages from Twitch channels.

```json
{
  "type": "chat_message",
  "channel": "ninja",
  "user": {
    "username": "viewer123",
    "display_name": "Viewer123",
    "user_id": "123456789",
    "color": "#FF69B4",
    "is_subscriber": true,
    "is_moderator": false,
    "is_vip": false,
    "is_broadcaster": false,
    "badges": ["subscriber/12", "premium/1"]
  },
  "message": "Hello chat!",
  "timestamp": "2025-06-10T15:30:45.123456",
  "message_id": "abc123-def456",
  "emotes": {
    "25": ["0-4"],
    "1902": ["6-10"]
  }
}
```

#### 2. Twitch Events
Various Twitch events like subscriptions, bits, timeouts, bans, and raids.

**Subscription Event:**
```json
{
  "type": "twitch_event",
  "event_type": "subscription",
  "channel": "ninja",
  "data": {
    "msg_id": "sub",
    "user": "NewSubscriber",
    "system_msg": "NewSubscriber subscribed at Tier 1!",
    "msg_param_cumulative_months": "1",
    "msg_param_sub_plan": "1000",
    "msg_param_sub_plan_name": "Channel Subscription (ninja)"
  },
  "timestamp": "2025-06-10T15:30:45.123456"
}
```

**Bits Event:**
```json
{
  "type": "twitch_event",
  "event_type": "bits",
  "channel": "ninja",
  "data": {
    "user": "BitDonator",
    "bits": 100,
    "system_msg": "BitDonator cheered 100 bits!"
  },
  "timestamp": "2025-06-10T15:30:45.123456"
}
```

**Timeout Event:**
```json
{
  "type": "twitch_event",
  "event_type": "timeout",
  "channel": "ninja",
  "data": {
    "target_user": "BadUser",
    "duration": "600",
    "reason": "Spam"
  },
  "timestamp": "2025-06-10T15:30:45.123456"
}
```

**Ban Event:**
```json
{
  "type": "twitch_event",
  "event_type": "ban",
  "channel": "ninja",
  "data": {
    "target_user": "BannedUser",
    "reason": "Harassment"
  },
  "timestamp": "2025-06-10T15:30:45.123456"
}
```

**Raid Event:**
```json
{
  "type": "twitch_event",
  "event_type": "raid",
  "channel": "ninja",
  "data": {
    "msg_param_displayName": "RaidingStreamer",
    "msg_param_viewer_count": "1234",
    "system_msg": "RaidingStreamer is raiding with 1234 viewers!"
  },
  "timestamp": "2025-06-10T15:30:45.123456"
}
```

#### 3. Error Messages
Error responses for invalid requests or server issues.

```json
{
  "error": "Unknown command",
  "command": "invalid_command"
}
```

```json
{
  "error": "Invalid JSON"
}
```

### Connection Management
- **Automatic Channel Management**: When the first client subscribes to a channel, the backend automatically joins that Twitch IRC channel. When the last client unsubscribes, the backend leaves the IRC channel.
- **Connection Keep-Alive**: Send periodic ping messages (every 30 seconds recommended) to maintain the connection.
- **Reconnection**: Implement client-side reconnection logic with exponential backoff for production use.

### Example JavaScript Client

```javascript
const socket = new WebSocket('ws://localhost:8080');

socket.onopen = function() {
    console.log('Connected to Twitch backend');
    
    // Join a channel
    socket.send(JSON.stringify({
        command: 'join_channel',
        channel: 'ninja'
    }));
};

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case 'chat_message':
            console.log(`[${data.channel}] ${data.user.display_name}: ${data.message}`);
            break;
        case 'twitch_event':
            console.log(`Event in ${data.channel}: ${data.event_type}`, data.data);
            break;
        case 'pong':
            console.log('Ping successful');
            break;
        default:
            if (data.status) {
                console.log('Status:', data.status, data.channel);
            } else if (data.error) {
                console.error('Error:', data.error);
            }
    }
};

// Keep connection alive
setInterval(() => {
    if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ command: 'ping' }));
    }
}, 30000);
```



## Supported Events
The backend monitors and processes the following Twitch events:

- **Chat Messages**: Regular chat messages with full user information including badges, colors, and emotes
- **Subscriptions**: New subscriptions, resubscriptions, and gift subscriptions with tier information
- **Bits**: Bit donations/cheering with bit amounts and user information
- **Timeouts**: User timeouts with duration and reason
- **Bans**: User bans with target user and reason
- **Raids**: Incoming raids from other channels with viewer count
- **User Notices**: Various other user-generated events and system messages
- **Ritual Events**: First-time chat participation and other ritual events


## Architecture
The backend consists of several key components working together:

- **TwitchAPI**: Handles Twitch Helix API requests for user and channel information with automatic session management
- **TwitchIRCClient**: Manages IRC connection to `irc.chat.twitch.tv`, parses IRC messages, and handles Twitch-specific IRC capabilities
- **WebSocketManager**: Manages WebSocket connections, channel subscriptions, and message broadcasting to clients
- **TwitchBackend**: Main coordinator that initializes components and handles the application lifecycle
- **User Caching**: Efficient in-memory caching system to reduce API calls and improve performance

### Data Flow
1. **IRC Connection**: Backend connects to Twitch IRC servers with OAuth authentication
2. **Channel Management**: WebSocket clients request to join/leave channels
3. **Message Processing**: IRC messages are parsed and converted to structured data
4. **Broadcasting**: Processed messages are broadcast to subscribed WebSocket clients
5. **Dynamic Scaling**: Channels are automatically joined/left based on client interest

## User Information
The backend captures and provides comprehensive user information for each chat message:

### User Data Structure
```json
{
  "username": "viewer123",
  "display_name": "Viewer123", 
  "user_id": "123456789",
  "color": "#FF69B4",
  "is_subscriber": true,
  "is_moderator": false,
  "is_vip": false,
  "is_broadcaster": false,
  "badges": ["subscriber/12", "moderator/1", "premium/1"]
}
```

### Badge Types Supported
- **Subscriber badges**: All tier levels (1, 2, 3) with month counts
- **Moderator badges**: Channel moderator status
- **VIP badges**: Channel VIP status  
- **Broadcaster badges**: Channel owner/broadcaster status
- **Premium badges**: Twitch Prime/Nitro subscribers
- **Bit badges**: Based on total bits cheered in channel
- **Founder badges**: Early supporters of the channel
- **Custom badges**: Channel-specific subscriber badges

### User Caching
- Automatic caching of user information to reduce API calls
- Cache key based on username and user ID combination
- Improves performance for active chatters
- Cache invalidation handled automatically

## Dynamic Channel Management
Channels are joined/left automatically based on WebSocket subscriptions:
- When the first client subscribes to a channel, the bot joins that IRC channel
- When the last client unsubscribes, the bot leaves the IRC channel
- No manual channel management required

## Error Handling
The backend implements comprehensive error handling and resilience features:

### IRC Connection Management
- **Automatic reconnection** for IRC disconnections with exponential backoff
- **Graceful handling** of network interruptions and timeouts
- **Connection state monitoring** with automatic recovery attempts

### WebSocket Management  
- **Connection cleanup** on client disconnect with proper resource deallocation
- **Message validation** with JSON parsing error handling
- **Broadcast failure recovery** with automatic client cleanup for dead connections

### API Rate Limiting
- **Twitch API rate limit** handling with proper error responses
- **Request queuing** and retry mechanisms for failed API calls
- **Fallback mechanisms** when API data is unavailable

### Logging and Monitoring
- **Comprehensive logging** at multiple levels (INFO, WARNING, ERROR, CRITICAL)
- **Structured error messages** with context for debugging
- **Performance monitoring** for message processing and API calls
- **Connection statistics** tracking for operational insights

### Production Considerations
- **Environment variable validation** with clear error messages for missing credentials
- **Graceful shutdown** handling for SIGINT/SIGTERM signals
- **Resource cleanup** on application termination
- **Error propagation** with proper exception handling throughout the stack

## Troubleshooting

### Common Issues

**WebSocket Connection Failed**
- Verify the backend is running on the correct port (8080 by default)
- Check firewall settings and port availability
- Ensure no other applications are using the same port

**IRC Authentication Failed**
- Verify your `TWITCH_ACCESS_TOKEN` is valid and not expired
- Ensure the token has the correct scopes (chat:read)
- Check that `TWITCH_CLIENT_ID` matches the application that generated the token

**Channel Join Failed**
- Verify the channel name is correct (without # prefix)
- Ensure the channel exists and is currently live or has recent activity
- Check that your bot account is not banned from the channel

**Missing Chat Messages**
- Verify you're subscribed to the correct channel via WebSocket
- Check the browser console for JavaScript errors
- Ensure the IRC connection is stable (check backend logs)

### Debug Mode
Enable detailed logging by modifying the logging level in `main.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Performance Optimization
For high-traffic channels:
- Increase the `maxMessages` limit in the HTML client
- Consider implementing message filtering on the client side
- Monitor memory usage and implement message cleanup strategies

## Contributing
We welcome contributions to improve the Twitch Backend! Here's how you can help:

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes with proper testing
4. Add tests if applicable
5. Update documentation as needed
6. Submit a pull request with a clear description

### Code Style
- Follow PEP 8 for Python code formatting
- Use type hints for function parameters and return values
- Include docstrings for all classes and functions
- Write descriptive commit messages

### Testing
- Test your changes with multiple Twitch channels
- Verify WebSocket connections work properly
- Check error handling paths
- Test with different types of Twitch events

## License
This project is open source and available under the [MIT License](https://opensource.org/licenses/MIT).

### MIT License

Copyright (c) 2025 Twitch Backend Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
