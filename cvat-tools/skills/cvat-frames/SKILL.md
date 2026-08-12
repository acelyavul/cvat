---
name: cvat-frames
description: Retrieve CVAT frames and create visual annotation review packets.
---

# CVAT Frames and Review

Read-only operations:

    cvat-tools frame get TASK_ID FRAME
    cvat-tools frame render TASK_ID FRAME

Review operations:

    cvat-tools review frame TASK_ID FRAME
    cvat-tools review task TASK_ID
    cvat-tools review annotation TASK_ID --id ANNOTATION_ID

For visual annotation review prefer `review annotation` or `review frame`.

Review packets contain:
- original image
- annotated image or crop
- annotation metadata
- label attributes
- annotation policy

Use Pillow-generated images only as review artifacts.
Do not alter CVAT data while reviewing.
