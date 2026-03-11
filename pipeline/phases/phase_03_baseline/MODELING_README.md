# Modeling Domain (`py/modeling/`)

Predictive modeling for expected campus movement patterns.

## Responsibilities

- Global model training
- Hierarchical model training
- Decision tree construction/checkpointing

## Typical hierarchy

- term
  - daytype
    - day_of_week
      - date

Model outputs are exported under run `model_tree/`.
