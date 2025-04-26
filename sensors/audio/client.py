import socket
import json
import numpy as np
import threading
import queue
from sensors.audio.config import SOCKET_PATH, STREAM_PORT

class AudioClient:
    def __init__(self, socket_path=SOCKET_PATH):
        """Initialize the audio client to connect to the audio service."""
        self.socket_path = socket_path
        self.streaming = False
        self.stream_socket = None
        self.config = None
        self.buffer = queue.Queue(maxsize=100)  # Client-side buffer
        self._stop = threading.Event()
        
        # Get configuration from server
        self.config = self._rpc_call('get_config')
        
    def _rpc_call(self, method, params=None):
        """Make a JSON-RPC call to the audio service."""
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(self.socket_path)
            req = {
                'jsonrpc': '2.0',
                'method': method,
                'params': params or {},
                'id': 1
            }
            sock.send(json.dumps(req).encode('utf-8'))
            resp = json.loads(sock.recv(8192).decode('utf-8'))
            
        if 'error' in resp:
            raise RuntimeError(resp['error']['message'])
        return resp['result']
    
    def start_streaming(self, callback=None):
        """Start streaming audio from the service.
        
        Args:
            callback: Optional function to call with each audio chunk.
                      If not provided, chunks are stored in buffer.
        """
        if self.streaming:
            return
            
        # Connect to streaming server
        self.stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stream_socket.connect(('localhost', STREAM_PORT))
        
        # Read header with audio configuration
        header_len_bytes = self.stream_socket.recv(4)
        header_len = int.from_bytes(header_len_bytes, byteorder='big')
        header_bytes = self.stream_socket.recv(header_len)
        self.config = json.loads(header_bytes.decode('utf-8'))
        
        # Start receiving thread
        self.streaming = True
        self._stop.clear()
        self.stream_thread = threading.Thread(
            target=self._streaming_thread,
            args=(callback,),
            daemon=True
        )
        self.stream_thread.start()
        
        return self.config
    
    def _streaming_thread(self, callback):
        """Thread function for receiving audio chunks."""
        chunk_size = self.config['chunk_size']
        
        try:
            while not self._stop.is_set():
                # Read exactly one chunk
                data = b''
                while len(data) < chunk_size * 2:  # *2 for 16-bit samples
                    packet = self.stream_socket.recv(chunk_size * 2 - len(data))
                    if not packet:
                        # Connection closed
                        return
                    data += packet
                
                # Convert to numpy array if needed
                if callback:
                    # Process data using callback
                    chunk = np.frombuffer(data, dtype=np.int16)
                    callback(chunk, self.config)
                else:
                    # Store in buffer
                    if self.buffer.full():
                        try:
                            self.buffer.get_nowait()  # Remove oldest if buffer is full
                        except queue.Empty:
                            pass
                    try:
                        self.buffer.put_nowait(data)
                    except queue.Full:
                        pass
        except (ConnectionResetError, BrokenPipeError):
            # Connection closed by server
            pass
        finally:
            self.streaming = False
            self.stream_socket.close()
    
    def read(self):
        """Read a single chunk of audio from the buffer.
        
        Returns:
            Audio chunk as bytes or None if buffer is empty
        """
        try:
            data = self.buffer.get_nowait()
            return data
        except queue.Empty:
            return None
            
    def read_as_array(self):
        """Read a single chunk of audio as numpy array.
        
        Returns:
            Audio chunk as numpy array or None if buffer is empty
        """
        data = self.read()
        if data:
            if self.config['format'] == 'int16':
                return np.frombuffer(data, dtype=np.int16)
            elif self.config['format'] == 'int32':
                return np.frombuffer(data, dtype=np.int32)
            elif self.config['format'] == 'float32':
                return np.frombuffer(data, dtype=np.float32)
            else:
                return np.frombuffer(data, dtype=np.int16)
        return None
    
    def stop_streaming(self):
        """Stop the audio streaming."""
        if not self.streaming:
            return
            
        self._stop.set()
        if self.stream_thread:
            self.stream_thread.join(timeout=1.0)
        
        if self.stream_socket:
            self.stream_socket.close()
            self.stream_socket = None
            
        self.streaming = False
        # Clear buffer
        while not self.buffer.empty():
            try:
                self.buffer.get_nowait()
            except queue.Empty:
                break