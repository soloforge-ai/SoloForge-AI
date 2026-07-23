from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class InventoryItem:
    path: str
    name: str
    extension: str
    language: str
    category: str

    classes: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    enums: list[str] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)