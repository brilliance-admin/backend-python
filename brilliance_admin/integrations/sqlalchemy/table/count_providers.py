from brilliance_admin.schema.table.count_providers import CountProvider, CountResult


class SQLAlchemyCountProvider(CountProvider):
    async def get_count(self, stmt, *, category, has_filters: bool, limit: int) -> CountResult:
        from sqlalchemy import func, select

        count_stmt = select(func.count()).select_from(stmt.subquery())
        async with category.db_async_session() as session:
            count = await session.scalar(count_stmt)
            return CountResult(
                total_count=str(count),
                pages_count=CountResult.get_pages_count(count, limit),
            )
