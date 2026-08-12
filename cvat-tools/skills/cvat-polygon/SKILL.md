---
name: cvat-polygon
description: Inspect, create and correct CVAT polygon annotations, especially privacy_region face and plate redactions.
---

# CVAT Polygon Annotation

Before polygon work read:

    /home/django/cvat-tools/policies/ANNOTATION_POLICY.md

Use the live CVAT label schema. Never hard-code label IDs.

The `privacy_region` label is a polygon annotation used as an assembly
instruction. CVAT itself does not redact source pixels.

For identifiable faces:
- cover the complete identifiable face
- extend coverage a few pixels beyond every edge

For legible plates:
- cover enough of the identifying character sequence that the complete
  registration cannot be recognised or reconstructed
- use a small margin around the covered characters
- covering the whole physical plate is not required

Privacy regions are required regardless of their proportion of the frame.

Available tools:

    cvat-tools polygon add
    cvat-tools polygon update
    cvat-tools polygon review

Polygon mutations are dry-run unless --yes is explicitly supplied.

Before drawing or changing a privacy polygon:
1. inspect the full-resolution frame
2. determine whether the target is an identifiable face or legible plate
3. choose vertices from actual visual boundaries
4. review the proposed coverage
5. mutate only when explicitly authorized
6. re-fetch and visually verify the result

Do not invent polygon coordinates from metadata alone.
