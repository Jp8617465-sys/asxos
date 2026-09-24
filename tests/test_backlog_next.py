"""``asxos.backlog`` — the deterministic pre-gate for the ``backlog-roll`` lane.

Two layers, both pinned:

1. Selection logic on a small fixture: ranking, dependency gating, the derived
   denied-path eligibility, overlap skipping, the click-list, and the exit codes.
2. Drift against the real boundary. The 2026-09-10 version parsed the guard hooks and
   went with them; the replacement at the bottom of this file PINS the denied set
   member-for-member against ``AGENTS.md``, because the boundary now lives in prose and
   cannot be derived.

Also asserts the checked-in seed parses and picks exactly what the current denied set
allows — so the next real fire is predictable.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from asxos.backlog import (
    DEFAULT_BACKLOG,
    DENIED_FILES,
    DENIED_PREFIXES,
    BacklogSchemaError,
    click_list,
    is_denied_path,
    main,
    parse,
    paths_overlap,
    pick,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _doc(items: list[dict]) -> dict:
    return {"version": 1, "updated": "2026-09-05", "items": items}


def _row(
    id: str,
    *,
    owner: str = "arbi",
    status: str = "open",
    route: str = "build",
    depends_on: list[str] | None = None,
    paths: list[str] | None = None,
) -> dict:
    return {
        "id": id,
        "title": f"item {id}",
        "phase": id[0],
        "owner": owner,
        "status": status,
        "depends_on": depends_on or [],
        "route": route,
        "paths": paths if paths is not None else [f"docs/proposals/{id}.md"],
        "source": "fixture",
    }


# --- denied paths --------------------------------------------------------------------


class TestDeniedPaths:
    @pytest.mark.parametrize(
        "path",
        [
            # AGENTS.md section 2: James's, by intent.
            "docs/product/north-star.md",
            ".env",
            "asxos/capital/broker.py",
            # AGENTS.md section 2 final paragraph / section 8: arbi's own permissions.
            ".claude/settings.json",
            ".claude/hooks/secrets-guard.sh",
            ".claude/rules/portfolio-conventions.md",
            # The lane's real permission surface, which is not under .claude/.
            ".github/runner/claude-user-settings.json",
            # Operational: AGENTS.md section 8's one-sitting apply sequence.
            "migrations/0055_x.sql",
        ],
    )
    def test_guarded_paths_are_denied(self, path: str) -> None:
        assert is_denied_path(path)

    @pytest.mark.parametrize(
        "path",
        [
            "docs/proposals/anything.md",
            "tests/test_backup_script.py",
            "asxos/backlog.py",
            "asxos/domain/decision_engine/builder.py",
            "docs/product/roadmap-state.md",
            "docs/product/backlog.yaml",
            # Newly allowed 2026-09-14. AGENTS.md section 14 gives arbi these
            # explicitly: "arbi amends this file, CLAUDE.md, .github/** and every other
            # authority doc by PR and merges them like anything else." The old entries
            # encoded the retired unattended fence, not the current boundary.
            "AGENTS.md",
            "CLAUDE.md",
            ".github/workflows/full-check.yml",
            "docs/product/memory/project-facts.md",
            "docs/product/memory/lessons.md",
            # Amber domain code (AGENTS.md section 6), reviewed by the conformance
            # agents — never section 2, so never the picker's to refuse.
            "asxos/domain/tax/positions.py",
            "asxos/domain/portfolio/allocator.py",
            "asxos/domain/theses/service.py",
        ],
    )
    def test_ordinary_paths_are_allowed(self, path: str) -> None:
        assert not is_denied_path(path)

    def test_a_directory_containing_a_guarded_file_is_denied(self) -> None:
        # Coarse globs cannot launder a guarded file.
        assert is_denied_path("docs/product/")  # holds north-star.md
        assert is_denied_path(".claude/")
        assert is_denied_path("asxos/")  # holds asxos/capital/
        assert is_denied_path(".github/runner/")  # holds the lane settings file
        assert is_denied_path("")

    def test_directories_that_no_longer_hold_a_guarded_file_are_allowed(self) -> None:
        """The 2026-09-14 trim's observable effect, pinned so a re-widen is visible.

        ``docs/product/memory/`` and ``asxos/domain/`` were denied only because the old
        set listed files inside them — most of which #254 had already deleted.
        """
        assert not is_denied_path("docs/product/memory/")
        assert not is_denied_path("asxos/domain/")
        assert not is_denied_path(".github/workflows/")

    def test_normalisation(self) -> None:
        assert is_denied_path("./migrations/0001.sql")
        assert is_denied_path("/CLAUDE.md")
        assert not is_denied_path("./docs/proposals/x.md")

    @pytest.mark.parametrize(
        "path",
        [
            "docs/proposals/../product/north-star.md",
            "docs/**",
            "docs/proposals/*.md",
            "docs//proposals/x.md",
            r"docs\proposals\x.md",
            "/docs/proposals/x.md",
        ],
    )
    def test_non_literal_or_non_relative_scopes_fail_closed(self, path: str) -> None:
        assert is_denied_path(path)


class TestOverlap:
    def test_distinct_files_in_one_dir_do_not_overlap(self) -> None:
        assert not paths_overlap(["docs/proposals/a.md"], ["docs/proposals/b.md"])

    def test_same_file_overlaps(self) -> None:
        assert paths_overlap(["docs/proposals/a.md"], ["docs/proposals/a.md"])

    def test_dir_contains_file_overlaps_both_ways(self) -> None:
        assert paths_overlap(["docs/proposals/"], ["docs/proposals/a.md"])
        assert paths_overlap(["docs/proposals/a.md"], ["docs/proposals/"])


# --- schema ---------------------------------------------------------------------------


class TestSchema:
    def test_minimal_valid(self) -> None:
        items = parse(_doc([_row("A-1")]))
        assert [i.id for i in items] == ["A-1"]

    @pytest.mark.parametrize(
        "mutation, fragment",
        [
            (lambda r: r.update(status="shipped"), "status"),
            (lambda r: r.update(owner="bot"), "owner"),
            (lambda r: r.update(route="yolo"), "route"),
            (lambda r: r.update(phase="B"), "disagrees"),
            (lambda r: r.update(extra=1), "unknown keys"),
            (lambda r: r.pop("source"), "missing keys"),
            (lambda r: r.update(depends_on=["Z-9"]), "unknown id"),
            (lambda r: r.update(depends_on=["A-1"]), "itself"),
            (lambda r: r.update(paths="not-a-list"), "list of strings"),
        ],
    )
    def test_rejects(self, mutation, fragment: str) -> None:
        row = _row("A-1")
        mutation(row)
        with pytest.raises(BacklogSchemaError, match=fragment):
            parse(_doc([row]))

    def test_rejects_duplicate_and_bad_ids(self) -> None:
        with pytest.raises(BacklogSchemaError, match="duplicate"):
            parse(_doc([_row("A-1"), _row("A-1")]))
        with pytest.raises(BacklogSchemaError, match="bad id"):
            parse(_doc([_row("F-1")]))

    def test_rejects_wrong_version(self) -> None:
        with pytest.raises(BacklogSchemaError, match="version"):
            parse({"version": 2, "items": [_row("A-1")]})

    def test_rejects_path_traversal_and_dependency_cycles(self) -> None:
        with pytest.raises(BacklogSchemaError, match="literal repo-relative"):
            parse(_doc([_row("A-1", paths=["docs/proposals/../product/north-star.md"])]))
        with pytest.raises(BacklogSchemaError, match="dependency cycle"):
            parse(
                _doc(
                    [
                        _row("A-1", depends_on=["A-2"]),
                        _row("A-2", depends_on=["A-1"]),
                    ]
                )
            )


# --- selection --------------------------------------------------------------------------


class TestSelection:
    def test_ranking_phase_then_dependents_then_id(self) -> None:
        items = parse(
            _doc(
                [
                    _row("B-1"),
                    _row("A-2"),
                    # A-1 has one open dependent (C-1), A-2 has none -> A-1 first.
                    _row("A-1"),
                    _row("C-1", depends_on=["A-1"]),
                ]
            )
        )
        picked, skipped = pick(items, max_items=10)
        assert [i.id for i in picked] == ["A-1", "A-2", "B-1"]
        assert skipped == []

    def test_dependency_gating_treats_unmerged_as_not_done(self) -> None:
        items = parse(
            _doc(
                [
                    _row("A-1", status="built-unmerged"),
                    _row("A-2", status="done"),
                    _row("A-3", status="void"),
                    _row("B-1", depends_on=["A-1"]),  # blocked
                    _row("B-2", depends_on=["A-2"]),  # ok
                    _row("B-3", depends_on=["A-3"]),  # ok (void counts)
                ]
            )
        )
        picked, _ = pick(items, max_items=10)
        assert [i.id for i in picked] == ["B-2", "B-3"]

    def test_only_arbi_or_both_with_buildable_route(self) -> None:
        items = parse(
            _doc(
                [
                    _row("A-1", owner="james", route="james"),
                    _row("A-2", owner="both", route="observe"),
                    _row("A-3", owner="arbi", route="attended"),
                    _row("A-4", owner="time", route="observe"),
                    _row("A-5", owner="both", route="mission"),
                    _row("A-6", owner="arbi", route="build"),
                ]
            )
        )
        picked, _ = pick(items, max_items=10)
        assert [i.id for i in picked] == ["A-5", "A-6"]

    def test_denied_path_is_never_picked_even_when_open_and_owned(self) -> None:
        items = parse(
            _doc(
                [
                    _row("A-1", paths=["docs/product/north-star.md"]),
                    _row("A-2", paths=[".claude/skills/x/SKILL.md"]),
                    _row("A-3", paths=["docs/proposals/ok.md", "migrations/0099.sql"]),
                    _row("A-4", paths=[]),  # no paths => nothing to build
                    _row("A-5", paths=["docs/proposals/ok.md"]),
                ]
            )
        )
        picked, _ = pick(items, max_items=10)
        assert [i.id for i in picked] == ["A-5"]

    def test_overlap_skips_the_later_pick_this_fire(self) -> None:
        items = parse(
            _doc(
                [
                    _row("A-1", paths=["docs/proposals/x.md"]),
                    _row("A-2", paths=["docs/proposals/"]),  # contains A-1's file
                    _row("A-3", paths=["tests/test_x.py"]),
                ]
            )
        )
        picked, skipped = pick(items, max_items=10)
        assert [i.id for i in picked] == ["A-1", "A-3"]
        assert [i.id for i in skipped] == ["A-2"]

    def test_max_items_caps(self) -> None:
        items = parse(_doc([_row("A-1"), _row("A-2"), _row("A-3")]))
        picked, _ = pick(items, max_items=2)
        assert [i.id for i in picked] == ["A-1", "A-2"]

    def test_click_list_includes_james_routes_and_built_unmerged_work(self) -> None:
        items = parse(
            _doc(
                [
                    _row("A-1", owner="james", route="james"),
                    _row("A-2", owner="james", route="james", depends_on=["A-1"]),
                    _row("A-3", owner="both", route="james"),
                    _row("A-4", owner="james", route="james", status="done"),
                    _row("A-5", owner="james", route="james", status="built-unmerged"),
                    _row("A-6", owner="arbi", route="build", status="built-unmerged"),
                ]
            )
        )
        assert [i.id for i in click_list(items)] == ["A-1", "A-3", "A-5", "A-6"]


# --- CLI + exit codes -------------------------------------------------------------------


class TestCli:
    def _write(self, tmp_path: Path, items: list[dict]) -> Path:
        p = tmp_path / "backlog.yaml"
        p.write_text(yaml.safe_dump(_doc(items), sort_keys=False), encoding="utf-8")
        return p

    def test_exit_0_and_json_shape_when_picked(self, tmp_path: Path, capsys) -> None:
        p = self._write(tmp_path, [_row("A-1"), _row("B-1", owner="james", route="james")])
        assert main(["--backlog", str(p)]) == 0
        out = json.loads(capsys.readouterr().out)
        assert {
            "generated",
            "backlog_updated",
            "eligible",
            "picked",
            "skipped_overlap",
            "click_list",
        } <= out.keys()
        assert [i["id"] for i in out["picked"]] == ["A-1"]
        assert [i["id"] for i in out["click_list"]] == ["B-1"]

    def test_exit_3_when_nothing_eligible_but_click_list_still_emitted(
        self, tmp_path: Path, capsys
    ) -> None:
        p = self._write(tmp_path, [_row("A-1", owner="james", route="james")])
        assert main(["--backlog", str(p)]) == 3
        out = json.loads(capsys.readouterr().out)
        assert out["picked"] == []
        assert [i["id"] for i in out["click_list"]] == ["A-1"]

    def test_exit_2_on_schema_error(self, tmp_path: Path, capsys) -> None:
        p = self._write(tmp_path, [_row("A-1", status="nope")])
        assert main(["--backlog", str(p)]) == 2
        assert "schema error" in capsys.readouterr().err

    def test_exit_2_on_missing_file(self, tmp_path: Path) -> None:
        assert main(["--backlog", str(tmp_path / "missing.yaml")]) == 2

    @pytest.mark.parametrize("value", ["0", "-1", "4"])
    def test_exit_2_when_max_is_outside_bounded_lane_limit(
        self, tmp_path: Path, capsys, value: str
    ) -> None:
        p = self._write(tmp_path, [_row("A-1")])
        assert main(["--backlog", str(p), "--max", value]) == 2
        assert "--max must be between 1 and 3" in capsys.readouterr().err


# --- the checked-in seed ---------------------------------------------------------------


class TestSeed:
    def test_seed_parses(self) -> None:
        items = __import__("asxos.backlog", fromlist=["load"]).load(DEFAULT_BACKLOG)
        assert len(items) >= 60
        # The seed must not declare anything eligible that the guard would deny.
        # Re-pinned 2026-09-14: E-11 used to be the deliberate negative example
        # (".github/workflows/full-check.yml", denied by the retired unattended fence).
        # AGENTS.md section 14 gives arbi ".github/**" outright, so it is now an
        # ordinary buildable row and there is no denied-but-eligible row left in the
        # seed. If one is added, it should be denied for a section 2 reason, not a
        # fence reason.
        for it in items:
            if (
                it.owner in {"arbi", "both"}
                and it.route in {"build", "mission"}
                and it.status == "open"
            ):
                assert not any(is_denied_path(p) for p in it.paths), it.id

    def test_ids_rank_numerically_not_lexically(self) -> None:
        items = parse(
            _doc(
                [
                    _row("B-10", owner="james", route="james"),
                    _row("B-5", owner="james", route="james"),
                    _row("B-13a", owner="james", route="james"),
                    _row("B-13", owner="james", route="james"),
                ]
            )
        )
        assert [i.id for i in click_list(items)] == ["B-5", "B-10", "B-13", "B-13a"]

    def test_seed_after_the_denied_set_trim_has_a_pick(self) -> None:
        """Re-pinned 2026-09-14, and the rename is the point.

        Every prior pin of this test asserted ``picked == []`` — the ``backlog-roll``
        lane had nothing it was allowed to build. That was never a property of the
        backlog; it was the denied set still encoding the retired unattended fence,
        which excluded ``.github/**``, ``migrations/**`` and most of ``asxos/`` — i.e.
        most of what ``AGENTS.md`` says is arbi's. Trimming the set to section 2 plus
        the two things a fire cannot mechanically finish turns E-11 into the lane's
        first real pick.

        Prior pins, for the diff: 09-05 (after the two proposal drafts landed), 09-06,
        09-14 merge-train (A-24 done via #230, lead click A-20).

        Re-pin deliberately when the seed changes shape again.
        """
        items = __import__("asxos.backlog", fromlist=["load"]).load(DEFAULT_BACKLOG)
        picked, skipped = pick(items, max_items=10)
        # Re-pinned 2026-09-16 by the first daily-product routine fire: E-11 is done
        # (the false claim lived in commit c35d435's message; the file residue was
        # corrected), and three rows were filed — A-34/A-35 (the two dark-launch DELETE
        # verdicts, phase A so they rank first) and E-20 (ingest_regulatory). A-35
        # overlaps A-34 on asxos/brief/compose.py, so the picker skips it for overlap.
        # Re-pinned 2026-09-17 by the attended triage: eight rows filed from two
        # proposals that had sat unfiled since 2026-09-16 (A-43..A-48, E-21, E-22).
        # Only E-21 joins the pick list — the rest are route=attended (a migration, a
        # .claude/ handover, or a James ruling), which the lane never picks. That is the
        # shape to expect from a triage: most of it is not lane work.
        # Re-pinned 2026-09-17 by the selection & ideation mission: five rows filed
        # (E-23..E-27). The PICKED list is deliberately unchanged — the whole mission
        # added zero new unattended lane work, which is the shape to expect from a
        # research mission. E-23 is route=attended because the backlog guard denied it
        # as a mission row: it names migrations/, and AGENTS.md §8's five-step sequence
        # must run in one sitting, which a fire cannot do. E-24 is blocked on E-23.
        # E-25 is parked, encoding James's "leave it, note it" ruling — filed open with
        # route=build it is one-file lane work and the picker WOULD have built it.
        # E-26 is a .claude/ handover. Only E-27 reaches the lane at all, and it is
        # skipped for overlap: its `tests/` path collides with an already-picked row.
        # Re-pinned 2026-09-19 by the daily-product fire that BUILT A-34 (dark-launch
        # DELETE verdict #1). A-34 -> done drops out and A-35 takes its place at the
        # head — the verdict-#3 deletion that had been skipped for overlap with A-34
        # all along, since the two share tests/test_brief_outcome.py. The tail is
        # unchanged, which is the shape to expect when a lane finishes a row rather
        # than filing one.
        # Re-pinned 2026-09-20 by the daily-product fire that BUILT A-35 (dark-launch
        # DELETE verdict #3). Same shape as the A-34 -> A-35 move the night before:
        # the built row drops out, and the row that was only ever skipped for
        # overlapping it takes the head. A-51 collided with A-35 on tests/.
        assert [i.id for i in picked] == ["A-51", "E-20", "E-21"], [i.id for i in picked]
        # A-35 left this list on 2026-09-19: it was only ever here because it overlapped
        # A-34, and A-34 is built. E-27 still overlaps on tests/.
        # Re-pinned 2026-09-19 by the capability-audit session: six rows filed
        # (A-49..A-52, E-28, E-29). PICKED is deliberately unchanged — A-49 and A-50 are
        # `done` (built in that session), A-52 and E-29 are route=attended, and the two
        # that reach the lane at all are both skipped for overlap: A-51 collides with
        # A-35 on tests/, and E-28 with E-21 on docs/proposals/. A session that
        # BUILDS two rows and files four more should move the skipped list and leave the
        # head alone, which is what this asserts.
        #
        # 2026-09-20: A-51 leaves this list by being PROMOTED, not dropped — the fire that
        # built A-35 removed the row it collided with, so it is now the head above. E-28
        # still collides with E-21 on docs/proposals/.
        #
        # 2026-09-21: E-30 JOINS the list, and the reason is a route change rather than a
        # new row. It was filed route=attended on 2026-09-20 (so the lane never saw it) and
        # re-scoped to route=build on 2026-09-21 once opening the code showed the design
        # question had evaporated. It reaches the lane now and is skipped for overlap.
        #
        # 2026-09-24: E-30 LEAVES the list by being BUILT (#369), not by being dropped —
        # it closes the half of #327 that #366's own fix created. Note the head is
        # unchanged, and that is the honest shape here rather than an oversight: this
        # fire's pick came from gate (b) (an open `incident` issue outranks the picker)
        # and from gate (d).1 (the carried PR #368), so the picker's own head was never
        # reached. A fire that builds a skipped-for-overlap row while leaving the head
        # alone should move this list only.
        assert [i.id for i in skipped] == ["E-27", "E-28"], [i.id for i in skipped]
        clicks = [i.id for i in click_list(items)]
        assert clicks[0] == "A-20", clicks
        assert "A-24" not in clicks  # done 2026-09-14: #230 retired issue-snapshot.yml
        assert "A-0" not in clicks  # discharged 2026-09-05
        assert "B-13a" not in clicks and "B-14a" not in clicks  # merged in #200
        assert "E-11" not in clicks  # arbi-owned and now buildable: a pick, not a click
        assert "E-17" not in clicks  # attended, arbi-owned: neither a pick nor a click


# --- drift against the real boundary ----------------------------------------------------
#
# ``TestDeniedSetMirrorsTheGuards`` was removed on 2026-09-10 with the guard hooks it
# parsed (``unattended-guard.sh`` and the old 33-entry settings deny array). Its note said
# a replacement belonged with the trim, not before it. The trim landed 2026-09-14; this is
# the replacement.
#
# What it can and cannot prove. The boundary now lives in prose (``AGENTS.md``), not in a
# machine-readable fence, so no test can derive the denied set automatically. What these
# tests do instead is PIN it: the set is asserted member-for-member, so widening or
# narrowing it is a visible, deliberate line in a diff rather than a silent drift — which
# is exactly how 17 dead entries accumulated unnoticed between #254 and 2026-09-14. The
# direction that matters is NARROWING: a pre-gate narrower than the real boundary starts
# work the lane can never finish.


class TestDeniedSetIsPinnedToTheAuthority:
    def test_the_denied_set_is_exactly_what_agents_md_reserves(self) -> None:
        """Change this pin only alongside the AGENTS.md line that justifies the change."""
        assert DENIED_FILES == frozenset(
            {
                "docs/product/north-star.md",  # section 2.1
                ".env",  # section 13
                ".github/runner/claude-user-settings.json",  # the lane's permission surface
            }
        )
        assert DENIED_PREFIXES == (
            ".claude/",  # section 2 final paragraph / section 8
            "asxos/capital/",  # section 2.2
            "migrations/",  # section 8's one-sitting apply sequence
        )

    def test_agents_md_still_reserves_the_paths_this_set_rests_on(self) -> None:
        """If a future amendment un-reserves these, this set is wrong and must move too.

        Substring checks on the load-bearing clauses, not on whole sentences: the wording
        gets edited, the reservation is what must survive.
        """
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        assert "`.claude/` — arbi drafts, James merges" in agents
        assert "`asxos/capital/`" in agents
        assert "north-star.md" in agents

    def test_capital_stays_empty(self) -> None:
        """AGENTS.md section 2.2: the directory stays empty until James decides otherwise.

        Denying the prefix is only meaningful while nothing has quietly appeared under it.
        """
        capital = REPO_ROOT / "asxos" / "capital"
        assert not capital.exists() or not any(capital.iterdir())
