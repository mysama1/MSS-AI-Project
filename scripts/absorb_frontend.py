"""Sprint 103: Absorb top-tier frontend design patterns."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mssclaw.core.agent_absorber import AgentAbsorber

absorber = AgentAbsorber()

targets = [
    {
        "name": "LobeChat Design",
        "description": (
            "Modern AI chat UI with plugin gateway architecture. "
            "Topic-based conversations, shadcn/ui components, Zustand state management, "
            "responsive mobile-first design, dark/light theme system, "
            "TTS/STT integration, file upload, knowledge base panel."
        ),
        "key_patterns": ["plugin_gateway", "topic_conversation", "shadcn_components", "mobile_first"],
    },
    {
        "name": "NextChat Architecture",
        "description": (
            "Zero-backend pure frontend architecture for AI chat. "
            "Mask prompt system, i18n multi-language support, "
            "markdown/LaTeX rendering with code highlighting, "
            "session management with local storage, "
            "streaming response with typewriter effect, model switching."
        ),
        "key_patterns": ["zero_backend", "mask_system", "i18n", "local_storage_session"],
    },
    {
        "name": "Dashboard Starter",
        "description": (
            "Admin dashboard with Next.js 16 App Router. "
            "Clerk authentication, KBar command palette (Cmd+K), "
            "shadcn/ui New York style components, "
            "React Query for data fetching, Zod form validation, "
            "Nuqs URL state manager, responsive sidebar navigation, "
            "dark/light theme toggle, breadcrumb navigation."
        ),
        "key_patterns": ["kbar_palette", "clerk_auth", "react_query", "sidebar_nav"],
    },
]

results = []
for target in targets:
    print(f"\nAbsorbing: {target['name']}...")
    try:
        result = absorber.absorb_from_text(target["description"])
        results.append({
            "name": target["name"],
            "patterns": target["key_patterns"],
            "absorbed": result.name,
        })
        print(f"  Absorbed: {result.name}")
    except Exception as e:
        print(f"  Error: {e}")

print(f"\nTotal absorbed: {len(absorber.list_absorbed())} agents")

# Now output design brief for new mssclaw webui
print("\n" + "=" * 50)
print("DESIGN BRIEF: mssclaw WebUI v2.0")
print("=" * 50)
print("""
Architecture: Next.js 16 App Router + shadcn/ui (New York style)
Pages:
  /chat       — AI chat (LobeChat-style topic system)
  /vault      — Password manager dashboard
  /models     — Model catalog + health
  /library    — Library browser (8 libraries)
  /settings   — Config panel

Components (from absorbed patterns):
  - CommandPalette (KBar Cmd+K navigation)
  - ThemeToggle (dark/light)
  - SidebarNav (responsive, collapsible)
  - ChatPanel (streaming, markdown, code highlight)
  - VaultTable (search/filter/export)
  - ModelCard (provider badge, stats)
  - StatusBar (health indicators)

Design Tokens:
  Colors: zinc neutral palette
  Font: Inter + JetBrains Mono (code)
  Radius: 0.5rem (shadcn default)
  Spacing: 4px grid

Tech Stack:
  next@16, react@19, tailwind@4, shadcn/ui, zustand, react-query
""")
