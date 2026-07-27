---
name: diagram-proposal
description: |
  Propose diagrams, exploded views, or illustrations needed in a document.
  Suggest captions and placement. Use when images or diagrams are missing
  or should be added.
use_when: |
  document needs figures, exploded views, or process diagrams,
  creating placeholders for images in user manuals or datasheets
---

# Diagram Proposal

## Instructions
1. Analyse content and identify where diagrams add value (components, flows, exploded views).  
2. Propose DiagramBlock or ImageBlock(placeholder=True) entries with:  
   - Suggested caption (e.g. “Illustration 1: Main components”)  
   - Brief description of what the diagram should show  
   - Recommended placement in the section  

## Output
List of proposed blocks ready for insertion into the Document AST.  
User must confirm before any SVG is generated.  
Does not invent technical details or paint layout.
