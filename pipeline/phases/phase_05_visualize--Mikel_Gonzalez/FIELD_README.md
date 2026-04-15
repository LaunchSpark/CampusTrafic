# Field Domain (`py/field/`)

Converts edge flows into continuous playback-ready spatial fields.

## Responsibilities

- Compute vector flow field `F(x,t)`
- Compute density field `N(x,t)`
- Apply spatial kernels around edges
- Tile outputs for efficient UI streaming

Outputs are persisted into run artifact `fields/` and `fields/tiles/`.
