"""Scene Splitter — tách truyện thành scenes.

Adapted from TTS_Voice_AndyLe-001 story maker scene splitting logic.
"""

import re
from dataclasses import dataclass


@dataclass
class Scene:
    """A single scene in a story."""
    id: int
    narration: str
    media_path: str = ""
    duration: float = 0.0
    transition: str = "fade"
    ken_burns: str = ""


def split_into_scenes(text: str) -> list[Scene]:
    """Split story text into scenes based on markers.

    Supported markers:
    - [SCENE 1], [SCENE 2], ...
    - Chương 1, Chương 2, ...
    - Scene 1:, Scene 2:, ...
    - --- (separator)
    """
    # Try [SCENE X] pattern first
    pattern = r'\[SCENE\s+(\d+)\]'
    parts = re.split(pattern, text, flags=re.IGNORECASE)

    scenes = []

    if len(parts) >= 3:
        # First part is preamble
        if parts[0].strip():
            scenes.append(Scene(id=0, narration=parts[0].strip()))

        for i in range(1, len(parts) - 1, 2):
            scene_id = int(parts[i])
            narration = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if narration:
                scenes.append(Scene(id=scene_id, narration=narration))

        if scenes:
            return scenes

    # Try chapter pattern
    chapter_pattern = r'(?:Chương|Chapter|Scene)\s+(\d+)[:\s]*'
    parts = re.split(chapter_pattern, text, flags=re.IGNORECASE)

    if len(parts) >= 3:
        if parts[0].strip():
            scenes.append(Scene(id=0, narration=parts[0].strip()))

        for i in range(1, len(parts) - 1, 2):
            scene_id = int(parts[i])
            narration = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if narration:
                scenes.append(Scene(id=scene_id, narration=narration))

        if scenes:
            return scenes

    # Try separator pattern (---)
    parts = re.split(r'\n---+\n', text)
    if len(parts) >= 2:
        for i, part in enumerate(parts):
            if part.strip():
                scenes.append(Scene(id=i + 1, narration=part.strip()))
        return scenes

    # Fallback: split into paragraphs of ~200 words
    paragraphs = text.split('\n\n')
    current = ""
    scene_id = 0

    for para in paragraphs:
        current = (current + "\n\n" + para).strip()
        words = len(current.split())
        if words >= 200:
            scene_id += 1
            scenes.append(Scene(id=scene_id, narration=current))
            current = ""

    if current.strip():
        scene_id += 1
        scenes.append(Scene(id=scene_id, narration=current))

    return scenes if scenes else [Scene(id=1, narration=text.strip())]


def sync_scenes_from_text(scenes: list[Scene], edited_text: str) -> list[Scene]:
    """Re-sync scenes after text has been edited."""
    new_scenes = split_into_scenes(edited_text)

    # Preserve media paths and other settings from original scenes
    for new_scene in new_scenes:
        for old_scene in scenes:
            if old_scene.id == new_scene.id:
                new_scene.media_path = old_scene.media_path
                new_scene.transition = old_scene.transition
                new_scene.ken_burns = old_scene.ken_burns
                break

    return new_scenes
