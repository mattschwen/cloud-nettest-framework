#!/usr/bin/env python3
"""Display ANUBIS logo with cyberpunk colors."""

from rich.console import Console
from rich.text import Text

console = Console()

def print_anubis_logo():
    """Print ANUBIS logo with cyberpunk pink/purple/blue colors."""
    
    logo = Text()
    
    # Top border - Cyan
    logo.append("\n╔═══════════════════════════════════════════════════════════════════════════════╗\n", style="bright_cyan")
    logo.append("║                                                                               ║\n", style="bright_cyan")
    
    # ANUBIS text - Bright Magenta (Pink/Purple)
    logo.append("║     ", style="bright_cyan")
    logo.append("█████╗ ███╗   ██╗██╗   ██╗██████╗ ██╗███████╗", style="bold bright_magenta")
    logo.append("                           ║\n", style="bright_cyan")

    logo.append("║    ", style="bright_cyan")
    logo.append("██╔══██╗████╗  ██║██║   ██║██╔══██╗██║██╔════╝", style="bold bright_magenta")
    logo.append("                           ║\n", style="bright_cyan")

    logo.append("║    ", style="bright_cyan")
    logo.append("███████║██╔██╗ ██║██║   ██║██████╔╝██║███████╗", style="bold bright_magenta")
    logo.append("                           ║\n", style="bright_cyan")

    logo.append("║    ", style="bright_cyan")
    logo.append("██╔══██║██║╚██╗██║██║   ██║██╔══██╗██║╚════██║", style="bold bright_magenta")
    logo.append("                           ║\n", style="bright_cyan")

    logo.append("║    ", style="bright_cyan")
    logo.append("██║  ██║██║ ╚████║╚██████╔╝██████╔╝██║███████║", style="bold bright_magenta")
    logo.append("                           ║\n", style="bright_cyan")

    logo.append("║    ", style="bright_cyan")
    logo.append("╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚═╝╚══════╝", style="bold bright_magenta")
    logo.append("                           ║\n", style="bright_cyan")
    
    logo.append("║                                                                               ║\n", style="bright_cyan")
    
    # Subtitle - Bright Blue
    logo.append("║           ", style="bright_cyan")
    logo.append("🔷 N E T W O R K   P A T H   G U A R D I A N 🔷", style="bold bright_blue")
    logo.append("                   ║\n", style="bright_cyan")
    
    logo.append("║                                                                               ║\n", style="bright_cyan")
    
    # Description box - Purple
    logo.append("║    ", style="bright_cyan")
    logo.append("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓", style="magenta")
    logo.append("    ║\n", style="bright_cyan")
    
    logo.append("║    ", style="bright_cyan")
    logo.append("┃  ", style="magenta")
    logo.append("Egyptian God of Network Diagnostics | Cyberpunk Edition", style="bold magenta")
    logo.append("        ┃", style="magenta")
    logo.append("    ║\n", style="bright_cyan")
    
    logo.append("║    ", style="bright_cyan")
    logo.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛", style="magenta")
    logo.append("    ║\n", style="bright_cyan")
    
    logo.append("║                                                                               ║\n", style="bright_cyan")
    
    # Features grid - Mixed colors
    logo.append("║    ", style="bright_cyan")
    logo.append("┌─────────────────────────────────────────────────────────────────┐", style="bright_blue")
    logo.append("      ║\n", style="bright_cyan")
    
    logo.append("║    ", style="bright_cyan")
    logo.append("│ ", style="bright_blue")
    logo.append("🌐 Multi-Cloud Testing    │ 🔬 L3→L4→L7 Correlation", style="bright_magenta")
    logo.append("            │", style="bright_blue")
    logo.append("      ║\n", style="bright_cyan")
    
    logo.append("║    ", style="bright_cyan")
    logo.append("│ ", style="bright_blue")
    logo.append("📊 MTR Path Analysis       │ 🔍 WHOIS ASN Lookup", style="bright_blue")
    logo.append("                │", style="bright_blue")
    logo.append("      ║\n", style="bright_cyan")
    
    logo.append("║    ", style="bright_cyan")
    logo.append("│ ", style="bright_blue")
    logo.append("💠 TCP Packet Intel        │ 🎯 Oracle OCI Specialized", style="magenta")
    logo.append("          │", style="bright_blue")
    logo.append("      ║\n", style="bright_cyan")
    
    logo.append("║    ", style="bright_cyan")
    logo.append("│ ", style="bright_blue")
    logo.append("🎨 Cyberpunk Terminal UI   │ 📈 Performance Grading A+→D", style="bright_cyan")
    logo.append("        │", style="bright_blue")
    logo.append("      ║\n", style="bright_cyan")
    
    logo.append("║    ", style="bright_cyan")
    logo.append("└─────────────────────────────────────────────────────────────────┘", style="bright_blue")
    logo.append("      ║\n", style="bright_cyan")
    
    logo.append("║                                                                               ║\n", style="bright_cyan")
    
    # Tagline - Gradient effect with purple/pink
    logo.append("║        ", style="bright_cyan")
    logo.append("▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓", style="bright_magenta")
    logo.append("          ║\n", style="bright_cyan")
    
    logo.append("║        ", style="bright_cyan")
    logo.append("█  GUIDING SOULS THROUGH THE NETWORK UNDERWORLD  █", style="bold bright_magenta")
    logo.append("                    ║\n", style="bright_cyan")
    
    logo.append("║        ", style="bright_cyan")
    logo.append("▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓", style="bright_magenta")
    logo.append("          ║\n", style="bright_cyan")
    
    logo.append("║                                                                               ║\n", style="bright_cyan")
    logo.append("╚═══════════════════════════════════════════════════════════════════════════════╝\n", style="bright_cyan")
    
    # Bottom tagline - Bright blue/purple gradient
    logo.append("\n       ", style="")
    logo.append("░█▀█░█▀█░█▀▀░█░█░█▀▀░▀█▀░░░█▀█░▀█▀░░░█▀█░░░▀█▀░▀█▀░█▄█░█▀▀\n", style="bright_blue")
    logo.append("       ", style="")
    logo.append("░█▀▀░█▀█░█░░░█▀▄░█▀▀░░█░░░░█▀█░░█░░░░█▀█░░░░█░░░█░░█░█░█▀▀\n", style="magenta")
    logo.append("       ", style="")
    logo.append("░▀░░░▀░▀░▀▀▀░▀░▀░▀▀▀░░▀░░░░▀░▀░░▀░░░░▀░▀░░░░▀░░▀▀▀░▀░▀░▀▀▀\n", style="bright_magenta")
    
    console.print(logo)


if __name__ == "__main__":
    print_anubis_logo()
