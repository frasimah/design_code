#!/usr/bin/env python3
"""
Sync WooCommerce products to ChromaDB embeddings.
Run this script periodically to keep WooCommerce products indexed for AI chat.

Usage:
    python scripts/sync_woocommerce.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rich.console import Console
from src.api.services.woocommerce import fetch_all_wc_products
from src.ai.embeddings import BrickEmbeddings

console = Console()


def main():
    console.print("[bold blue]WooCommerce -> ChromaDB Sync[/bold blue]\n")
    
    # 1. Fetch all WooCommerce products
    console.print("[cyan]Step 1: Fetching WooCommerce products...[/cyan]")
    products = fetch_all_wc_products()
    
    if not products:
        console.print("[red]No products fetched. Check WooCommerce credentials.[/red]")
        return 1
    
    console.print(f"[green]✓ Fetched {len(products)} products[/green]\n")
    
    # 2. Initialize embeddings
    console.print("[cyan]Step 2: Initializing ChromaDB...[/cyan]")
    embeddings = BrickEmbeddings()
    console.print(f"[dim]Current collection size: {embeddings.collection.count()}[/dim]\n")
    
    # 3. Sync to ChromaDB
    console.print("[cyan]Step 3: Syncing to ChromaDB...[/cyan]")
    embeddings.sync_products(products, source="woocommerce")
    
    # 4. Verify
    console.print(f"\n[bold green]✓ Sync complete![/bold green]")
    console.print(f"[dim]New collection size: {embeddings.collection.count()}[/dim]")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
