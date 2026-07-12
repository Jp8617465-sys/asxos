"""
asx — Typer CLI entrypoint.

Commands added per BUILD_GUIDE milestone:
  M6  — `asx predict <date>`
  M7+ — `asx signal`, `asx tax-view`, `asx journal`, ...
"""
from __future__ import annotations

import typer

from asxos.cli.agent_run import agent_run_app
from asxos.cli.brief import brief
from asxos.cli.holdings import import_holdings
from asxos.cli.journal import journal_app
from asxos.cli.macro_thesis import macro_thesis_app
from asxos.cli.model import model_app
from asxos.cli.news import news_app
from asxos.cli.portfolio import build_portfolio, portfolio_app, propose_trades
from asxos.cli.position import position_app
from asxos.cli.predict import predict
from asxos.cli.profile import profile_app
from asxos.cli.screen import screen_app
from asxos.cli.signal import signal
from asxos.cli.tax import tax_action, tax_view
from asxos.cli.theme import theme_app
from asxos.cli.thesis import thesis_app

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def _main() -> None:
    """asx — asxos CLI."""


app.command()(predict)
app.command()(signal)
app.command("import-holdings")(import_holdings)
app.command("tax-view")(tax_view)
app.command("tax-action")(tax_action)
app.command("brief")(brief)
app.command("build-portfolio")(build_portfolio)
app.command("propose-trades")(propose_trades)

app.add_typer(model_app, name="model")
app.add_typer(journal_app, name="journal")
app.add_typer(profile_app, name="profile")
app.add_typer(news_app, name="news")
app.add_typer(portfolio_app, name="portfolio")
app.add_typer(position_app, name="position")
app.add_typer(thesis_app, name="thesis")
app.add_typer(theme_app, name="theme")
app.add_typer(macro_thesis_app, name="macro-thesis")
app.add_typer(agent_run_app, name="agent-run")
app.add_typer(screen_app, name="screen")


if __name__ == "__main__":  # pragma: no cover
    app()
