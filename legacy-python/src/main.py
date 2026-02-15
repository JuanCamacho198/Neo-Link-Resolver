"""
Neo-Link-Resolver v0.3 - Intelligent Multi-Site Resolver
Navega automaticamente en multiples sitios (peliculasgd, hackstore, etc)
y encuentra el mejor link segun criterios del usuario.

Usage:
    python main.py <url> [--quality 1080p] [--format WEB-DL] [--provider utorrent]

Examples:
    python main.py https://www.peliculasgd.net/bob-esponja-...
    python main.py https://hackstore.mx/peliculas/eragon-2006 --quality 1080p --format WEB-DL --provider utorrent
"""

import sys
import argparse
from playwright.sync_api import sync_playwright
from config import SearchCriteria
from adapters import get_adapter


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Neo-Link-Resolver: Intelligent link resolver for movie download sites"
    )
    parser.add_argument(
        "url",
        help="URL of the movie page to resolve"
    )
    parser.add_argument(
        "--quality",
        default="1080p",
        help="Preferred quality (1080p, 720p, 2160p, etc). Default: 1080p"
    )
    parser.add_argument(
        "--format",
        default="WEB-DL",
        help="Preferred format (WEB-DL, BluRay, BRRip, etc). Default: WEB-DL"
    )
    parser.add_argument(
        "--provider",
        nargs="+",
        default=["utorrent", "drive.google"],
        help="Preferred providers (utorrent, drive.google, mega, etc). Default: utorrent drive.google"
    )
    parser.add_argument(
        "--language",
        default="latino",
        help="Preferred language (latino, español, english). Default: latino"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no GUI)"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 70)
    print(" Neo-Link-Resolver v0.3 - Intelligent Multi-Site Resolver")
    print(" 'There is no spoon... and there are no ads.'")
    print("=" * 70)
    print(f"\nTarget URL: {args.url}")
    print(f"Search Criteria:")
    print(f"  Quality: {args.quality}")
    print(f"  Format: {args.format}")
    print(f"  Providers: {', '.join(args.provider)}")
    print(f"  Language: {args.language}")
    print()

    # Crear criterios de busqueda
    criteria = SearchCriteria(
        quality=args.quality,
        format=args.format,
        preferred_providers=args.provider,
        language=args.language,
    )

    # Usar LinkResolver (Centraliza la lógica de Playwright, Stealth y Analizadores)
    from resolver import LinkResolver
    resolver = LinkResolver(headless=args.headless)
    
    try:
        result = resolver.resolve(
            url=args.url,
            quality=args.quality,
            format_type=args.format,
            providers=args.provider,
            language=args.language
        )

        print("\n" + "=" * 70)
        if result and result.url != "LINK_NOT_RESOLVED":
            print(" [SUCCESS] Link resolved!")
            print(f" URL:      {result.url}")
            print(f" Provider: {result.provider}")
            print(f" Score:    {result.score:.1f}/100")
        else:
            print(" [FAILED] Could not resolve the link.")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n [ERROR] Fatal error during execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        print("\n[EXIT] Disconnected from the Matrix.\n")


if __name__ == "__main__":
    main()
