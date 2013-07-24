import os
import tempfile


class Channel(object):
    def __init__(self, server, name):
        self.server = server
        self.name = name
        self.members = set()
        self._topic = ""
        self._key = None
        if self.server.statedir:
            self._state_path = "%s/%s" % (
                self.server.statedir,
                name.replace("_", "__").replace("/", "_"))
            self._read_state()
        else:
            self._state_path = None

    def add_member(self, client):
        self.members.add(client)

    def get_topic(self):
        return self._topic

    def set_topic(self, value):
        self._topic = value
        self._write_state()

    topic = property(get_topic, set_topic)

    def get_key(self):
        return self._key

    def set_key(self, value):
        self._key = value
        self._write_state()

    key = property(get_key, set_key)

    def remove_client(self, client):
        self.members.discard(client)
        if not self.members:
            self.server.remove_channel(self)

    def _read_state(self):
        if not (self._state_path and os.path.exists(self._state_path)):
            return
        data = {}
        exec(open(self._state_path), {}, data)
        self._topic = data.get("topic", "")
        self._key = data.get("key")

    def _write_state(self):
        if not self._state_path:
            return
        (fd, path) = tempfile.mkstemp(dir=os.path.dirname(self._state_path))
        fp = os.fdopen(fd, "w")
        fp.write("topic = %r\n" % self.topic)
        fp.write("key = %r\n" % self.key)
        fp.close()
        os.rename(path, self._state_path)


