"""AutoTeam CLI entry point."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

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
    workflow: str = typer.Option(
        "review",
        "--workflow",
        "-w",
        help="Workflow to run (review, analysis)",
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
    from autoteam.config import load_config
    from autoteam.workflows import ReviewWorkflow, WorkflowState

    console.print(Panel.fit(
        f"[bold blue]AutoTeam[/bold blue] v0.1.0\n"
        f"Workflow: {workflow}\n"
        f"Task: {requirement[:100]}...",
        title="Starting",
    ))

    if dry_run:
        console.print("[yellow]Dry run mode - no actions will be taken[/yellow]")
        _show_dry_run_plan(workflow, requirement)
        return

    # Load config
    cfg = load_config(config)
    cfg.guardrails.max_rounds = max_rounds

    # Run workflow
    wf = ReviewWorkflow(config=cfg)

    async def run_async():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running workflow...", total=None)

            result = await wf.execute(requirement)

            progress.update(task, description=f"Completed: {result.state.value}")

        return result

    try:
        result = asyncio.run(run_async())

        # Display results
        status_color = {
            WorkflowState.COMPLETED: "green",
            WorkflowState.FAILED: "red",
            WorkflowState.PAUSED: "yellow",
        }.get(result.state, "white")

        console.print(f"\n[bold]Run ID:[/bold] {result.run_id}")
        console.print(f"[bold]Status:[/bold] [{status_color}]{result.state.value}[/{status_color}]")
        console.print(f"[bold]Rounds:[/bold] {result.current_round}")
        console.print(f"[bold]Steps:[/bold] {len(result.steps)}")

        if result.error:
            console.print(f"[bold red]Error:[/bold red] {result.error}")

        if result.final_result:
            console.print(Panel(
                result.final_result[:2000],
                title="Result",
                border_style="green" if result.state == WorkflowState.COMPLETED else "yellow",
            ))

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


def _show_dry_run_plan(workflow: str, requirement: str) -> None:
    """Show what would happen in a dry run."""
    console.print("\n[bold]Execution Plan:[/bold]")
    console.print("1. Load configuration")
    console.print("2. Initialize adapters (Claude, Copilot)")
    console.print("3. Initialize Judge (DeepSeek)")
    console.print("4. Execute workflow:")
    console.print("   └─ Round 1:")
    console.print("      ├─ Claude: Analyze task")
    console.print("      ├─ Judge: Evaluate Claude output")
    console.print("      ├─ Copilot: Review analysis")
    console.print("      └─ Judge: Decide continue/stop")
    console.print("5. Store results")


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
        run_data = store.load_run(run_id)
        if run_data:
            state = run_data.get("state", "unknown")
            status_color = {
                "completed": "green",
                "running": "yellow",
                "failed": "red",
                "paused": "orange",
            }.get(state, "white")

            task = run_data.get("task", "")[:50]
            console.print(
                f"  {run_id} [{status_color}]{state}[/{status_color}] - {task}..."
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
    run_data = store.load_run(run_id)

    if not run_data:
        console.print(f"[red]Run not found: {run_id}[/red]")
        raise typer.Exit(1)

    console.print(Panel.fit(
        f"[bold]Run ID:[/bold] {run_id}\n"
        f"[bold]Workflow:[/bold] {run_data.get('workflow_name', 'unknown')}\n"
        f"[bold]State:[/bold] {run_data.get('state', 'unknown')}\n"
        f"[bold]Rounds:[/bold] {run_data.get('current_round', 0)}\n"
        f"[bold]Steps:[/bold] {len(run_data.get('steps', []))}\n"
        f"[bold]Started:[/bold] {run_data.get('started_at', 'N/A')}\n"
        f"[bold]Completed:[/bold] {run_data.get('completed_at', 'N/A')}",
        title=f"Run {run_id}",
    ))

    # Show steps
    steps = run_data.get("steps", [])
    if steps:
        console.print("\n[bold]Steps:[/bold]")
        for step in steps:
            status = step.get("result_status", "unknown")
            color = "green" if status == "succeeded" else "red" if status == "failed" else "yellow"
            console.print(
                f"  {step['step_number']}. {step['worker_id']} [{color}]{status}[/{color}]"
            )
            if step.get("result_summary"):
                console.print(f"     {step['result_summary'][:80]}...")

    # Show final result
    final = run_data.get("final_result")
    if final:
        console.print(Panel(final[:1000], title="Final Result"))

    # Show error
    error = run_data.get("error")
    if error:
        console.print(f"\n[bold red]Error:[/bold red] {error}")


@app.command()
def health() -> None:
    """Check health of all components."""
    import asyncio
    from autoteam.adapters import ClaudeAdapter, CopilotAdapter

    console.print("[bold]Health Check[/bold]\n")

    async def check_all():
        # Check Claude
        try:
            claude = ClaudeAdapter()
            healthy = await claude.health_check()
            console.print(f"Claude CLI: {'[green]OK[/green]' if healthy else '[red]NOT FOUND[/red]'}")
        except Exception as e:
            console.print(f"Claude CLI: [red]ERROR[/red] - {e}")

        # Check Copilot
        try:
            copilot = CopilotAdapter()
            healthy = await copilot.health_check()
            console.print(f"Copilot CLI: {'[green]OK[/green]' if healthy else '[red]NOT FOUND[/red]'}")
        except Exception as e:
            console.print(f"Copilot CLI: [red]ERROR[/red] - {e}")

        # Check DeepSeek
        try:
            from autoteam.policy import JudgeAdapter
            judge = JudgeAdapter.create_with_deepseek()
            healthy, msg = await judge.health_check()
            console.print(f"DeepSeek API: {'[green]OK[/green]' if healthy else '[red]ERROR[/red]'} - {msg}")
        except Exception as e:
            console.print(f"DeepSeek API: [red]ERROR[/red] - {e}")

    asyncio.run(check_all())


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
