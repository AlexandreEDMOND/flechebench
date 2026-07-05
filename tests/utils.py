from flechebench.data import Direction, Entry, Puzzle


def make_sample_puzzle() -> Puzzle:
    return Puzzle(
        puzzle_id="sample-001",
        width=4,
        height=4,
        entries=[
            Entry(
                entry_id="e1",
                clue="Petit felin domestique",
                answer="CHAT",
                start_row=0,
                start_column=0,
                direction=Direction.ACROSS,
                length=4,
            ),
            Entry(
                entry_id="e2",
                clue="Personne proche",
                answer="AMI",
                start_row=0,
                start_column=2,
                direction=Direction.DOWN,
                length=3,
            ),
        ],
        blocked_cells={(3, 3)},
        metadata={"source": "test"},
    )
