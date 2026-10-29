#!/usr/bin/env python3
"""Export an ESPN fantasy football league to league.json for the League Ledger page.

Setup:   pip install espn_api
Public:  python export_espn_league.py --league-id 123456 --year 2026
Private: python export_espn_league.py --league-id 123456 --year 2026 --espn-s2 "..." --swid "{...}"

Find espn_s2 and SWID in your browser: espn.com > developer tools > Application > Cookies.
"""
import argparse
import json
from datetime import datetime, timezone

from espn_api.football import League

STATUS = {"OUT": "OUT", "INJURY_RESERVE": "IR", "DOUBTFUL": "D", "QUESTIONABLE": "Q"}


def owner_name(team):
    owners = getattr(team, "owners", None) or []
    if owners and isinstance(owners[0], dict):
        first = owners[0].get("firstName", "")
        last = owners[0].get("lastName", "")
        return f"{first} {last}".strip() or "Unknown"
    return "Unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--league-id", type=int, required=True)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--espn-s2")
    ap.add_argument("--swid")
    ap.add_argument("--out", default="league.json")
    a = ap.parse_args()

    lg = League(league_id=a.league_id, year=a.year, espn_s2=a.espn_s2, swid=a.swid)
    week = lg.current_week
    reg_weeks = lg.settings.reg_season_count
    played = max(0, min(week, reg_weeks + 1) - 1)

    teams, schedule, players = [], [], []
    for t in lg.teams:
        teams.append({
            "id": t.team_id,
            "name": t.team_name,
            "owner": owner_name(t),
            "wins": t.wins,
            "losses": t.losses,
            "ties": t.ties,
            "pf": round(t.points_for, 1),
            "pa": round(t.points_against, 1),
            "scores": [round(s, 1) for s in t.scores[:played]],
        })
        # Remaining regular-season games, listed once per pairing.
        for i, opp in enumerate(t.schedule):
            wk = i + 1
            if wk >= week and wk <= reg_weeks and t.team_id < opp.team_id:
                schedule.append({"week": wk, "home": t.team_id, "away": opp.team_id})
        for p in t.roster:
            players.append({
                "name": p.name,
                "pos": p.position,
                "nfl": p.proTeam,
                "team": t.team_id,
                "pts": round(p.total_points, 1),
                "avg": round(p.avg_points, 1),
                "status": STATUS.get(p.injuryStatus, ""),
                "note": "" if p.injuryStatus in (None, "ACTIVE") else p.injuryStatus.replace("_", " ").title(),
            })

    data = {
        "league": {
            "name": lg.settings.name,
            "season": a.year,
            "week": week,
            "regSeasonWeeks": reg_weeks,
            "playoffTeams": lg.settings.playoff_team_count,
            "updated": datetime.now(timezone.utc).isoformat(),
        },
        "teams": teams,
        "schedule": schedule,
        "players": players,
    }
    with open(a.out, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {a.out}: {len(teams)} teams, {len(players)} players, {len(schedule)} games left.")


if __name__ == "__main__":
    main()
