import typer, json
from . import prompts, model
from .config import DEFAULT_DCC

app = typer.Typer(help="DCC LLM assistant CLI")

@app.command()
def chat(
    dcc: str = typer.Option(DEFAULT_DCC, help="Houdini | Blender | Maya …"),
):
    messages = [prompts.system_prompt(dcc)]
    typer.echo("Type 'exit' to quit.\n")

    while True:
        user = typer.prompt("You")
        if user.lower() == "exit":
            break
        messages.append({"role": "user", "content": user})
        answer = model.chat(messages)
        messages.append({"role": "assistant", "content": answer})
        typer.echo(f"\nAssistant:\n{answer}\n")

@app.command()
def system(dcc: str = DEFAULT_DCC):
    """Print the raw system-prompt JSON (for Open WebUI import)."""
    typer.echo(json.dumps(prompts.system_prompt(dcc), indent=2))

if __name__ == "__main__":
    app()
