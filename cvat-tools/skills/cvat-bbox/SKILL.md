---
name: cvat-bbox
description: Create and correct CVAT rectangle bounding boxes with label attributes.
---

# CVAT Bounding Boxes

Before bbox operations read:

    /home/django/cvat-tools/policies/ANNOTATION_POLICY.md

Before creating or correcting a box:

1. inspect the frame
2. inspect current annotations
3. inspect current label attributes
4. follow the annotation policy
5. validate coordinates against frame dimensions

BBox creation is available through:

    cvat-tools box add

BBox correction is available through:

    cvat-tools annotations update

For the `tire` label the current CVAT attribute specs include:
- is_crowd
- sidewall_only

Do not hard-code their numeric spec IDs.
Resolve them dynamically from CVAT.

Never invent bbox coordinates without visually inspecting the frame.
Never mutate real annotations merely for testing.
