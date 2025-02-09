# Archive Warrior Leaderboard [![PyPI - Version](https://img.shields.io/pypi/v/warriors-leaderboard)](https://pypi.org/project/warriors-leaderboard/)

A python CLI tool to list rank of [Archive Warriors](https://wiki.archiveteam.org/index.php/ArchiveTeam_Warrior)

<img width="466" alt="image" src="https://github.com/user-attachments/assets/3f0d6088-4f8e-47f9-9f45-d4b735b69564" />

([Command line for this](#sample-image-command-line))

# Install

## Via pip

```shell
pip install warriors-leaderboard
```

## Via [brew](https://brew.sh/)/pipx

If you don't have [`pipx`](https://github.com/pypa/pipx):

```shell
brew install pipx
pipx ensurepath
```

Restart terminal, then:

```shell
pipx install warriors-leaderboard
```

# Run

```shell
warriors <project> [<user(s)>] [--top count] [--bottom count] [--surround count]
```

Full usage available under `--help`:

```
Usage: warriors [OPTIONS] PROJECT [USERS]...

  Shows leaderboard for given Archive Warrior project, focussing on supplied
  users or ranks

Options:
  -t, --top TEXT               Include these many from the top of the ranking
  -b, --bottom TEXT            Include these many from the bottom of the
                               ranking
  -s, --surround TEXT          Include these many either side of each supplied
                               user
  -r, --rank TEXT              Include this rank, or inclusive range of ranks
                               using a..b format, e.g. -r10..20
  --no-totals                  Hide the totals row
  --no-speed                   Hide speed column and do not show rank changes
  -l, --live                   Show and update the table in real time, ctrl+c
                               to exit
  -p, --poll-time TEXT         Live mode: Refresh rate in seconds, default 60
  -c, --average-count TEXT     Live mode: Number of refreshes to calculate
                               speed and compare ranks over, default 60
  -j, --json-record-path TEXT  Save every response under this path, latest
                               used when resuming a live view.Potentially
                               useful for a future playback mode.
  --help                       Show this message and exit.

```

With only a project specified you get the top 10 users:
```
% warriors telegram
                   telegram                   
┏━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Rank ┃ User        ┃      Bytes ┃    Items ┃
┡━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━┩
│    1 │ fuzzy80211  │ 513.13 TiB │   2.79 G │
│    2 │ igloo22225  │ 183.59 TiB │ 917.25 M │
│    3 │ fionera     │ 181.88 TiB │ 636.09 M │
│    4 │ DLoader     │ 154.84 TiB │   1.06 G │
│    5 │ Nothing4You │ 104.87 TiB │ 460.27 M │
│    6 │ T31M        │  96.87 TiB │ 368.98 M │
│    7 │ Sluggs      │  76.79 TiB │ 205.35 M │
│    8 │ datechnoman │  69.84 TiB │ 234.03 M │
│    9 │ nstrom      │  36.51 TiB │ 209.52 M │
│   10 │ chrismeller │  34.65 TiB │  91.96 M │
└──────┴─────────────┴────────────┴──────────┘
```

Or you can list a number of users after the project:

```
% warriors usgovernment kiwi breadbrix
              usgovernment               
┏━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Rank ┃ User      ┃    Bytes ┃   Items ┃
┡━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│   14 │ breadbrix │ 4.38 TiB │ 10.88 M │
├──────┼───────────┼──────────┼─────────┤
│   17 │ kiwi      │ 3.73 TiB │  9.11 M │
└──────┴───────────┴──────────┴─────────┘
```

To include top or bottom ranks, use `-t` or `-b`:

```
% warriors usgovernment kiwi -t5 -b1
                  usgovernment                  
┏━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Rank ┃ User           ┃     Bytes ┃    Items ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━┩
│    1 │ filesdotdog    │ 83.37 TiB │ 170.05 M │
│    2 │ datechnoman    │ 52.74 TiB │  83.02 M │
│    3 │ fuzzy80211     │ 26.04 TiB │  58.39 M │
│    4 │ nstrom         │ 14.85 TiB │  29.44 M │
│    5 │ paarklicks     │ 13.41 TiB │   29.4 M │
├──────┼────────────────┼───────────┼──────────┤
│   17 │ kiwi           │  3.72 TiB │   9.11 M │
├──────┼────────────────┼───────────┼──────────┤
│ 1893 │ atomicbunnies2 │ 10.26 kiB │        2 │
└──────┴────────────────┴───────────┴──────────┘
```

To lookaround the specified user(s), use `-sN`. e.g. to list the 3 above and below `kiwi`:

```
% warriors usgovernment kiwi -s3    
                usgovernment                 
┏━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Rank ┃ User          ┃    Bytes ┃   Items ┃
┡━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│   14 │ breadbrix     │ 4.38 TiB │ 10.87 M │
│   15 │ katia         │  4.1 TiB │ 10.58 M │
│   16 │ Sluggs        │ 3.91 TiB │  7.32 M │
│   17 │ kiwi          │ 3.72 TiB │  9.11 M │
│   18 │ xxdesmus      │ 3.61 TiB │  6.81 M │
│   19 │ DigitalDragon │ 3.37 TiB │  7.34 M │
│   20 │ meisnick      │ 3.27 TiB │  6.53 M │
└──────┴───────────────┴──────────┴─────────┘
```

## Styling

When specifying a user, you can specify a [rich](https://rich.readthedocs.io/en/stable/style.html) style.

For a list of colors, see https://rich.readthedocs.io/en/stable/appendix/colors.html#appendix-colors

If the style contains "on" then it applies to the whole row. Speed and Rank text foreground colors will not be replaced.

Examples:

`alan:red` - Highlight user `alan` in red.
`alan:"red bold"` - Highlight user `alan` in red with bold.
`alan:"red bold on yellow"` - Highlight user `alan` in red with bold on a yellow background, and apply to whole row.

## Development

1. Clone repo.
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it.

Then run:

```shell
uv run warrior_rank.py <options as decripted above>
```

## Sample image command line

The sample image was taken while running:

```shell
warriors telegram red5:"red1 bold on grey19" blue2:"deep_sky_blue1 bold on grey23" --top 10 --bottom 1 --surround 5 --live
```
