class GovernanceNode:

    def __init__(
        self,
        coordinate
    ):

        self.coordinate = tuple(
            coordinate
        )

    def __hash__(self):

        return hash(
            self.coordinate
        )

    def __eq__(
        self,
        other
    ):

        return (
            self.coordinate
            ==
            other.coordinate
        )

    def __repr__(self):

        return (
            f"Node{self.coordinate}"
        )
