import pyaudio
import numpy as np
import threading
import socket
import json
import time
import queue
import logging
from datetime import datetime
from sensors.audio.config import *

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AudioService')

class AudioService:
    def __init__(self):
        """Initialize the audio service with a microphone stream and buffer."""
        # Initialize PyAudio
        self.p = pyaudio.PyAudio()
        
        # Set up format based on config
        if FORMAT == 'int16':
            self.format = pyaudio.paInt16
        elif FORMAT == 'int32':
            self.format = pyaudio.paInt32
        elif FORMAT == 'float32':
            self.format = pyaudio.paFloat32
        else:
            self.format = pyaudio.paInt16  # Default
        
        # Create a ring buffer to store recent audio chunks
        self.buffer = queue.Queue(maxsize=MAX_BUFFER_SIZE)
        
        # Set up connections for clients
        self.clients = []
        self.client_lock = threading.Lock()
        
        # For stopping the service
        self._stop = threading.Event()
        
        # Start the microphone stream
        self.stream = self.p.open(
            format=self.format,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self._audio_callback
        )
        
        # Start the JSON-RPC listener for control commands
        threading.Thread(target=self._start_rpc, daemon=True).start()
        
        # Start TCP server for streaming audio
        threading.Thread(target=self._start_stream_server, daemon=True).start()
        
        logger.info("Audio service started")

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Callback function for PyAudio stream that receives audio chunks."""
        # Add to buffer (with overflow protection)
        if self.buffer.full():
            try:
                self.buffer.get_nowait()  # Remove oldest item if buffer is full
            except queue.Empty:
                pass
        
        try:
            self.buffer.put_nowait(in_data)
        except queue.Full:
            pass
            
        # Send to all connected clients
        with self.client_lock:
            disconnected_clients = []
            for client in self.clients:
                try:
                    client.send(in_data)
                except (BrokenPipeError, ConnectionResetError):
                    disconnected_clients.append(client)
            
            # Clean up disconnected clients
            for client in disconnected_clients:
                self.clients.remove(client)
                
        return (None, pyaudio.paContinue)

    def _start_rpc(self):
        """Start a Unix socket for JSON-RPC control commands."""
        # Clean up old socket if it exists
        try:
            import os
            os.unlink(SOCKET_PATH)
        except OSError:
            pass
            
        # Create and bind the socket
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o660)  # audio group
        srv.listen()
        
        while not self._stop.is_set():
            try:
                conn, _ = srv.accept()
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except OSError:
                # Socket closed
                break
                
    def _handle_client(self, conn):
        """Handle RPC commands from clients."""
        data = conn.recv(4096).decode('utf-8')
        try:
            req = json.loads(data)
            method = req.get('method')
            params = req.get('params', {})
            rid = req.get('id', None)
            
            if method == 'get_config':
                # Return current audio configuration
                result = {
                    'sample_rate': SAMPLE_RATE,
                    'channels': CHANNELS,
                    'format': FORMAT,
                    'chunk_size': CHUNK_SIZE,
                    'stream_port': STREAM_PORT
                }
                resp = {'jsonrpc': '2.0', 'result': result, 'id': rid}
                
            elif method == 'start_stream':
                # Connect to streaming server
                resp = {
                    'jsonrpc': '2.0', 
                    'result': {'port': STREAM_PORT}, 
                    'id': rid
                }
                
            else:
                resp = {
                    'jsonrpc': '2.0',
                    'error': {'code': -32601, 'message': 'Method not found'},
                    'id': rid
                }
                
        except Exception as e:
            resp = {
                'jsonrpc': '2.0',
                'error': {'code': -32000, 'message': str(e)},
                'id': None
            }
            
        conn.send(json.dumps(resp).encode('utf-8'))
        conn.close()

    def _start_stream_server(self):
        """Start a TCP server for streaming audio data."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', STREAM_PORT))
        server.listen(5)
        
        logger.info(f"Audio streaming server started on port {STREAM_PORT}")
        
        while not self._stop.is_set():
            try:
                server.settimeout(0.5)  # Allow checking for stop every 0.5 seconds
                client, addr = server.accept()
                logger.info(f"Client connected from {addr}")
                
                # Send audio configuration as header
                config = {
                    'sample_rate': SAMPLE_RATE,
                    'channels': CHANNELS,
                    'format': FORMAT,
                    'chunk_size': CHUNK_SIZE
                }
                header = json.dumps(config).encode('utf-8')
                header_len = len(header).to_bytes(4, byteorder='big')
                client.send(header_len + header)
                
                # Add to client list for streaming
                with self.client_lock:
                    self.clients.append(client)
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error in stream server: {e}")
                
        server.close()

    def get_buffer_snapshot(self):
        """Get a copy of the current audio buffer content."""
        chunks = list(self.buffer.queue)
        return b''.join(chunks)
    
    def stop(self):
        """Stop all services cleanly."""
        logger.info("Stopping audio service...")
        self._stop.set()
        
        # Stop the streaming
        self.stream.stop_stream()
        self.stream.close()
        
        # Close all client connections
        with self.client_lock:
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.clients = []
            
        # Clean up PyAudio
        self.p.terminate()
        
        # Clean up socket
        try:
            import os
            os.unlink(SOCKET_PATH)
        except:
            pass
            
        logger.info("Audio service stopped")

if __name__ == "__main__":
    # Run the service standalone
    svc = AudioService()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        svc.stop()