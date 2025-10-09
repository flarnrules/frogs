from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

@dataclass
class ProjectContext:
    name: str
    projects_root: Path
    out_root: Path
    explicit_png: str | None
    explicit_layers: str | None
    config: Dict[str, Any]

class Project:
    def default_config(self) -> Dict[str, Any]:
        return {}

    def config(self) -> Dict[str, Any]:
        return {}

    def resolve_input(self, ctx: ProjectContext):
        raise NotImplementedError

    @staticmethod
    def parse_hex_color(s: str | None):
        if not s:
            return None
        t = s.strip().lstrip("#")
        if len(t) == 3:
            t = "".join(ch * 2 for ch in t)
        if len(t) != 6:
            raise ValueError("bg color must be 3 or 6 hex digits")
        return (int(t[0:2], 16), int(t[2:4], 16), int(t[4:6], 16))

    # safe default: projects don't have to implement postbuild
    def postbuild(self, ctx: ProjectContext, model: Dict[str, Any], out_dir: Path) -> Dict[str, str]:
        return {}

def merge_configs(*objs: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for o in objs:
        for k, v in (o or {}).items():
            out[k] = v
    return out
