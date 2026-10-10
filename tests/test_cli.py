"""Unit tests for ParaDecomp Typer CLI commands."""

from typer.testing import CliRunner

from paradecomp.cli.main import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "ParaDecomp" in result.stdout


def test_cli_analyze():
    result = runner.invoke(app, ["analyze", "-t", "0.60"])
    assert result.exit_code == 0
    assert "Pairwise Subtask Orthogonality Matrix" in result.stdout
    assert "Mean Orthogonality" in result.stdout


def test_cli_research():
    result = runner.invoke(app, ["research", "-f", "3", "-n", "10"])
    assert result.exit_code == 0
    assert "Total Sources Gathered" in result.stdout
    assert "30" in result.stdout


def test_cli_benchmark():
    result = runner.invoke(app, ["benchmark", "-n", "5", "-s", "20"])
    assert result.exit_code == 0
    assert "Multi-Agent Decomposition Benchmark" in result.stdout
    assert "ParaDecomp" in result.stdout
    assert "100" in result.stdout
