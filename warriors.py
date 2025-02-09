import glob
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cached_property
from pathlib import Path
from typing import Tuple, Optional

import click
import requests
from rich import print as rprint
from rich.layout import Layout
from rich.live import Live
from rich.table import Table


@click.command()
@click.argument("project")
@click.argument("users", nargs=-1)
@click.option("--top", "-t", default="0", help="Include these many from the top of the ranking")
@click.option("--bottom", "-b", default="0", help="Include these many from the bottom of the ranking")
@click.option("--surround", "-s", default="0", help="Include these many either side of each supplied user")
@click.option("include_ranks", "--rank", "-r", multiple=True,
              help="Include this rank, or inclusive range of ranks using a..b format, e.g. -r10..20")
@click.option("--no-totals", is_flag=True, help="Hide the totals row")
@click.option("--no-speed", is_flag=True, help="Hide speed column and do not show rank changes")
@click.option("--live", "-l", is_flag=True, help="Show and update the table in real time, ctrl+c to exit")
@click.option("--poll-time", "-p", default="60", help="Live mode: Refresh rate in seconds, default 60")
@click.option("--average-count", "-c", default="60",
              help="Live mode: Number of refreshes to calculate speed and compare ranks over, default 60")
@click.option("--json-record-path", "-j", default="",
              help="Save every response under this path, latest used when resuming a live view."
                   "Potentially useful for a future playback mode.")
def leaderboard(project: str,
                top,
                bottom,
                surround,
                include_ranks,
                no_totals: bool,
                no_speed: bool,
                live: bool,
                poll_time,
                average_count,
                json_record_path,
                users: Tuple[str]):
    """Shows leaderboard for given Archive Warrior project, focussing on supplied users or ranks"""
    top = int(top)
    bottom = int(bottom)
    surround = int(surround)
    poll_time = int(poll_time)
    include_ranks = _parse_ranks(include_ranks)

    if not users and not top and not bottom:
        top = 10

    users_and_style = list(_parse_users(users))
    users_style = dict(users_and_style)
    users = [user for user, style in users_and_style]

    past_ranking = []
    last_ranking_limit = int(average_count)

    ranking_fetch = RankingFetch(
        project=project,
        results_save_path=Path(json_record_path) if json_record_path else None,
    )

    if not no_speed:
        # Load latest file
        file_project_stats_json_and_timestamp = ranking_fetch.get_latest_saved()
        if file_project_stats_json_and_timestamp:
            past_ranking.append(
                ranking_fetch.filter(
                    file_project_stats_json_and_timestamp[0],
                    timestamp=file_project_stats_json_and_timestamp[1],
                    users=users,
                    surround=surround,
                    top=top,
                    bottom=bottom,
                    include_ranks=include_ranks,
                )
            )

    def new_table(*, exit_on_fail: bool) -> Optional[Table]:
        try:
            project_stats_json, timestamp = ranking_fetch.get_from_url(exit_on_fail=exit_on_fail)
        except Exception:
            return None
        ranking = ranking_fetch.filter(
            project_stats_json,
            timestamp=timestamp,
            users=users,
            surround=surround,
            top=top,
            bottom=bottom,
            include_ranks=include_ranks,
        )
        ranking_table = _create_ranking_table(
            ranking,
            past_ranking=past_ranking[0] if past_ranking else None,
            show_total_row=not no_totals,
            user_style=users_style,
        )
        if not no_speed:
            past_ranking.append(ranking)
            if len(past_ranking) > last_ranking_limit:
                past_ranking.pop(0)
        return ranking_table

    if live:
        layout = Layout()
        layout.update("[yellow]Starting...")
        with Live(layout, auto_refresh=False) as live:
            while True:
                table = new_table(exit_on_fail=False)
                if table:
                    layout.update(table)
                    live.refresh()
                time.sleep(poll_time)
    else:
        rprint(new_table(exit_on_fail=True))


@dataclass
class UserStats:
    name: str
    rank: int
    bytes: int
    items: int
    supplied: bool


@dataclass()
class Ranks:
    project: str
    timestamp: datetime
    users: [UserStats]

    @cached_property
    def total_bytes(self):
        return sum([u.bytes for u in self.users])

    @cached_property
    def total_items(self):
        return sum([u.items for u in self.users])

    @cached_property
    def user_dictionary(self):
        return dict([(u.name, u) for u in self.users])

    def speed(self, past_ranking, *, name: Optional[str] = None) -> Optional[float]:
        """Bytes/second"""
        delta_time = self.timestamp - past_ranking.timestamp
        if not name:
            delta_bytes = self.total_bytes - past_ranking.total_bytes
        else:
            last_stats = past_ranking.user_dictionary.get(name)
            if not last_stats:
                return None
            delta_bytes = self.user_dictionary[name].bytes - last_stats.bytes
        return delta_bytes / delta_time.total_seconds()

    def rank_change(self, name: str, past_ranking) -> Optional[int]:
        """A positive represents a new lower rank, i.e. an improvement"""
        last_stats = past_ranking.user_dictionary.get(name)
        if not last_stats:
            return None
        return last_stats.rank - self.user_dictionary[name].rank


def _create_ranking_table(
        ranking: Ranks,
        *,
        past_ranking: Optional[Ranks] = None,
        show_total_row: bool = True,
        user_style=None,
) -> Table:
    if user_style is None:
        user_style = {}

    if past_ranking:

        def _human_readable_timedelta(delta: timedelta):
            if delta.total_seconds() < 120:
                return f"{int(delta.total_seconds())} seconds"
            else:
                return f"{int(round(delta.total_seconds() / 60, 0))} minutes"

        delta_description = f" [yellow]△ {_human_readable_timedelta(ranking.timestamp - past_ranking.timestamp)}[/]"
    else:
        delta_description = ""
    table = Table(title=f"[cyan]{ranking.project}[/] {ranking.timestamp}{delta_description}")
    table.add_column("Rank", justify="right")
    table.add_column("User")
    table.add_column("Bytes", justify="right")
    table.add_column("Items", justify="right")
    if past_ranking:
        table.add_column("Speed", justify="right")

    last_rank = 1
    for user_stats in ranking.users:
        if user_stats.rank != last_rank + 1:
            table.add_section()
        last_rank = user_stats.rank
        rank_style = "default"
        rank_movement = ""
        if past_ranking:
            rank_movement = "•"
            rank_change = ranking.rank_change(user_stats.name, past_ranking)
            if rank_change:
                if rank_change > 0:
                    rank_movement = "↑"
                    rank_style = "green"
                else:
                    rank_movement = "↓"
                    rank_style = "red"
        style = user_style.get(user_stats.name, "cyan")
        row_style = "default"
        # If the user style contains "on", then we apply to the whole row
        if "on" in style:
            row_style = style
        row = [
            f"[{rank_style}]{user_stats.rank} {rank_movement}[/]",
            f"[{style}]{user_stats.name}[/]",
            _human_readable_bytes(user_stats.bytes),
            _human_readable_count(user_stats.items),
        ]
        if past_ranking:
            speed_bytes_per_second = ranking.speed(past_ranking, name=user_stats.name)
            if speed_bytes_per_second:
                row.append(_format_speed_to_str(speed_bytes_per_second))
            else:
                row.append("")
        table.add_row(*row, style=row_style)

    if show_total_row:
        table.add_section()
        row = [
            "",
            "[cyan]Total[/]",
            _human_readable_bytes(ranking.total_bytes),
            _human_readable_count(ranking.total_items),
        ]
        if past_ranking:
            row.append(_format_speed_to_str(ranking.speed(past_ranking)))
        table.add_row(*row)

    return table


def _format_speed_to_str(speed_bytes_per_second: Optional[float]):
    if speed_bytes_per_second:
        speed_bytes = int(speed_bytes_per_second * 3600)
        style = "green" if speed_bytes >= 1024 * 1024 * 1024 else "default"
        return f"[{style}]{_human_readable_bytes(speed_bytes)}/h[/]"
    else:
        return ""


class RankingFetch:
    def __init__(self,
                 project: str,
                 results_save_path: Optional[Path] = None,
                 ):
        self.project = project
        self.url = f"https://legacy-api.arpa.li/{project}/stats.json"
        self.results_save_path = Path(results_save_path, self.project) if results_save_path else None

    def get_from_url(self, exit_on_fail: bool):
        timestamp = datetime.now().replace(microsecond=0)
        result = requests.get(self.url)
        if result.status_code == 404:
            rprint(f"[red]Project [cyan]{self.project}[/] not found.[/] The first param should be the project.")
            exit(1)
        if result.status_code != 200:
            if exit_on_fail:
                rprint(f"[red]Failed to get {self.url} with {result.status_code}")
                exit(1)
            raise Exception()
        if self.results_save_path:
            self.results_save_path.mkdir(exist_ok=True, parents=True)
            file_name_stem = timestamp.isoformat().replace(":", "-")
            with open(Path(self.results_save_path, f"{file_name_stem}.json"),
                      "w") as f:
                f.write(result.text)
        project_stats_json = result.json()
        return project_stats_json, timestamp

    def get_latest_saved(self):
        if not self.results_save_path or not self.results_save_path.exists():
            return None
        list_of_files = glob.glob(
            os.path.join(self.results_save_path, '*.json'))  # * means all if need specific format then *.csv
        if not list_of_files:
            return None
        latest_file = Path(max(list_of_files, key=os.path.getctime))
        try:
            with open(latest_file) as f:
                return json.load(f), datetime.fromisoformat(
                    latest_file.stem.replace("-", ":").replace(":", "-", 2)
                )
        except Exception as e:
            rprint(f"[yellow]Unable to load [cyan]{latest_file}[/] {e}")
            return None

    def filter(self,
               project_stats_json,
               *,
               timestamp: datetime,
               bottom: int = 0,
               surround: int = 0,
               top: int = 0,
               users=None,
               include_ranks=None,
               ) -> Ranks:
        users = set(users or [])
        include_rank_indexes = set([i - 1 for i in include_ranks] or [])
        ranking = list(enumerate(sorted(project_stats_json["downloader_bytes"].items(), key=lambda e: -e[1])))
        include_after_idx = len(ranking) - bottom
        if surround > 0:
            for r in [rank_index for rank_index, (user, b) in ranking if user in users]:
                for i in range(r - surround, r + surround + 1):
                    include_rank_indexes.add(i)
        ranking = [r for r in ranking if
                   r[1][0] in users or r[0] < top or r[0] >= include_after_idx or r[0] in include_rank_indexes]

        return Ranks(
            project=self.project,
            timestamp=timestamp,
            users=[UserStats(
                name=user,
                rank=rank_index + 1,
                bytes=b,
                items=project_stats_json["downloader_count"][user],
                supplied=user in users,
            ) for rank_index, (user, b) in ranking],
        )


def _human_readable_bytes(b: int, *, digits: int = 2):
    unit = ["B", "kiB", "MiB", "GiB", "TiB", "PiB"]
    ui = 0
    while b >= 1024:
        b /= 1024
        ui += 1
    return f"{round(b, ndigits=digits)} {unit[ui]}"


def _human_readable_count(count, *, base_unit=""):
    unit = ["", "k", "M", "G", "T", "P"]
    ui = 0
    while count >= 1000:
        count /= 1000
        ui += 1
    return f"{round(count, ndigits=2)} {unit[ui]}{base_unit}"


def _parse_ranks(include_ranks: [str]):
    """Parses text ranks in formats a|a..b|a-b"""
    ranks = []
    rank_pattern = re.compile(r"(\d+)(?:\.\.|-)?(\d+)?")
    for r in include_ranks:
        m = rank_pattern.fullmatch(r)
        if not m:
            rprint(f"[red]Bad rank option:[/] {r}")
            exit(1)
        from_rank = int(m.group(1))
        if not m.group(2):
            ranks.append(from_rank)
        else:
            to_rank = int(m.group(2))
            if to_rank < from_rank:
                rprint(f"[red]Bad rank option, range is backwards:[/] {r}")
                exit(1)
            rprint(f"{from_rank}..{to_rank}")
            ranks += range(from_rank, to_rank + 1)
    return ranks


def _parse_users(users):
    """Extract style from users"""
    for u in users:
        split = u.split(":", maxsplit=2)
        if len(split) == 1:
            yield u, "green bold"
        else:
            yield split[0], split[1]


if __name__ == "__main__":
    leaderboard()
