from tabulate import tabulate

def render(rows, *, headers="keys", head=False, head_n=20):
    if head:
        rows = rows[:head_n]
    return tabulate(
        rows,
        headers=headers,
        tablefmt="github",
        stralign="left",
    )
