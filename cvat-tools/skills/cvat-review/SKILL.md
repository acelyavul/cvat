---
name: cvat-review
description: End-to-end CVAT annotation review workflow using task metadata, frames, annotation crops, policy rules, validation, and safe mutation tools.
---

# CVAT Annotation Review Workflow

Always read:

    /home/django/cvat-tools/policies/ANNOTATION_POLICY.md

Use the existing `cvat-tools` CLI. Do not create ad-hoc CVAT scripts when an
existing command can perform the operation.

## Workflow

When asked to inspect or correct a CVAT task:

1. Inspect the task and current schema.
2. Fetch labels and attribute specifications from CVAT.
3. Validate annotation structure.
4. Build task/frame/annotation review artifacts as needed.
5. Inspect the actual image before judging geometry.
6. Apply ANNOTATION_POLICY.md.
7. Record findings as PASS, REVIEW, or FAIL.
8. Only mutate CVAT if the user explicitly requested the change.
9. Re-fetch and verify every mutation.

## Read-only tools

Use:

    cvat-tools tasks list
    cvat-tools tasks show TASK_ID
    cvat-tools labels show TASK_ID

    cvat-tools annotations list TASK_ID
    cvat-tools annotations validate TASK_ID

    cvat-tools review task TASK_ID
    cvat-tools review frame TASK_ID FRAME
    cvat-tools review annotation TASK_ID --id ANNOTATION_ID

    cvat-tools frame get TASK_ID FRAME
    cvat-tools frame render TASK_ID FRAME

## Annotation decisions

A review decision must be based on both:

- visual evidence from the image
- ANNOTATION_POLICY.md

Do not mark an annotation incorrect solely from coordinates or metadata when
the decision requires visual interpretation.

Statuses:

- PASS: annotation complies with policy
- REVIEW: uncertain or requires human judgment
- FAIL: clear policy violation

## Tire attributes

Never hard-code numeric attribute IDs.

Resolve current attributes from CVAT.

For tire annotations currently expect semantic fields such as:

- is_crowd
- sidewall_only

Judge their values from the image and annotation policy.

## Mutations

Available mutation tools include:

- bbox creation
- standalone rectangle update
- standalone shape deletion
- filtered standalone shape deletion

Deletion and update commands default to dry-run where implemented.

Never add `--yes` unless the user has explicitly authorized the actual change.

Never:
- clear a whole task implicitly
- guess coordinates
- guess labels
- guess attribute IDs
- treat a track as a standalone shape
- change real annotations merely to test tooling

## Visual bbox correction

When correcting a bounding box:

1. inspect the frame or annotation crop
2. identify the visible object boundary
3. follow policy rules for occlusion/truncation/crowd/sidewall cases
4. determine corrected coordinates
5. dry-run the update
6. show the proposed before/after state
7. perform the actual update only with explicit authorization
8. re-render the frame and verify visually

## Privacy regions

The task may contain the polygon label `privacy_region`.

For privacy review:

- inspect the full-resolution frame
- identify every identifiable face and legible registration plate
- follow `ANNOTATION_POLICY.md` exactly
- existing privacy polygons are visible in rendered review images
- use `cvat-tools polygon review` to inspect one existing polygon
- use `cvat-tools polygon add` for a missing privacy region
- use `cvat-tools polygon update` to correct polygon vertices
- standalone privacy polygons can be deleted with the annotation deletion tool

For faces:

- cover the complete identifiable face
- extend the polygon a few pixels beyond every edge

For plates:

- cover enough of the identifying character sequence that the complete
  registration cannot be recognised or reconstructed
- include a small margin around the covered characters
- covering the whole physical plate is not required

There is no minimum frame-proportion threshold for privacy regions.

`privacy_region` is an assembly instruction. CVAT does not modify source
pixels when the polygon is created.

Never infer polygon coordinates from metadata alone.
Inspect the actual full-resolution image before creating or changing vertices.

After any privacy polygon mutation:

1. re-fetch the annotation from CVAT
2. render the frame again
3. visually verify that coverage follows `ANNOTATION_POLICY.md`

