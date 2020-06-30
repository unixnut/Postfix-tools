import uuid


class UUIDs(object):
    """A FIFO queue (stack) of auto-generated UUID strings."""
    uuids = []

    def create(self):
        u = str(uuid.uuid4())
        self.uuids.append(u)
        return u


    def pop(self, target_uuid=None):
        """Pop either the first element, or the specified one if present."""

        for index, uuid in enumerate(self.uuids):
            if self.uuids[index] == target_uuid:
                target_index = index
                break
        else:
            target_index = 0

        u = self.uuids[target_index]
        del self.uuids[target_index]
        return u


    def peek(self, index=0):
        return self.uuids[index]


    def empty(self):
        return len(self.uuids) == 0
