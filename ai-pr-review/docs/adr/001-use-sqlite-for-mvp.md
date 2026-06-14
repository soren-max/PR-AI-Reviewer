# ADR-001: Use SQLite for MVP

## Status

Accepted

## Context

The AI PR Review MVP needs a persistence layer. Options considered:

- **SQLite**: Zero-config, file-based, no server process
- **PostgreSQL**: Mature RDBMS, concurrent write support, requires Docker/service
- **DuckDB**: OLAP-oriented, not ideal for row-level CRUD
- **In-memory**: No persistence, breaks on restart

## Decision

Use **SQLite** via `aiosqlite` for the MVP.

Key decision factors:
1. **Zero operations** — no server to install, no Docker dependency for local dev
2. **Low cognitive load** — anyone with Python can `pip install` and run
3. **Alembic abstraction** — migration scripts are written to SQLAlchemy, not SQLite, so migrating to PostgreSQL later only requires changing `DATABASE_URL` and regenerating a migration
4. **MVP concurrency is low** — a single developer or small team using the MVP generates < 10 concurrent tasks, well within SQLite's WAL-mode comfort zone

## Consequences

### Positive
- Fast startup: `git clone → pip install → run`
- Portable: database is a single file (`data/reviews.db`)
- Compatible with SQLAlchemy async: `sqlite+aiosqlite`

### Negative
- No concurrent writes: SQLite serializes all writes. WAL mode mitigates reads but writes are sequential
- Not horizontally scalable: cannot split across multiple nodes
- No role-based access at the DB level
- `ALTER TABLE` support is limited in older SQLite versions

## Migration Path

When the project outgrows SQLite (expected at > 5 concurrent review requests):

1. Switch `DATABASE_URL` to `postgresql+asyncpg://...`
2. Run `alembic revision --autogenerate` to create the PostgreSQL-compatible migration
3. Test, then deploy with PostgreSQL service
4. No application code changes needed — SQLAlchemy ORM abstracts the dialect
