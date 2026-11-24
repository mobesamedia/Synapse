# MindMap node arrangement

Arrange Nodes reflows the open mind map into a readable tree. It is reached from
the MindMap hamburger menu and opens the same option modal as Learning Setup,
with a Layout group (Vertical, Horizontal, Radial) and a Spacing group (Compact,
Normal, Wide). Both choices are remembered per profile in `mindmap_arrange_options`
through the tool's storage adapter, so the sandboxed tutorial frame keeps its own
in-memory copy and never writes user storage.

## Placement

Node coordinates stay absolute and free; the command only rewrites `x`/`y` once.
Dragging, the dot grid and the canvas connectors are unchanged, and connectors
follow because they are drawn centre to centre.

Every node reserves room for its **whole subtree** rather than only its direct
children, which is what the previous import-only layout could not do: it spaced
direct children by a fixed 180 px and therefore let a bushy branch grow across
its siblings. Vertical and horizontal share one implementation with the axes
swapped: a post-order pass measures the span each subtree needs along the level,
a pre-order pass assigns each subtree its slot, and a final post-order pass
centres every parent on its children. A row of children narrower than its parent
is centred under it. Level offsets come from the largest node on each level, so
`large` nodes and image nodes do not crowd the next level.

Radial keeps the root in the centre and gives each subtree an angular wedge
proportional to its leaf count, with the first branch pointing up. Ring radius is
the larger of two constraints: the room each node needs along its own radius, and
the radius at which its wedge is a long enough arc. Both use the node's angle, so
a node placed above the root costs its height rather than its width. A crowded
ring grows outward instead of overlapping. Radial suits shallow maps; a map four
or more levels deep is wide by construction and reads better as a tree.

Measured `offsetWidth`/`offsetHeight` are used wherever a node element exists,
because node width depends on the text and on manual corner resizing. Imported
maps have no elements yet and fall back to 154×60.

The root keeps its position, so the view does not jump; the command then calls
the existing fit-to-view. Arranging is one undo step, and a run that would change
nothing removes its own history entry instead of leaving an empty undo. While the
modal is open the map does not receive Delete.

Cyclic parent references and unreachable nodes cannot hang the layout: placement
walks a breadth-first spanning tree from the root, as the storage sanitiser does,
and any node outside it keeps its coordinates.

## Imported maps

`autoLayoutNodes()` keeps its name, signature and import-time anchor, and now
delegates to the same engine with Vertical/Normal. Maps created with Create with
AI therefore no longer arrive with branches stacked on top of each other.

## Checks

- `node tests/web_mindmap_arrange.cjs`: all three layouts at all three spacings
  separate every node of a deliberately piled, lopsided fixture; wider spacing
  uses more area; one arrangement is one undo/redo step and a no-op adds none;
  the modal remembers its choices across a reload and swallows Delete; a repaired
  cyclic map arranges without hanging; the practice frame writes no user storage.
- `node tests/web_mindmap_tutorial.cjs`: unchanged tutorial flow and storage
  isolation.
- `python3 scripts/audit_translations.py`: the seven new sources in all nine
  target languages.

Automated checks cannot guarantee that a particular map reads well after
arranging; the command is a single undoable step so it can simply be reverted.
