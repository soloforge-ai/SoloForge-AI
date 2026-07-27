"""
SoloForge AI
MiniBoss Engine V2

Grade Calculator
"""


def calculate_grade(score):
    """
    Convert score into grade.
    """

    if score >= 90:
        return "A"

    if score >= 75:
        return "B"

    if score >= 60:
        return "C"

    if score >= 40:
        return "D"

    return "E"