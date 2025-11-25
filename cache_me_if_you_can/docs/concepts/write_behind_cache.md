# Write-Behind (Write-Back)

Write to cache immediately, database asynchronously.

```mermaid
graph LR
    A[App Update] --> B[Cache]
    B --> C[Async DB Update]
    C --> D[Higher Performance]
```

