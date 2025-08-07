# ADR-004: Repository Pattern for Data Access Layer

## Status
Accepted

## Context
The original codebase had a single `DatabaseInterface` class that attempted to handle both SQLite (local development) and DynamoDB (production) in the same class using conditional logic. This created several problems:

1. **Leaky Abstraction**: SQL and NoSQL paradigms are fundamentally different
2. **Testing Complexity**: Behavior changes dramatically between environments
3. **Maintenance Burden**: Adding new databases requires modifying existing code
4. **Performance Issues**: No connection pooling, inefficient queries
5. **No Migration Strategy**: Schema changes break compatibility

## Decision
Implement a proper Repository Pattern with:

1. **Abstract Base Class**: Define contract all implementations must follow
2. **Separate Implementations**: SQLiteRepository and DynamoDBRepository
3. **Factory Pattern**: Create appropriate repository based on environment
4. **Connection Pooling**: SQLite pool for better concurrency
5. **Domain Models**: ChatInteraction as core domain model
6. **Metrics Integration**: Built-in observability support

## Architecture

```
┌─────────────────────────────────────────────┐
│             Application Layer               │
│         (Service, API Endpoints)            │
└────────────────┬────────────────────────────┘
                 │ Uses
                 ▼
┌─────────────────────────────────────────────┐
│           Repository Interface              │
│            (ChatRepository ABC)             │
└────────────────┬────────────────────────────┘
                 │ Implements
     ┌───────────┴───────────┬────────────────┐
     ▼                       ▼                 ▼
┌─────────────┐    ┌──────────────┐   ┌──────────────┐
│   SQLite    │    │   DynamoDB   │   │   InMemory   │
│ Repository  │    │  Repository  │   │  Repository  │
└─────────────┘    └──────────────┘   └──────────────┘
     │                      │                  │
     ▼                      ▼                  ▼
┌─────────────┐    ┌──────────────┐   ┌──────────────┐
│SQLite + Pool│    │  DynamoDB    │   │   Memory     │
└─────────────┘    └──────────────┘   └──────────────┘
```

## Consequences

### Positive
1. **Clean Separation**: Each database has optimized implementation
2. **Testability**: Easy to mock/stub repositories
3. **Scalability**: Connection pooling and batch operations
4. **Maintainability**: Add new databases without changing existing code
5. **Type Safety**: Strong typing with domain models
6. **Performance**: O(1) cache operations, connection pooling

### Negative
1. **More Files**: Increased number of files to maintain
2. **Initial Complexity**: More upfront design work
3. **Learning Curve**: Developers need to understand the pattern

## Implementation Details

### SQLiteRepository
- Connection pooling with configurable size
- WAL mode for better concurrency
- Automatic schema migrations
- Prepared statements for performance
- Retry decorator for lock contention

### DynamoDBRepository
- Single table design for cost optimization
- GSI for user queries
- TTL for automatic data expiration
- Soft deletes for audit trail
- Batch operations support

### Factory Pattern
```python
# Automatic environment detection
repository = get_repository()  # Returns appropriate implementation

# Explicit environment
repository = RepositoryFactory.create_repository("production")

# Dependency injection
@app.post("/chat")
async def chat(repo: ChatRepository = Depends(get_repository_dependency)):
    # Use repository
```

## Metrics and Observability
Each repository operation records:
- Operation name
- Duration in milliseconds
- Success/failure status
- Error details if failed

## Migration Path
1. Keep old `DatabaseInterface` for backward compatibility
2. Gradually migrate services to use new repositories
3. Remove old interface once migration complete

## Trade-offs

### Why Not Use ORM Everywhere?
- **SQLAlchemy**: Great for complex queries but adds overhead for Lambda
- **DynamoDB ORMs**: Limited benefits, better to use SDK directly
- **Decision**: Hybrid approach - raw SQL/SDK with type safety

### Consistency Model
- **SQLite**: ACID transactions, strong consistency
- **DynamoDB**: Eventually consistent for most operations
- **Decision**: Document consistency requirements per use case

## Future Considerations
1. **Read Replicas**: Add support when scale demands
2. **Caching Layer**: Redis for frequently accessed data
3. **Event Sourcing**: Store events instead of state
4. **CQRS**: Separate read and write models

## References
- [Martin Fowler - Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [AWS DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)