---
name: cvat-tasks
description: List and inspect CVAT tasks, labels, attributes and task metadata.
---

# CVAT Tasks

Use the existing `cvat-tools` CLI.

Read-only operations:

    cvat-tools status
    cvat-tools tasks list
    cvat-tools tasks show TASK_ID
    cvat-tools labels show TASK_ID

Always fetch current labels and attribute specs from CVAT.
Never guess label IDs, attribute IDs or task IDs.
