class ShortMemory:
    def __init__(self, max_items: int = 20) -> None:
        self.max_items = max_items
        self.items = []

    def push(self, item: dict) -> None:
        self.items.append(item)
        if len(self.items) > self.max_items:
            self.items.pop(0)

    def dump(self):
        return list(self.items)
