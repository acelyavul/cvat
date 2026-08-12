---
name: cvat-annotations
description: Inspect, validate, update and safely delete CVAT annotations.
---

# CVAT Annotations

Before annotation work read:

    /home/django/cvat-tools/policies/ANNOTATION_POLICY.md

Available operations:

    cvat-tools annotations list TASK_ID
    cvat-tools annotations list TASK_ID --frame FRAME
    cvat-tools annotations validate TASK_ID
    cvat-tools annotations validate TASK_ID --frame FRAME

Mutation commands are dry-run unless --yes:

    cvat-tools annotations update ...
    cvat-tools annotations delete ...
    cvat-tools annotations delete-filtered ...

Rules:

- inspect before changing
- never use --yes unless the user explicitly requested the mutation
- never silently clear a task
- never treat tracks as standalone shapes
- re-fetch and verify every mutation
- preserve existing attributes unless explicitly changing them
