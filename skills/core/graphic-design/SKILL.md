---
name: graphic-design
description: |
  Improve visual hierarchy, image placement, and professional appearance of documents
  while staying strictly inside the DesignSystem and LayoutTree rules.
  Never invent layout, colors, fonts, or spacing. Only propose block choices and structure.
use_when: |
  document looks flat or poorly structured,
  user asks for better visual hierarchy / more professional look,
  need guidance on image placement, feature grids, callouts, or section balance,
  or preparing a document for print / high-quality PDF export
---

# Graphic Design Skill

## Goal
Raise the visual quality of engineering documents without breaking the core contract:
- DesignSystem and LayoutTree own every visual decision
- This skill only proposes better block choices, image treatment, and hierarchy
- The agent never paints layout or invents styles

## What this skill can do
- Recommend the most appropriate block type for content (HeroBlock, FeatureGrid, EngineeringTable, CalloutBox variants, etc.)
- Suggest image roles (hero, exploded, detail, icon) and caption style
- Identify weak visual hierarchy (too much prose, missing tables, unbalanced sections)
- Propose reordering or splitting of content for better page flow
- Flag when a section needs a diagram or illustration
- Ensure consistent use of Warning / Requirement / Note callouts

## What this skill must never do
- Invent colors, fonts, spacing, or margins
- Bypass DesignSystem tokens
- Generate free-form HTML/CSS
- Override print-first layout rules
- Create decorative elements that have no engineering purpose

## Workflow
1. Inspect the current Document AST (or the section being edited).
2. Evaluate against professional engineering document standards:
   - Clear hierarchy
   - Tables for data, procedures for steps
   - Balanced use of images
   - Consistent callout usage
   - Good page rhythm (avoid large empty regions or dense text walls)
3. Propose concrete, tool-callable improvements only:
   - “Convert this list to EngineeringTable”
   - “Move this image to hero position and add caption”
   - “Split this long section into two”
   - “Add FeatureGrid for the four main components”
   - “Replace paragraph warning with CalloutBox(variant=warning)”
4. Leave all actual layout, typography, and spacing to the LayoutEngine + DesignSystem.

## Output contract
Return a list of actionable proposals:

```json
{
  "proposals": [
    {
      "type": "convert_block" | "move_block" | "add_block" | "split_section" | "image_treatment",
      "target": "section_id or block_id",
      "recommendation": "...",
      "reason": "...",
      "tool_call": "force_block | insert_block | set_image | regenerate_section | ..."
    }
  ],
  "summary": "Short overall assessment of visual quality"
}
```

Does not rewrite the document or paint layout. Proposes ops only for the orchestrator.
