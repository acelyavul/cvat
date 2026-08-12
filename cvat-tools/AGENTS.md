# CVAT Tools Agent Instructions

## Purpose

This project provides tools for inspecting and modifying annotations on the
local self-hosted CVAT v2.66.0 server.

Codex is running inside the CVAT server container.

The tools must support:

- list CVAT tasks
- inspect task details
- inspect labels
- inspect annotations
- inspect annotations by frame
- download task frames
- visualize frames with Pillow
- draw rectangle/bounding-box annotations
- create rectangle annotations
- delete individual annotations
- filtered annotation deletion
- verify writes after modification

Do not modify CVAT core/server source unless explicitly requested.

Use the official CVAT SDK/API.

## Environment

CVAT server version:

    2.66.0

Use Python 3.

Project virtualenv:

    /home/django/data/cvat-tools/.venv

This project directory is stored under the persistent cvat_data Docker volume.

Do not write project files to temporary container paths when they need to
survive container recreation.

## CVAT connection

Codex is running inside cvat_server.

Default local URL:

    http://localhost:8080

Authentication must come from environment variables.

Supported variables:

    CVAT_URL=http://localhost:8080
    CVAT_ACCESS_TOKEN=
    CVAT_USERNAME=
    CVAT_PASSWORD=
    CVAT_ORG=

Never hard-code credentials.

Never print complete access tokens.

Never commit `.env`.

## SDK

The server is CVAT 2.66.0.

Prefer the CVAT SDK matching the server version.

If /home/django/cvat-sdk exists and corresponds to this server version,
prefer using the local SDK source.

Do not blindly install the latest CVAT SDK.

## Dependencies

Use:

- cvat-sdk
- Pillow
- python-dotenv
- typer
- rich
- pytest
- ruff

Do not install OpenCV, torch, ultralytics, transformers, or other heavy
dependencies unless explicitly required.

Use Pillow for image visualization.

## Structure

Keep code organized as:

    src/cvat_tools/client.py
    src/cvat_tools/tasks.py
    src/cvat_tools/annotations.py
    src/cvat_tools/frames.py
    src/cvat_tools/drawing.py
    src/cvat_tools/cli.py

Do not put everything into one Python file.

## Required CLI

Implement commands similar to:

    cvat-tools server status

    cvat-tools tasks list
    cvat-tools tasks show TASK_ID

    cvat-tools annotations list TASK_ID
    cvat-tools annotations list TASK_ID --frame FRAME

    cvat-tools frame get TASK_ID FRAME

    cvat-tools frame render TASK_ID FRAME
    cvat-tools frame render TASK_ID FRAME --output output/frame.jpg

    cvat-tools box add TASK_ID \
        --frame FRAME \
        --label LABEL \
        --x1 X1 \
        --y1 Y1 \
        --x2 X2 \
        --y2 Y2

    cvat-tools annotations delete TASK_ID --id ANNOTATION_ID

## Task listing

Task list should display useful information including:

- task ID
- task name
- status
- size/frame count
- owner when available
- assignee when available
- project ID when available

Read-only commands must never change server state.

## Annotation inspection

Show useful annotation fields:

- ID
- frame
- label ID
- label name
- shape type
- points
- occluded
- outside
- rotation
- source

Resolve label IDs to human readable names.

## Frames

Frames must be retrieved through the CVAT API/SDK.

Use original quality when coordinate accuracy matters.

Downloaded/rendered previews may be cached in:

    .cache/cvat-tools/

Do not modify original task images.

## Pillow rendering

For rectangle annotations interpret CVAT points as:

    [x1, y1, x2, y2]

Draw:

- bounding box
- label name
- annotation ID

Rendered images go to:

    output/

Rendering must be strictly read-only.

## Bounding boxes

Before creating a rectangle validate:

    x1 < x2
    y1 < y2
    x1 >= 0
    y1 >= 0

Check coordinates against image dimensions.

Resolve label name to label ID.

Never guess a label ID.

After creating an annotation:

1. fetch annotations again
2. verify it exists
3. report its annotation ID
4. report frame, label and coordinates

## Deletion safety

Deletion is destructive.

Inspection and deletion are separate operations.

Default deletion behavior must be DRY RUN.

Example:

    cvat-tools annotations delete 42 --id 100

must NOT delete anything.

It should print:

    DRY RUN
    Would delete annotation 100

Actual deletion requires:

    --yes

Example:

    cvat-tools annotations delete 42 --id 100 --yes

Before deletion:

1. fetch current annotations
2. verify annotation exists
3. show task ID
4. show frame
5. show label
6. show type
7. show coordinates

After deletion:

1. retrieve annotations again
2. verify annotation is gone

Never replace all task annotations merely to remove one annotation.

## Bulk deletion

Bulk deletion requires explicit filters.

Possible filters:

    --frame
    --label
    --type

Missing filters must never mean "delete everything".

Bulk deletion requires:

    --yes

Task-wide clearing must be a dedicated explicit command and must never happen
implicitly.

## Tracks

CVAT tracks are different from independent shapes.

Do not treat a tracked shape as a standalone annotation without checking the
parent track.

Identify tracks and keyframes before modifying them.

## Safety

Never automatically:

- delete tasks
- delete projects
- clear all annotations
- modify labels
- modify users
- modify ownership
- change assignees
- expose credentials
- overwrite task annotations

All destructive operations require explicit user intent.

## Testing

Use:

    pytest -q
    ruff check .

Tests must not destructively modify the real CVAT server.

Prefer mocked tests for write/delete operations.

At minimum test:

- bbox validation
- label resolution
- filtering
- deletion selection
- dry-run protection
- rendering coordinates

## Workflow

Before implementing features:

1. inspect existing project files
2. read AGENTS.md
3. verify CVAT connectivity
4. verify SDK/server compatibility
5. make small changes
6. test
7. lint
8. report changed files

Implement read-only operations before destructive operations.

Initial priority:

1. configuration
2. authentication
3. server status
4. task listing
5. task details
6. annotation listing
7. frame retrieval
8. Pillow rendering
9. bbox creation
10. annotation deletion

Do not modify CVAT core code unless explicitly requested.
'''

(root / "AGENTS.md").write_text(agents, encoding="utf-8")

(root / ".env.example").write_text(
"""CVAT_URL=http://localhost:8080
CVAT_ACCESS_TOKEN=
CVAT_USERNAME=
CVAT_PASSWORD=
CVAT_ORG=
""",
encoding="utf-8",
)

(root / ".gitignore").write_text(
""".venv/
.env
**pycache**/
\*.pyc
.pytest_cache/
.ruff_cache/
.cache/
output/
""",
encoding="utf-8",
)

(root / "requirements.txt").write_text(
"""Pillow
python-dotenv
typer
rich
pytest
ruff
""",
encoding="utf-8",
)

(root / "src/cvat_tools/**init**.py").write_text(
'"""CVAT helper tools."""\n',
encoding="utf-8",
)

print("Created:")
for p in sorted(root.rglob("\*")):
print(" ", p)

## Annotation Policy

Before inspecting, creating, modifying, or deleting annotations, read:

    policies/ANNOTATION_POLICY.md

Project labels and their attributes must always be fetched from CVAT through the SDK.
Do not hard-code label IDs or attribute IDs.

## Available CVAT Skills

Use these skills when relevant:

- cvat-tasks: list and inspect CVAT tasks, labels, jobs, and metadata.
- cvat-annotations: inspect, validate, filter, and safely delete annotations.
- cvat-frames: retrieve frames and render annotation previews with Pillow.
- cvat-bbox: validate and create rectangle bounding boxes with label attributes.

Before annotation review or mutation, read:

    policies/ANNOTATION_POLICY.md

Prefer the existing `cvat-tools` CLI instead of writing ad-hoc API scripts.
