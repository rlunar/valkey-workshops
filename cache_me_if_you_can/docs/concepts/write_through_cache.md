# Write-Through Cache

Write to cache and database simultaneously.

```mermaid
graph LR
    A[App Update] --> B[Database]
    A --> C[Cache]
    B --> D[Consistent Data]
    C --> D
```
