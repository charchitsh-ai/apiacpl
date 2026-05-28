from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import NotificationTemplate


class TemplateRenderer:
    """Utility class resolving and rendering notification templates with context variables."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_template(self, name: str) -> Optional[NotificationTemplate]:
        """Fetch an active notification template by its unique name."""
        stmt = select(NotificationTemplate).filter(
            NotificationTemplate.name == name,
            NotificationTemplate.is_active == True,  # noqa
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def render(
        self, template_name: str, context: Dict[str, Any]
    ) -> Tuple[Optional[str], str]:
        """
        Resolves a template by name and renders its subject and body with context variables.
        Returns (subject, rendered_body).
        Subject is None for non-email channels.
        Raises ValueError if template is not found.
        """
        template = await self.get_template(template_name)
        if not template:
            raise ValueError(f"No active notification template found with name '{template_name}'.")

        # Validate all declared variables are provided in context
        missing = [var for var in template.variables if var not in context]
        if missing:
            raise ValueError(
                f"Missing required template variables: {missing}. "
                f"Template '{template_name}' requires: {template.variables}"
            )

        try:
            rendered_body = template.body.format_map(context)
            rendered_subject = template.subject.format_map(context) if template.subject else None
        except KeyError as e:
            raise ValueError(f"Template rendering error: missing variable key {e}")

        return rendered_subject, rendered_body

    def render_inline(self, body: str, context: Dict[str, Any]) -> str:
        """Renders an inline message string (not loaded from DB) with context substitution."""
        try:
            return body.format_map(context)
        except KeyError as e:
            raise ValueError(f"Inline template rendering error: missing key {e}")
