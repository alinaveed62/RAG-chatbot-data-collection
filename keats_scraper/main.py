#!/usr/bin/env python3
"""
KEATS Student Handbook Scraper

A web scraper for extracting the Informatics Student Handbook from
King's College London's KEATS platform for use in a RAG chatbot.

Usage:
    python main.py login     # Authenticate with KEATS (manual 2FA)
    python main.py scrape    # Scrape handbook content
    python main.py process   # Process and chunk documents
    python main.py all       # Run complete pipeline
    python main.py status    # Show scraping progress
"""

import sys
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from config import ScraperConfig, config
from auth import SSOHandler
from scraper import CourseNavigator, PageScraper, PDFHandler, RateLimiter
from processors import HTMLCleaner, TextNormalizer, Chunker
from storage import CheckpointManager, JSONLExporter
from models import Document, Chunk
from utils.logging_config import setup_logging, get_logger

console = Console()


def setup_environment():
    """Initialize directories and logging."""
    config.ensure_directories()
    setup_logging(level=config.log_level, log_file=config.log_file)
    return get_logger()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """KEATS Student Handbook Scraper for RAG Pipeline."""
    pass


@cli.command()
@click.option("--force", is_flag=True, help="Force new login even if session exists")
def login(force: bool):
    """Authenticate with KEATS (requires manual 2FA)."""
    logger = setup_environment()

    console.print("\n[bold blue]KEATS Authentication[/bold blue]\n")

    sso = SSOHandler(config)

    if not force:
        # Check if we have a valid session
        cookies = sso.session_manager.load_cookies()
        if cookies:
            session = sso.session_manager.create_session_with_cookies(cookies)
            if sso.session_manager.validate_session(session, config.auth.session_check_url):
                console.print("[green]Existing session is still valid![/green]")
                console.print("Use --force to re-authenticate anyway.")
                return

    try:
        session = sso.get_valid_session(force_login=force)
        console.print("\n[bold green]Login successful![/bold green]")
        console.print("Session cookies have been saved for future use.")

    except Exception as e:
        console.print(f"\n[bold red]Login failed:[/bold red] {e}")
        sys.exit(1)


@cli.command()
def logout():
    """Clear saved session."""
    logger = setup_environment()

    sso = SSOHandler(config)
    sso.logout()
    console.print("[green]Session cleared.[/green]")


@cli.command()
@click.option("--resume", is_flag=True, help="Resume from last checkpoint")
def scrape(resume: bool):
    """Scrape handbook content from KEATS."""
    logger = setup_environment()

    console.print("\n[bold blue]KEATS Handbook Scraper[/bold blue]\n")

    # Initialize components
    sso = SSOHandler(config)
    checkpoint = CheckpointManager(config.data_dir / "checkpoints")
    html_cleaner = HTMLCleaner()
    text_normalizer = TextNormalizer()

    # Check for valid session
    try:
        session = sso.get_valid_session()
    except Exception as e:
        console.print(f"[bold red]Authentication required.[/bold red]")
        console.print("Run: python main.py login")
        sys.exit(1)

    rate_limiter = RateLimiter(config.rate_limit)
    navigator = CourseNavigator(session, config, rate_limiter)
    page_scraper = PageScraper(session, rate_limiter)
    pdf_handler = PDFHandler(session, rate_limiter, config)
    exporter = JSONLExporter(config.processed_dir)

    # Resume or start fresh
    progress_data = None
    if resume:
        progress_data = checkpoint.load()
        if progress_data:
            console.print(f"[yellow]Resuming from checkpoint...[/yellow]")
            console.print(f"Already processed: {len(progress_data.processed_urls)} URLs")

    # Discover resources
    console.print("\n[bold]Discovering handbook resources...[/bold]")
    try:
        resources = navigator.discover_resources()
    except Exception as e:
        console.print(f"[bold red]Failed to discover resources:[/bold red] {e}")
        console.print("Your session may have expired. Run: python main.py login")
        sys.exit(1)

    console.print(f"Found [bold]{len(resources)}[/bold] resources to process.\n")

    if not progress_data:
        progress_data = checkpoint.start_new(len(resources))

    # Process resources
    documents: List[Document] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Scraping...", total=len(resources))

        for resource in resources:
            # Skip if already processed
            if checkpoint.is_processed(resource.url):
                progress.advance(task)
                continue

            progress.update(task, description=f"Scraping: {resource.title[:40]}...")

            try:
                doc = None

                if resource.resource_type == "page":
                    doc = page_scraper.scrape_page(resource.url, resource.section)

                elif resource.resource_type in ("resource", "pdf"):
                    doc = pdf_handler.process_pdf(
                        resource.url, resource.title, resource.section
                    )

                elif resource.resource_type == "book":
                    # Discover and process book chapters
                    chapters = navigator.discover_book_chapters(resource.url)
                    for chapter in chapters:
                        if not checkpoint.is_processed(chapter.url):
                            chapter_doc = page_scraper.scrape_page(
                                chapter.url, resource.section
                            )
                            if chapter_doc:
                                documents.append(chapter_doc)
                                checkpoint.mark_processed(chapter.url)

                elif resource.resource_type == "folder":
                    # Discover and process folder contents
                    files = navigator.discover_folder_contents(resource.url)
                    for file_info in files:
                        if not checkpoint.is_processed(file_info.url):
                            if file_info.resource_type == "pdf":
                                file_doc = pdf_handler.process_pdf(
                                    file_info.url, file_info.title, resource.section
                                )
                            else:
                                file_doc = page_scraper.scrape_page(
                                    file_info.url, resource.section
                                )
                            if file_doc:
                                documents.append(file_doc)
                                checkpoint.mark_processed(file_info.url)

                if doc:
                    # Clean and normalize content
                    if doc.raw_html:
                        cleaned = html_cleaner.clean(doc.raw_html)
                        doc.content = text_normalizer.normalize(cleaned)
                    else:
                        doc.content = text_normalizer.normalize(doc.content)

                    documents.append(doc)
                    checkpoint.mark_processed(resource.url)
                else:
                    checkpoint.mark_failed(resource.url)

            except Exception as e:
                logger.error(f"Failed to process {resource.url}: {e}")
                checkpoint.mark_failed(resource.url)

            progress.advance(task)

    # Save documents
    if documents:
        doc_path = exporter.export_documents(documents)
        console.print(f"\n[green]Saved {len(documents)} documents to {doc_path}[/green]")

    # Show stats
    stats = checkpoint.get_stats()
    console.print(f"\n[bold]Scraping Complete[/bold]")
    console.print(f"  Processed: {stats['processed']}")
    console.print(f"  Failed: {stats['failed']}")


@cli.command()
def process():
    """Process scraped documents into RAG-ready chunks."""
    logger = setup_environment()

    console.print("\n[bold blue]Processing Documents into Chunks[/bold blue]\n")

    # Load documents
    doc_file = config.processed_dir / "documents.jsonl"
    if not doc_file.exists():
        console.print("[bold red]No documents found.[/bold red]")
        console.print("Run: python main.py scrape")
        sys.exit(1)

    documents = list(JSONLExporter.load_documents(doc_file))
    console.print(f"Loaded [bold]{len(documents)}[/bold] documents.")

    # Chunk documents
    chunker = Chunker(config.chunk)
    chunks = chunker.chunk_documents(documents)

    console.print(f"Created [bold]{len(chunks)}[/bold] chunks.")

    # Export chunks
    exporter = JSONLExporter(config.chunks_dir)
    chunk_path = exporter.export_chunks(chunks)
    embed_path = exporter.export_embedding_format(chunks)
    index_path = exporter.create_index(chunks)

    console.print(f"\n[green]Output files:[/green]")
    console.print(f"  Chunks: {chunk_path}")
    console.print(f"  Embeddings format: {embed_path}")
    console.print(f"  Index: {index_path}")


@cli.command()
def all():
    """Run complete pipeline: scrape and process."""
    logger = setup_environment()

    console.print("\n[bold blue]Running Complete Pipeline[/bold blue]\n")

    # Import and run commands
    from click.testing import CliRunner
    runner = CliRunner()

    # Scrape
    console.print("[bold]Step 1: Scraping[/bold]")
    result = runner.invoke(scrape)
    if result.exit_code != 0:
        console.print(f"[red]Scraping failed[/red]")
        sys.exit(1)

    # Process
    console.print("\n[bold]Step 2: Processing[/bold]")
    result = runner.invoke(process)
    if result.exit_code != 0:
        console.print(f"[red]Processing failed[/red]")
        sys.exit(1)

    console.print("\n[bold green]Pipeline complete![/bold green]")


@cli.command()
def status():
    """Show current scraping progress."""
    setup_environment()

    checkpoint = CheckpointManager(config.data_dir / "checkpoints")
    stats = checkpoint.get_stats()

    console.print("\n[bold blue]Scraping Status[/bold blue]\n")

    if stats.get("status") == "no session":
        console.print("No scraping session found.")
        return

    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Started", stats.get("started_at", "N/A"))
    table.add_row("Last Updated", stats.get("last_updated", "N/A"))
    table.add_row("Total Resources", str(stats.get("total_resources", 0)))
    table.add_row("Processed", str(stats.get("processed", 0)))
    table.add_row("Failed", str(stats.get("failed", 0)))
    table.add_row("Remaining", str(stats.get("remaining", 0)))
    table.add_row("Documents Saved", str(stats.get("documents_saved", 0)))

    console.print(table)


@cli.command()
def clear():
    """Clear all scraped data and checkpoints."""
    setup_environment()

    if click.confirm("This will delete all scraped data. Continue?"):
        import shutil

        # Clear data directories
        for directory in [config.raw_dir, config.processed_dir, config.chunks_dir]:
            if directory.exists():
                shutil.rmtree(directory)
                directory.mkdir(parents=True)

        # Clear checkpoints
        checkpoint = CheckpointManager(config.data_dir / "checkpoints")
        checkpoint.clear()

        console.print("[green]All data cleared.[/green]")


if __name__ == "__main__":
    cli()
