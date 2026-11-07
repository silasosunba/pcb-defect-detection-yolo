"""Transparent class-based review guidance; not a trained severity classifier."""

GUIDANCE = {
    "short": (
        "critical",
        "Copper may connect conductors that should be separate.",
        "Verify the affected nets against the design and check electrical isolation before qualified rework.",
    ),
    "open_circuit": (
        "critical",
        "A conductive trace may have a gap.",
        "Inspect the trace and verify continuity against the circuit design before qualified repair.",
    ),
    "missing_hole": (
        "critical",
        "An expected hole appears absent or obstructed.",
        "Compare with the fabrication drawing and inspect the pad or via before deciding whether repair is possible.",
    ),
    "mouse_bite": (
        "minor",
        "A notch may remove copper from the edge of a trace or pad.",
        "Check the remaining conductor width against the design tolerance and inspect under magnification.",
    ),
    "spur": (
        "minor",
        "An extra copper projection may extend from a conductor.",
        "Check clearance to nearby conductors and refer any required removal to a qualified technician.",
    ),
    "spurious_copper": (
        "minor",
        "An isolated copper fragment may be present outside the intended pattern.",
        "Compare with the board layout and check whether the fragment affects electrical clearance.",
    ),
    "pin_hole": (
        "minor",
        "A small void may interrupt an otherwise continuous copper region.",
        "Inspect the copper area and verify conductor width and continuity against the board specification.",
    ),
}


def assess(detections):

    results = []

    for detection in detections:

        priority, explanation, recommendation = GUIDANCE.get(
            detection["label"],
            (
                "review",
                "Review this predicted region.",
                "Compare this region with the approved board specification.",
            ),
        )
        results.append(
            {
                **detection,
                "review_priority": priority,
                "explanation": explanation,
                "recommendation": recommendation,
            }
        )

    return results
