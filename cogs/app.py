import os
import re
import time
import sys
import traceback
from typing import Any, Dict, List, Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

API_BASE = os.getenv("JB_API_BASE_URL", "https://api.jailbreaks.app")
API_ALL = f"{API_BASE}/appinfo/all"
API_STATS = f"{API_BASE}/stats"  # /stats/<slug>
SITE_APPS_JSON = "https://jailbreaks.app/json/apps.json"
SITE_BASE = "https://jailbreaks.app"
INSTALL_BASE = "https://api.jailbreaks.app/install"

CACHE_TTL_SECONDS = 600
HTTP_TIMEOUT_SECONDS = 10
HTTP_RETRIES = 2


def slugify(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9\-]", "", s)
    return s


def abs_site_url(maybe_relative: str) -> str:
    if not maybe_relative:
        return ""
    return maybe_relative if maybe_relative.startswith("http") else f"{SITE_BASE}/{maybe_relative.lstrip('/')}"


def md_escape(s: Any) -> str:
    return discord.utils.escape_markdown(str(s or "").strip())


def html_to_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()


def find_app(apps: List[Dict[str, Any]], query: str) -> Optional[Dict[str, Any]]:
    q = (query or "").strip().lower()
    qn = q.replace(" ", "")

    for a in apps:
        name = str(a.get("name", "")).strip()
        if name and name.lower().replace(" ", "") == qn:
            return a

    for a in apps:
        name = str(a.get("name", "")).strip()
        if name and q in name.lower():
            return a

    return None


async def asyncio_sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


async def fetch_json_with_retry(session: aiohttp.ClientSession, url: str) -> Any:
    last_exc: Optional[BaseException] = None
    for attempt in range(HTTP_RETRIES + 1):
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            last_exc = e
            if attempt < HTTP_RETRIES:
                await asyncio_sleep(0.4 * (attempt + 1))
    raise last_exc  # type: ignore[misc]


async def fetch_downloads(session: aiohttp.ClientSession, app_name: str) -> Optional[int]:
    url = f"{API_STATS}/{slugify(app_name)}"
    async with session.get(url) as resp:
        if resp.status != 200:
            return None
        data = await resp.json()
        return data.get("downloads")


def build_header(api_app: Dict[str, Any], downloads: Optional[int]) -> str:
    name = md_escape(api_app.get("name") or "Unknown")
    featured = bool(api_app.get("featured") or False)

    short = md_escape(api_app.get("short_description") or "")
    latest = md_escape(api_app.get("latest_version") or "Unknown")
    developer = md_escape(api_app.get("developer") or "Unknown")
    category = md_escape(api_app.get("category") or "unknown")

    title = f"**{name}**" + (" ⭐" if featured else "")
    lines = [
        title,
        f"*{short}*" if short else None,
        f"**Latest:** **{latest}**",
        f"**Developer:** **{developer}**",
        f"**Category:** **{category}**",
        (f"**Downloads:** **{downloads:,}**" if isinstance(downloads, int) else None),
    ]
    return "\n".join([x for x in lines if x])


def build_description(api_app: Dict[str, Any]) -> str:
    desc_html = str(api_app.get("description") or "").strip()
    if not desc_html:
        return ""
    desc = html_to_text(desc_html)
    desc = md_escape(desc)
    if len(desc) > 1200:
        desc = desc[:1200].rstrip() + "…"
    return desc


class VersionSelect(discord.ui.Select):
    def __init__(self, app_name: str, versions: List[str]):
        self.app_name = app_name
        options = [
            discord.SelectOption(
                label=md_escape(v),
                value=str(v),
                description=f"Install {app_name} {v}",
            )
            for v in (versions or [])[:25]
        ]
        super().__init__(
            placeholder="Install an older version…",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"app:ver:{slugify(app_name)}",
        )

    async def callback(self, interaction: discord.Interaction):
        v = self.values[0]
        url = f"{INSTALL_BASE}/{slugify(self.app_name)}/{v}"
        await interaction.response.send_message(
            f"**Install {md_escape(self.app_name)} {md_escape(v)}:**\n{url}",
            ephemeral=True,
        )


class NotFoundLayout(discord.ui.LayoutView):
    def __init__(self, query: str):
        super().__init__(timeout=60)
        container = discord.ui.Container(accent_color=0xED4245, id=1)
        container.add_item(
            discord.ui.TextDisplay(
                f"**App not found**\nNo match for: **{md_escape(query)}**\n\nTip: start typing to use autocomplete.",
                id=2,
            )
        )
        self.add_item(container)


class AppLayout(discord.ui.LayoutView):
    def __init__(
        self,
        api_app: Dict[str, Any],
        site_app: Optional[Dict[str, Any]],
        downloads: Optional[int],
    ):
        super().__init__(timeout=180)

        raw_name = str(api_app.get("name") or "Unknown")
        icon = abs_site_url(str(api_app.get("icon") or ""))

        description = build_description(api_app)
        other_versions = api_app.get("other_versions") or []
        screenshots = (site_app or {}).get("screenshots") or []

        container = discord.ui.Container(accent_color=0x5865F2, id=1)

        thumb = discord.ui.Thumbnail(icon, description=f"{md_escape(raw_name)} icon", id=2) if icon else None
        section = discord.ui.Section(accessory=thumb, id=3)
        section.add_item(discord.ui.TextDisplay(build_header(api_app, downloads), id=4))
        container.add_item(section)

        if description:
            container.add_item(discord.ui.TextDisplay(description, id=9))

        if isinstance(screenshots, list) and screenshots:
            container.add_item(discord.ui.TextDisplay("**Screenshots**", id=10))

            items: List[discord.components.MediaGalleryItem] = []
            for s in screenshots[:10]:
                url = abs_site_url(str(s))
                if url:
                    items.append(
                        discord.components.MediaGalleryItem(
                            url,
                            description=f"{md_escape(raw_name)} screenshot",
                        )
                    )

            if items:
                container.add_item(discord.ui.MediaGallery(*items, id=5))

        row = discord.ui.ActionRow(id=6)
        row.add_item(discord.ui.Button(label="Install Latest", url=f"{INSTALL_BASE}/{slugify(raw_name)}"))
        row.add_item(discord.ui.Button(label="Website", url=SITE_BASE))
        container.add_item(row)

        if isinstance(other_versions, list) and other_versions:
            container.add_item(discord.ui.TextDisplay("**Older versions**", id=7))
            pick_row = discord.ui.ActionRow(id=8)
            pick_row.add_item(VersionSelect(raw_name, other_versions))
            container.add_item(pick_row)

        self.add_item(container)


class AppCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self._api_cache: List[Dict[str, Any]] = []
        self._api_cache_time = 0.0
        self._site_cache: List[Dict[str, Any]] = []
        self._site_cache_time = 0.0

        import asyncio

        self._api_lock = asyncio.Lock()
        self._site_lock = asyncio.Lock()

        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
        self._session = aiohttp.ClientSession(timeout=timeout)

    async def cog_unload(self) -> None:
        try:
            await self._session.close()
        except Exception:
            print("[app] Failed to close aiohttp session", file=sys.stderr)
            traceback.print_exc()

    async def _get_api_cached(self) -> List[Dict[str, Any]]:
        now = time.time()
        if self._api_cache and (now - self._api_cache_time) < CACHE_TTL_SECONDS:
            return self._api_cache

        async with self._api_lock:
            now = time.time()
            if self._api_cache and (now - self._api_cache_time) < CACHE_TTL_SECONDS:
                return self._api_cache

            try:
                apps = await fetch_json_with_retry(self._session, API_ALL)
                self._api_cache = apps if isinstance(apps, list) else []
                self._api_cache_time = now
                return self._api_cache
            except Exception:
                print(f"[app] Failed to fetch API app list: {API_ALL}", file=sys.stderr)
                traceback.print_exc()
                raise

    async def _get_site_cached(self) -> List[Dict[str, Any]]:
        now = time.time()
        if self._site_cache and (now - self._site_cache_time) < CACHE_TTL_SECONDS:
            return self._site_cache

        async with self._site_lock:
            now = time.time()
            if self._site_cache and (now - self._site_cache_time) < CACHE_TTL_SECONDS:
                return self._site_cache

            try:
                apps = await fetch_json_with_retry(self._session, SITE_APPS_JSON)
                self._site_cache = apps if isinstance(apps, list) else []
                self._site_cache_time = now
                return self._site_cache
            except Exception:
                print(f"[app] Failed to fetch site apps JSON: {SITE_APPS_JSON}", file=sys.stderr)
                traceback.print_exc()
                raise

    async def app_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        try:
            apps = await self._get_api_cached()
        except Exception:
            # _get_api_cached already logged
            return []

        cur = (current or "").lower().strip()

        prefix: List[str] = []
        contains: List[str] = []
        for a in apps:
            nm = str(a.get("name") or "").strip()
            if not nm:
                continue
            low = nm.lower()
            if not cur or low.startswith(cur):
                prefix.append(nm)
            elif cur in low:
                contains.append(nm)

        results = (prefix + contains)[:25]
        return [app_commands.Choice(name=r, value=r) for r in results]

    @app_commands.command(name="app", description="Show an app from Jailbreaks.app")
    @app_commands.describe(
        name="App name",
        ephemeral="Optional: Make the bot's reply only be visible to you (Default is true)",
    )
    @app_commands.autocomplete(name=app_name_autocomplete)
    async def app(self, interaction: discord.Interaction, name: str, ephemeral: bool = True):
        await interaction.response.defer(ephemeral=ephemeral)

        try:
            api_apps = await self._get_api_cached()
        except Exception:
            return await interaction.followup.send("Failed to fetch app list from the API.", ephemeral=ephemeral)

        api_app = find_app(api_apps, name)
        if not api_app:
            return await interaction.followup.send(view=NotFoundLayout(name), ephemeral=ephemeral)

        downloads: Optional[int] = None
        try:
            downloads = await fetch_downloads(self._session, str(api_app.get("name") or name))
        except Exception:
            print(f"[app] Failed to fetch downloads for: {api_app.get('name') or name}", file=sys.stderr)
            traceback.print_exc()
            downloads = None

        site_app: Optional[Dict[str, Any]] = None
        try:
            site_apps = await self._get_site_cached()
            site_app = find_app(site_apps, str(api_app.get("name") or name))
        except Exception:
            # _get_site_cached already logged
            site_app = None

        await interaction.followup.send(
            view=AppLayout(api_app, site_app, downloads),
            ephemeral=ephemeral,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AppCog(bot))