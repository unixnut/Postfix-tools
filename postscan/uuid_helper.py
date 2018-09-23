import uuid


class UUIDs(object):
    uuids = []

    def create(self):
        u = uuid.uuid4()
        self.uuids.append(u)
        return u

    def pop(self):
        u = self.uuids[0]
        del self.uuids[0]
        return u

    def peek(self):
        return self.uuids[0]

    def empty(self):
        return len(self.uuids) == 0
