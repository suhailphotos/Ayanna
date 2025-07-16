from tabulate import tabulate

def render_table(rows, *, headers="keys", full=False, head=False, head_n=20):
    if head:
        rows = rows[:head_n]
    table = tabulate(rows, headers=headers, tablefmt="github", stralign="left")
    if not full and not head:
        table += f"\n\n(Use --head for first {head_n} rows, --full for no truncation.)"
    return table
