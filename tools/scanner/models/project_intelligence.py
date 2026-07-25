from dataclasses import dataclass, field

@dataclass(slots=True)
class ProjectIntelligence:

    completed_features: list[str] = field(default_factory=list)

    in_progress_features: list[str] = field(default_factory=list)

    missing_features: list[str] = field(default_factory=list)

    duplicate_files: list[str] = field(default_factory=list)

    orphan_files: list[str] = field(default_factory=list)

    recommendations: list[str] = field(default_factory=list)