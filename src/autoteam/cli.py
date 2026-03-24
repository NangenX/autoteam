"""AutoTeam CLI entry point."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="autoteam",
    help="Multi-CLI orchestration control plane for AI agents",
    add_completion=False,
)

console = Console()


@app.command()
def run(
    requirement: str = typer.Argument(..., help="The requirement to process"),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to roles config YAML",
    ),
    runs_dir: Path = typer.Option(
        Path("runs"),
        "--runs-dir",
        "-r",
        help="Directory to store run data",
    ),
    max_rounds: int = typer.Option(
        5,
        "--max-rounds",
        "-m",
        help="Maximum number of orchestration rounds",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print what would happen without executing",
    ),
) -> None:
    """Run an orchestration workflow with the given requirement."""
    from autoteam.runtime import RunManager

    console.print(f"[bold blue]AutoTeam[/bold blue] v0.1.0")
    console.print(f"Requirement: {requirement}")

    if dry_run:
        console.print("[yellow]Dry run mode - no actions will be taken[/yellow]")
        return

    manager = RunManager(runs_dir=runs_dir, max_rounds=max_rounds)
    run_state = manager.create_run(requirement)

    console.print(f"Created run: [green]{run_state.run_id}[/green]")
    console.print(f"Run directory: {runs_dir / run_state.run_id}")

    manager.start_run(run_state)
    console.print(f"Status: [yellow]{run_state.status}[/yellow]")

    console.print("\n[bold]Ready to execute workflow[/bold]")
    console.print("(Workflow execution not yet implemented)")


@app.command()
def list_runs(
    runs_dir: Path = typer.Option(
        Path("runs"),
        "--runs-dir",
        "-r",
        help="Directory containing run data",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        "-n",
        help="Maximum number of runs to show",
    ),
) -> None:
    """List recent runs."""
    from autoteam.storage import RunStore

    store = RunStore(runs_dir)
    runs = store.list_runs(limit=limit)

    if not runs:
        console.print("No runs found")
        return

    console.print(f"[bold]Recent runs ({len(runs)}):[/bold]")
    for run_id in runs:
        run_state = store.load_run(run_id)
        if run_state:
            status_color = {
                "ready": "blue",
                "running": "yellow",
                "done": "green",
                "blocked": "orange",
                "failed": "red",
            }.get(run_state.status, "white")

            console.print(
                f"  {run_id} [{status_color}]{run_state.status}[/{status_color}] "
                f"- {run_state.requirement[:50]}..."
            )
        else:
            console.print(f"  {run_id} [dim](metadata not found)[/dim]")


@app.command()
def show(
    run_id: str = typer.Argument(..., help="Run ID to show"),
    runs_dir: Path = typer.Option(
        Path("runs"),
        "--runs-dir",
        "-r",
        help="Directory containing run data",
    ),
) -> None:
    """Show details of a specific run."""
    from autoteam.storage import RunStore

    store = RunStore(runs_dir)
    run_state = store.load_run(run_id)

    if not run_state:
        console.print(f"[red]Run not found: {run_id}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Run: {run_state.run_id}[/bold]")
    console.print(f"Status: {run_state.status}")
    console.print(f"Requirement: {run_state.requirement}")
    console.print(f"Started: {run_state.started_at}")
    console.print(f"Finished: {run_state.finished_at or 'N/A'}")
    console.print(f"Loops: {run_state.loop_count}")
    console.print(f"Steps: {run_state.current_step}")
    console.print(f"Workers: {len(run_state.workers)}")
    console.print(f"Decisions: {len(run_state.decisions)}")


@app.command()
def version() -> None:
    """Show version information."""
    from autoteam import __version__

    console.print(f"AutoTeam v{__version__}")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
