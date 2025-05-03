import redis
import json

class SpeakerClient:
    def __init__(self, url='redis://localhost'):
        self.r = redis.from_url(url)

    def play_file(self, path):
        """Instruct the service to play an audio file from disk."""
        msg = json.dumps({'action': 'play_file', 'path': path})
        self.r.publish('audio:cmd', msg)

    def enqueue_raw(self, pcm_bytes):
        """Push raw PCM bytes into the playback stream."""
        self.r.xadd('audio:stream', {'data': pcm_bytes})

    def stop(self):
        """Stop decoding and clear the stream."""
        msg = json.dumps({'action': 'stop'})
        self.r.publish('audio:cmd', msg)

    def status(self):
        """Get current playback state."""
        state = self.r.hgetall('audio:state')
        return {k.decode(): v.decode() for k, v in state.items()}