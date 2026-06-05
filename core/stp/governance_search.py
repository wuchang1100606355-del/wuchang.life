from collections import deque

from core.stp.governance_rules import RULES


def find_path(
    symbol,
    start,
    end
):

    if start == end:
        return [start]

    queue = deque()

    queue.append(
        (
            start,
            [start]
        )
    )

    visited = set()

    while queue:

        current, path = queue.popleft()

        if current == end:
            return path

        if current in visited:
            continue

        visited.add(current)

        for nxt in RULES.get(
            symbol,
            {}
        ).get(
            current,
            []
        ):

            queue.append(
                (
                    nxt,
                    path + [nxt]
                )
            )

    return None
